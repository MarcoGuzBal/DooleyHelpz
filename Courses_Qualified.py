"""
DooleyHelpz MVP – Step 2: Course Qualification / Filtering
"""

import argparse
import os
import json
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pathlib import Path


def parse_hhmm_to_min(hhmm):
    if not hhmm:
        return None
    parts = hhmm.split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return h * 60 + m


def qualifies(doc, min_rating, method, allowed_days, start_min, end_min):
    if method and (doc.get("instruction_method") or "").lower() != method.lower():
        return False
    rating = (doc.get("rmp") or {}).get("rating") or 0
    if rating < min_rating:
        return False
    meeting = doc.get("meeting") or {}
    days = meeting.get("days") or []
    if allowed_days and not any(d in allowed_days for d in days):
        return False
    st = meeting.get("start_min")
    en = meeting.get("end_min")
    if start_min and (st is None or st < start_min):
        return False
    if end_min and (en is None or en > end_min):
        return False
    return True


def run(uri, min_rating, method, days_csv, start, end):
    allowed_days = [d.strip() for d in (days_csv.split(",") if days_csv else [])]
    start_min = parse_hhmm_to_min(start)
    end_min = parse_hhmm_to_min(end)

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

    qualified = [d for d in source if qualifies(d, min_rating, method, allowed_days, start_min, end_min)]

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
    main()
