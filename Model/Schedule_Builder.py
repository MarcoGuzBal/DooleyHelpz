"""
Schedule_Builder.py

Builds a conflict-free final schedule for a student by combining:

  - ML-based course scoring from Recommended_Courses.recommend_for_student_ml
  - Student preference priorities (priorityOrder in synthetic_pref.json)
  - GER due, major requirements, CS electives, interests, and time preferences
  - Time conflict avoidance and credit caps

Usage (CLI):

  python Schedule_Builder.py --shared_id 000005 --n_courses 5 --top_n 200
"""

from __future__ import annotations

import argparse
from typing import List, Dict, Any

import pandas as pd

from Recommended_Courses import recommend_for_student_ml
from Courses_Qualified_new import fetch_user_doc


# -------------------- Time helpers --------------------

def hhmm_to_min(s: str | None) -> int | None:
    """
    Convert 'HH:MM' 24-hour string into minutes since midnight.
    Example: '08:30' -> 510
    """
    if not s:
        return None
    try:
        parts = s.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    except Exception:
        return None


def score_time(course_doc: Dict[str, Any] | pd.Series,
               time_pref: List[str]) -> float:
    """
    time_pref: ["HH:MM", "HH:MM"] (24h earliest, latest)

    Uses course_doc["meeting"]["start_min"] / ["end_min"].
    Returns a score ~[0,1], higher is better.
    """
    if not time_pref or len(time_pref) < 2:
        return 0.5  # neutral if no preference given

    # course_doc might be a dict or a pandas Series; both support .get
    mtg = course_doc.get("meeting") or {}
    start = mtg.get("start_min")
    end = mtg.get("end_min")

    if start is None or end is None:
        return 0.5  # neutral if unknown

    pref_start = hhmm_to_min(time_pref[0])
    pref_end = hhmm_to_min(time_pref[1])
    if pref_start is None or pref_end is None:
        return 0.5

    # Case 1: Class overlaps with preferred window → reward
    overlap_start = max(start, pref_start)
    overlap_end = min(end, pref_end)
    overlap = max(0, overlap_end - overlap_start)
    duration = max(0, end - start)

    if duration > 0 and overlap > 0:
        # 0.7 base + up to +0.3 if fully inside preferred window
        return 0.7 + 0.3 * (overlap / duration)

    # Case 2: No overlap → penalize by distance (up to 2 hours)
    if start < pref_start:
        distance = pref_start - start
    else:
        distance = start - pref_end

    SCALE = 120  # 2 hours
    penalty = min(1.0, distance / SCALE)
    return max(0.0, 1.0 - penalty)


# -------------------- Preference-aware ranking --------------------

def is_cs(code: Any) -> bool:
    return isinstance(code, str) and code.upper().startswith("CS")


def compute_preference_scores(shared_id: str,
                              top_n: int = 200) -> pd.DataFrame:
    """
    1) Calls recommend_for_student_ml(shared_id, top_n) to get ML-scored courses.
    2) Loads the student's preferences (priorityOrder, timePreference, etc.).
    3) Computes sub-scores:
         - GER, MAJOR, PROFESSOR_RATING (score_ml), INTERESTS, TIME_PREFERENCE
    4) Combines them into a single total_score using priorityOrder as weights.
    5) Returns a DataFrame sorted by total_score descending.
    """
    # 1) ML-based recommendations (this also writes a JSON backup for transparency)
    recs = recommend_for_student_ml(shared_id, top_n=top_n)

    if not recs:
        return pd.DataFrame()

    df = pd.DataFrame(recs)

    # 2) Student preferences from synthetic_pref.json via fetch_user_doc
    user_doc = fetch_user_doc(shared_id)
    pref = user_doc.get("pref", {})
    priority_order = pref.get("priorityOrder", []) or []
    time_pref = pref.get("timePreference", []) or []

    # 3) Sub-scores
    # GER score: 1.0 if course helps satisfy a GER that is actually due.
    # If the field does not exist yet, treat as "no GER due" (all zeros).
    if "reason_ger_due" in df.columns:
        ger_series = df["reason_ger_due"]
    else:
        # fallback: no GER_due info → all empty lists
        ger_series = pd.Series([[] for _ in range(len(df))])

    ger_scores = ger_series.apply(lambda lst: 1.0 if lst else 0.0)

    def major_score_row(row: pd.Series) -> float:
        if row.get("reason_major_must"):
            return 1.0
        if row.get("reason_major_elec") or is_cs(row.get("code")):
            # treat CS + major_elec as “good for major” but slightly less than must
            return 0.8
        return 0.0

    major_scores = df.apply(major_score_row, axis=1)
    interest_scores = df["reason_interest"].apply(lambda v: 1.0 if v else 0.0)
    time_scores = df.apply(lambda row: score_time(row, time_pref), axis=1)
    prof_scores = df["score_ml"]  # output of the ML model

    # 4) priorityOrder → weights
    # Recognized keys:
    #   GER_REQUIREMENTS, MAJOR_REQUIREMENTS, PROFESSOR_RATING,
    #   INTERESTS, TIME_PREFERENCE
    weights = {
        "GER_REQUIREMENTS": 0.0,
        "MAJOR_REQUIREMENTS": 0.0,
        "PROFESSOR_RATING": 0.0,
        "INTERESTS": 0.0,
        "TIME_PREFERENCE": 0.0,
    }

    # If priorityOrder is missing or empty, use a sensible default
    if not priority_order:
        priority_order = [
            "GER_REQUIREMENTS",
            "MAJOR_REQUIREMENTS",
            "PROFESSOR_RATING",
            "INTERESTS",
            "TIME_PREFERENCE",
        ]

    # Example: first priority gets 1.0, second 0.8, third 0.6, fourth 0.4, fifth 0.2
    PRIORITY_LEVELS = [1.0, 0.8, 0.6, 0.4, 0.2]
    for rank, key in enumerate(priority_order):
        if key in weights and rank < len(PRIORITY_LEVELS):
            weights[key] = PRIORITY_LEVELS[rank]

    # 5) total_score
    df["total_score"] = (
        weights["GER_REQUIREMENTS"] * ger_scores +
        weights["MAJOR_REQUIREMENTS"] * major_scores +
        weights["PROFESSOR_RATING"] * prof_scores +
        weights["INTERESTS"] * interest_scores +
        weights["TIME_PREFERENCE"] * time_scores
    )

    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)
    return df


# -------------------- Schedule builder (no time conflicts) --------------------

def build_schedule_from_ranked(df_ranked: pd.DataFrame,
                               shared_id: str,
                               n_courses: int = 5) -> pd.DataFrame:
    """
    Given a ranked DataFrame (with total_score) for a student,
    build a non-overlapping schedule of up to n_courses.

    - Enforces time conflict avoidance using meeting.days / start_min / end_min
    - Respects preferredCredits from the student's preferences (soft cap)
    - Ensures NO duplicate course codes in the final schedule
    """
    if df_ranked.empty:
        return pd.DataFrame()

    user_doc = fetch_user_doc(shared_id)
    pref = user_doc.get("pref", {})
    pref_cred = pref.get("preferredCredits") or 16

    selected_rows = []
    total_credits = 0.0
    # schedule_blocks[day] = list of (start, end) for already chosen courses
    schedule_blocks: Dict[str, List[tuple[int, int]]] = {}
    # 👇 NEW: track which course codes we've already selected
    used_codes: set[str] = set()

    for _, row in df_ranked.iterrows():
        if len(selected_rows) >= n_courses:
            break

        code = row.get("code")
        # skip if we've already chosen this course code (avoid repeats like two MATH112s)
        if isinstance(code, str) and code in used_codes:
            continue

        mtg = row.get("meeting") or {}
        days = mtg.get("days") or []
        start = mtg.get("start_min")
        end = mtg.get("end_min")

        # skip if we have no usable meeting time
        if start is None or end is None or not days:
            continue

        # credits
        try:
            credits = float(row.get("credits", 3.0))
        except Exception:
            credits = 3.0

        # credit cap check
        if total_credits + credits > float(pref_cred) + 1e-6:
            continue

        # time conflict check
        conflict = False
        for d in days:
            blocks = schedule_blocks.get(d, [])
            for (s, e) in blocks:
                # intervals overlap iff max starts < min ends
                if max(s, start) < min(e, end):
                    conflict = True
                    break
            if conflict:
                break

        if conflict:
            continue

        # accept this course
        selected_rows.append(row)
        total_credits += credits
        if isinstance(code, str):
            used_codes.add(code)

        for d in days:
            schedule_blocks.setdefault(d, []).append((start, end))

    if not selected_rows:
        return pd.DataFrame()

    schedule = pd.DataFrame(selected_rows).reset_index(drop=True)
    schedule["slot"] = range(1, len(schedule) + 1)

    # You can adjust which columns to show in the final table
    return schedule[[
        "slot",
        "code",
        "title",
        "meeting",
        "credits",
        "total_score",
    ]]



# -------------------- High-level helper --------------------

def get_schedule(shared_id: str,
                 n_courses: int = 5,
                 top_n_candidates: int = 200) -> pd.DataFrame:
    """
    Main public function.

    1) Compute preference-aware scores for many candidate courses.
    2) Build a conflict-free schedule from the top-ranked candidates.
    """
    df_ranked = compute_preference_scores(shared_id, top_n=top_n_candidates)
    if df_ranked.empty:
        print(f"[INFO] No ranked courses for student {shared_id}.")
        return pd.DataFrame()

    schedule = build_schedule_from_ranked(df_ranked, shared_id, n_courses=n_courses)
    if schedule.empty:
        print(f"[INFO] No conflict-free schedule could be built for student {shared_id}.")
    return schedule


# -------------------- CLI --------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared_id", type=str, required=True,
                        help="Synthetic shared_id of the student (e.g., '000005').")
    parser.add_argument("--n_courses", type=int, default=5,
                        help="Number of courses to include in the final schedule.")
    parser.add_argument("--top_n", type=int, default=200,
                        help="Number of top ML recommendations to consider as candidates.")
    args = parser.parse_args()

    schedule = get_schedule(args.shared_id,
                            n_courses=args.n_courses,
                            top_n_candidates=args.top_n)

    if schedule.empty:
        print("No schedule generated.")
    else:
        print("\nFinal schedule:")
        print(schedule.to_string(index=False))


if __name__ == "__main__":
    main()
