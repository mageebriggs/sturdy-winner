"""Sources and keyword rules for the daily brief.

Every source is optional: if one is down or changes format, the build skips it
and keeps going. Edit these lists to change what the brief covers.
"""

# (label, url) — RSS 2.0 or Atom feeds.
CRYPTO_FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("Google News: XRP", "https://news.google.com/rss/search?q=XRP+OR+Ripple+OR+XRPL+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: Crypto policy", "https://news.google.com/rss/search?q=crypto+(SEC+OR+CFTC+OR+stablecoin+OR+ETF+OR+Congress)+when:1d&hl=en-US&gl=US&ceid=US:en"),
]

MACRO_FEEDS = [
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("Google News: Macro", "https://news.google.com/rss/search?q=(Fed+OR+FOMC+OR+CPI+OR+inflation+OR+%22jobs+report%22+OR+Treasury+yields)+when:1d&hl=en-US&gl=US&ceid=US:en"),
]

PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=ripple,bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
)
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"

# Lower-case substrings. Matching is on title + summary.
XRP_KEYWORDS = ["xrp", "ripple", "xrpl", "rlusd", "garlinghouse"]

MACRO_KEYWORDS = [
    "fed ", "federal reserve", "fomc", "rate cut", "rate hike", "interest rate",
    "inflation", "cpi", "pce", "jobs report", "payroll", "unemployment",
    "treasury", "yield", "dollar index", "dxy", "recession", "gdp", "tariff",
    "sec ", "cftc", "stablecoin", "etf", "regulation", "congress", "senate",
    "market structure", "clarity act", "genius act",
]

MAX_PER_SECTION = {"xrp": 8, "macro": 8, "crypto": 8}
LOOKBACK_HOURS = 30
