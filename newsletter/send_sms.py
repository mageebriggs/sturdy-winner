"""Send a text through Twilio's REST API (standard library only).

Env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM (your Twilio number),
     SMS_TO (your phone, e.g. +15125550123).
Usage: python newsletter/send_sms.py site/sms.txt
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def main() -> int:
    body = open(sys.argv[1], encoding="utf-8").read().strip()
    need = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM", "SMS_TO"]
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        print(f"SMS skipped: missing secrets {', '.join(missing)}. Page was still published.")
        print("--- would have sent ---\n" + body)
        return 0

    sid, token = os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({
        "To": os.environ["SMS_TO"], "From": os.environ["TWILIO_FROM"], "Body": body,
    }).encode()
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req = urllib.request.Request(url, data=data, headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"Twilio error {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
        return 1
    print(f"Sent: sid={resp.get('sid')} status={resp.get('status')} segments={resp.get('num_segments')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
