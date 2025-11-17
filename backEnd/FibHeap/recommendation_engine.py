import json
from typing import Dict, List, Set, Optional
from fibonacci_heap import FibonacciHeap
from course_heuristic_optimized import CourseHeuristic


class CourseRecommendationEngine:
    
    def __init__(self, 
                 course_catalog_path: str,
                 professor_ratings_path: Optional[str] = None,
                 major_requirements_path: Optional[str] = None):
        self.courses = self._load_courses(course_catalog_path)
        self.professor_ratings = self._load_professor_ratings(professor_ratings_path)
        self.major_requirements = self._load_major_requirements(major_requirements_path)
    
    def _load_courses(self, path: str) -> List[Dict]:
        courses = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    course = json.loads(line.strip())
                    courses.append(course)
                except json.JSONDecodeError:
                    continue
        return courses
    
    def _load_professor_ratings(self, path: Optional[str]) -> Dict[str, float]:
        if not path:
            return {}
        
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _load_major_requirements(self, path: Optional[str]) -> Dict[str, List[str]]:
        if not path:
            return {}
        
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def generate_recommendations(self,
                                user_profile: Dict,
                                transcript: List[Dict],
                                num_recommendations: int = 20) -> List[Dict]:
        courses_taken = self._parse_transcript(transcript)
        ger_requirements = self._determine_ger_needs(transcript, user_profile)
        
        heuristic = CourseHeuristic(
            user_profile=user_profile,
            courses_taken=courses_taken,
            professor_ratings=self.professor_ratings,
            major_requirements=self.major_requirements,
            ger_requirements=ger_requirements
        )
        
        heap = FibonacciHeap()
        eligible_count = 0
        
        for course in self.courses:
            score = heuristic.calculate_score(course)
            if score is not None:
                course_with_score = course.copy()
                course_with_score['recommendation_score'] = score
                course_with_score['score_breakdown'] = self._get_score_breakdown(
                    course, heuristic
                )
                
                heap.insert(score, course_with_score)
                eligible_count += 1
        
        recommendations = heap.extract_top_k(num_recommendations)
        
        print(f"Processed {len(self.courses)} courses")
        print(f"Found {eligible_count} eligible courses")
        print(f"Returning top {len(recommendations)} recommendations")
        
        return recommendations
    
    def _parse_transcript(self, transcript: List[Dict]) -> Set[str]:
        courses_taken = set()
        
        for entry in transcript:
            course_code = entry.get('code', '')
            if course_code:
                courses_taken.add(course_code)
        
        return courses_taken
    
    def _determine_ger_needs(self, transcript: List[Dict], user_profile: Dict) -> Dict[str, bool]:
        ger_categories = {
            'First-Year Writing': False,
            'First-Year Seminar': False,
            'Continued Writing': False,
            'Mathematics and Quantitative Reasoning': False,
            'Science, Nature, and Technology': False,
            'History, Society, and Culture': False,
            'Humanities, Arts, and Performance': False,
            'Physical Education': False,
        }
        
        for entry in transcript:
            ger = entry.get('ger', '')
            if ger:
                import re
                ger_category = re.sub(r'\s*\([^)]*\)', '', ger).strip()
                
                if ger_category in ger_categories:
                    ger_categories[ger_category] = True
        
        return ger_categories
    
    def _get_score_breakdown(self, course: Dict, heuristic: CourseHeuristic) -> Dict[str, float]:
        return {
            'professor_rating': heuristic._score_professor(course),
            'time_preference': heuristic._score_time_preference(course),
            'major_requirements': heuristic._score_major_requirements(course),
            'ger_requirements': heuristic._score_ger_requirements(course),
            'interests': heuristic._score_interests(course),
            'credit_fit': heuristic._score_credit_fit(course),
        }
    
    def filter_by_credits(self, 
                         recommendations: List[Dict],
                         target_credits: int,
                         tolerance: int = 1) -> List[Dict]:
        selected = []
        total_credits = 0
        
        for course in recommendations:
            credits_str = course.get('credits', '0')
            
            if '-' in credits_str:
                credits = int(credits_str.split('-')[0])
            else:
                try:
                    credits = int(credits_str)
                except ValueError:
                    continue
            
            if total_credits + credits <= target_credits + tolerance:
                selected.append(course)
                total_credits += credits
            
            if abs(total_credits - target_credits) <= tolerance:
                break
        
        return selected
    
    def generate_schedule(self, recommendations: List[Dict], max_courses: int = 5) -> Dict:
        schedule = {
            'Monday': [],
            'Tuesday': [],
            'Wednesday': [],
            'Thursday': [],
            'Friday': [],
            'Saturday': [],
        }

        selected_courses: List[Dict] = []
        used_codes: set = set()

        for course in recommendations[:max_courses * 2]:
            if len(selected_courses) >= max_courses:
                break

            code = course.get('code')
            if not code:
                continue
            if code in used_codes:
                continue

            schedule_location = course.get('schedule_location', '') or ''
            if not schedule_location:
                continue

            days = self._extract_days(schedule_location)
            if not days:
                continue

            if self._has_schedule_conflict_with_selected(course, selected_courses):
                continue

            selected_courses.append(course)
            used_codes.add(code)

            time_str = self._extract_time(schedule_location)
            loc_str  = self._extract_location(schedule_location)

            for day in days:
                if day in schedule:
                    schedule[day].append({
                        'code': code,
                        'title': course.get('title', ''),
                        'time': time_str,
                        'location': loc_str
                    })

        return {
            'schedule': schedule,
            'courses': selected_courses,
            'total_credits': sum(self._get_credits(c) for c in selected_courses)
        }

    
    def _has_schedule_conflict_with_selected(self, 
                                            course: Dict,
                                            selected: List[Dict]) -> bool:
        import re
        
        course_schedule = course.get('schedule_location', '')
        if not course_schedule:
            return False
        
        time_match = re.search(r'([MTWRFS]+)\s+(\d{1,2}:\d{2}[ap]m)-(\d{1,2}:\d{2}[ap]m)', 
                              course_schedule)
        if not time_match:
            return False
        
        course_days = set(time_match.group(1))
        course_start = time_match.group(2)
        course_end = time_match.group(3)
        
        for selected_course in selected:
            selected_schedule = selected_course.get('schedule_location', '')
            selected_match = re.search(r'([MTWRFS]+)\s+(\d{1,2}:\d{2}[ap]m)-(\d{1,2}:\d{2}[ap]m)',
                                      selected_schedule)
            
            if selected_match:
                selected_days = set(selected_match.group(1))
                
                if course_days & selected_days:
                    if self._time_ranges_overlap(course_start, course_end,
                                                 selected_match.group(2), 
                                                 selected_match.group(3)):
                        return True
        
        return False
    
    def _time_ranges_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        def time_to_minutes(time_str: str) -> int:
            import re
            match = re.match(r'(\d{1,2}):(\d{2})([ap]m)', time_str.lower())
            if not match:
                return 0
            hour, minute, period = match.groups()
            hour = int(hour)
            minute = int(minute)
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            return hour * 60 + minute
        
        start1_min = time_to_minutes(start1)
        end1_min = time_to_minutes(end1)
        start2_min = time_to_minutes(start2)
        end2_min = time_to_minutes(end2)
        
        return not (end1_min <= start2_min or start1_min >= end2_min)
    
    def _extract_days(self, schedule: str) -> List[str]:
        import re
        norm = re.sub(r'\bTh\b', 'R', schedule)
        match = re.search(r'([MTWRFS]+)', norm)
        if not match:
            return []
        day_map = {'M':'Monday','T':'Tuesday','W':'Wednesday','R':'Thursday','F':'Friday','S':'Saturday'}
        seen = set()
        out = []
        for ch in match.group(1):
            if ch in day_map and ch not in seen:
                seen.add(ch)
                out.append(day_map[ch])
        return out

    
    def _extract_time(self, schedule: str) -> str:
        import re
        match = re.search(r'(\d{1,2}:\d{2}[ap]m-\d{1,2}:\d{2}[ap]m)', schedule)
        return match.group(1) if match else 'TBA'
    
    def _extract_location(self, schedule: str) -> str:
        import re
        match = re.search(r'in (.+)$', schedule)
        return match.group(1) if match else 'TBA'
    
    def _get_credits(self, course: Dict) -> int:
        credits_str = course.get('credits', '0')
        if '-' in credits_str:
            return int(credits_str.split('-')[0])
        try:
            return int(credits_str)
        except ValueError:
            return 0
