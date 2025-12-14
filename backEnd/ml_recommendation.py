import os
import math
import numpy as np
import joblib
from typing import Dict, List, Any, Optional
from pathlib import Path

from ml_course_qualification import build_qualified_courses_for_user

# Path to the trained ML model
MODEL_PATH = Path(__file__).parent / "recommender_ml.joblib"

# -------------------------------------------------------------------
# Feature Extraction & Scoring
# -------------------------------------------------------------------

def norm(val, lo, hi, invert=False):
    """Normalize value to [0, 1] range."""
    if val is None:
        return 0.0
    try:
        v = max(lo, min(hi, float(val)))
    except (TypeError, ValueError):
        return 0.0
    x = (v - lo) / (hi - lo) if hi > lo else 0.0
    return 1.0 - x if invert else x

def safe_num_ratings(val):
    """Convert num_ratings to float safely."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0

def extract_features_from_doc(doc):
    """
    Extract ML model features from course document.

    Features:
      [rating_norm, would_take_again_norm, difficulty_norm, popularity_norm]
    """
    rmp = doc.get("rmp") or {}

    # Rating: 0-5 scale
    rating = norm(rmp.get("rating"), 0, 5)

    # Would take again: 0-100 scale (percentage)
    again_raw = (
        rmp.get("would_take_again_%")
        or rmp.get("would_take_again_pct")
        or rmp.get("would_take_again")
        or rmp.get("would_take_again_percent")
        or rmp.get("wouldTakeAgain")
    )
    again = norm(again_raw, 0, 100)

    # Difficulty: 1-5 scale (inverted so easier = higher score)
    difficulty_raw = (
        rmp.get("difficulty")
        or rmp.get("difficulty_rating")
        or rmp.get("difficultyScore")
    )
    easy = norm(difficulty_raw, 1, 5, invert=True)

    # Popularity: log-scaled number of ratings
    raw_num = rmp.get("num_ratings")
    num = safe_num_ratings(raw_num)
    pop = math.log1p(num) / math.log1p(100) if num > 0 else 0.0

    return np.array([rating, again, easy, pop], dtype=float)

def score_course_rule_based(doc, w_rating=0.55, w_again=0.15, w_easy=0.15, w_pop=0.15):
    """Fallback rule-based scoring if ML model not available."""
    features = extract_features_from_doc(doc)
    rating, again, easy, pop = features
    return (w_rating * rating) + (w_again * again) + (w_easy * easy) + (w_pop * pop)

# -------------------------------------------------------------------
# ML Model Loading
# -------------------------------------------------------------------

_cached_model = None
_load_error: Optional[str] = None

def load_ml_model():
    """Load the trained ML model from disk."""
    global _cached_model, _load_error

    if _cached_model is not None:
        return _cached_model

    if _load_error:
        return None

    if not MODEL_PATH.exists():
        _load_error = f"Model file not found: {MODEL_PATH}"
        print(f"[ML Recommendation] {_load_error}")
        return None

    try:
        _cached_model = joblib.load(MODEL_PATH)
        print(f"[ML Recommendation] Loaded model from {MODEL_PATH}")
        return _cached_model
    except Exception as e:
        _load_error = str(e)
        print(f"[ML Recommendation] Failed to load model: {e}")
        return None

def score_course_fibheap_style(course: Dict[str, Any], reason_major_must: bool, reason_major_elec: bool,
                               reason_ger_due: list, interests: list, is_cs: bool) -> float:
    """
    Score using FibHeap's intelligent prioritization system.

    Scoring factors (prioritizing CS major courses):
    1. Required for major (50 points)
    2. CS courses (40 points)
    3. Elective for major (35 points)
    4. GER due this semester (20 points)
    5. Professor rating (15 points)
    6. Matches interests (10 points)
    """
    score = 0.0

    # 1. MAJOR MUST (highest priority)
    if reason_major_must:
        score += 50.0

    # 2. CS COURSES (high priority for CS majors)
    if is_cs:
        score += 40.0

    # 3. MAJOR ELECTIVES
    if reason_major_elec:
        score += 35.0

    # 4. GER DUE THIS SEMESTER (lower priority than CS)
    if reason_ger_due:
        score += 20.0

    # 5. PROFESSOR RATING
    rmp = course.get('rmp', {})
    rating = rmp.get('rating')
    if rating:
        try:
            # Normalize 0-5 to 0-15 points
            score += (float(rating) / 5.0) * 15.0
        except (TypeError, ValueError):
            score += 7.5
    else:
        score += 7.5  # No rating = neutral

    # 6. INTERESTS
    title = (course.get('title') or '').lower()
    code = (course.get('code') or '').lower()
    for interest in (interests or []):
        interest_lower = str(interest).lower()
        if interest_lower in title or interest_lower in code:
            score += 10.0
            break

    return score

def score_course_ml(course: Dict[str, Any], model, interests: list = None) -> tuple[float, bool]:
    """
    Score a course using FibHeap's intelligent prioritization.

    This now uses the same scoring logic as integrated_recommendation_engine
    for better, more consistent results.

    Returns:
        (score, used_fallback)
    """
    # Use FibHeap-style scoring instead of ML model
    reason_major_must = course.get('reason_major_must', False)
    reason_major_elec = course.get('reason_major_elec', False)
    reason_ger_due = course.get('reason_ger_due', [])
    code = course.get('code', '')
    is_cs = is_cs_course(code)

    score = score_course_fibheap_style(
        course,
        reason_major_must,
        reason_major_elec,
        reason_ger_due,
        interests or [],
        is_cs
    )

    return score, False

# -------------------------------------------------------------------
# Priority Bucketing
# -------------------------------------------------------------------

def is_cs_course(code: str) -> bool:
    """Check if course code is a CS course."""
    return isinstance(code, str) and code.upper().startswith("CS")

def bucket_and_prioritize_courses(scored_courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort courses into priority buckets:
      1. Major MUST courses (required for CS degree)
      2. CS electives (major_elec or CS courses)
      3. GER courses that are DUE this semester
      4. Other courses

    Within each bucket, sort by ML score descending.

    Returns prioritized list (high priority first).
    """
    bucket_major_must = []
    bucket_cs_electives = []
    bucket_ger_due = []
    bucket_other = []

    for course in scored_courses:
        # Bucket 1: Major MUST courses (highest priority!)
        if course.get("reason_major_must"):
            bucket_major_must.append(course)

        # Bucket 2: CS electives (second priority)
        elif course.get("reason_major_elec") or is_cs_course(course.get("code")):
            bucket_cs_electives.append(course)

        # Bucket 3: GERs due THIS semester (third priority)
        elif course.get("reason_ger_due"):
            bucket_ger_due.append(course)

        # Bucket 4: Pure electives (lowest priority)
        else:
            bucket_other.append(course)

    # Sort each bucket by ML score (descending)
    for bucket in (bucket_major_must, bucket_cs_electives, bucket_ger_due, bucket_other):
        bucket.sort(key=lambda c: c.get("score_ml", 0), reverse=True)

    # Combine buckets in priority order: MAJOR -> CS -> GER -> OTHER
    prioritized = (
        bucket_major_must +
        bucket_cs_electives +
        bucket_ger_due +
        bucket_other
    )

    return prioritized

# -------------------------------------------------------------------
# Main Recommendation Function
# -------------------------------------------------------------------

def recommend_courses_for_user(
    uid: str,
    course_col,
    pref_col,
    enriched_courses_col,
    basic_courses_col,
    rmp_col,
    top_n: int = 200,
    min_rating: float = 0.0,
    instruction_method: str = None,
    use_trained_model: bool = True
) -> list:
    """
    Main ML recommendation function adapted for MongoDB.

    Steps:
      1. Build qualified courses (filters by prereqs, GER, major, time, etc.)
      2. Attach RMP data to courses
      3. Score each course with ML model
      4. Bucket courses by priority (GER due -> major must -> CS electives -> other)
      5. Return top N prioritized courses

    Args:
        uid: User Firebase UID
        course_col: MongoDB Users.TestCourses collection
        pref_col: MongoDB Users.UserPreferences collection
        enriched_courses_col: MongoDB DetailedCourses.CoursesEnriched collection
        basic_courses_col: MongoDB DetailedCourses.DetailedCourses collection
        rmp_col: MongoDB RMP.RMP collection
        top_n: Number of top courses to return
        min_rating: Minimum RMP rating filter
        instruction_method: Filter by instruction method
        use_trained_model: Whether to use ML model or fallback to rule-based

    Returns:
        List of top N recommended courses with scores and annotations
    """
    print(f"[ML Recommendation] Starting recommendation for user {uid}")

    # 1. Build qualified courses using the smart filtering logic
    try:
        qualified = build_qualified_courses_for_user(
            uid=uid,
            course_col=course_col,
            pref_col=pref_col,
            enriched_courses_col=enriched_courses_col,
            basic_courses_col=basic_courses_col,
            min_rating=min_rating,
            instruction_method=instruction_method
        )
    except Exception as e:
        print(f"[ML Recommendation] Error building qualified courses: {e}")
        return []

    if not qualified:
        print(f"[ML Recommendation] No qualified courses for user {uid}")
        return []

    print(f"[ML Recommendation] {len(qualified)} qualified courses, now scoring with FibHeap-style prioritization")

    # 2. Get user interests for interest matching
    user_prefs = pref_col.find_one({"uid": uid}, sort=[("_id", -1)])
    interests = user_prefs.get("interests", []) if user_prefs else []

    # 3. Score each course using FibHeap-style scoring
    scored = []

    for doc in qualified:
        score_ml, _ = score_course_ml(doc, None, interests)

        # Add score directly to existing dict (avoid copying)
        doc["score_ml"] = score_ml
        doc["score_source"] = "fibheap_style"
        scored.append(doc)

    # 4. Bucket and prioritize courses
    prioritized = bucket_and_prioritize_courses(scored)

    # 5. Return top N
    top_courses = prioritized[:top_n]

    ger_due_count = sum(1 for c in top_courses if c.get('reason_ger_due'))
    major_must_count = sum(1 for c in top_courses if c.get('reason_major_must'))
    major_elec_count = sum(1 for c in top_courses if c.get('reason_major_elec') or is_cs_course(c.get('code')))

    print(f"[ML Recommendation] Returning top {len(top_courses)} courses")
    print(f"[ML Recommendation] Priority breakdown:")
    print(f"  - GER due THIS semester: {ger_due_count}")
    print(f"  - Major MUST courses: {major_must_count}")
    print(f"  - CS electives: {major_elec_count}")
    print(f"  - Other: {len(top_courses) - ger_due_count - major_must_count - major_elec_count}")

    if top_courses:
        print(f"[ML Recommendation] Top 5 courses by priority:")
        for i, c in enumerate(top_courses[:5], 1):
            tags = []
            if c.get('reason_ger_due'): tags.append(f"GER:{','.join(c['reason_ger_due'])}")
            if c.get('reason_major_must'): tags.append("MAJOR-MUST")
            if c.get('reason_major_elec'): tags.append("MAJOR-ELEC")
            print(f"    {i}. {c.get('code')} (score: {c.get('score_ml', 0):.2f}) {' '.join(tags)}")

    return top_courses
