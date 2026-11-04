import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "newsletter"))
import build, gate  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
NOW = "2026-11-04T12:45:00+00:00"


def run(tmp_path):
    assert build.main(["--out", str(tmp_path), "--url", "https://u.github.io/r/",
                       "--offline", str(FIX), "--now", NOW]) == 0
    return (tmp_path / "index.html").read_text(), (tmp_path / "sms.txt").read_text()


def test_sections_dedupe_and_filter(tmp_path):
    page, _ = run(tmp_path)
    assert page.count("RLUSD") == 1                 # cross-source duplicate removed
    assert "XRP ETF inflows hit record" in page     # Google News " - Bloomberg" stripped
    assert "Bloomberg" in page
    assert "FOMC statement" in page                 # macro
    assert "SEC delays decision" in page            # Atom feed parsed, macro keyword
    assert "Example Bank" not in page               # off-topic Fed item dropped
    assert "Old story" not in page                  # outside lookback window


def test_sms_short_and_ascii(tmp_path):
    _, sms = run(tmp_path)
    assert sms.isascii()
    assert len(sms) <= 320, len(sms)                # at most 2 segments
    assert "XRP $2.34 (+3.2%)" in sms
    assert "BTC $104,250 (-1.0%)" in sms
    assert sms.strip().endswith("https://u.github.io/r/?d=20261104")


def test_gate_dst():
    winter = datetime(2026, 11, 4, 12, 45, tzinfo=timezone.utc)   # CST
    summer = datetime(2026, 7, 4, 11, 45, tzinfo=timezone.utc)    # CDT
    assert gate.should_run("schedule", "45 12 * * *", winter)
    assert not gate.should_run("schedule", "45 11 * * *", winter)
    assert gate.should_run("schedule", "45 11 * * *", summer)
    assert not gate.should_run("schedule", "45 12 * * *", summer)
    assert gate.should_run("workflow_dispatch", "", winter)
