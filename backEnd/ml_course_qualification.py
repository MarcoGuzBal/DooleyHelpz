import re
from typing import List, Dict, Any, Set
from bson import ObjectId

from track_graduation import track_grad

# -------------------------------------------------------------------
# Time parsing helpers
# -------------------------------------------------------------------

DAY_MAP = {
    "m": "M", "mon": "M", "monday": "M",
    "t": "T", "tue": "T", "tues": "T", "tuesday": "T",
    "w": "W", "wed": "W", "weds": "W", "wednesday": "W",
    "th": "Th", "thu": "Th", "thur": "Th", "thurs": "Th", "thursday": "Thursday",
    "f": "F", "fri": "F", "friday": "F",
}

def _parse_time_component(t: str):
    """Parse time string like '10:00am' to minutes since midnight."""
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
    """Normalize day string to standard token (M, T, W, Th, F)."""
    if not day_str:
        return None
    return DAY_MAP.get(day_str.strip().lower())

def parse_unavailable_blocks(time_unavailable: List[Dict[str, Any]]):
    """Parse user's unavailable time blocks from preferences."""
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
    """Check if two time intervals overlap."""
    if None in (a_start, a_end, b_start, b_end):
        return False
    return max(a_start, b_start) < min(a_end, b_end)

def course_conflicts_with_unavailable(doc: Dict[str, Any], blocks):
    """Check if course meeting time conflicts with unavailable blocks."""
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
    """Normalize course code (uppercase, no spaces)."""
    if not code:
        return ""
    return code.replace(" ", "").upper()

def get_requirements_for_code(code: str, basic_courses_col) -> Dict[str, Any]:
    """Fetch prerequisites for a course code from MongoDB."""
    doc = basic_courses_col.find_one({"code": code}, {"requirements": 1, "_id": 0})
    if not doc:
        return {}
    return doc.get("requirements") or {}

def prereqs_satisfied_from_requirements(req: Dict[str, Any], completed_codes: Set[str]) -> bool:
    """
    Check if prerequisites are satisfied.
    req["prereq"] is List[List[str]] where each inner list is an OR group,
    and the outer list is AND.
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
        # At least one course from this OR group must be completed
        if not (group_norm & completed_norm):
            return False
    return True

def extract_coreq_groups(req: Dict[str, Any]) -> List[List[str]]:
    """Extract corequisite groups from requirements."""
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
    """Check if course matches any of user's interests."""
    if not interests:
        return False
    title = (doc.get("title") or "").lower()
    desc  = (doc.get("description") or "").lower()
    for kw in interests:
        if kw.lower() in title or kw.lower() in desc:
            return True
    return False

# -------------------------------------------------------------------
# MongoDB User Data Helpers
# -------------------------------------------------------------------

def fetch_user_data(uid: str, course_col, pref_col) -> Dict[str, Any]:
    """
    Fetch user data from MongoDB collections.

    Returns dict with:
      - pref: user preferences document
      - history: user course history document
    """
    user_courses = course_col.find_one({"uid": uid}, sort=[("_id", -1)])
    if not user_courses:
        raise ValueError(f"No course data found for user {uid}")

    user_prefs = pref_col.find_one({"uid": uid}, sort=[("_id", -1)])
    if not user_prefs:
        raise ValueError(f"No preferences found for user {uid}")

    return {
        "uid": uid,
        "pref": user_prefs,
        "history": user_courses
    }

def build_completed_codes_from_history(user_doc):
    """Extract all completed course codes from user history."""
    hist = user_doc["history"]
    test     = hist.get("incoming_test_courses", []) or []
    transfer = hist.get("incoming_transfer_courses", []) or []
    emory    = hist.get("emory_courses", []) or []
    spring   = hist.get("spring_2026_courses", []) or []

    completed = set(test) | set(transfer) | set(emory) | set(spring)
    return {
        "incoming_test": test,
        "incoming_transfer": transfer,
        "emory_courses": emory,
        "spring_courses": spring,
        "completed_codes": completed,
    }

def run_track_grad_for_user(user_doc):
    """
    Run track_graduation logic for a user to determine:
      - major_must: required major courses
      - major_elec_groups: major elective groups
      - ger_due: GERs due this semester
      - ger_left: GERs remaining
      - completed_codes: all completed course codes
    """
    pref = user_doc["pref"]
    hist_info = build_completed_codes_from_history(user_doc)

    degree = pref.get("degreeType", "BA")
    major_code = "CSBA" if degree == "BA" else "CSBS"

    year = pref.get("year", "Freshman")
    term = pref.get("expectedGraduation", {}).get("semester", "Fall")

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
    """Remove MongoDB _id fields for JSON serialization."""
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

def build_qualified_courses_for_user(
    uid: str,
    course_col,
    pref_col,
    enriched_courses_col,
    basic_courses_col,
    min_rating: float = 0.0,
    instruction_method: str = None
) -> List[Dict[str, Any]]:
    """
    Build list of qualified courses for a MongoDB user.

    Filters courses by:
      1. Not already completed
      2. Minimum RMP rating
      3. Instruction method (if specified)
      4. Time conflicts with timeUnavailable
      5. Prerequisites satisfied

    Annotates each course with:
      - reason_major_must: is this a required major course?
      - reason_major_elec: is this a major elective?
      - reason_ger_due: what GERs does this satisfy that are due?
      - reason_interest: does this match user interests?
      - requirements: prereq/coreq groups

    Args:
        uid: User Firebase UID
        course_col: MongoDB Users.TestCourses collection
        pref_col: MongoDB Users.UserPreferences collection
        enriched_courses_col: MongoDB DetailedCourses.CoursesEnriched collection
        basic_courses_col: MongoDB DetailedCourses.DetailedCourses collection (for prereqs)
        min_rating: Minimum RMP rating filter
        instruction_method: Filter by instruction method (e.g., "In-Person")

    Returns:
        List of qualified course documents with annotations
    """
    # 1. Fetch user data from MongoDB
    user_doc = fetch_user_data(uid, course_col, pref_col)
    pref = user_doc["pref"]

    # 2. Parse user constraints
    unavailable_blocks = parse_unavailable_blocks(pref.get("timeUnavailable", []))
    interests = pref.get("interests", [])

    # 3. Run track_graduation to get major/GER requirements
    major_must, major_elec_groups, ger_due, ger_left, completed_codes = \
        run_track_grad_for_user(user_doc)

    # Build set of all major elective codes
    remaining_elec_codes = set()
    for g in major_elec_groups:
        remaining_elec_codes.update(g.get("courses", []))

    # Extract GER tags that are due this semester
    due_ger_tags = {tag for d in ger_due for tag in d.keys()}

    # 4. Fetch all courses from MongoDB
    try:
        source = list(enriched_courses_col.find({}))
        print(f"[ML Qualification] Loaded {len(source)} courses from MongoDB")
    except Exception as e:
        print(f"[ML Qualification] Error loading courses: {e}")
        source = []

    # 5. Filter and annotate courses
    qualified = []

    for doc in source:
        code = doc.get("code")
        if not code:
            continue
        code_norm = _normalize_code(code)

        # a) Skip if already completed
        if code in completed_codes:
            continue

        # b) RMP rating filter
        rating = (doc.get("rmp") or {}).get("rating") or 0
        if rating < min_rating:
            continue

        # c) Instruction method filter
        if instruction_method:
            if (doc.get("instruction_method") or "").lower() != instruction_method.lower():
                continue

        # d) Time conflict check
        if course_conflicts_with_unavailable(doc, unavailable_blocks):
            continue

        # e) Prerequisite check
        req = get_requirements_for_code(code_norm, basic_courses_col)
        if not prereqs_satisfied_from_requirements(req, completed_codes):
            continue

        # 6. Annotate the course with recommendation reasons
        coreq_groups = extract_coreq_groups(req)
        ger_list = doc.get("ger") or []

        # Which GERs does this course satisfy that are actually DUE?
        ger_due_satisfied = [g for g in ger_list if g in due_ger_tags]

        base = clean_for_json(doc)

        doc_out = {
            **base,
            "uid": uid,
            "reason_major_must": code in major_must,
            "reason_major_elec": code in remaining_elec_codes,
            "reason_ger": ger_list,  # All GERs this course satisfies
            "reason_ger_due": ger_due_satisfied,  # GERs that are DUE this semester
            "reason_interest": matches_interests(doc, interests),
            "requirements": {
                "prereq_groups": req.get("prereq") or [],
                "coreq_groups": coreq_groups,
            },
        }
        qualified.append(doc_out)

    print(f"[ML Qualification] For user {uid}, {len(qualified)} courses qualified")

    return qualified
