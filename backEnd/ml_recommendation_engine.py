import os
import math
import re
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

import numpy as np

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    print("[WARN] joblib not available, ML model will use rule-based scoring")

from dotenv import load_dotenv

load_dotenv()

# Path to the trained model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "recommender_ml.joblib")

# Global model cache
_cached_model = None


def load_ml_model():
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    
    if not JOBLIB_AVAILABLE:
        return None
    
    if os.path.exists(MODEL_PATH):
        try:
            _cached_model = joblib.load(MODEL_PATH)
            print(f"[ML Engine] Loaded model from {MODEL_PATH}")
            return _cached_model
        except Exception as e:
            print(f"[ML Engine] Failed to load model: {e}")
            return None
    else:
        print(f"[ML Engine] Model file not found at {MODEL_PATH}")
        return None


def norm(val, lo, hi, invert=False):
    if val is None:
        return 0.0
    try:
        v = max(lo, min(hi, float(val)))
    except (TypeError, ValueError):
        return 0.0
    x = (v - lo) / (hi - lo) if hi > lo else 0.0
    return 1.0 - x if invert else x


def safe_num_ratings(val):
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def extract_features(course: Dict[str, Any]) -> np.ndarray:
    rmp = course.get("rmp") or {}
    
    rating = norm(rmp.get("rating"), 0, 5)
    again = norm(rmp.get("would_take_again_%") or rmp.get("would_take_again_pct"), 0, 100)
    easy = norm(rmp.get("difficulty"), 1, 5, invert=True)
    
    raw_num = rmp.get("num_ratings")
    num = safe_num_ratings(raw_num)
    pop = math.log1p(num) / math.log1p(100) if num > 0 else 0.0
    
    return np.array([rating, again, easy, pop], dtype=float)


def score_course_rule_based(course: Dict[str, Any], 
                            w_rating=0.55, w_again=0.15, w_easy=0.15, w_pop=0.15) -> float:
    features = extract_features(course)
    rating, again, easy, pop = features
    return (w_rating * rating) + (w_again * again) + (w_easy * easy) + (w_pop * pop)


def score_course_ml(course: Dict[str, Any], model) -> float:
    if model is None:
        return score_course_rule_based(course)
    
    features = extract_features(course)
    try:
        score = float(model.predict(features.reshape(1, -1))[0])
        return score
    except Exception as e:
        print(f"[ML Engine] Prediction failed: {e}")
        return score_course_rule_based(course)


def normalize_code(code: str) -> str:
    """Normalize course code."""
    if not code:
        return ""
    return re.sub(r'\s+', '', str(code).upper())


def parse_meeting_time(time_str: str) -> Dict[str, Any]:
    """Parse meeting time string into structured format."""
    result = {"days": [], "start_min": None, "end_min": None, "raw": time_str}
    
    if not time_str or time_str == "TBA":
        return result
    
    parts = time_str.split(None, 1)
    if len(parts) != 2:
        return result
    
    days_part, times_part = parts
    
    # Parse days
    DAY_TOKENS = ["Th", "M", "T", "W", "F"]
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
            i += 1
    
    result["days"] = days
    
    # Parse times
    time_match = re.match(
        r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)$',
        times_part.strip(),
        re.IGNORECASE
    )
    
    if time_match:
        start_h = int(time_match.group(1))
        start_m = int(time_match.group(2) or 0)
        start_ampm = time_match.group(3).lower()
        end_h = int(time_match.group(4))
        end_m = int(time_match.group(5) or 0)
        end_ampm = time_match.group(6).lower()
        
        if start_h == 12:
            start_h = 0
        if start_ampm == "pm":
            start_h += 12
        
        if end_h == 12:
            end_h = 0
        if end_ampm == "pm":
            end_h += 12
        
        result["start_min"] = start_h * 60 + start_m
        result["end_min"] = end_h * 60 + end_m
    
    return result


def check_time_conflict(course: Dict[str, Any], unavailable_blocks: List[Dict]) -> bool:
    if not unavailable_blocks:
        return False
    
    meeting = course.get("meeting") or {}
    if isinstance(meeting, dict):
        days = meeting.get("days") or []
        start = meeting.get("start_min")
        end = meeting.get("end_min")
    else:
        # Parse from time string
        time_str = course.get("time", "")
        parsed = parse_meeting_time(time_str)
        days = parsed["days"]
        start = parsed["start_min"]
        end = parsed["end_min"]
    
    if start is None or end is None or not days:
        return False
    
    DAY_MAP = {
        "M": "Monday", "Mon": "Monday", "Monday": "Monday",
        "T": "Tuesday", "Tue": "Tuesday", "Tuesday": "Tuesday",
        "W": "Wednesday", "Wed": "Wednesday", "Wednesday": "Wednesday",
        "Th": "Thursday", "Thu": "Thursday", "Thursday": "Thursday",
        "F": "Friday", "Fri": "Friday", "Friday": "Friday",
    }
    
    for day in days:
        day_full = DAY_MAP.get(day, day)
        
        for block in unavailable_blocks:
            block_day = block.get("day", "")
            block_day_full = DAY_MAP.get(block_day, block_day)
            
            if day_full != block_day_full:
                continue
            
            try:
                block_start_parts = block.get("start", "").split(":")
                block_end_parts = block.get("end", "").split(":")
                
                block_start = int(block_start_parts[0]) * 60 + int(block_start_parts[1] if len(block_start_parts) > 1 else 0)
                block_end = int(block_end_parts[0]) * 60 + int(block_end_parts[1] if len(block_end_parts) > 1 else 0)
                
                # Check overlap
                if max(start, block_start) < min(end, block_end):
                    return True
            except (ValueError, IndexError):
                continue
    
    return False


def filter_completed_courses(courses: List[Dict], completed_codes: Set[str]) -> List[Dict]:
    completed_normalized = {normalize_code(c) for c in completed_codes}
    return [c for c in courses if normalize_code(c.get("code", "")) not in completed_normalized]


def build_conflict_free_schedules(
    ranked_courses: List[Dict],
    num_schedules: int = 10,
    max_credits: int = 18,
    min_courses: int = 4,
    max_courses: int = 6
) -> List[Dict]:
    def safe_credits(raw, default: float = 3.0) -> float:
        
        if raw is None:
            return default
        if isinstance(raw, (int, float)):
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default

        if isinstance(raw, str):
            # Extract numbers and optional range (supports hyphen or en dash)
            match = re.match(r"\s*(\d+(?:\.\d+)?)(?:\s*[-\u2013]\s*(\d+(?:\.\d+)?))?", raw)
            if match:
                first = float(match.group(1))
                second = float(match.group(2)) if match.group(2) else None
                # Use upper bound if present, otherwise first number
                return second if second is not None else first
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    schedules = []
    used_root_codes = set()
    
    for root_course in ranked_courses[:50]:  # Try first 50 as roots
        root_code = normalize_code(root_course.get("code", ""))
        if root_code in used_root_codes:
            continue
        
        schedule_courses = [root_course]
        total_credits = safe_credits(root_course.get("credits", 3))
        schedule_blocks = []
        
        # Get time blocks for root course
        meeting = root_course.get("meeting") or {}
        if isinstance(meeting, dict):
            days = meeting.get("days") or []
            start = meeting.get("start_min")
            end = meeting.get("end_min")
            if days and start is not None and end is not None:
                for d in days:
                    schedule_blocks.append({"day": d, "start": start, "end": end})
        
        # Add more courses
        for candidate in ranked_courses:
            if len(schedule_courses) >= max_courses:
                break
            if total_credits >= max_credits:
                break
            
            cand_code = normalize_code(candidate.get("code", ""))
            if cand_code == root_code:
                continue
            if any(normalize_code(c.get("code", "")) == cand_code for c in schedule_courses):
                continue
            
            # Check time conflict with current schedule
            cand_meeting = candidate.get("meeting") or {}
            if isinstance(cand_meeting, dict):
                cand_days = cand_meeting.get("days") or []
                cand_start = cand_meeting.get("start_min")
                cand_end = cand_meeting.get("end_min")
            else:
                parsed = parse_meeting_time(candidate.get("time", ""))
                cand_days = parsed["days"]
                cand_start = parsed["start_min"]
                cand_end = parsed["end_min"]
            
            conflict = False
            if cand_days and cand_start is not None and cand_end is not None:
                for block in schedule_blocks:
                    if block["day"] in cand_days:
                        if max(block["start"], cand_start) < min(block["end"], cand_end):
                            conflict = True
                            break
            
            if conflict:
                continue
            
            # Add course to schedule
            cand_credits = safe_credits(candidate.get("credits", 3))
            if total_credits + cand_credits > max_credits:
                continue
            
            schedule_courses.append(candidate)
            total_credits += cand_credits
            
            # Add time blocks
            if cand_days and cand_start is not None and cand_end is not None:
                for d in cand_days:
                    schedule_blocks.append({"day": d, "start": cand_start, "end": cand_end})
        
        if len(schedule_courses) >= min_courses:
            used_root_codes.add(root_code)
            
            # Calculate total score
            total_score = sum(c.get("score", 0) for c in schedule_courses)
            
            schedules.append({
                "root_course_code": root_code,
                "courses": schedule_courses,
                "course_count": len(schedule_courses),
                "total_credits": total_credits,
                "total_score": total_score
            })
            
            if len(schedules) >= num_schedules:
                break
    
    return schedules


def generate_schedule_for_user(
    uid: str,
    course_col,
    pref_col,
    enriched_courses_col,
    rmp_col,
    basic_courses_col,
    num_recommendations: int = 10
) -> Dict[str, Any]:
    try:
        # Load ML model
        model = load_ml_model()
        
        # Get user courses
        user_courses = course_col.find_one({"uid": uid}, sort=[("_id", -1)])
        if not user_courses:
            return {"success": False, "error": "No course data found for user"}
        
        # Get user preferences
        user_prefs = pref_col.find_one({"uid": uid}, sort=[("_id", -1)])
        if not user_prefs:
            return {"success": False, "error": "No preferences found for user"}
        
        # Build completed courses set
        completed_codes = set()
        for key in ["incoming_transfer_courses", "incoming_test_courses", "emory_courses", "spring_2026_courses"]:
            courses = user_courses.get(key, [])
            if courses:
                completed_codes.update(courses)
        
        # Get time unavailable blocks
        time_unavailable = user_prefs.get("timeUnavailable", [])
        
        # Get all enriched courses
        all_courses = list(enriched_courses_col.find({}))
        
        # Filter out completed courses
        available_courses = filter_completed_courses(all_courses, completed_codes)
        
        # Filter out courses that conflict with unavailable times
        filtered_courses = []
        for course in available_courses:
            if not check_time_conflict(course, time_unavailable):
                filtered_courses.append(course)
        
        if not filtered_courses:
            return {"success": False, "error": "No available courses after filtering"}
        
        # Score courses using ML model
        for course in filtered_courses:
            course["score"] = score_course_ml(course, model)
            course["normalized_code"] = normalize_code(course.get("code", ""))
        
        # Sort by score
        filtered_courses.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Get preferred credits
        pref_credits = user_prefs.get("preferredCredits", 16)
        try:
            max_credits = int(pref_credits)
        except (ValueError, TypeError):
            max_credits = 16
        
        # Build schedules
        schedules = build_conflict_free_schedules(
            filtered_courses,
            num_schedules=num_recommendations,
            max_credits=max_credits
        )
        
        if not schedules:
            return {"success": False, "error": "Could not build any valid schedules"}
        
        # Clean up courses for JSON serialization
        for schedule in schedules:
            for course in schedule["courses"]:
                course.pop("_id", None)
        
        return {
            "success": True,
            "schedules": schedules,
            "count": len(schedules),
            "engine": "ml",
            "metadata": {
                "model_loaded": model is not None,
                "total_available_courses": len(filtered_courses),
                "completed_courses": len(completed_codes),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
