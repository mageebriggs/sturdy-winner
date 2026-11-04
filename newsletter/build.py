"""Build the daily XRP / crypto / macro brief.

Writes <out>/index.html (the web page) and <out>/sms.txt (the short text).
Standard library only, so the workflow needs no pip install.

    python newsletter/build.py --out site --url https://example.github.io/repo/
    python newsletter/build.py --out site --url ... --offline tests/fixtures
"""
from __future__ import annotations

import argparse
import email.utils
import html
import json
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import feeds  # noqa: E402

CENTRAL = ZoneInfo("America/Chicago")
UA = "daily-crypto-brief/1.0 (+https://github.com)"
ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass
class Item:
    title: str
    link: str
    source: str
    published: datetime | None
    summary: str = ""

    @property
    def text(self) -> str:
        return f"{self.title} {self.summary}".lower()


# ---------- fetching ----------

def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)  # RFC 822 (RSS)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))  # ISO 8601 (Atom)
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def parse_feed(data: bytes, source: str) -> list[Item]:
    root = ET.fromstring(data)
    items: list[Item] = []
    for el in root.iter("item"):  # RSS 2.0
        title = _strip_tags(el.findtext("title", ""))
        src = el.find("source")
        label = src.text.strip() if src is not None and src.text else source
        # Google News appends " - Publisher" to titles; drop it since we show the source.
        if src is not None and src.text and title.endswith(" - " + src.text.strip()):
            title = title[: -len(" - " + src.text.strip())]
        items.append(Item(
            title=title,
            link=(el.findtext("link") or "").strip(),
            source=label,
            published=_parse_date(el.findtext("pubDate")),
            summary=_strip_tags(el.findtext("description", ""))[:300],
        ))
    for el in root.iter(f"{ATOM}entry"):  # Atom
        link_el = el.find(f"{ATOM}link[@rel='alternate']")
        if link_el is None:  # Elements with no children are falsy, so no `or` here
            link_el = el.find(f"{ATOM}link")
        items.append(Item(
            title=_strip_tags(el.findtext(f"{ATOM}title", "")),
            link=link_el.get("href", "") if link_el is not None else "",
            source=source,
            published=_parse_date(el.findtext(f"{ATOM}published") or el.findtext(f"{ATOM}updated")),
            summary=_strip_tags(el.findtext(f"{ATOM}summary", ""))[:300],
        ))
    return [i for i in items if i.title and i.link]


def load_feed(label: str, url: str, offline: Path | None) -> list[Item]:
    try:
        if offline:
            f = offline / f"{_slug(label)}.xml"
            if not f.exists():
                return []
            data = f.read_bytes()
        else:
            data = fetch(url)
        return parse_feed(data, label)
    except Exception as e:  # one bad source must not kill the brief
        print(f"warn: {label}: {e}", file=sys.stderr)
        return []


def load_json(url: str, offline: Path | None, name: str) -> dict | None:
    try:
        if offline:
            f = offline / f"{name}.json"
            return json.loads(f.read_text()) if f.exists() else None
        return json.loads(fetch(url))
    except Exception as e:
        print(f"warn: {name}: {e}", file=sys.stderr)
        return None


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---------- selecting ----------

def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", t.lower())[:80]


def matches(item: Item, keywords: list[str]) -> bool:
    t = f" {item.text} "
    return any(k in t for k in keywords)


def select(items: list[Item], now: datetime) -> dict[str, list[Item]]:
    cutoff = now - timedelta(hours=feeds.LOOKBACK_HOURS)
    fresh = [i for i in items if i.published is None or i.published >= cutoff]
    fresh.sort(key=lambda i: i.published or cutoff, reverse=True)

    seen: set[str] = set()
    out: dict[str, list[Item]] = {"xrp": [], "macro": [], "crypto": []}
    for i in fresh:
        key = _norm_title(i.title)
        if key in seen:
            continue
        if matches(i, feeds.XRP_KEYWORDS):
            bucket = "xrp"
        elif matches(i, feeds.MACRO_KEYWORDS):
            bucket = "macro"
        elif i.source in {lbl for lbl, _ in feeds.MACRO_FEEDS}:
            continue  # off-topic item from a macro feed (e.g. a bank enforcement notice)
        else:
            bucket = "crypto"
        if len(out[bucket]) < feeds.MAX_PER_SECTION[bucket]:
            out[bucket].append(i)
            seen.add(key)
    return out


# ---------- rendering ----------

def fmt_price(p: float) -> str:
    return f"${p:,.4f}" if p < 1 else f"${p:,.2f}" if p < 1000 else f"${p:,.0f}"


def fmt_change(c: float | None) -> str:
    return "n/a" if c is None else f"{c:+.1f}%"


def ascii_only(s: str) -> str:
    """SMS: any non-GSM character (emoji, curly quote) cuts a segment from 160 to 70 chars."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def build_sms(prices: dict | None, sections: dict[str, list[Item]], url: str, date_str: str) -> str:
    lines = [f"Crypto brief {date_str}"]
    if prices and "ripple" in prices:
        x = prices["ripple"]
        line = f"XRP {fmt_price(x['usd'])} ({fmt_change(x.get('usd_24h_change'))})"
        if "bitcoin" in prices:
            b = prices["bitcoin"]
            line += f" | BTC {fmt_price(b['usd'])} ({fmt_change(b.get('usd_24h_change'))})"
        lines.append(line)
    top = (sections["xrp"] or sections["macro"] or sections["crypto"] or [None])[0]
    if top:
        t = top.title if len(top.title) <= 90 else top.title[:87].rstrip() + "..."
        lines.append(f"Top: {t}")
    lines.append(url)
    return ascii_only("\n".join(lines))


SECTION_TITLES = {
    "xrp": "XRP &amp; Ripple",
    "macro": "Macro &amp; policy",
    "crypto": "Rest of crypto",
}


def _time_label(d: datetime | None) -> str:
    if not d:
        return ""
    return d.astimezone(CENTRAL).strftime("%b %-d, %-I:%M %p CT")


def render_html(prices: dict | None, fng: dict | None, sections: dict[str, list[Item]],
                now: datetime) -> str:
    e = html.escape
    local = now.astimezone(CENTRAL)

    tiles = []
    names = [("ripple", "XRP"), ("bitcoin", "BTC"), ("ethereum", "ETH")]
    for cid, sym in names:
        if prices and cid in prices:
            p = prices[cid]
            ch = p.get("usd_24h_change")
            cls = "up" if (ch or 0) >= 0 else "down"
            tiles.append(
                f'<div class="tile"><div class="sym">{sym}</div>'
                f'<div class="px">{fmt_price(p["usd"])}</div>'
                f'<div class="ch {cls}">{fmt_change(ch)} 24h</div></div>'
            )
    if fng and fng.get("data"):
        d = fng["data"][0]
        tiles.append(
            f'<div class="tile"><div class="sym">Fear &amp; Greed</div>'
            f'<div class="px">{e(str(d.get("value", "?")))}</div>'
            f'<div class="ch">{e(str(d.get("value_classification", "")))}</div></div>'
        )
    tiles_html = "".join(tiles) or '<p class="muted">Prices unavailable this morning.</p>'

    body = []
    for key in ("xrp", "macro", "crypto"):
        rows = sections[key]
        body.append(f"<section><h2>{SECTION_TITLES[key]}</h2>")
        if not rows:
            body.append('<p class="muted">Nothing new in the last day.</p>')
        else:
            body.append("<ul>")
            for i in rows:
                body.append(
                    f'<li><a href="{e(i.link)}" target="_blank" rel="noopener">{e(i.title)}</a>'
                    f'<div class="meta">{e(i.source)}'
                    f'{" &middot; " + _time_label(i.published) if i.published else ""}</div></li>'
                )
            body.append("</ul>")
        body.append("</section>")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Crypto Brief</title>
<style>
:root {{ --bg:#f7f7f5; --card:#fff; --fg:#1a1a1a; --muted:#6b6b6b; --line:#e4e4e0;
        --accent:#1f5fbf; --up:#1a7f37; --down:#c62828; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#121212; --card:#1c1c1c; --fg:#ececec; --muted:#9a9a9a; --line:#2c2c2c;
          --accent:#7aa7ff; --up:#4ccf6a; --down:#ff6b6b; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg);
       font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:680px; margin:0 auto; padding:20px 16px 48px; }}
h1 {{ font-size:1.5rem; margin:0; }}
.date {{ color:var(--muted); margin:2px 0 18px; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; }}
.tile {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px; }}
.sym {{ font-size:.8rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }}
.px {{ font-size:1.3rem; font-weight:600; font-variant-numeric:tabular-nums; }}
.ch {{ font-size:.9rem; color:var(--muted); }} .up {{ color:var(--up); }} .down {{ color:var(--down); }}
h2 {{ font-size:1.1rem; margin:28px 0 8px; padding-bottom:6px; border-bottom:1px solid var(--line); }}
ul {{ list-style:none; padding:0; margin:0; }}
li {{ padding:10px 0; border-bottom:1px solid var(--line); }}
a {{ color:var(--accent); text-decoration:none; }} a:hover {{ text-decoration:underline; }}
.meta, .muted {{ color:var(--muted); font-size:.85rem; }}
footer {{ margin-top:32px; color:var(--muted); font-size:.8rem; }}
</style>
</head>
<body>
<main>
<h1>Daily Crypto Brief</h1>
<p class="date">{local.strftime("%A, %B %-d, %Y")} &middot; built {local.strftime("%-I:%M %p")} CT</p>
<div class="tiles">{tiles_html}</div>
{"".join(body)}
<footer>Headlines are pulled automatically from public RSS feeds and filtered by keyword;
nothing here is investment advice. Prices: CoinGecko. Sentiment: alternative.me.</footer>
</main>
</body>
</html>
"""


# ---------- main ----------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--url", required=True, help="public URL of the page, used in the text")
    ap.add_argument("--offline", type=Path, help="read feeds from fixture files instead of the network")
    ap.add_argument("--now", help="ISO timestamp to treat as now (testing)")
    a = ap.parse_args(argv)

    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc)
    items: list[Item] = []
    for label, url in feeds.CRYPTO_FEEDS + feeds.MACRO_FEEDS:
        got = load_feed(label, url, a.offline)
        print(f"{label}: {len(got)} items", file=sys.stderr)
        items += got

    prices = load_json(feeds.PRICE_URL, a.offline, "prices")
    fng = load_json(feeds.FEAR_GREED_URL, a.offline, "fng")
    sections = select(items, now)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render_html(prices, fng, sections, now), encoding="utf-8")
    date_str = now.astimezone(CENTRAL).strftime("%a %b %-d")
    # Date in the query string so the phone doesn't show yesterday's cached page.
    link = f"{a.url.rstrip('/')}/?d={now.astimezone(CENTRAL):%Y%m%d}"
    sms = build_sms(prices, sections, link, date_str)
    (out / "sms.txt").write_text(sms, encoding="utf-8")
    (out / ".nojekyll").write_text("")

    total = sum(len(v) for v in sections.values())
    print(f"sections: { {k: len(v) for k, v in sections.items()} }", file=sys.stderr)
    print(sms)
    if total == 0 and prices is None:
        print("error: every source failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
