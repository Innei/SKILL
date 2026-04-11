#!/usr/bin/env -S uv run --quiet --with chinesecalendar python
"""Compute working-summary date range with Chinese holiday awareness.

Default range: previous Mon-Sun week.
  Today=Mon        -> [last Mon, yesterday Sun]
  Today=Tue..Sun   -> [prev Mon, prev Sun]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta

try:
    from chinese_calendar import get_holiday_detail, is_holiday, is_workday
    HAS_CC = True
except ImportError:
    HAS_CC = False


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def default_range(today: date) -> tuple[date, date]:
    weekday = today.weekday()  # Mon=0..Sun=6
    this_monday = today - timedelta(days=weekday)
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    return last_monday, last_sunday


def classify_day(d: date) -> dict:
    weekday = d.strftime("%a")
    if HAS_CC:
        try:
            workday = bool(is_workday(d))
            name = None
            if is_holiday(d):
                detail = get_holiday_detail(d)
                if detail:
                    name = detail[1]
            return {"date": d.isoformat(), "weekday": weekday, "workday": workday, "holiday": name}
        except NotImplementedError:
            pass
    return {"date": d.isoformat(), "weekday": weekday, "workday": d.weekday() < 5, "holiday": None}


def classify_range(start: date, end: date) -> list[dict]:
    out = []
    d = start
    while d <= end:
        out.append(classify_day(d))
        d += timedelta(days=1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", help="YYYY-MM-DD")
    ap.add_argument("--to", dest="end", help="YYYY-MM-DD")
    ap.add_argument("--date", help="reference date, default today")
    ap.add_argument("--classify", action="store_true", help="include per-day holiday breakdown")
    args = ap.parse_args()

    today = parse_date(args.date) if args.date else date.today()

    if args.start and args.end:
        start, end = parse_date(args.start), parse_date(args.end)
    elif args.start:
        start, end = parse_date(args.start), today
    else:
        start, end = default_range(today)

    payload: dict = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": (end - start).days + 1,
        "has_holiday_lib": HAS_CC,
    }
    if args.classify:
        breakdown = classify_range(start, end)
        payload["breakdown"] = breakdown
        payload["workdays"] = sum(1 for d in breakdown if d["workday"])
        payload["holidays"] = sum(1 for d in breakdown if d["holiday"])

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
