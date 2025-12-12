"""
DooleyHelpz – Per-Student Course Qualification (Synthetic Version)

Uses:
  - synthetic_pref.json
  - synthetic_courses.json
  - DetailedCourses.CoursesEnriched
  - track_graduation.track_grad

Outputs:
  out/courses_qualified_<shared_id>.json
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Set
import re
from bson import ObjectId

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

from track_graduation import track_grad

# -------------------------------------------------------------------
# Load synthetic data
# -------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(__file__)
SYNTHETIC_COURSES_PATH = os.path.join(SCRIPT_DIR, "synthetic_courses.json")
SYNTHETIC_PREF_PATH    = os.path.join(SCRIPT_DIR, "synthetic_pref.json")

with open(SYNTHETIC_COURSES_PATH, "r", encoding="utf-8") as f:
    _synthetic_courses_list = json.load(f)

with open(SYNTHETIC_PREF_PATH, "r", encoding="utf-8") as f:
    _synthetic_pref_list = json.load(f)

SYN_COURSES_BY_ID = {str(rec["shared_id"]): rec for rec in _synthetic_courses_list}
SYN_PREF_BY_ID    = {str(rec["shared_id"]): rec for rec in _synthetic_pref_list}

# -------------------------------------------------------------------
# Mongo setup
# -------------------------------------------------------------------

load_dotenv()
DB_URI = os.getenv("DB_URI")
if not DB_URI:
    raise RuntimeError("❌ DB_URI is not set in your .env file")

client = MongoClient(DB_URI)
DB_DETAILED = client["DetailedCourses"]
COL_ENRICHED = DB_DETAILED["CoursesEnriched"]
COL_DETAILED = DB_DETAILED["DetailedCourses"]

# -------------------------------------------------------------------
# Time parsing helpers
# -------------------------------------------------------------------

DAY_MAP = {
    "m": "M", "mon": "M", "monday": "M",
    "t": "T", "tue": "T", "tues": "T", "tuesday": "T",
    "w": "W", "wed": "W", "weds": "W", "wednesday": "W",
    "th": "Th", "thu": "Th", "thur": "Th", "thurs": "Th", "thursday": "Th",
    "f": "F", "fri": "F", "friday": "F",
}

def _parse_time_component(t: str):
    if not t:
        return None
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

def normalize_day_token(day_str: str):
    if not day_str:
        return None
    return DAY_MAP.get(day_str.strip().lower())

def parse_unavailable_blocks(time_unavailable: List[Dict[str, Any]]):
    blocks = []
    if not time_unavailable:
        return blocks
    for item in time_unavailable:
        if not item:
            continue

        days_field = item.get("days")
        if days_field is None:
            single = item.get("day")
            days_field = [single] if single else []

        start = _parse_time_component(item.get("start"))
        end   = _parse_time_component(item.get("end"))
        if start is None or end is None:
            continue

        for d in days_field:
            token = normalize_day_token(d)
            if not token:
                continue
            blocks.append({
                "day": token,
                "start_min": start,
                "end_min": end,
            })
    return blocks

def intervals_overlap(a_start, a_end, b_start, b_end):
    if None in (a_start, a_end, b_start, b_end):
        return False
    return max(a_start, b_start) < min(a_end, b_end)

def course_conflicts_with_unavailable(doc: Dict[str, Any], blocks):
    if not blocks:
        return False
    mtg = doc.get("meeting") or {}
    days = mtg.get("days") or []
    start = mtg.get("start_min")
    end   = mtg.get("end_min")
    if start is None or end is None:
        return False
    for d in days:
        for blk in blocks:
            if blk["day"] != d:
                continue
            if intervals_overlap(start, end, blk["start_min"], blk["end_min"]):
                return True
    return False

# -------------------------------------------------------------------
# Prereq helpers
# -------------------------------------------------------------------

def _normalize_code(code: str) -> str:
    if not code:
        return ""
    return code.replace(" ", "").upper()

def get_requirements_for_code(code: str) -> Dict[str, Any]:
    doc = COL_DETAILED.find_one({"code": code}, {"requirements": 1, "_id": 0})
    if not doc:
        return {}
    return doc.get("requirements") or {}

def prereqs_satisfied_from_requirements(req: Dict[str, Any], completed_codes: Set[str]) -> bool:
    if not req:
        return True
    prereq = req.get("prereq")
    if not prereq:
        return True
    completed_norm = {_normalize_code(c) for c in completed_codes}
    for group in prereq:
        if not group:
            continue
        group_norm = {_normalize_code(c) for c in group}
        if not (group_norm & completed_norm):
            return False
    return True

def extract_coreq_groups(req: Dict[str, Any]) -> List[List[str]]:
    if not req:
        return []
    coreq = req.get("coreq")
    if not coreq:
        return []
    groups = []
    for group in coreq:
        if not group:
            continue
        groups.append([_normalize_code(c) for c in group])
    return groups

def matches_interests(doc: Dict[str, Any], interests: List[str]) -> bool:
    if not interests:
        return False
    title = (doc.get("title") or "").lower()
    desc  = (doc.get("description") or "").lower()
    for kw in interests:
        if kw.lower() in title or kw.lower() in desc:
            return True
    return False

# -------------------------------------------------------------------
# User + track_grad helpers
# -------------------------------------------------------------------

def fetch_user_doc(shared_id: str) -> Dict[str, Any]:
    key = str(shared_id)
    pref = SYN_PREF_BY_ID.get(key)
    hist = SYN_COURSES_BY_ID.get(key)
    if pref is None or hist is None:
        raise ValueError(f"No synthetic pref or courses found for ID={key}")
    return {"shared_id": key, "pref": pref, "history": hist}

def build_completed_codes_from_history(user_doc):
    hist = user_doc["history"]
    test     = hist.get("incoming_test_courses", [])
    transfer = hist.get("incoming_transfer_courses", [])
    emory    = hist.get("emory_courses", [])
    completed = set(test) | set(transfer) | set(emory)
    return {
        "incoming_test": test,
        "incoming_transfer": transfer,
        "emory_courses": emory,
        "completed_codes": completed,
    }

def run_track_grad_for_user(user_doc):
    pref = user_doc["pref"]
    hist_info = build_completed_codes_from_history(user_doc)
    degree = pref.get("degreeType", "BA")
    major_code = "CSBA" if degree == "BA" else "CSBS"
    year = pref.get("year", "Freshman")
    term = pref.get("term", "Fall")
    major_must, major_elec_groups, ger_due, ger_left = track_grad(
        major_code,
        hist_info["incoming_test"],
        hist_info["incoming_transfer"],
        hist_info["emory_courses"],
        year,
        term,
        countic=True,
    )
    return major_must, major_elec_groups, ger_due, ger_left, hist_info["completed_codes"]

def clean_for_json(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items() if k != "_id"}
    if isinstance(obj, list):
        return [clean_for_json(x) for x in obj]
    return obj

# -------------------------------------------------------------------
# CORE LOGIC
# -------------------------------------------------------------------

def build_qualified_courses_for_student(shared_id: str,
                                        min_rating: float = 0.0,
                                        instruction_method: str = None):
    user_doc = fetch_user_doc(shared_id)
    pref = user_doc["pref"]

    unavailable_blocks = parse_unavailable_blocks(pref.get("timeUnavailable", []))
    interests = pref.get("interests", [])

    major_must, major_elec_groups, ger_due, ger_left, completed_codes = \
        run_track_grad_for_user(user_doc)

    remaining_elec_codes = set()
    for g in major_elec_groups:
        remaining_elec_codes.update(g.get("courses", []))

    due_ger_tags = {tag for d in ger_due for tag in d.keys()}

    try:
        source = list(COL_ENRICHED.find({}))
        print(f"[INFO] Loaded {len(source)} docs from DetailedCourses.CoursesEnriched.")
    except:
        source = []

    qualified = []

    for doc in source:
        code = doc.get("code")
        if not code:
            continue
        code_norm = _normalize_code(code)

        # a) skip completed
        if code in completed_codes:
            continue

        # b) rating filter
        rating = (doc.get("rmp") or {}).get("rating") or 0
        if rating < min_rating:
            continue

        # c) instruction method
        if instruction_method:
            if (doc.get("instruction_method") or "").lower() != instruction_method.lower():
                continue

        # d) timeUnavailable (correct indentation)
        if course_conflicts_with_unavailable(doc, unavailable_blocks):
            continue

        # e) prereqs
        req = get_requirements_for_code(code_norm)
        if not prereqs_satisfied_from_requirements(req, completed_codes):
            continue

        coreq_groups = extract_coreq_groups(req)
        ger_list = doc.get("ger") or []
        base = clean_for_json(doc)

        doc_out = {
            **base,
            "shared_id": shared_id,
            "reason_major_must": code in major_must,
            "reason_major_elec": code in remaining_elec_codes,
            "reason_ger": ger_list,
            "reason_interest": matches_interests(doc, interests),
            "requirements": {
                "prereq_groups": req.get("prereq") or [],
                "coreq_groups": coreq_groups,
            },
        }
        qualified.append(doc_out)

    print(f"[INFO] For student {shared_id}, {len(qualified)} courses qualified.")

    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"courses_qualified_{shared_id}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(qualified, f, indent=2)
    print(f"[INFO] Saved → {out_path}")

    return qualified

# -------------------------------------------------------------------

if __name__ == "__main__":
    build_qualified_courses_for_student("000025")
