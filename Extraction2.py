#!/usr/bin/env python3
# Extraction.py — DooleyHelpz / CS 370
# Enrich course docs with RateMyProfessors (RMP) data using robust name matching.
# Includes: multi-instructor support, schema normalization, issues logging,
# upserts (or full refresh), JSON/CSV exports, and safe dry-run mode.

import os
import re
import csv
import json
import argparse
import unicodedata
import difflib
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Dict, Any, List

from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError


# =========================
# CLI
# =========================

def parse_args():
    p = argparse.ArgumentParser(description="Enrich courses with RMP data (robust matching + normalization).")
    p.add_argument("--mongo_uri", type=str, default=os.getenv("MONGODB_URI", ""),
                   help="MongoDB connection string. Falls back to $MONGODB_URI.")
    p.add_argument("--db_courses", type=str, default="DetailedCourses",
                   help="Database containing input courses and output collections.")
    p.add_argument("--in_col", type=str, default="DetailedCourses",
                   help="Input collection with raw courses.")
    p.add_argument("--out_col", type=str, default="CoursesEnriched",
                   help="Output collection to upsert enriched courses.")
    p.add_argument("--issues_col", type=str, default="ExtractIssues",
                   help="Collection to log extraction issues (optional).")
    p.add_argument("--db_rmp", type=str, default="RateMyProfessors",
                   help="Database containing RMP professors.")
    p.add_argument("--rmp_col", type=str, default="Professors",
                   help="Collection with RMP professor docs.")
    p.add_argument("--refresh", action="store_true",
                   help="If set, empties the out_col before writing (full refresh).")
    p.add_argument("--backup", action="store_true",
                   help="If set, exports current out_col to out/backup_*.json before changes.")
    p.add_argument("--export_csv", action="store_true",
                   help="Also export out/courses_enriched.csv for quick inspection.")
    p.add_argument("--dry_run", action="store_true",
                   help="Do all processing but DO NOT write to Mongo (still writes local JSON/CSV).")
    p.add_argument("--min_ratings_prefer", type=int, default=3,
                   help="Tie-breaker: prefer RMP entries with at least this many ratings.")
    p.add_argument("--fuzzy_cutoff", type=float, default=0.92,
                   help="Similarity cutoff (0..1) for fuzzy matches (same last-name block).")
    return p.parse_args()


# =========================
# Normalization Helpers
# =========================

SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
DEGREES  = {"phd", "md", "msc", "ms", "mba", "edd", "dphil"}
HONORIFICS = {"dr", "prof", "professor"}

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def normalize_name(name: Optional[str]) -> Optional[str]:
    """Accents, punctuation, hyphens, suffixes, degrees, honorifics.
       Also converts 'Last, First Middle' -> 'First Middle Last'."""
    if not name:
        return None
    n = _strip_accents(str(name)).lower().strip()

    # unify separators / punctuation
    n = n.replace("-", " ")
    n = n.replace("’", "'").replace("`", "'")
    n = n.replace(".", "")
    # keep simple letters, numbers, spaces, and comma (for last, first)
    n = "".join(ch for ch in n if ch.isalnum() or ch.isspace() or ch == ",")

    # compress whitespace
    n = " ".join(n.split())

    # split on comma if formatted "Last, First Middle"
    parts = [p.strip() for p in n.split(",")]
    if len(parts) == 2 and parts[0] and parts[1]:
        last = parts[0]
        first_and_more = parts[1]
        tokens = [t for t in first_and_more.split()
                  if t not in SUFFIXES and t not in DEGREES and t not in HONORIFICS]
        core = " ".join(tokens)
        n = f"{core} {last}".strip()
    else:
        tokens = [t for t in n.split()
                  if t not in SUFFIXES and t not in DEGREES and t not in HONORIFICS]
        n = " ".join(tokens)

    return n or None

def first_last_keys(n: str) -> set:
    """Alias keys from a normalized full name."""
    toks = n.split()
    if len(toks) == 0:
        return set()
    if len(toks) == 1:
        return {n}
    first, last = toks[0], toks[-1]
    keys = {
        n,                          # full
        f"{first} {last}",          # collapse middles
        f"{first[0]} {last}",       # first initial + last
        f"{first}{last}",           # joined
        f"{first[0]}{last}",        # joined initial+last
        f"{last} {first}",          # reversed
    }
    return keys

def split_multi_instructors(value: Optional[str]) -> List[str]:
    """Turn a combined instructor string into a list."""
    if not value:
        return []
    x = value
    for sep in [";", "&", " and ", "/", "|"]:
        x = x.replace(sep, ",")
    return [p.strip() for p in x.split(",") if p.strip()]


# =========================
# Course Field Parsers
# =========================

TIME_RE = re.compile(r"(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})")

def parse_meeting_time(s: Optional[str]) -> Dict[str, Any]:
    """Parse 'M,W,F 10:00-10:50' / 'MW 14:30-15:45' strings (best-effort)."""
    out = {"days": None, "start": None, "end": None, "raw": s}
    if not s:
        return out
    # days
    days = re.findall(r"(M|Tu|T|W|Th|R|F|Sa|Su)", s, flags=re.IGNORECASE)
    if days:
        norm = []
        for d in days:
            d = d.capitalize()
            if d == "R":
                d = "Th"
            if d == "T":
                d = "Tu"
            norm.append(d)
        out["days"] = norm
    m = TIME_RE.search(s)
    if m:
        out["start"] = m.group("start")
        out["end"] = m.group("end")
    return out

CREDITS_RANGE_RE = re.compile(r"(?P<min>\d+(\.\d+)?)\s*-\s*(?P<max>\d+(\.\d+)?)")
CREDITS_SINGLE_RE = re.compile(r"(?P<v>\d+(\.\d+)?)")

def parse_credits(s: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Parse credits like '3', '1-4', '3.0' -> (value, min, max)."""
    if not s:
        return None, None, None
    s = s.strip()
    m = CREDITS_RANGE_RE.search(s)
    if m:
        cmin = float(m.group("min")); cmax = float(m.group("max"))
        return None, cmin, cmax
    m = CREDITS_SINGLE_RE.search(s)
    if m:
        v = float(m.group("v"))
        return v, v, v
    return None, None, None

# Normalize instruction method to a small, consistent set
def normalize_method(x: Optional[str]) -> Optional[str]:
    if not x:
        return None
    t = str(x).lower().strip()
    if any(k in t for k in ["in person", "in-person", "classroom", "campus", "face to face", "face-to-face"]):
        return "in-person"
    if any(k in t for k in ["hybrid", "blended", "flex"]):
        return "hybrid"
    if any(k in t for k in ["online", "virtual", "remote"]):
        return "online"
    return t  # unknowns pass through


# =========================
# RMP Index + Matching
# =========================

def build_rmp_index(col, min_ratings_prefer: int = 3) -> Dict[str, Dict[str, Any]]:
    """Index mapping many alias keys -> a representative RMP doc (prefers more ratings)."""
    idx = {}
    for doc in col.find({}, {"name": 1, "rating": 1, "num_ratings": 1,
                             "difficulty": 1, "would_take_again_%": 1, "url": 1, "department": 1}):
        base = normalize_name(doc.get("name"))
        if not base:
            continue
        for k in first_last_keys(base):
            existing = idx.get(k)
            if not existing:
                idx[k] = doc
            else:
                # prefer entry with more ratings when both are 'good enough'
                if (doc.get("num_ratings") or 0) > (existing.get("num_ratings") or 0) >= min_ratings_prefer:
                    idx[k] = doc
    return idx

def _same_last_block(name_norm: str, key: str) -> bool:
    toks_a = name_norm.split()
    toks_b = key.split()
    return bool(toks_a and toks_b and toks_a[-1] == toks_b[-1])

def match_one_name_to_rmp(name_raw: str, rmp_index: Dict[str, Dict[str, Any]],
                           fuzzy_cutoff: float = 0.92) -> Tuple[Optional[Dict[str, Any]], str]:
    """Return best RMP doc for a single person name, with a reason label."""
    n = normalize_name(name_raw)
    if not n:
        return None, "empty_after_normalize"

    # 1) exact
    if n in rmp_index:
        return rmp_index[n], "exact"

    # 2) alias key family
    for k in first_last_keys(n):
        if k in rmp_index:
            return rmp_index[k], f"alias:{k}"

    # 3) fuzzy within same last-name block
    pool = [k for k in rmp_index.keys() if _same_last_block(n, k)]
    if pool:
        best = difflib.get_close_matches(n, pool, n=1, cutoff=fuzzy_cutoff)
        if best:
            return rmp_index[best[0]], f"fuzzy:{best[0]}"

    return None, f"no_match_for:{n}"

def match_professors_to_rmp_multi(raw_instructor_field: Optional[str],
                                  rmp_index: Dict[str, Dict[str, Any]],
                                  fuzzy_cutoff: float = 0.92,
                                  min_ratings_prefer: int = 3) -> Tuple[Optional[Dict[str, Any]],
                                                                        List[Dict[str, Any]],
                                                                        str]:
    """
    Handle multi-instructor strings.
    Returns: (primary_rmp_doc_or_None, per_instructor_matches[], aggregate_reason)
      - per_instructor_matches: [{raw, normalized, rmp, reason}]
      - primary chosen by: exact > alias > fuzzy; tie-breaker on num_ratings >= min_ratings_prefer
    """
    people = split_multi_instructors(raw_instructor_field)
    if not people:
        return None, [], "no_name"

    matches = []
    for person in people:
        rmp_doc, reason = match_one_name_to_rmp(person, rmp_index, fuzzy_cutoff=fuzzy_cutoff)
        matches.append({
            "raw": person,
            "normalized": normalize_name(person),
            "rmp": {
                "rating": (rmp_doc or {}).get("rating"),
                "num_ratings": (rmp_doc or {}).get("num_ratings"),
                "difficulty": (rmp_doc or {}).get("difficulty"),
                "would_take_again_%": (rmp_doc or {}).get("would_take_again_%"),
                "url": (rmp_doc or {}).get("url"),
                "name": (rmp_doc or {}).get("name"),
                "department": (rmp_doc or {}).get("department"),
            } if rmp_doc else None,
            "rmp_match_reason": reason
        })

    # choose primary
    def score(m):
        reason = m["rmp_match_reason"]
        base = 0
        if reason.startswith("exact"):
            base = 3
        elif reason.startswith("alias"):
            base = 2
        elif reason.startswith("fuzzy"):
            base = 1
        nr = ((m["rmp"] or {}).get("num_ratings") or 0)
        prefer = 0.2 if nr >= min_ratings_prefer else 0
        return base + prefer

    primary = None
    if matches:
        matches_sorted = sorted(matches, key=score, reverse=True)
        primary = matches_sorted[0]["rmp"]  # may be None if all failed
        aggregate_reason = matches_sorted[0]["rmp_match_reason"]
    else:
        aggregate_reason = "no_instructors_parsed"

    return (primary, matches, aggregate_reason)


# =========================
# Export Helpers
# =========================

def export_collection(col, filepath: str):
    docs = list(col.find({}))
    Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, default=str)
    return len(docs)

def export_csv(rows: List[Dict[str, Any]], filepath: str):
    if not rows:
        return
    Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)
    # flatten a few top-level fields for quick scanning
    fieldnames = [
        "code", "section", "title", "instruction_method",
        "meeting.days", "meeting.start", "meeting.end",
        "professors_raw", "rmp_primary.rating", "rmp_primary.num_ratings",
        "rmp_primary.difficulty", "rmp_primary.would_take_again_%", "rmp_primary.url",
        "rmp_match_reason"
    ]
    def _get(row, path, default=""):
        cur = row
        for part in path.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                cur = None
        return cur if cur is not None else default

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fieldnames)
        for r in rows:
            w.writerow([_get(r, p) for p in fieldnames])


# =========================
# Main Enrichment Flow
# =========================

def enrich_courses(args):
    if not args.mongo_uri:
        raise SystemExit("ERROR: Provide --mongo_uri or set $MONGODB_URI")

    client = MongoClient(args.mongo_uri)

    # Collections
    db_courses = client[args.db_courses]
    col_in = db_courses[args.in_col]
    col_out = db_courses[args.out_col]
    issues_out = db_courses[args.issues_col]

    db_rmp = client[args.db_rmp]
    col_rmp = db_rmp[args.rmp_col]

    # Optional backup
    if args.backup and not args.dry_run:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"out/backup_{args.out_col}_{ts}.json"
        try:
            n = export_collection(col_out, backup_path)
            print(f"[backup] Exported {n} docs from {args.out_col} -> {backup_path}")
        except Exception as e:
            print(f"[backup][WARN] Failed to export {args.out_col}: {e}")

    # Optional full refresh
    if args.refresh and not args.dry_run:
        try:
            res = col_out.delete_many({})
            print(f"[refresh] Cleared {res.deleted_count} docs from {args.out_col}")
        except PyMongoError as e:
            print(f"[refresh][WARN] delete_many failed: {e}")

    # Build RMP index
    rmp_index = build_rmp_index(col_rmp, min_ratings_prefer=args.min_ratings_prefer)
    print(f"[rmp] Indexed {len(rmp_index)} alias keys from RMP")

    # Iterate input courses
    ops = []
    enriched_docs: List[Dict[str, Any]] = []
    extract_issues: List[Dict[str, Any]] = []

    # metrics
    m_total = 0
    m_exact = m_alias = m_fuzzy = m_no = 0
    m_multi = 0

    cursor = col_in.find({})
    for course in cursor:
        m_total += 1

        # read commonly used fields (use fallbacks to be resilient)
        code = str(course.get("code") or course.get("course") or "")
        section = str(course.get("section") or "")
        title = course.get("title")
        method = normalize_method(course.get("instruction_method") or course.get("method"))
        professor_raw_field = course.get("professor") or course.get("instructor") or course.get("instructors")
        professors_list = split_multi_instructors(professor_raw_field)
        if len(professors_list) > 1:
            m_multi += 1

        rmp_primary, per_matches, aggregate_reason = match_professors_to_rmp_multi(
            professor_raw_field, rmp_index,
            fuzzy_cutoff=args.fuzzy_cutoff, min_ratings_prefer=args.min_ratings_prefer
        )

        # metrics tally
        if aggregate_reason.startswith("exact"): m_exact += 1
        elif aggregate_reason.startswith("alias"): m_alias += 1
        elif aggregate_reason.startswith("fuzzy"): m_fuzzy += 1
        else: m_no += 1

        meeting = parse_meeting_time(course.get("time") or course.get("meeting") or course.get("schedule"))
        credits_val, credits_min, credits_max = parse_credits(course.get("credits"))

        enriched = {
            "code": code,
            "title": title,
            "section": section,
            "credits": credits_val,
            "credits_min": credits_min,
            "credits_max": credits_max,
            "instruction_method": method,
            "location": course.get("location"),
            "professors_raw": professors_list,     # list for transparency
            "meeting": meeting,
            # store the chosen primary RMP summary
            "rmp_primary": rmp_primary or {
                "rating": None, "num_ratings": None, "difficulty": None,
                "would_take_again_%": None, "url": None, "name": None, "department": None
            },
            # and all per-instructor attempts
            "rmp_per_instructor": per_matches,
            "rmp_match_reason": aggregate_reason,
            "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        enriched_docs.append(enriched)

        if code and section and not args.dry_run:
            ops.append(UpdateOne(
                {"code": code, "section": section},
                {"$set": enriched},
                upsert=True
            ))
        # issues when match is missing or fuzzy (manual review later)
        if aggregate_reason.startswith("no_") or aggregate_reason.startswith("fuzzy"):
            extract_issues.append({
                "code": code,
                "section": section,
                "professors_raw": professors_list,
                "match_reason": aggregate_reason
            })
        # issues for missing keys
        if not code or not section:
            extract_issues.append({
                "code": code, "section": section,
                "professors_raw": professors_list,
                "match_reason": f"bad_key:{aggregate_reason}"
            })

    # Mongo writes
    if not args.dry_run:
        try:
            if ops:
                res = col_out.bulk_write(ops, ordered=False)
                print(f"[write] upserted/modified {res.upserted_count or 0}+{res.modified_count or 0} docs "
                      f"({len(ops)} ops) into {args.out_col}")
        except PyMongoError as e:
            print(f"[write][WARN] bulk_write failed: {e}")

        try:
            issues_out.delete_many({})
            if extract_issues:
                issues_out.insert_many(extract_issues)
            print(f"[issues] logged {len(extract_issues)} rows to {args.issues_col}")
        except PyMongoError as e:
            print(f"[issues][WARN] issues write failed: {e}")
    else:
        print("[dry_run] Skipped Mongo writes (out_col & issues_col).")

    # Local artifacts
    Path("out").mkdir(exist_ok=True)
    with open("out/courses_enriched.json", "w", encoding="utf-8") as f:
        json.dump(enriched_docs, f, indent=2)
    with open("out/extract_issues.json", "w", encoding="utf-8") as f:
        json.dump(extract_issues, f, indent=2)
    if args.export_csv:
        export_csv(enriched_docs, "out/courses_enriched.csv")

    # Summary
    print(f"[done] processed: {m_total} courses")
    print(f"[match] exact={m_exact} alias={m_alias} fuzzy={m_fuzzy} no_match={m_no}  multi_instructor={m_multi}")
    print("Saved: out/courses_enriched.json, out/extract_issues.json" + (", out/courses_enriched.csv" if args.export_csv else ""))
    if args.dry_run:
        print("NOTE: --dry_run was enabled; no Mongo writes were performed.")


def main():
    args = parse_args()
    enrich_courses(args)


if __name__ == "__main__":
    main()
