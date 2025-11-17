"""
DooleyHelpz Integrated Recommendation Engine
Combines Fibonacci Heap with actual major/GER tracking
"""

import re
from typing import Dict, List, Set, Optional, Tuple
from fibonacci_heap import FibonacciHeap


CSBA_REQUIREMENTS = {
    "must": ["MATH111", "MATH112", "MATH221", "CS170", "CS171", "CS224", "CS253",
             "CS255", "CS326", "CS350"],
    "elective_groups": [
        {"choose": 1, "courses": ["CS370", "CS371W"]},
        {"choose": 2, "courses": ["CS325", "CS329", "CS334", "CS377"]},
        {"choose": 2, "courses": ["CS312", "CS325", "CS326", "CS329", "CS334", "CS350", 
                                  "CS370", "CS371W", "CS377", "CS385", "CS424", "CS441", 
                                  "CS443", "CS444", "CS452", "CS463", "CS470", "CS480", 
                                  "CS485", "CS495A", "CS495BW", "CS497R", "CS498R"]}
    ]
}

CSBS_REQUIREMENTS = {
    "must": ["MATH111", "MATH112", "MATH221", "CS170", "CS171", "CS224", "CS253", 
             "CS255", "CS326", "CS350"],
    "elective_groups": [
        {"choose": 1, "courses": ["CS370", "CS371W"]},
        {"choose": 1, "courses": ["CS325", "CS329", "CS334", "CS377"]},
        {"choose": 2, "courses": ["CS312", "CS325", "CS326", "CS329", "CS334", "CS350", 
                                  "CS370", "CS371W", "CS377", "CS385"]},
        {"choose": 1, "courses": ["CS312", "CS325", "CS326", "CS329", "CS334", "CS350", 
                                  "CS370", "CS371W", "CS377", "CS385", "MATH315", "MATH346", 
                                  "MATH347", "MATH351", "MATH361", "MATH362"]},
        {"choose": 3, "courses": ["CS424", "CS441", "CS443", "CS444", "CS452", "CS463", 
                                  "CS470", "CS480", "CS485", "CS495A", "CS495BW", "CS497R", "CS498R"]}
    ]
}

GER_REQUIREMENTS = {
    "ECS": 1, "HLTH": 1, "FS": 1, "FW": 1, "PE": 1,
    "HA": 1, "NS": 1, "QR": 1, "SS": 1, "IC": 2,
    "ETHN": 1, "CW": 2, "XA": 1
}



def normalize_course_code(course_code: str) -> str:

    if not course_code:
        return course_code
    
    code = course_code.strip().upper().replace(" ", "")
    
    if code.endswith('ZL'):
        return code[:-2] + 'L'
    elif code.endswith('Z'):
        return code[:-1]
    
    return code



class IntegratedRecommendationEngine:

    def __init__(self):
        self.time_pattern = re.compile(r'([MTWRF]+)\s+(\d{1,2}:\d{2}[ap]m)-(\d{1,2}:\d{2}[ap]m)')
    
    def generate_recommendations(self,
                                user_courses: Dict,
                                user_prefs: Dict,
                                all_courses: List[Dict],
                                num_recommendations: int = 15) -> List[Dict]:
        """
        Main recommendation function
        
        Args:
            user_courses: {incoming_transfer_courses: [...], incoming_test_courses: [...], emory_courses: [...]}
            user_prefs: {interests: [...], timeUnavailable: [...], timePreference: [...], degreeType: "BS", ...}
            all_courses: List of course dicts from MongoDB
            num_recommendations: How many to return
        
        Returns:
            List of recommended courses with scores
        """
        # 1. Normalize and collect completed courses
        completed = set()
        for course_list in ['incoming_transfer_courses', 'incoming_test_courses', 'emory_courses']:
            for code in user_courses.get(course_list, []):
                completed.add(normalize_course_code(code))
        
        # 2. Determine major requirements
        degree_type = user_prefs.get('degreeType', 'BS')
        major_reqs = CSBA_REQUIREMENTS if degree_type == 'BS' else CSBS_REQUIREMENTS
        
        # 3. Track what's still needed
        needed_must, needed_electives = self._get_remaining_requirements(completed, major_reqs)
        
        # 4. Parse user time constraints
        unavailable_blocks = self._parse_time_unavailable(user_prefs.get('timeUnavailable', []))
        time_pref = user_prefs.get('timePreference')
        
        # 5. Score all courses
        heap = FibonacciHeap()
        eligible_count = 0
        
        for course in all_courses:
            course_code = normalize_course_code(course.get('code', ''))
            
            # Skip if already taken
            if course_code in completed:
                continue
            
            # Skip if time conflict
            if self._has_time_conflict(course, unavailable_blocks):
                continue
            
            # Calculate score
            score = self._calculate_score(
                course=course,
                course_code=course_code,
                needed_must=needed_must,
                needed_electives=needed_electives,
                interests=user_prefs.get('interests', []),
                time_pref=time_pref,
                completed=completed
            )
            
            if score > 0:
                course_with_score = course.copy()
                course_with_score['recommendation_score'] = score
                course_with_score['normalized_code'] = course_code
                heap.insert(score, course_with_score)
                eligible_count += 1
        
        # 6. Extract top K
        recommendations = heap.extract_top_k(num_recommendations)
        
        print(f"Processed {len(all_courses)} courses")
        print(f"Found {eligible_count} eligible courses")
        print(f"Returning top {len(recommendations)} recommendations")
        
        return recommendations
    
    def _get_remaining_requirements(self, completed: Set[str], major_reqs: Dict) -> Tuple[Set[str], List[Dict]]:
        # Must courses
        needed_must = set(major_reqs['must']) - completed
        
        # Elective groups
        needed_electives = []
        for group in major_reqs['elective_groups']:
            remaining = [c for c in group['courses'] if c not in completed]
            if remaining:
                needed_electives.append({
                    'choose': group['choose'],
                    'courses': set(remaining)
                })
        
        return needed_must, needed_electives
    
    def _parse_time_unavailable(self, time_unavailable: List[Dict]) -> List[Tuple]:
        blocks = []
        for block in time_unavailable:
            days = block.get('days', [])
            if isinstance(days, str):
                days = [days]
            
            start = block.get('start', block.get('start_time', ''))
            end = block.get('end', block.get('end_time', ''))
            
            if not start or not end:
                continue
            
            start_min = self._time_to_minutes(start)
            end_min = self._time_to_minutes(end)
            
            for day in days:
                blocks.append((day, start_min, end_min))
        
        return blocks
    
    def _time_to_minutes(self, time_str: str) -> int:
        match = re.match(r'(\d{1,2}):(\d{2})([ap]m)', time_str.lower())
        if not match:
            return 0
        
        hour = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        return hour * 60 + minute
    
    def _has_time_conflict(self, course: Dict, unavailable_blocks: List[Tuple]) -> bool:
        meeting = course.get('meeting', {})
        days = meeting.get('days', [])
        start_min = meeting.get('start_min')
        end_min = meeting.get('end_min')
        
        if not days or start_min is None or end_min is None:
            return False
        
        day_map = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 
                   'Th': 'Thursday', 'F': 'Friday'}
        
        for day_abbr in days:
            day_full = day_map.get(day_abbr, day_abbr)
            
            for unavail_day, unavail_start, unavail_end in unavailable_blocks:
                if day_full == unavail_day or day_abbr == unavail_day:
                    # Check overlap
                    if not (end_min <= unavail_start or start_min >= unavail_end):
                        return True
        
        return False
    
    def _calculate_score(self,
                        course: Dict,
                        course_code: str,
                        needed_must: Set[str],
                        needed_electives: List[Dict],
                        interests: List[str],
                        time_pref: Optional[List[str]],
                        completed: Set[str]) -> float:
        """
        Calculate recommendation score for a course
        
        Scoring factors:
        1. Required for major (40 points)
        2. Elective for major (30 points)
        3. Professor rating (15 points)
        4. Matches interests (10 points)
        5. Time preference (5 points)
        """
        score = 0.0
        
        # 1. MAJOR REQUIREMENTS (highest priority)
        if course_code in needed_must:
            score += 40.0
        else:
            # Check elective groups
            for group in needed_electives:
                if course_code in group['courses']:
                    score += 30.0
                    break
        
        # 2. PROFESSOR RATING
        rmp = course.get('rmp', {})
        rating = rmp.get('rating')
        if rating:
            # Normalize 0-5 to 0-15 points
            score += (rating / 5.0) * 15.0
        else:
            # No rating = neutral (7.5 points)
            score += 7.5
        
        # 3. INTERESTS
        title = course.get('title', '').lower()
        for interest in interests:
            interest_lower = interest.lower()
            if interest_lower in title or interest_lower in course_code.lower():
                score += 10.0
                break
        
        # 4. TIME PREFERENCE
        if time_pref and len(time_pref) == 2:
            meeting = course.get('meeting', {})
            start_min = meeting.get('start_min')
            
            if start_min:
                pref_start_min = self._time_to_minutes(time_pref[0])
                pref_end_min = self._time_to_minutes(time_pref[1])
                
                # Course starts within preferred window
                if pref_start_min <= start_min <= pref_end_min:
                    score += 5.0
        
        # 5. BONUS: Check prerequisites are met
        prereqs = course.get('prerequisites', [[]])
        if prereqs and prereqs != [[]]:
            # If has prereqs, check if met
            prereqs_met = self._check_prerequisites(prereqs, completed)
            if not prereqs_met:
                # Penalize heavily if prereqs not met
                score *= 0.1
        
        return score
    
    def _check_prerequisites(self, prereqs: List[List[str]], completed: Set[str]) -> bool:

        if not prereqs or prereqs == [[]]:
            return True
        
        for or_group in prereqs:
            if not or_group:
                continue
            
            # Need at least one from this OR group
            has_one = any(normalize_course_code(p) in completed for p in or_group)
            
            if not has_one:
                return False
        
        return True



def generate_schedule_for_user(shared_id: int, 
                               course_col, 
                               pref_col, 
                               enriched_courses_col,
                               num_recommendations: int = 15) -> Dict:
    """
    Flask-compatible function to generate recommendations
    
    Args:
        shared_id: User's anonymous ID
        course_col: MongoDB collection for user courses
        pref_col: MongoDB collection for user preferences
        enriched_courses_col: MongoDB collection for course catalog
        num_recommendations: How many courses to recommend
    
    Returns:
        Dict with recommendations and metadata
    """
    # Fetch user data
    user_courses = course_col.find_one(
        {"shared_id": shared_id},
        sort=[("_id", -1)]
    )
    
    user_prefs = pref_col.find_one(
        {"shared_id": shared_id},
        sort=[("_id", -1)]
    )
    
    if not user_courses or not user_prefs:
        return {
            "success": False,
            "error": "Missing data. Please complete transcript upload and preferences.",
            "has_courses": user_courses is not None,
            "has_preferences": user_prefs is not None
        }
    
    # Get all available courses
    all_courses = list(enriched_courses_col.find({}))
    
    # Generate recommendations
    engine = IntegratedRecommendationEngine()
    recommendations = engine.generate_recommendations(
        user_courses=user_courses,
        user_prefs=user_prefs,
        all_courses=all_courses,
        num_recommendations=num_recommendations
    )
    
    # Format for frontend
    formatted = []
    for rec in recommendations:
        formatted.append({
            "code": rec.get("code"),
            "title": rec.get("title"),
            "professor": rec.get("professor"),
            "credits": rec.get("credits"),
            "time": rec.get("time"),
            "meeting": rec.get("meeting"),
            "rmp": rec.get("rmp"),
            "score": round(rec.get("recommendation_score", 0), 2),
            "ger": rec.get("ger")
        })
    
    return {
        "success": True,
        "recommendations": formatted,
        "count": len(formatted),
        "metadata": {
            "degree_type": user_prefs.get("degreeType"),
            "year": user_prefs.get("year"),
            "interests": user_prefs.get("interests"),
            "total_courses_processed": len(all_courses)
        }
    }


if __name__ == "__main__":
    # Test normalization, comment oout if not needed later
    print("Testing course code normalization:")
    test_codes = ["MATH112Z", "MATH112ZL", "CS170", "CHEM150L"]
    for code in test_codes:
        print(f"  {code} -> {normalize_course_code(code)}")