"""
DooleyHelpz MVP – Step 2: Course Qualification / Filtering
"""

import argparse
import os
import json
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pathlib import Path
import re

from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Read DB_URI from environment
MONGO_URI = os.getenv("DB_URI")

if not MONGO_URI:
    raise RuntimeError("❌ DB_URI is not set in your .env file")


def parse_hhmm_to_min(hhmm):
    if not hhmm:
        return None
    parts = hhmm.split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return h * 60 + m

# --- AM/PM parser reused for questionnaire time strings ---


def _parse_time_component(t):
    """
    Parse '9am', '9:30am', '10:00pm' into minutes since midnight.
    """
    t = t.strip().lower()
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", t)
    if not m:
        return None

    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = m.group(3)

    if hour == 12:
        hour = 0
    if ampm == "pm":
        hour += 12

    return hour * 60 + minute


# --- Day normalization for questionnaire output (Monday–Friday) ---


DAY_MAP = {
    "m": "M", "mon": "M", "monday": "M",
    "t": "T", "tue": "T", "tues": "T", "tuesday": "T",
    "w": "W", "wed": "W", "weds": "W", "wednesday": "W",
    "th": "Th", "thu": "Th", "thur": "Th", "thurs": "Th", "thursday": "Th",
    "f": "F", "fri": "F", "friday": "F",
}


def normalize_day_token(day_str):
    if not day_str:
        return None
    key = str(day_str).strip().lower()
    return DAY_MAP.get(key)


def parse_unavailable_blocks(time_unavailable):
    """
    Input example (from questionnaire -> user_profile.json):

      "time_unavailable": [
        {"days": ["Monday", "Wednesday"], "start": "9:00am", "end": "11:15am"},
        {"days": ["Friday"], "start": "1:00pm", "end": "3:45pm"}
      ]

    Output:

      [
        {"day": "M", "start_min": 540, "end_min": 675},
        {"day": "W", "start_min": 540, "end_min": 675},
        {"day": "F", "start_min": 780, "end_min": 945}
      ]
    """
    blocks = []
    if not time_unavailable:
        return blocks

    for item in time_unavailable:
        if not item:
            continue

        days_field = item.get("days")
        if days_field is None:
            single_day = item.get("day")
            days_field = [single_day] if single_day else []

        start_s = item.get("start")
        end_s = item.get("end")
        if not start_s or not end_s:
            continue

        start_min = _parse_time_component(start_s)
        end_min = _parse_time_component(end_s)
        if start_min is None or end_min is None:
            continue

        for d in days_field:
            token = normalize_day_token(d)
            if not token:
                continue
            blocks.append(
                {
                    "day": token,
                    "start_min": start_min,
                    "end_min": end_min,
                }
            )
    return blocks


def intervals_overlap(a_start, a_end, b_start, b_end):
    """
    True if [a_start, a_end) intersects [b_start, b_end).
    """
    if None in (a_start, a_end, b_start, b_end):
        return False
    return max(a_start, b_start) < min(a_end, b_end)


def course_conflicts_with_unavailable(course_doc, unavailable_blocks):
    """
    course_doc['meeting'] looks like:

      {
        "days": ["M", "W"],
        "start_min": 510,
        "end_min": 585,
        "raw": "MW 8:30am-9:45am"
      }
    """
    if not unavailable_blocks:
        return False

    meeting = course_doc.get("meeting") or {}
    days = meeting.get("days") or []
    start_min = meeting.get("start_min")
    end_min = meeting.get("end_min")

    if start_min is None or end_min is None:
        return False  # you can change this to True if you want to drop unknowns

    for day in days:
        for blk in unavailable_blocks:
            if blk["day"] != day:
                continue
            if intervals_overlap(start_min, end_min, blk["start_min"], blk["end_min"]):
                return True

    return False

def qualifies(doc, min_rating, method, allowed_days, start_min, end_min, unavailable_blocks):
    if method and (doc.get("instruction_method") or "").lower() != method.lower():
        return False

    rating = (doc.get("rmp") or {}).get("rating") or 0
    if rating < min_rating:
        return False

    meeting = doc.get("meeting") or {}
    days = meeting.get("days") or []

    # Filter by preferred days (if user specified allowed days)
    if allowed_days and not any(d in allowed_days for d in days):
        return False

    st = meeting.get("start_min")
    en = meeting.get("end_min")

    # Filter by preferred time window (CLI --start/--end, optional)
    if start_min and (st is None or st < start_min):
        return False
    if end_min and (en is None or en > end_min):
        return False

    # NEW: drop courses that overlap with user's unavailable blocks
    if unavailable_blocks and course_conflicts_with_unavailable(doc, unavailable_blocks):
        return False

    return True



def run(min_rating=0.0, method="avg", days_csv="", start=None, end=None):
    uri = MONGO_URI   # loaded from .env
    allowed_days = [d.strip() for d in (days_csv.split(",") if days_csv else [])]
    start_min = parse_hhmm_to_min(start)
    end_min = parse_hhmm_to_min(end)

    # 🔹 No per-user unavailable blocks here
    unavailable_blocks = []

    client = MongoClient(uri)
    db = client["DetailedCourses"]
    col_in = db["CoursesEnriched"]
    col_out = db["CoursesQualified"]

    try:
        source = list(col_in.find({}))
    except PyMongoError as e:
        print(f"[WARN] DB read failed: {e}")
        with open("out/courses_enriched.json") as f:
            source = json.load(f)

    qualified = [
        d for d in source
        if qualifies(d, min_rating, method, allowed_days, start_min, end_min, unavailable_blocks)
    ]

    try:
        col_out.delete_many({})
        if qualified:
            col_out.insert_many(qualified)
            print(f"Wrote {len(qualified)} qualified courses → Mongo.")
    except PyMongoError as e:
        print(f"[WARN] Mongo write failed: {e}")

    Path("out").mkdir(exist_ok=True)
    with open("out/courses_qualified.json", "w", encoding="utf-8") as f:
        json.dump(qualified, f, indent=2)
    print("Saved backup JSON → out/courses_qualified.json")



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--min_rating", type=float, default=0)
    parser.add_argument("--method", type=str, default=None)
    parser.add_argument("--days", type=str, default=None)
    parser.add_argument("--start", type=str, default=None)
    parser.add_argument("--end", type=str, default=None)
    args = parser.parse_args()

    run(args.uri, args.min_rating, args.method, args.days, args.start, args.end)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate courses_qualified.json using MongoDB and local constraints."
    )

    parser.add_argument("--min_rating", type=float, default=0.0,
                        help="Minimum professor rating required")
    parser.add_argument("--method", type=str, default="avg",
                        help="Rating method (avg, median, etc.)")
    parser.add_argument("--days", type=str, default="",
                        help="Comma-separated list of allowed days (optional)")
    parser.add_argument("--start", type=str, default=None,
                        help="Start time (optional)")
    parser.add_argument("--end", type=str, default=None,
                        help="End time (optional)")

    args = parser.parse_args()

    # -------- CALL UPDATED run() --------
    run(
        min_rating=args.min_rating,
        method=args.method,
        days_csv=args.days,
        start=args.start,
        end=args.end,
    )

