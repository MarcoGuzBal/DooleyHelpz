"""
DooleyHelpz MVP – Step 3: Course Recommendations
"""

import argparse
import os
import json
import math
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


def norm(val, lo, hi, invert=False):
    if val is None:
        return 0
    v = max(lo, min(hi, float(val)))
    x = (v - lo) / (hi - lo) if hi > lo else 0
    return 1 - x if invert else x


def score_course(doc, w_rating, w_again, w_easy, w_pop):
    rmp = doc.get("rmp") or {}
    rating = norm(rmp.get("rating"), 0, 5)
    again = norm(rmp.get("would_take_again_%"), 0, 100)
    easy = norm(rmp.get("difficulty"), 1, 5, invert=True)
    num = rmp.get("num_ratings") or 0
    pop = math.log1p(num) / math.log1p(100)
    return (w_rating * rating) + (w_again * again) + (w_easy * easy) + (w_pop * pop)


def run(uri, top):
    client = MongoClient(uri)
    db = client["DetailedCourses"]
    try:
        source = list(db["CoursesQualified"].find({}))
    except PyMongoError:
        with open("out/courses_qualified.json") as f:
            source = json.load(f)

    weights = [0.55, 0.15, 0.15, 0.15]
    ranked = []
    for d in source:
        s = score_course(d, *weights)
        ranked.append({**d, "score": s})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    ranked = ranked[:top]

    try:
        col_out = db["Recommended"]
        col_out.delete_many({})
        col_out.insert_many(ranked)
        print(f"Wrote {len(ranked)} recommendations → Mongo.")
    except PyMongoError as e:
        print(f"[WARN] Mongo write failed: {e}")

    Path("out").mkdir(exist_ok=True)
    with open("out/recommended.json", "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2)
    print("Saved backup JSON → out/recommended.json")

    for d in ranked[:10]:
        r = d.get("rmp", {})
        print(f"{d.get('code')} | {d.get('professor')} | RMP {r.get('rating')} | Score {d['score']:.2f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    run(args.uri, args.top)


if __name__ == "__main__":
    main()
