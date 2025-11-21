import re
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from functools import lru_cache


class CourseHeuristic:
    
    PRIORITY_WEIGHTS = {
        1: 0.30,
        2: 0.25,
        3: 0.20,
        4: 0.15,
        5: 0.10
    }
    
    _course_code_pattern = re.compile(r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]?)\b')
    _time_pattern = re.compile(r'([MTWRFS]+)\s+(\d{1,2}:\d{2}[ap]m)-(\d{1,2}:\d{2}[ap]m)')
    _time_extract_pattern = re.compile(r'(\d{1,2}):\d{2}([ap]m)')
    _name_pattern = re.compile(r'([A-Za-z\s]+)')
    _ger_cleanup_pattern = re.compile(r'\s*\([^)]*\)')
    
    _day_map = {
        'M': 'Monday',
        'T': 'Tuesday',
        'W': 'Wednesday',
        'R': 'Thursday',
        'F': 'Friday',
        'S': 'Saturday'
    }
    
    _major_dept_map = {
        'Computer Science': 'CS',
        'Mathematics': 'MATH',
        'Biology': 'BIOL',
        'Chemistry': 'CHEM',
        'Physics': 'PHYS',
        'Economics': 'ECON',
        'Business': 'BUS',
        'Psychology': 'PSYC',
        'English': 'ENG',
        'History': 'HIST',
        'Political Science': 'POLS',
    }
    
    def __init__(self, 
                 user_profile: Dict,
                 courses_taken: Set[str],
                 professor_ratings: Dict[str, float] = None,
                 major_requirements: Dict[str, List[str]] = None,
                 ger_requirements: Dict[str, bool] = None):
        self.user_profile = user_profile
        self.courses_taken = courses_taken
        self.professor_ratings = professor_ratings or {}
        self.major_requirements = major_requirements or {}
        self.ger_requirements = ger_requirements or {}
        
        self.weights = self._build_weight_mapping()
        
        self._prereq_cache = {}
        self._time_cache = {}
        self._unavailable_times_parsed = self._preprocess_unavailable_times()
        self._required_courses_set = set(self.major_requirements.get(
            self.user_profile.get('major', ''), []))
        self._major_dept = self._major_dept_map.get(
            self.user_profile.get('major', ''), 
            self.user_profile.get('major', '')[:4].upper())
    
    def _build_weight_mapping(self) -> Dict[str, float]:
        priority_order = self.user_profile.get('priority_order', {
            'professor_rating': 1,
            'time_preference': 2,
            'major_requirements': 3,
            'ger_requirements': 4,
            'interests': 5
        })
        
        return {
            'professor_rating': self.PRIORITY_WEIGHTS[priority_order['professor_rating']],
            'time_preference': self.PRIORITY_WEIGHTS[priority_order['time_preference']],
            'major_requirements': self.PRIORITY_WEIGHTS[priority_order['major_requirements']],
            'ger_requirements': self.PRIORITY_WEIGHTS[priority_order['ger_requirements']],
            'interests': self.PRIORITY_WEIGHTS[priority_order['interests']]
        }
    
    def _preprocess_unavailable_times(self) -> List[Tuple]:
        parsed = []
        for unavailable in self.user_profile.get('time_unavailable', []):
            day = unavailable.get('day')
            start_min = self._time_to_minutes(unavailable.get('start_time', '12:00am'))
            end_min = self._time_to_minutes(unavailable.get('end_time', '11:59pm'))
            parsed.append((day, start_min, end_min))
        return parsed
    
    @staticmethod
    @lru_cache(maxsize=256)
    def _time_to_minutes(time_str: str) -> int:
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
    
    def calculate_score(self, course: Dict) -> Optional[float]:
        if not self._is_eligible(course):
            return None
        
        score = 0.0
        
        score += self._score_professor(course) * self.weights['professor_rating']
        score += self._score_time_preference(course) * self.weights['time_preference']
        score += self._score_major_requirements(course) * self.weights['major_requirements']
        score += self._score_ger_requirements(course) * self.weights['ger_requirements']
        score += self._score_interests(course) * self.weights['interests']
        score += self._score_credit_fit(course) * 0.05
        
        return min(100.0, score * 100)
    
    def _is_eligible(self, course: Dict) -> bool:
        course_code = course['code']
        if course_code in self.courses_taken:
            return False
        
        req_sentence = course.get('requirement_sentence', '').lower()
        
        if req_sentence:
            if req_sentence in self._prereq_cache:
                if self._prereq_cache[req_sentence]:
                    return False
            else:
                has_unmet = self._has_unmet_prerequisites(req_sentence)
                self._prereq_cache[req_sentence] = has_unmet
                if has_unmet:
                    return False
        
        schedule = course.get('schedule_location', '')
        if schedule and self._has_schedule_conflict(schedule):
            return False
        
        return True
    
    def _has_unmet_prerequisites(self, requirement_sentence: str) -> bool:
        prereq_courses = self._course_code_pattern.findall(requirement_sentence.upper())
        
        if not prereq_courses:
            return False
        
        has_or = ' or ' in requirement_sentence.lower()
        
        for dept, num in prereq_courses:
            course_code = f"{dept} {num}"
            if course_code not in self.courses_taken:
                if not has_or:
                    return True
        
        return False
    
    def _has_schedule_conflict(self, schedule: str) -> bool:
        if not schedule:
            return False
        
        if schedule in self._time_cache:
            time_data = self._time_cache[schedule]
        else:
            time_match = self._time_pattern.search(schedule)
            if not time_match:
                self._time_cache[schedule] = None
                return False
            
            days_str, start_time, end_time = time_match.groups()
            course_days = {self._day_map[d] for d in days_str if d in self._day_map}
            course_start = self._time_to_minutes(start_time)
            course_end = self._time_to_minutes(end_time)
            
            time_data = (course_days, course_start, course_end)
            self._time_cache[schedule] = time_data
        
        if time_data is None:
            return False
        
        course_days, course_start, course_end = time_data
        
        for unavail_day, unavail_start, unavail_end in self._unavailable_times_parsed:
            if unavail_day in course_days:
                if not (course_end <= unavail_start or course_start >= unavail_end):
                    return True
        
        return False
    
    def _score_professor(self, course: Dict) -> float:
        professor = course.get('professor', '') or ''
        if not professor:
            return 0.5
        import re
        professor = re.split(r'\s+[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\s*', professor)[0]
        professor = professor.replace('Primary Instructor', '').strip()
        parts = [p for p in professor.split() if p.isalpha()]
        key = ' '.join(parts[:2]) if parts else ''
        cand = [key]
        if len(parts) >= 2:
            cand.append(f'{parts[0]} {parts[1]}')
            cand.append(f'{parts[1]} {parts[0]}')
        for k in cand:
            if k in self.professor_ratings:
                return self.professor_ratings[k] / 5.0
        return 2.5 / 5.0

    
    def _score_time_preference(self, course: Dict) -> float:
        schedule = course.get('schedule_location', '')
        if not schedule:
            return 0.8
        
        score = 0.7
        
        time_pref = self.user_profile.get('preferred_time_of_day', None)
        if time_pref:
            time_match = self._time_extract_pattern.search(schedule)
            if time_match:
                hour, period = time_match.groups()
                hour = int(hour)
                if period == 'pm' and hour != 12:
                    hour += 12
                
                if time_pref == 'morning' and 8 <= hour < 12:
                    score += 0.3
                elif time_pref == 'afternoon' and 12 <= hour < 17:
                    score += 0.3
                elif time_pref == 'evening' and 17 <= hour < 21:
                    score += 0.3
        
        return min(1.0, score)
    
    def _score_major_requirements(self, course: Dict) -> float:
        course_code = course['code']
        
        if course_code in self._required_courses_set:
            return 1.0
        
        for req in self._required_courses_set:
            if 'X' in req:
                req_pattern = req.replace('X', r'\d')
                if re.match(f'^{req_pattern}$', course_code):
                    return 1.0
        
        course_dept = course_code.split()[0]
        if course_dept == self._major_dept:
            return 0.5
        
        return 0.0
    
    def _score_ger_requirements(self, course: Dict) -> float:
        ger = course.get('ger', '').strip()
        if not ger:
            return 0.0
        
        ger_category = self._ger_cleanup_pattern.sub('', ger).strip()
        
        if ger_category and not self.ger_requirements.get(ger_category, False):
            return 1.0
        
        return 0.0
    
    def _score_interests(self, course: Dict) -> float:
        interests = self.user_profile.get('interests', [])
        if not interests:
            return 0.5
        
        course_code = course['code']
        course_title = course['title'].lower()
        course_dept = course_code.split()[0].lower()
        
        for interest in interests:
            interest_lower = interest.lower()
            
            if interest_lower in course_dept or course_dept in interest_lower:
                return 1.0
            
            if interest_lower in course_title:
                return 0.8
        
        return 0.0
    
    def _score_credit_fit(self, course: Dict) -> float:
        credits_str = course.get('credits', '0')
        
        if '-' in credits_str:
            credits = int(credits_str.split('-')[0])
        else:
            try:
                credits = int(credits_str)
            except ValueError:
                return 0.5
        
        if 3 <= credits <= 4:
            return 1.0
        elif credits <= 2:
            return 0.7
        else:
            return 0.5
