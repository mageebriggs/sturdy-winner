"""Decide whether this run should go out, so the text lands ~7am Central all year.

GitHub cron is UTC only and Central shifts between UTC-6 (CST) and UTC-5 (CDT).
The workflow schedules two runs, 11:45 and 12:45 UTC; this lets through only the
one that equals 6:45 local today. Manual runs always go.

Usage: python newsletter/gate.py <event_name> "<cron string>"  -> prints go=true|false
"""
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TARGET_LOCAL_HOUR = 6  # cron minute is :45, so 6:45 CT; GitHub often runs schedules a few minutes late


def should_run(event: str, cron: str, now: datetime) -> bool:
    if event != "schedule":
        return True
    utc_hour = int(cron.split()[1])
    offset_h = int(now.astimezone(ZoneInfo("America/Chicago")).utcoffset().total_seconds() // 3600)
    return (utc_hour + offset_h) % 24 == TARGET_LOCAL_HOUR


if __name__ == "__main__":
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    cron = sys.argv[2] if len(sys.argv) > 2 else ""
    print(f"go={'true' if should_run(event, cron, datetime.now(timezone.utc)) else 'false'}")
