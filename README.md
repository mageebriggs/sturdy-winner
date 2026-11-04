# Daily Crypto Brief

Every morning at about 7:00 AM Central, a GitHub Actions job:

1. Pulls XRP/Ripple, crypto and macro headlines from public RSS feeds, plus XRP/BTC/ETH prices (CoinGecko) and the Fear & Greed index.
2. Publishes them as a web page on GitHub Pages: `https://mageebriggs.github.io/sturdy-winner/`
3. Texts you a short summary with the link (via Twilio).

No AI summaries and no API keys except Twilio's. Everything runs on the Python standard library.

## One-time setup

### 1. Turn on GitHub Pages
Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.

### 2. Twilio (for the text)
1. Sign up at twilio.com and buy a phone number. A **toll-free** number is usually the quickest to get approved for personal use.
2. US carriers block unregistered texts. Submit **toll-free verification** (or A2P 10DLC registration for a local number) in the Twilio console. Approval can take days.
3. Add these as repo secrets under **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `TWILIO_ACCOUNT_SID` | From the Twilio console (starts with `AC`) |
| `TWILIO_AUTH_TOKEN` | From the Twilio console |
| `TWILIO_FROM` | Your Twilio number, e.g. `+18885551234` |
| `SMS_TO` | Your phone in E.164 format, e.g. `+15125551234` |

Until these exist, the job still publishes the page and just logs the text it would have sent.

### 3. Test it
**Actions → Daily crypto brief → Run workflow.**

## Customising
- Sources and keywords: `newsletter/feeds.py`
- Text format: `build_sms()` in `newsletter/build.py`
- Send time: `TARGET_LOCAL_HOUR` in `newsletter/gate.py`, plus the two cron lines in `.github/workflows/daily-brief.yml`

## Known limits
- GitHub's scheduled runs are often a few to 30+ minutes late. That's why the job is scheduled for 6:45.
- GitHub disables scheduled workflows in public repos after 60 days with no commits. If that happens, re-enable it in the Actions tab.
- Headlines are chosen by keyword matching, so expect some noise and some misses.

## Tests
```
python -m pytest tests
```
