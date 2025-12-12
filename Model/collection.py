from pymongo import MongoClient
import os
import json
import sys
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Use MONGODB_URI from .env (do NOT commit credentials). If absent, raise.
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("Missing MONGODB_URI environment variable. Add it to a .env file.")

client = MongoClient(MONGODB_URI)

# Use database named "Collections" (created on first insert) and a collection for course placements.
DB_NAME = "Collections"
COLLECTION_NAME = "course_placements"

db = client[DB_NAME]
col = db[COLLECTION_NAME]


def extract_course_sequence(data):
    """
    Try common shapes for the transcript JSON and return an ordered list of course codes.
    Adjust if your parser output differs.
    """
    if isinstance(data, list):
        return data

    # common keys
    for key in ("courses", "course_list", "transcript", "classes"):
        if key in data and isinstance(data[key], list):
            vals = data[key]
            # if items are dicts, extract likely code fields
            if vals and isinstance(vals[0], dict):
                out = []
                for item in vals:
                    for ck in ("code", "course_code", "course", "id", "subject"):
                        if ck in item:
                            out.append(item[ck])
                            break
                return out
            return vals

    # fallback: find first list of strings or dicts
    for v in data.values():
        if isinstance(v, list):
            if v and isinstance(v[0], dict):
                out = []
                for item in v:
                    for ck in ("code", "course_code", "course", "id", "subject"):
                        if ck in item:
                            out.append(item[ck])
                            break
                if out:
                    return out
            elif v and isinstance(v[0], str):
                return v

    return []

def process_transcript_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    seq = extract_course_sequence(data)
    seq = [normalize_code(c) for c in seq if c and str(c).strip()]

    if not seq:
        print("No course sequence found in JSON:", path)
        return

    for idx, course in enumerate(seq):
        # For each occurrence:
        # - increment placement_count by 1
        # - push the position index into placements array (duplicates allowed; reflects frequency)
        # - set first_seen on insert
        position = idx  # zero-based; change to idx+1 if you want 1-based positions
        col.update_one(
            {"course_code": course},
            {
                "$inc": {"placement_count": 1},
                "$push": {"placements": position},
                "$setOnInsert": {"first_seen": datetime.utcnow()},
                "$currentDate": {"last_updated": True}
            },
            upsert=True
        )

    print(f"Processed {len(seq)} courses from {os.path.basename(path)}")

if __name__ == "__main__":
    # pass JSON path as argument or pick newest .json in cwd
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        json_files = [f for f in os.listdir(os.getcwd()) if f.lower().endswith(".json")]
        if not json_files:
            print("No JSON files found in current directory. Provide a path as the first argument.")
            sys.exit(1)
        json_files_full = [os.path.join(os.getcwd(), f) for f in json_files]
        json_path = max(json_files_full, key=os.path.getmtime)

    process_transcript_json(json_path)