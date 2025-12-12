"""
DooleyHelpz – Per-Student Course Qualification (Synthetic Version)

Uses:
  - synthetic_pref.json      (user preferences)
  - synthetic_courses.json   (user history)
  - DetailedCourses.CoursesEnriched (catalog)
  - track_graduation.track_grad     (requirements)

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
# Paths + synthetic user data
# -------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(__file__)
SYNTHETIC_COURSES_PATH = os.path.join(SCRIPT_DIR, "synthetic_courses.json")
SYNTHETIC_PREF_PATH    = os.path.join(SCRIPT_DIR, "synthetic_pref.json")

with open(SYNTHETIC_COURSES_PATH, "r", encoding="utf-8") as f:
    _synthetic_courses_list = json.load(f)

with open(SYNTHETIC_PREF_PATH, "r", encoding="utf-8") as f:
    _synthetic_pref_list = json.load(f)

# Map by shared_id for quick lookup
SYN_COURSES_BY_ID = {str(rec["shared_id"]): rec for rec in _synthetic_courses_list}
SYN_PREF_BY_ID    = {str(rec["shared_id"]): rec for rec in _synthetic_pref_list}

# -------------------------------------------------------------------
# Mongo catalog connection (for DetailedCourses.CoursesEnriched)
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
# Time helpers (adapted from your old Courses_Qualified)
# -------------------------------------------------------------------

DAY_MAP = {
    "m": "M", "mon": "M", "monday": "M",
    "t": "T", "tue": "T", "tues": "T", "tuesday": "T",
    "w": "W", "wed": "W", "weds": "W", "wednesday": "W",
    "th": "Th", "thu": "Th", "thur": "Th", "thurs": "Th", "thursday": "Th",
    "f": "F", "fri": "F", "friday": "F",
}


def _parse_time_component(t: str):
    # '9am', '9:30am', '10:00pm' -> minutes since midnight
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
    key = str(day_str).strip().lower()
    return DAY_MAP.get(key)


def parse_unavailable_blocks(time_unavailable: List[Dict[str, Any]]):
    """
    Convert pref.timeUnavailable entries into blocks like:
      {"day": "M", "start_min": 540, "end_min": 675}
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
            blocks.append({
                "day": token,
                "start_min": start_min,
                "end_min": end_min,
            })
    return blocks


def intervals_overlap(a_start, a_end, b_start, b_end):
    if None in (a_start, a_end, b_start, b_end):
        return False
    return max(a_start, b_start) < min(a_end, b_end)


def course_conflicts_with_unavailable(course_doc: Dict[str, Any],
                                      unavailable_blocks: List[Dict[str, Any]]) -> bool:
    if not unavailable_blocks:
        return False

    meeting = course_doc.get("meeting") or {}
    days = meeting.get("days") or []
    start_min = meeting.get("start_min")
    end_min = meeting.get("end_min")

    if start_min is None or end_min is None:
        return False  # or True if you want to drop unknowns

    for day in days:
        for blk in unavailable_blocks:
            if blk["day"] != day:
                continue
            if intervals_overlap(start_min, end_min,
                                 blk["start_min"], blk["end_min"]):
                return True
    return False


# -------------------------------------------------------------------
# Simple prereq + interest helpers
# -------------------------------------------------------------------
def _normalize_code(code: str) -> str:
    """Normalize course codes like 'CS 171 ' -> 'CS171'."""
    if not code:
        return ""
    return str(code).replace(" ", "").upper()


def matches_interests(course_doc: Dict[str, Any], interests: List[str]) -> bool:
    if not interests:
        return False
    title = (course_doc.get("title") or "").lower()
    desc = (course_doc.get("description") or "").lower()
    for kw in interests:
        kw = kw.lower()
        if kw in title or kw in desc:
            return True
    return False


# -------------------------------------------------------------------
# Synthetic "user doc" + track_grad helpers
# -------------------------------------------------------------------

def fetch_user_doc(shared_id: str) -> Dict[str, Any]:
    """
    Build a user_doc from synthetic JSONs:

      {
        "shared_id": "000025",
        "pref": <from synthetic_pref.json>,
        "history": <from synthetic_courses.json>
      }
    """
    key = str(shared_id)
    pref = SYN_PREF_BY_ID.get(key)
    hist = SYN_COURSES_BY_ID.get(key)
    if pref is None or hist is None:
        raise ValueError(f"No synthetic pref or courses for shared_id={key}")
    return {
        "shared_id": key,
        "pref": pref,
        "history": hist,
    }


def build_completed_codes_from_history(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    hist = user_doc.get("history", {})
    incoming_test = hist.get("incoming_test_courses", []) or []
    incoming_transfer = hist.get("incoming_transfer_courses", []) or []
    emory_courses = hist.get("emory_courses", []) or []
    completed = set(incoming_test) | set(incoming_transfer) | set(emory_courses)
    return {
        "incoming_test": incoming_test,
        "incoming_transfer": incoming_transfer,
        "emory_courses": emory_courses,
        "completed_codes": completed,
    }


def run_track_grad_for_user(user_doc: Dict[str, Any]):
    pref = user_doc.get("pref", {})
    hist_info = build_completed_codes_from_history(user_doc)

    degree_type = pref.get("degreeType", "BA")
    major_code = "CSBA" if degree_type == "BA" else "CSBS"
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
    """
    Recursively convert Mongo types (ObjectId, etc.) into JSON-safe values
    and drop the raw '_id' field.
    """
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "_id":
                continue  # drop Mongo's internal id
            out[k] = clean_for_json(v)
        return out
    if isinstance(obj, list):
        return [clean_for_json(x) for x in obj]
    return obj
def _normalize_code(code: str) -> str:
    """Normalize course codes like 'CS 171 ' -> 'CS171'."""
    if not code:
        return ""
    return str(code).replace(" ", "").upper()


def get_requirements_for_code(code: str) -> Dict[str, Any]:
    """
    Look up the 'requirements' object in DetailedCourses.DetailedCourses by code.
    Returns {} if not found.
    """
    doc = COL_DETAILED.find_one({"code": code}, {"requirements": 1, "_id": 0})
    if not doc:
        return {}
    return doc.get("requirements") or {}


def prereqs_satisfied_from_requirements(req: Dict[str, Any],
                                        completed_codes: Set[str]) -> bool:
    """
    Enforce prereqs using the structure:
      requirements: {
        "prereq": [
          ["CS171", "CS171Z", "CS_OX171"],  # OR group
          ["MATH111", "MATH112"]           # another OR group, etc.
        ],
        ...
      }

    Rule:
      For each group in 'prereq', the student must have completed
      at least ONE code in that group.
    """
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
        # need at least one from this group
        if not (group_norm & completed_norm):
            return False

    return True


def extract_coreq_groups(req: Dict[str, Any]) -> List[List[str]]:
    """
    Extract coreq groups from requirements into a normalized list of lists.

    Example:
      "coreq": [
        ["CS255", "CS255Z"]
      ]
    returns:
      [["CS255", "CS255Z"]]
    """
    if not req:
        return []

    coreq = req.get("coreq")
    if not coreq:
        return []

    result = []
    for group in coreq:
        if not group:
            continue
        group_norm = [_normalize_code(c) for c in group]
        result.append(group_norm)
    return result
def prereqs_satisfied_from_prereq_groups(prereq_groups: List[List[str]],
                                         completed_codes: Set[str]) -> bool:
    """
    Enforce prereqs using the normalized 'prerequisites' field in the course doc.

    prereq_groups is expected to be a list of OR-groups, e.g.:

      [
        ["CS171", "CS171Z", "CS_OX171"],   # group 1 (any of these)
        ["MATH111", "MATH112"],            # group 2 (any of these)
      ]

    Rule:
      For each group in prereq_groups, the student must have completed
      at least ONE code in that group. Empty / malformed groups are ignored.
    """
    if not prereq_groups:
        return True

    for group in prereq_groups:
        if not group:
            # nothing to enforce in this group
            continue

        # at least one of the codes in this OR-group must be completed
        if not any((code in completed_codes) for code in group):
            return False

    return True

# -------------------------------------------------------------------
# Core: build qualified courses for ONE student
# -------------------------------------------------------------------

def build_qualified_courses_for_student(shared_id: str,
                                        min_rating: float = 0.0,
                                        instruction_method: str = None) -> List[Dict[str, Any]]:
    """
    Main entry point used by the notebook.

    This version:
      - Keeps GER behavior via track_grad (major_must, major_elec_groups, ger_due, ger_left)
      - Does NOT touch MongoDB schema (reads existing fields only)
      - Does NOT hard-block courses based on prereqs (so CS courses are not all filtered out)
    """
    # Toggle if you later want to re-enable prereq enforcement using doc["prerequisites"]
    IGNORE_PREREQS = True

    # 1) load synthetic user
    user_doc = fetch_user_doc(shared_id)
    pref = user_doc["pref"]

    time_unavailable = pref.get("timeUnavailable", []) or []
    interests = pref.get("interests", [])

    unavailable_blocks = parse_unavailable_blocks(time_unavailable)

    # 2) requirements + completed codes via track_grad
    major_must, major_elec_groups, ger_due, ger_left, completed_codes = \
        run_track_grad_for_user(user_doc)

    # set of remaining elective course codes
    remaining_elec_codes: Set[str] = set()
    for group in major_elec_groups:
        remaining_elec_codes.update(group.get("courses", []))

    # GER tags that are actually due for this student right now
    due_ger_tags: Set[str] = set()
    for d in ger_due:
        # each d is like {"HA": 1} or {"NS": 1}
        for tag in d.keys():
            due_ger_tags.add(tag)

    # 3) load catalog from CoursesEnriched
    try:
        source = list(COL_ENRICHED.find({}))
        print(f"[INFO] Loaded {len(source)} docs from DetailedCourses.CoursesEnriched.")
    except PyMongoError as e:
        print(f"[WARN] Mongo read failed: {e}")
        source = []

    # 4) filter to qualified
    qualified: List[Dict[str, Any]] = []
    for doc in source:
        code = doc.get("code")
        if not code:
            continue
        code_norm = str(code).upper()

        # a) drop already completed (incoming_test, incoming_transfer, emory_courses)
        if code in completed_codes:
            continue

        # b) rating filter
        rating = (doc.get("rmp") or {}).get("rating") or 0
        if rating < min_rating:
            continue

        # c) instruction method filter (optional)
        if instruction_method:
            if (doc.get("instruction_method") or "").lower() != instruction_method.lower():
                continue

            # d) timeUnavailable
        if course_conflicts_with_unavailable(doc, unavailable_blocks):
            continue

            # e) Enforce prereqs using DetailedCourses.DetailedCourses.requirements
        #    based on COMPLETED courses only.
        req = get_requirements_for_code(code_norm)  # uses COL_DETAILED under the hood
        if not prereqs_satisfied_from_requirements(req, completed_codes):
            # Student has NOT satisfied these prereqs → skip this course completely
            # Optional: debug print
            # print(f"[DEBUG] skipping {code_norm} due to prereqs: {req}")
            continue

        # Extract coreq groups (for scheduler/UI; we do NOT *block* on them here)
        coreq_groups = extract_coreq_groups(req)

        ger_list = doc.get("ger") or []

        base = clean_for_json(doc)

        doc_out = {
            **base,
            "shared_id": str(shared_id),
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

    # 5) save per-student JSON
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"courses_qualified_{shared_id}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(qualified, f, indent=2)
    print(f"[INFO] Saved → {out_path}")

    return qualified

# -------------------------------------------------------------------
# Simple CLI for debugging
# -------------------------------------------------------------------

if __name__ == "__main__":
    # default synthetic student id; adjust to one that exists in your JSONs
    test_shared_id = "000025"
    build_qualified_courses_for_student(test_shared_id)
