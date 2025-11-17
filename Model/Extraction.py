"""
DooleyHelpz MVP – Step 1: Extraction/Normalization/Enrichment

Goal:
- Normalize raw DetailedCourses.DetailedCourses → unified course_detailed schema
- Derive course_basic (subset)
- Parse meeting times into blocks (days, start_min, end_min) for Step 2
- Enrich with RateMyProfessors.Professors (matched by normalized professor name)
- Write normalized+enriched docs to Mongo (DetailedCourses.CoursesEnriched) for Steps 2–3
- Export staging JSONs:
    • staging/courses_detailed.json
    • staging/courses_basic.json
    • staging/extract_issues.json

Usage:
    python extraction.py --uri "$MONGODB_URI" --outdir staging --write_mongo

If --uri is omitted, defaults to mongodb://localhost:27017
"""

from __future__ import annotations
import argparse
import json
import os
import re
from typing import Dict, Any, Optional, Tuple, List

from pymongo import MongoClient, UpdateOne


# -----------------------------
# Normalization helpers
# -----------------------------

CODE_RE = re.compile(r"\s+")

def normalize_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    c = str(code).strip().upper()
    c = CODE_RE.sub("", c)         # "CS 170" -> "CS170"
    return c or None

def to_str_or_none(x) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None

def name_case(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    # Basic name-case; keeps apostrophes/hyphens
    s = re.sub(r"\s+", " ", s.strip().lower())
    return " ".join([w.capitalize() for w in s.split(" ")])

def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        # numeric string → float
        xs = str(x).strip()
        return float(xs)
    except Exception:
        return None

def normalize_credits(raw) -> Any:
    """
    Keep numeric credits as float (3.0).
    If it's a range like '1-4', keep as string '1-4'.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if re.match(r"^\d+(\.\d+)?-\d+(\.\d+)?$", s):
        return s  # keep range string
    f = _safe_float(s)
    return f if f is not None else s  # last resort keep original string

def normalize_list_tokens(v, *, lower=False, trim=True, unique=True, sort=True) -> List[str]:
    if v is None:
        return []
    if isinstance(v, str):
        items = re.split(r"[;,/|]+", v) if ("," not in v and ";" not in v) else v.split(",")
    else:
        items = list(v)
    out = []
    for t in items:
        s = str(t)
        if trim: s = s.strip()
        if lower: s = s.lower()
        if s:
            out.append(s)
    if unique:
        out = list(dict.fromkeys(out))
    if sort:
        out.sort()
    return out

def normalize_prereqs(raw) -> List[List[str]]:
    """
    Keep as AND-of-OR lists of course codes.
    Examples:
      - None → [[]]
      - "MATH111 or (CS170, CS171)" → [["MATH111"], ["CS170","CS171"]]
      - [["math111"],["cs170","cs171"]] → [['MATH111'],['CS170','CS171']]
    """
    if raw is None:
        return [[]]
    # already list[list]
    if isinstance(raw, list) and all(isinstance(x, list) for x in raw):
        return [[normalize_code(c) for c in group if normalize_code(c)] or [] for group in raw] or [[]]

    # heuristic parser for simple strings
    s = str(raw)
    # split AND groups by ';' or 'AND' or newline
    and_parts = re.split(r";|\band\b|\n", s, flags=re.IGNORECASE)
    groups: List[List[str]] = []
    for part in and_parts:
        # OR group: ',', '/' or 'OR'
        or_items = re.split(r",|/|\bor\b", part, flags=re.IGNORECASE)
        codes = []
        for it in or_items:
            m = re.findall(r"[A-Za-z]{2,}\s*\d+[A-Za-z]?", it)
            codes += [normalize_code(c) for c in m if normalize_code(c)]
        groups.append(codes or [])
    return groups or [[]]

def map_instruction_method(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = str(raw).strip().lower()
    if "online" in s:
        return "online"
    if "hybrid" in s or "hy-flex" in s or "hyflex" in s:
        return "hybrid"
    # default
    return "in-person"

def normalize_name_for_match(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    n = re.sub(r"[\.]", "", name).strip().lower()
    n = re.sub(r"\s+", " ", n)
    return n


# -----------------------------
# Meeting time parsing
# -----------------------------

DAY_TOKENS = ["Th", "M", "T", "W", "F"]  # order matters; match 'Th' before 'T'

def _parse_time_component(t):
    t = t.strip().lower()

    # Example match: "10:00am", "2pm", "11:15 pm"
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", t)
    if not m:
        return None  # return None instead of -1

    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = m.group(3)

    # Convert to 24-hour scale
    if hour == 12:
        hour = 0
    if ampm == "pm":
        hour += 12

    return hour * 60 + minute

def parse_meeting_time(time_str: Optional[str]) -> Dict[str, Any]:
    """
    Input examples: 'MW 8:30am-9:45am', 'TTh 11:30am-12:45pm', 'F 1pm-1:50pm'
    Output: {days: [..], start_min: int|None, end_min: int|None, raw: str|None}
    """
    out = {"days": [], "start_min": None, "end_min": None, "raw": time_str}
    if not time_str:
        return out

    s = time_str.strip()
    parts = s.split(None, 1)
    if len(parts) != 2:
        return out

    days_part, times_part = parts[0], parts[1]

    i = 0
    days = []
    while i < len(days_part):
        matched = False
        for token in DAY_TOKENS:
            if days_part.startswith(token, i):
                days.append(token)
                i += len(token)
                matched = True
                break
        if not matched:
            break

    tm = re.match(r"^([0-9:apm\s]+)\s*-\s*([0-9:apm\s]+)$", times_part.strip(), re.IGNORECASE)
    if not tm:
        return {"days": days, "start_min": None, "end_min": None, "raw": time_str}

    start_s, end_s = tm.group(1).strip(), tm.group(2).strip()
    start_min = _parse_time_component(start_s)
    end_min = _parse_time_component(end_s)

    return {"days": days, "start_min": start_min, "end_min": end_min, "raw": time_str}


# -----------------------------
# RMP enrichment
# -----------------------------

def build_rmp_index(rmp_col) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for doc in rmp_col.find({}, {
        "name": 1, "rating": 1, "num_ratings": 1,
        "difficulty": 1, "would_take_again_%": 1,
        "department": 1, "url": 1
    }):
        key = normalize_name_for_match(doc.get("name"))
        if key:
            idx[key] = doc
    return idx


# -----------------------------
# Core extraction
# -----------------------------

def normalize_course(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    """
    Returns: (course_detailed, course_basic, issues[])
    course_detailed schema:
      { code, title, section, credits, typically_offered[], prerequisites[[]], ger[],
        instruction_method, time, professor, location,
        meeting{days[], start_min, end_min}, rmp{...} (to be added later) }
    """
    issues: List[str] = []

    code = normalize_code(raw.get("code"))
    title = to_str_or_none(raw.get("title"))
    if not code:
        issues.append("missing_code")
    if not title:
        issues.append("missing_title")

    section = to_str_or_none(raw.get("section"))
    credits = normalize_credits(raw.get("credits"))

    # lists
    typically_offered = normalize_list_tokens(raw.get("typically_offered"), lower=True)
    prereqs = normalize_prereqs(raw.get("prerequisites"))
    ger = normalize_list_tokens(raw.get("ger"), lower=False)

    instr_method = map_instruction_method(raw.get("instruction_method"))
    time_raw = to_str_or_none(raw.get("time"))
    professor_raw = name_case(raw.get("professor"))
    location = to_str_or_none(raw.get("location"))

    meeting = parse_meeting_time(time_raw)

    detailed = {
        "code": code,
        "title": title,
        "section": section,
        "credits": credits if isinstance(credits, float) else _safe_float(credits),  # prefer numeric for downstream
        "credits_raw": credits,  # keep original interpretation
        "typically_offered": typically_offered,
        "prerequisites": prereqs if prereqs else [[]],
        "ger": sorted(list(dict.fromkeys(ger))),
        "instruction_method": instr_method,
        "time": time_raw,                 # keep raw for UI
        "professor": professor_raw,
        "location": location,
        "meeting": meeting,               # parsed for filters/recs
        # rmp filled later
    }

    basic = {
        "code": detailed["code"],
        "title": detailed["title"],
        "credits": detailed["credits"],
        "typically_offered": detailed["typically_offered"],
        "prerequisites": detailed["prerequisites"],
        "ger": detailed["ger"],
    }

    # required defaults
    if detailed["prerequisites"] is None:
        detailed["prerequisites"] = [[]]
    if detailed["ger"] is None:
        detailed["ger"] = []

    return detailed, basic, issues


def enrich_with_rmp(detailed: Dict[str, Any], rmp_index: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    key = normalize_name_for_match(detailed.get("professor"))
    rmp = rmp_index.get(key) if key else None

    enriched = dict(detailed)
    enriched["rmp"] = {
        "name": rmp.get("name") if rmp else None,
        "rating": _safe_float(rmp.get("rating")) if rmp else None,
        "num_ratings": rmp.get("num_ratings") if rmp else None,
        "difficulty": _safe_float(rmp.get("difficulty")) if rmp else None,
        "would_take_again_pct": _safe_float(rmp.get("would_take_again_%")) if rmp else None,
        "department": rmp.get("department") if rmp else None,
        "url": rmp.get("url") if rmp else None,
    }
    return enriched


def run(uri: str, outdir: str, write_mongo: bool) -> Tuple[int, int]:
    os.makedirs(outdir, exist_ok=True)

    client = MongoClient(uri)

    db_courses = client["DetailedCourses"]
    col_in = db_courses["DetailedCourses"]
    col_out = db_courses["CoursesEnriched"]

    db_rmp = client["RateMyProfessors"]
    col_rmp = db_rmp["Professors"]

    rmp_index = build_rmp_index(col_rmp)

    detailed_list: List[Dict[str, Any]] = []
    basic_list: List[Dict[str, Any]] = []
    issues_list: List[Dict[str, Any]] = []

    ops: List[UpdateOne] = []
    in_count = 0
    out_count = 0

    for raw in col_in.find({}):
        in_count += 1
        detailed, basic, issues = normalize_course(raw)
        enriched = enrich_with_rmp(detailed, rmp_index)

        detailed_list.append(enriched)
        basic_list.append(basic)
        if issues:
            issues_list.append({"code": detailed.get("code"), "errors": issues})

        if write_mongo:
            upsert_filter = {
                "code": enriched.get("code"),
                "section": enriched.get("section"),
                "professor": enriched.get("professor"),
            }
            ops.append(UpdateOne(upsert_filter, {"$set": enriched}, upsert=True))

            if len(ops) >= 500:
                res = col_out.bulk_write(ops, ordered=False)
                out_count += res.upserted_count + res.modified_count
                ops = []

    if write_mongo and ops:
        res = col_out.bulk_write(ops, ordered=False)
        out_count += res.upserted_count + res.modified_count

    # Write staging JSONs
    with open(os.path.join(outdir, "courses_detailed.json"), "w", encoding="utf-8") as f:
        json.dump(detailed_list, f, ensure_ascii=False, indent=2)
    with open(os.path.join(outdir, "courses_basic.json"), "w", encoding="utf-8") as f:
        json.dump(basic_list, f, ensure_ascii=False, indent=2)
    with open(os.path.join(outdir, "extract_issues.json"), "w", encoding="utf-8") as f:
        json.dump(issues_list, f, ensure_ascii=False, indent=2)

    return in_count, out_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--outdir", default="staging")
    parser.add_argument("--write_mongo", action="store_true", help="Write to DetailedCourses.CoursesEnriched")
    args = parser.parse_args()

    in_count, out_count = run(args.uri, args.outdir, args.write_mongo)

    print(f"Normalized {in_count} source courses → wrote JSONs in '{args.outdir}'.")
    if args.write_mongo:
        print(f"Upserted/updated ~{out_count} docs in DetailedCourses.CoursesEnriched.")
    else:
        print("(Dry run) Skipped Mongo writes; only JSONs were produced.")


if __name__ == "__main__":
    main()
