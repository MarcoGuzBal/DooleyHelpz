import re
from typing import Dict, List, Set, Optional, Tuple, Any
from fibonacci_heap import FibonacciHeap
import unicodedata
import difflib


CSBA_REQUIREMENTS = {
    "must": [
        "MATH111", "MATH112", "MATH221",
        "CS170", "CS171", "CS224", "CS253",
        "CS255", "CS326", "CS350"
    ],
    "elective_groups": [
        {"choose": 1, "courses": ["CS370", "CS371W"]},
        {"choose": 2, "courses": ["CS325", "CS329", "CS334", "CS377"]},
        {
            "choose": 2,
            "courses": [
                "CS312", "CS325", "CS326", "CS329", "CS334", "CS350",
                "CS370", "CS371W", "CS377", "CS385", "CS424", "CS441",
                "CS443", "CS444", "CS452", "CS463", "CS470", "CS480",
                "CS485", "CS495A", "CS495BW", "CS497R", "CS498R"
            ]
        }
    ]
}

CSBS_REQUIREMENTS = {
    "must": [
        "MATH111", "MATH112", "MATH221",
        "CS170", "CS171", "CS224", "CS253",
        "CS255", "CS326", "CS350"
    ],
    "elective_groups": [
        {"choose": 1, "courses": ["CS370", "CS371W"]},
        {"choose": 1, "courses": ["CS325", "CS329", "CS334", "CS377"]},
        {
            "choose": 2,
            "courses": [
                "CS312", "CS325", "CS326", "CS329", "CS334", "CS350",
                "CS370", "CS371W", "CS377", "CS385"
            ]
        },
        {
            "choose": 1,
            "courses": [
                "CS312", "CS325", "CS326", "CS329", "CS334", "CS350",
                "CS370", "CS371W", "CS377", "CS385",
                "MATH315", "MATH346", "MATH347", "MATH351",
                "MATH361", "MATH362"
            ]
        },
        {
            "choose": 3,
            "courses": [
                "CS424", "CS441", "CS443", "CS444", "CS452", "CS463",
                "CS470", "CS480", "CS485", "CS495A", "CS495BW",
                "CS497R", "CS498R"
            ]
        }
    ]
}

GER_REQUIREMENTS = {
    "ECS": 1, "HLTH": 1, "FS": 1, "FW": 1, "PE": 1,
    "HA": 1, "NS": 1, "QR": 1, "SS": 1, "IC": 2,
    "ETHN": 1, "CW": 2, "XA": 1
}

GER_DUE_BY_YEAR = {
    "Freshman": {"ECS", "HLTH", "FS", "FW", "PE"},
    "Sophomore": {"HA", "NS", "QR", "SS"},
    "Junior": {"IC", "ETHN"},
    "Senior": {"CW", "XA"}
}

IC_LANGUAGE_PREFIXES = {
    "SPAN", "FREN", "GER", "ITAL", "PORT", "RUSS", "ARAB", "HEBR",
    "CHN", "JPN", "KRN", "LAT", "GRK", "SWAH", "HNDI", "TBT"
}

EASY_LANGUAGES = {"SPAN", "FREN", "ITAL", "PORT"}

# Day mapping - used in multiple places
DAY_MAP = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "Th": "Thursday", "F": "Friday"}


def normalize_course_code(course_code: str) -> str:
    if not course_code:
        return course_code

    code = course_code.strip().upper().replace(" ", "")
    code = code.replace("_OX", "")

    if code.endswith("ZL"):
        return code[:-2] + "L"
    elif code.endswith("Z"):
        return code[:-1]

    return code


def parse_credits(credits_value, default: int = 3) -> int:
    if credits_value is None:
        return default
    
    if isinstance(credits_value, (int, float)):
        return int(credits_value)
    
    if isinstance(credits_value, str):
        credits_value = credits_value.strip()
        
        if '-' in credits_value:
            parts = credits_value.split('-')
            try:
                low = int(float(parts[0].strip()))
                high = int(float(parts[1].strip()))
                return (low + high) // 2
            except (ValueError, IndexError):
                return default
        
        try:
            return int(float(credits_value))
        except ValueError:
            return default
    
    return default


def get_course_number(course_code: str) -> Optional[int]:
    """Extract the numeric part of a course code (e.g., 'SPAN302W' -> 302)."""
    nums = "".join(filter(str.isdigit, course_code))
    if nums:
        return int(nums[:3]) if len(nums) >= 3 else int(nums)
    return None


def get_department(course_code: str) -> str:
    """Extract department code from a course code."""
    if not course_code:
        return ""
    code = normalize_course_code(str(course_code))
    m = re.match(r"^([A-Z]+?)(?=\d)", code)
    if m:
        return m.group(1)
    dept = []
    for ch in code:
        if ch.isalpha():
            dept.append(ch)
        else:
            break
    return "".join(dept) if dept else ""


class IntegratedRecommendationEngine:

    def __init__(self):
        self.time_pattern = re.compile(r"([MTWRF]+)\s+(\d{1,2}:\d{2}[ap]m)-(\d{1,2}:\d{2}[ap]m)")
        self.suffixes = {"jr", "sr", "ii", "iii", "iv"}
        self.degrees = {"phd", "md", "msc", "ms", "mba", "edd", "dphil"}
        self.honorifics = {"dr", "prof", "professor"}
        
        # OPTIMIZATION: Caches for expensive operations
        self._meeting_blocks_cache: Dict[str, List[Tuple[str, int, int]]] = {}
        self._course_metadata_cache: Dict[str, Dict[str, Any]] = {}

    def _clear_caches(self):
        """Clear all caches - call at start of each recommendation run."""
        self._meeting_blocks_cache.clear()
        self._course_metadata_cache.clear()

    def _get_course_metadata(self, course: Dict) -> Dict[str, Any]:
        """Get or compute cached metadata for a course."""
        code = course.get("code") or ""
        if not code:
            return {"normalized_code": "", "department": "", "course_number": None}
        
        # Use object id as cache key since code might not be unique
        cache_key = f"{code}_{id(course)}"
        
        if cache_key in self._course_metadata_cache:
            return self._course_metadata_cache[cache_key]
        
        normalized = normalize_course_code(code)
        dept = get_department(normalized)
        num = get_course_number(normalized)
        
        metadata = {
            "normalized_code": normalized,
            "department": dept,
            "course_number": num,
        }
        
        self._course_metadata_cache[cache_key] = metadata
        return metadata

    def _strip_accents(self, s: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFKD", s)
            if not unicodedata.combining(c)
        )

    def _normalize_name(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        n = self._strip_accents(str(name)).lower().strip()
        n = n.replace("-", " ")
        n = n.replace("'", "'").replace("`", "'")
        n = n.replace(".", "")
        n = "".join(ch for ch in n if ch.isalnum() or ch.isspace() or ch == ",")
        n = " ".join(n.split())
        parts = [p.strip() for p in n.split(",")]
        if len(parts) == 2 and parts[0] and parts[1]:
            last = parts[0]
            first_and_more = parts[1]
            tokens = [
                t for t in first_and_more.split()
                if t not in self.suffixes and t not in self.degrees and t not in self.honorifics
            ]
            core = " ".join(tokens)
            n = f"{core} {last}".strip()
        else:
            tokens = [
                t for t in n.split()
                if t not in self.suffixes and t not in self.degrees and t not in self.honorifics
            ]
            n = " ".join(tokens)
        return n or None

    def _first_last_keys(self, n: str) -> Set[str]:
        toks = n.split()
        if len(toks) == 0:
            return set()
        if len(toks) == 1:
            return {n}
        first, last = toks[0], toks[-1]
        return {
            n,
            f"{first} {last}",
            f"{first[0]} {last}",
            f"{first}{last}",
            f"{first[0]}{last}",
            f"{last} {first}",
        }

    def _same_last_block(self, name_norm: str, key: str) -> bool:
        toks_a = name_norm.split()
        toks_b = key.split()
        return bool(toks_a and toks_b and toks_a[-1] == toks_b[-1])

    def _match_professor(self, raw_name: str, rmp_index: Dict[str, Any]) -> Optional[Dict]:
        if not raw_name:
            return None
        if ";" in raw_name:
            raw_name = raw_name.split(";")[0]
        elif " and " in raw_name:
            raw_name = raw_name.split(" and ")[0]
        n = self._normalize_name(raw_name)
        if not n:
            return None

        if n in rmp_index:
            return rmp_index[n]

        for k in self._first_last_keys(n):
            if k in rmp_index:
                return rmp_index[k]

        pool = [k for k in rmp_index.keys() if self._same_last_block(n, k)]
        if pool:
            best = difflib.get_close_matches(n, pool, n=1, cutoff=0.92)
            if best:
                return rmp_index[best[0]]

        return None

    def _requires_permission(self, course: Dict) -> bool:
        """Check if course requires permission/consent to enroll."""
        if course.get("permission_required"):
            return True
        
        notes = (course.get("requirements") or {}).get("notes") or ""
        if not notes:
            return False
        
        notes_lower = notes.lower()
        permission_phrases = [
            "permission of the department required",
            "permission required",
            "consent required",
            "department consent",
            "instructor consent",
            "permission of instructor",
            "open only to students admitted",
        ]
        
        return any(phrase in notes_lower for phrase in permission_phrases)

    def _is_research_course(self, course: Dict) -> bool:
        """Check if course is a research/independent study course."""
        meta = self._get_course_metadata(course)
        code = meta["normalized_code"]
        title = (course.get("title") or "").lower()
        
        research_keywords = [
            "independent study", "directed study", "directed research",
            "undergraduate research", "honors research", "thesis", "special research",
        ]
        if any(kw in title for kw in research_keywords):
            return True
        
        if code.endswith("R") and not code.endswith("RW"):
            course_num = meta["course_number"]
            if course_num:
                if 395 <= course_num <= 399 or 485 <= course_num <= 499:
                    return True
        
        return False

    def _is_cross_listed_duplicate(
        self, 
        course: Dict, 
        schedule_codes: Set[str], 
        all_courses_map: Dict[str, Dict]
    ) -> bool:
        """Check if this course is cross-listed with any course already in schedule."""
        meta = self._get_course_metadata(course)
        code = meta["normalized_code"]
        
        cross_listed = course.get("cross_listed_with") or []
        for cross_code in cross_listed:
            if normalize_course_code(cross_code) in schedule_codes:
                return True
        
        for sched_code in schedule_codes:
            if sched_code in all_courses_map:
                sched_course = all_courses_map[sched_code]
                sched_cross = sched_course.get("cross_listed_with") or []
                if code in [normalize_course_code(c) for c in sched_cross]:
                    return True
        
        # Check by title + time (same course, different code)
        course_title = (course.get("title") or "").strip().lower()
        course_time = course.get("time") or ""
        
        if course_title and course_time:
            for sched_code in schedule_codes:
                if sched_code in all_courses_map:
                    sched_course = all_courses_map[sched_code]
                    sched_title = (sched_course.get("title") or "").strip().lower()
                    sched_time = sched_course.get("time") or ""
                    
                    if sched_title == course_title and sched_time == course_time:
                        return True
        
        return False

    def _time_to_minutes(self, time_str: str) -> int:
        if not time_str:
            return 0

        s = str(time_str).strip().lower()

        match_12 = re.match(r"(\d{1,2}):(\d{2})([ap]m)", s)
        if match_12:
            hour = int(match_12.group(1))
            minute = int(match_12.group(2))
            period = match_12.group(3)
            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0
            return hour * 60 + minute

        match_24 = re.match(r"(\d{1,2}):(\d{2})$", s)
        if match_24:
            hour = int(match_24.group(1))
            minute = int(match_24.group(2))
            return hour * 60 + minute

        return 0

    def _parse_time_unavailable(self, time_unavailable: List[Dict]) -> List[Tuple]:
        blocks: List[Tuple] = []
        if not time_unavailable:
            return blocks

        for block in time_unavailable:
            days = block.get("days") or block.get("day")
            if not days:
                continue
            if isinstance(days, str):
                days = [days]

            start = block.get("start") or block.get("start_time")
            end = block.get("end") or block.get("end_time")
            if not start or not end:
                continue

            start_min = self._time_to_minutes(start)
            end_min = self._time_to_minutes(end)
            if start_min == end_min:
                continue

            for day in days:
                blocks.append((day, start_min, end_min))

        return blocks

    def _parse_days(self, day_str: str) -> List[str]:
        """Parse day string like 'TTh' or 'MWF' into list of day abbreviations."""
        if not day_str:
            return []
        days: List[str] = []
        cleaned = str(day_str).replace(" ", "")
        i = 0
        while i < len(cleaned):
            two = cleaned[i:i+2]
            if two == "Th":
                days.append("Th")
                i += 2
                continue
            ch = cleaned[i]
            if ch in "MTWF":
                days.append(ch)
            i += 1
        return days

    def _parse_time_range(self, time_str: str) -> Tuple[int, int]:
        """Parse time string like '10am-12:45pm' into (start_min, end_min)."""
        if not time_str:
            return (0, 0)
        s = str(time_str).strip()
        s = re.sub(r'(?<![:\d])(\d{1,2})(am|pm)', r'\1:00\2', s, flags=re.IGNORECASE)
        m = re.match(
            r'(\d{1,2}):(\d{2})\s*(am|pm)\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)',
            s, flags=re.IGNORECASE
        )
        if not m:
            return (0, 0)
        sh, sm, sap, eh, em, eap = m.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)
        sap, eap = sap.lower(), eap.lower()
        if sap == "pm" and sh != 12:
            sh += 12
        if sap == "am" and sh == 12:
            sh = 0
        if eap == "pm" and eh != 12:
            eh += 12
        if eap == "am" and eh == 12:
            eh = 0
        return (sh * 60 + sm, eh * 60 + em)

    def _extract_meeting_blocks(self, course: Dict) -> List[Tuple[str, int, int]]:
        """Extract time blocks as (day_abbr, start_min, end_min). CACHED."""
        code = course.get("code") or ""
        cache_key = f"{code}_{id(course)}"
        
        if cache_key in self._meeting_blocks_cache:
            return self._meeting_blocks_cache[cache_key]
        
        blocks: List[Tuple[str, int, int]] = []

        meeting = course.get("meeting") or course.get("meetings")

        def add_block(day_val, start_min, end_min):
            if start_min is None or end_min is None or end_min <= start_min:
                return
            days_list: List[str] = []
            if isinstance(day_val, list):
                for d in day_val:
                    if isinstance(d, str):
                        days_list.extend(self._parse_days(d))
            elif isinstance(day_val, str):
                days_list = self._parse_days(day_val)
            for d in days_list:
                blocks.append((d, start_min, end_min))

        def handle_meeting_obj(mo: Dict):
            if not isinstance(mo, dict):
                return
            day_val = mo.get("day") or mo.get("days") or ""

            t_str = mo.get("time")
            if t_str:
                start_min, end_min = self._parse_time_range(t_str)
                if start_min and end_min and end_min > start_min:
                    add_block(day_val, start_min, end_min)
                    return

            start_raw = mo.get("start_min") or mo.get("start_time") or mo.get("start")
            end_raw = mo.get("end_min") or mo.get("end_time") or mo.get("end")
            if start_raw is None or end_raw is None:
                return

            if isinstance(start_raw, (int, float)) and isinstance(end_raw, (int, float)):
                start_min = int(start_raw)
                end_min = int(end_raw)
            else:
                start_min = self._time_to_minutes(str(start_raw))
                end_min = self._time_to_minutes(str(end_raw))

            add_block(day_val, start_min, end_min)

        if meeting:
            if isinstance(meeting, list):
                for mo in meeting:
                    handle_meeting_obj(mo)
            elif isinstance(meeting, dict):
                handle_meeting_obj(meeting)
        else:
            t = course.get("time")
            if isinstance(t, str) and " " in t:
                day_part, time_part = t.split(" ", 1)
                start_min, end_min = self._parse_time_range(time_part)
                if start_min and end_min and end_min > start_min:
                    for d in self._parse_days(day_part):
                        blocks.append((d, start_min, end_min))

        self._meeting_blocks_cache[cache_key] = blocks
        return blocks

    def _has_time_conflict(self, course: Dict, unavailable_blocks: List[Tuple]) -> bool:
        """Check if course conflicts with any unavailable blocks."""
        course_blocks = self._extract_meeting_blocks(course)
        if not course_blocks:
            return False

        for day_abbr, start_min, end_min in course_blocks:
            day_full = DAY_MAP.get(day_abbr, day_abbr)

            for unavail_day, unavail_start, unavail_end in unavailable_blocks:
                if day_full == unavail_day or day_abbr == unavail_day:
                    if not (end_min <= unavail_start or start_min >= unavail_end):
                        return True

        return False

    def _get_ic_status(self, completed: Set[str]) -> Dict[str, Any]:
        """Properly track IC requirement status."""
        language_counts: Dict[str, int] = {}
        highest_completed: Dict[str, int] = {}
        
        for code in completed:
            dept = get_department(code)
            if dept in IC_LANGUAGE_PREFIXES:
                language_counts[dept] = language_counts.get(dept, 0) + 1
                num = get_course_number(code)
                if num:
                    if dept not in highest_completed or num > highest_completed[dept]:
                        highest_completed[dept] = num
        
        fulfilled = any(count >= 2 for count in language_counts.values())
        
        best_language = None
        best_count = 0
        best_level = 0
        
        for lang, count in language_counts.items():
            level = highest_completed.get(lang, 0)
            if count > best_count or (count == best_count and level > best_level):
                best_language = lang
                best_count = count
                best_level = level
        
        return {
            "fulfilled": fulfilled,
            "language_counts": language_counts,
            "best_language": best_language,
            "highest_completed": highest_completed
        }

    def _is_valid_next_language_course(
        self,
        course_code: str,
        ic_status: Dict[str, Any],
        year: str = "Freshman"
    ) -> Tuple[bool, int]:
        dept = get_department(course_code)
        if dept not in IC_LANGUAGE_PREFIXES:
            return False, 0

        course_num = get_course_number(course_code)
        if not course_num:
            return False, 0

        language_counts = ic_status.get("language_counts", {})
        highest_completed = ic_status.get("highest_completed", {})
        best_language = ic_status.get("best_language")
        
        is_easy_language = dept in EASY_LANGUAGES

        has_unfinished_101 = any(
            cnt == 1 and highest_completed.get(lang) == 101
            for lang, cnt in language_counts.items()
        )

        # Continuing an existing language
        if dept in highest_completed:
            their_highest = highest_completed[dept]
            
            if course_num == 101:
                return False, 0
            
            if course_num == 102:
                if 101 <= their_highest < 102:
                    priority = 100 if dept == best_language else 85
                    if is_easy_language:
                        priority += 10
                    return True, priority
                else:
                    return False, 0
            
            if course_num >= 200:
                if their_highest >= 102:
                    priority = 40 if dept == best_language else 30
                    if is_easy_language:
                        priority += 5
                    return True, priority
                else:
                    return False, 0
            
            return False, 0

        # New language - only allow 101
        if course_num == 101:
            if has_unfinished_101:
                return False, 0
            if is_easy_language:
                base_priority = 20
            else:
                base_priority = 8
            return True, base_priority

        return False, 0

    def _get_ger_urgency(self, ger_tag: str, year: str) -> str:
        year_order = ["Freshman", "Sophomore", "Junior", "Senior"]
        
        if year not in year_order:
            year = "Freshman"
        
        current_idx = year_order.index(year)
        
        for due_year, ger_set in GER_DUE_BY_YEAR.items():
            if ger_tag in ger_set:
                due_idx = year_order.index(due_year)
                
                if current_idx > due_idx:
                    return "overdue"
                elif current_idx == due_idx:
                    return "due"
                elif current_idx == due_idx - 1:
                    return "upcoming"
                else:
                    return "future"
        
        return "future"

    def _get_remaining_gers(
        self,
        completed: Set[str],
        all_courses: List[Dict],
        ger_reqs: Dict,
        ic_status: Dict[str, Any],
        year: str = "Freshman",
        ger_lookup: Dict[str, List[str]] = None
    ) -> Dict[str, int]:
        """Calculate which GER categories still need credits."""
        completed_gers = {k: 0 for k in ger_reqs}

        course_ger_map: Dict[str, List[str]] = {}
        
        if ger_lookup:
            course_ger_map = dict(ger_lookup)
        
        for c in all_courses:
            if not c or not isinstance(c, dict):
                continue
            code = normalize_course_code(c.get("code") or "")
            if not code:
                continue
            g = c.get("ger") or []
            if isinstance(g, str):
                g = [g]
            elif not isinstance(g, list):
                g = []
            if code not in course_ger_map:
                course_ger_map[code] = g

        for code in completed:
            gers = course_ger_map.get(code) or []
            for g in gers:
                if not g or g == "IC":
                    continue
                if g in completed_gers:
                    completed_gers[g] += 1

        if ic_status and isinstance(ic_status, dict) and ic_status.get("fulfilled"):
            completed_gers["IC"] = 2

        needed_gers: Dict[str, int] = {}
        for cat, req_count in ger_reqs.items():
            if cat == "FS" and year != "Freshman":
                continue
            
            if completed_gers.get(cat, 0) < req_count:
                needed_gers[cat] = req_count - completed_gers.get(cat, 0)

        return needed_gers

    def _calculate_score(
        self,
        course: Dict,
        course_code: str,
        needed_must: Set[str],
        needed_electives: List[Dict],
        needed_gers: Dict[str, int],
        interests: List[str],
        time_pref: Optional[List[str]],
        completed: Set[str],
        rmp_index: Dict[str, Any] = None,
        year: str = "Freshman",
        ic_status: Dict[str, Any] = None,
        language_already_in_schedule: bool = False
    ) -> float:
        """Calculate recommendation score for a course."""
        
        if self._requires_permission(course):
            return 0.0
        
        if self._is_research_course(course):
            return 0.0
        
        # FIX: Get GERs once at the start
        course_gers = course.get("ger") or []
        if isinstance(course_gers, str):
            course_gers = [course_gers]
        
        if "FS" in course_gers and year != "Freshman":
            return 0.0
        
        # Get cached metadata
        meta = self._get_course_metadata(course)
        course_dept = meta["department"]
        course_num = meta["course_number"]
        
        score = 0.0
        rating_factor = 1.0
        
        has_major_unmet = bool(needed_must) or any(
            (group.get("choose", 0) > group.get("chosen", 0))
            for group in needed_electives
        )

        if language_already_in_schedule and course_dept in IC_LANGUAGE_PREFIXES:
            return 0.0

        # 1. Major requirements - MUST courses are ABSOLUTE TOP PRIORITY
        if course_code in needed_must:
            score += 500.0
        else:
            for group in needed_electives:
                courses = group.get("courses", set())
                if course_code in courses:
                    choose = int(group.get("choose", 0))
                    chosen = int(group.get("chosen", 0))
                    if choose and chosen >= choose:
                        score += 25.0
                    else:
                        score += 120.0
                    break

        # 2. GER requirements (excluding IC) - use course_gers already parsed above
        gers_fulfilled = 0  
        for g in course_gers:
            if g == "IC":
                continue
            if g in needed_gers and needed_gers[g] > 0:
                urgency = self._get_ger_urgency(g, year)

                ger_weight = 1.0
                if has_major_unmet and urgency in ("upcoming", "future"):
                    ger_weight = 0.65

                if urgency == "overdue":
                    base = 65.0
                elif urgency == "due":
                    base = 55.0
                elif urgency == "upcoming":
                    base = 42.0
                else:
                    base = 15.0

                score += base * ger_weight
                gers_fulfilled += 1
        
        if gers_fulfilled >= 2:
            score += 15.0 * (gers_fulfilled - 1)
        
        ger_score_added = gers_fulfilled > 0

        # 3. IC language handling
        if ic_status and not ic_status.get("fulfilled", False):
            if course_dept in IC_LANGUAGE_PREFIXES:
                is_valid, priority = self._is_valid_next_language_course(
                    course_code, ic_status, year
                )
                
                if is_valid:
                    urgency = self._get_ger_urgency("IC", year)
                    
                    if urgency == "overdue":
                        ic_score = 40.0
                    elif urgency == "due":
                        ic_score = 30.0
                    elif urgency == "upcoming":
                        ic_score = 20.0
                    else:
                        ic_score = 12.0
                    
                    score += ic_score + priority
                    ger_score_added = True

        # Extra MASSIVE bonus for 102 when 101 is done
        if ic_status and isinstance(ic_status, dict):
            highest_completed = ic_status.get("highest_completed", {})
            language_counts = ic_status.get("language_counts", {})

            if (
                course_dept in IC_LANGUAGE_PREFIXES
                and course_num == 102
                and highest_completed.get(course_dept) == 101
                and language_counts.get(course_dept, 0) == 1
            ):
                score += 250.0

        # 4. Professor rating
        rmp = course.get("rmp") or {}
        if (not rmp) and rmp_index:
            prof_name = course.get("professor") or course.get("instructor")
            matched_rmp = self._match_professor(prof_name, rmp_index)
            if matched_rmp:
                rmp = matched_rmp
                course["rmp"] = rmp

        rating = rmp.get("rating")
        if isinstance(rating, (int, float)) and rating > 0:
            rating_points = (rating / 5.0) * 15.0
            score += rating_points

            if rating < 3.0:
                rating_factor = 0.7
            elif rating >= 4.5:
                rating_factor = 1.08
        else:
            score += 7.5

        # 5. Interests
        text = f"{course_code} {course.get('title') or ''}".lower()
        if interests and isinstance(interests, list):
            interest_hit = False
            for interest in interests:
                if not interest:
                    continue
                parts = re.findall(r"[a-z0-9]+", str(interest).lower())
                for part in parts:
                    if part and len(part) > 2 and part in text:
                        interest_hit = True
                        break
                if interest_hit:
                    break
            if interest_hit:
                score += 12.0

        # 6. Time preference
        if time_pref and len(time_pref) == 2:
            blocks = self._extract_meeting_blocks(course)
            if blocks:
                start_min = blocks[0][1]
                pref_start = self._time_to_minutes(time_pref[0])
                pref_end = self._time_to_minutes(time_pref[1])
                if pref_start <= start_min <= pref_end:
                    score += 5.0

        # 7. Prerequisites
        prereqs = course.get("prerequisites")
        if prereqs is None:
            requirements = course.get("requirements") or {}
            prereqs = requirements.get("prereq")

        if not prereqs:
            prereqs = [[]]

        if prereqs and prereqs != [[]]:
            if not self._check_prerequisites(prereqs, completed):
                return 0.0

        return score * rating_factor

    def _check_prerequisites(self, prereqs: List[List[str]], completed: Set[str]) -> bool:
        if not prereqs or prereqs == [[]] or prereqs == []:
            return True

        for or_group in prereqs:
            if not or_group or not isinstance(or_group, (list, tuple)):
                continue
            has_one = any(normalize_course_code(str(p)) in completed for p in or_group if p)
            if not has_one:
                return False

        return True

    def _calculate_contextual_score(
        self,
        candidate: Dict,
        root_course: Dict,
        base_score: float
    ) -> float:
        synergy_bonus = 0.0

        root_meta = self._get_course_metadata(root_course)
        cand_meta = self._get_course_metadata(candidate)

        root_dept = root_meta["department"]
        cand_dept = cand_meta["department"]

        if root_dept == cand_dept and root_dept:
            synergy_bonus += 3.0

        root_num = root_meta["course_number"]
        cand_num = cand_meta["course_number"]
        if root_num and cand_num:
            root_level = str(root_num)[0] if root_num >= 100 else "0"
            cand_level = str(cand_num)[0] if cand_num >= 100 else "0"
            if root_level == cand_level:
                synergy_bonus += 1.5

        return base_score + synergy_bonus

    def _get_course_blocks(self, course: Dict) -> List[Tuple]:
        """Get time blocks for a course as (day_full, start_min, end_min) tuples."""
        blocks = self._extract_meeting_blocks(course)
        return [(DAY_MAP.get(d, d), start, end) for d, start, end in blocks]

    def _calculate_schedule_balance(self, schedule: List[Dict]) -> float:
        if len(schedule) < 2:
            return 1.0
        
        day_courses: Dict[str, List[Tuple[int, int, str, int]]] = {}
        
        for course in schedule:
            meta = self._get_course_metadata(course)
            code = meta["normalized_code"]
            course_num = meta["course_number"]
            level = (course_num // 100 * 100) if course_num else 100

            blocks = self._extract_meeting_blocks(course)
            for day_abbr, start_min, end_min in blocks:
                if start_min is not None and end_min is not None:
                    if day_abbr not in day_courses:
                        day_courses[day_abbr] = []
                    day_courses[day_abbr].append((start_min, end_min, code, level))
        
        if not day_courses:
            return 1.0
        
        total_penalty = 0.0
        total_bonus = 0.0
        comparisons = 0
        
        for day, courses in day_courses.items():
            if len(courses) < 2:
                continue
            
            courses.sort(key=lambda x: x[0])
            
            for i in range(len(courses) - 1):
                start1, end1, code1, level1 = courses[i]
                start2, end2, code2, level2 = courses[i + 1]
                
                gap = start2 - end1
                comparisons += 1
                
                both_hard = level1 >= 300 and level2 >= 300
                
                if gap < 0:
                    total_penalty += 0.10
                elif gap < 15:
                    total_penalty += 0.08 if both_hard else 0.04
                elif gap < 30:
                    total_penalty += 0.05 if both_hard else 0.02
                elif 60 <= gap <= 120:
                    total_bonus += 0.03
                elif gap > 180:
                    total_penalty += 0.02
        
        if comparisons == 0:
            return 1.0
        
        modifier = 1.0 - total_penalty + total_bonus
        return max(0.85, min(1.15, modifier))

    def _build_schedule_tree(
        self,
        root_course: Dict,
        all_courses: List[Dict],
        all_courses_map: Dict[str, Dict],
        unavailable_blocks: List[Tuple],
        completed: Set[str],
        needed_must: Set[str],
        needed_electives: List[Dict],
        needed_gers: Dict[str, int],
        interests: List[str],
        time_pref: Optional[List[str]],
        rmp_index: Dict[str, Any],
        year: str = "Freshman",
        ic_status: Dict[str, Any] = None,
        target_credits: int = 15,
        max_credits: int = 19
    ) -> Tuple[float, List[Dict]]:
        
        root_meta = self._get_course_metadata(root_course)
        root_code = root_meta["normalized_code"]
        root_dept = root_meta["department"]

        language_in_schedule = root_dept in IC_LANGUAGE_PREFIXES

        root_base_score = self._calculate_score(
            root_course, root_code, needed_must, needed_electives, needed_gers,
            interests, time_pref, completed, rmp_index, year, ic_status,
            language_already_in_schedule=False
        )
        root_course["recommendation_score"] = root_base_score

        schedule = [root_course]
        current_schedule_codes = {root_code}
        
        total_credits = parse_credits(root_course.get("credits"))
        department_counts = {root_dept: 1}

        schedule_blocks = list(unavailable_blocks)
        root_blocks = self._get_course_blocks(root_course)
        if root_blocks:
            schedule_blocks.extend(root_blocks)

        total_score = root_base_score

        remaining_must = set(needed_must)
        if root_code in remaining_must:
            remaining_must.remove(root_code)

        remaining_electives: List[Dict] = []
        for group in needed_electives:
            remaining_electives.append({
                "choose": int(group.get("choose", 0)),
                "courses": set(group.get("courses", set())),
                "chosen": int(group.get("chosen", 0)),
            })

        for group in remaining_electives:
            if root_code in group["courses"] and group["chosen"] < group["choose"]:
                group["chosen"] += 1

        remaining_gers = dict(needed_gers)
        root_gers = root_course.get("ger") or []
        if isinstance(root_gers, str):
            root_gers = [root_gers]
        for g in root_gers:
            if g in remaining_gers:
                remaining_gers[g] -= 1
                if remaining_gers[g] <= 0:
                    del remaining_gers[g]

        # Categorize candidates by priority
        must_course_candidates: List[Tuple[float, float, Dict, str]] = []
        lang_102_candidates: List[Tuple[float, float, Dict, str]] = []
        other_candidates: List[Tuple[float, float, Dict, str]] = []

        for course in all_courses:
            meta = self._get_course_metadata(course)
            code = meta["normalized_code"]
            
            if not code or code in current_schedule_codes or code in completed:
                continue

            cand_dept = meta["department"]
            course_num = meta["course_number"]
            
            is_must = code in remaining_must
            
            is_lang_102 = (
                not language_in_schedule
                and cand_dept in IC_LANGUAGE_PREFIXES
                and course_num == 102
                and ic_status
                and isinstance(ic_status, dict)
                and ic_status.get("highest_completed", {}).get(cand_dept) == 101
                and ic_status.get("language_counts", {}).get(cand_dept, 0) == 1
            )
            
            if not is_must and not is_lang_102 and self._has_time_conflict(course, schedule_blocks):
                continue
            
            if self._is_cross_listed_duplicate(course, current_schedule_codes, all_courses_map):
                continue

            base_score = self._calculate_score(
                course, code, remaining_must, remaining_electives, remaining_gers,
                interests, time_pref, completed, rmp_index, year, ic_status,
                language_already_in_schedule=language_in_schedule
            )
            if base_score <= 0:
                continue

            final_score = self._calculate_contextual_score(course, root_course, base_score)
            
            if is_must:
                must_course_candidates.append((final_score, base_score, course, code))
            elif is_lang_102:
                lang_102_candidates.append((final_score, base_score, course, code))
            else:
                other_candidates.append((final_score, base_score, course, code))

        # Sort by score
        must_course_candidates.sort(key=lambda x: x[0], reverse=True)
        lang_102_candidates.sort(key=lambda x: x[0], reverse=True)
        other_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Helper to add course to schedule
        def add_to_schedule(course: Dict, code: str, base_score: float, total_candidate_score: float) -> bool:
            nonlocal total_credits, total_score, language_in_schedule
            
            cand_meta = self._get_course_metadata(course)
            cand_dept = cand_meta["department"]
            course_credits = parse_credits(course.get("credits"))
            
            if total_credits + course_credits > max_credits:
                return False

            schedule.append(course)
            current_schedule_codes.add(code)
            course["recommendation_score"] = base_score
            total_credits += course_credits
            
            department_counts[cand_dept] = department_counts.get(cand_dept, 0) + 1
            
            if cand_dept in IC_LANGUAGE_PREFIXES:
                language_in_schedule = True
            
            total_score += total_candidate_score

            new_blocks = self._get_course_blocks(course)
            if new_blocks:
                schedule_blocks.extend(new_blocks)

            if code in remaining_must:
                remaining_must.remove(code)

            for group in remaining_electives:
                if code in group["courses"] and group["chosen"] < group["choose"]:
                    group["chosen"] += 1

            course_gers = course.get("ger") or []
            if isinstance(course_gers, str):
                course_gers = [course_gers]
            for g in course_gers:
                if g in remaining_gers:
                    remaining_gers[g] -= 1
                    if remaining_gers[g] <= 0:
                        del remaining_gers[g]
            
            return True

        def has_schedule_conflict(course: Dict) -> bool:
            """Check conflict only against courses already in schedule."""
            course_blocks = self._get_course_blocks(course)
            for existing in schedule:
                existing_blocks = self._get_course_blocks(existing)
                for cb in course_blocks:
                    for eb in existing_blocks:
                        if cb[0] == eb[0]:  # Same day
                            if not (cb[2] <= eb[1] or cb[1] >= eb[2]):  # Overlap
                                return True
            return False

        # PHASE 1: Add MUST courses (can override unavailable times)
        for total_candidate_score, base_score, course, code in must_course_candidates:
            if has_schedule_conflict(course):
                continue
            if self._is_cross_listed_duplicate(course, current_schedule_codes, all_courses_map):
                continue
            add_to_schedule(course, code, base_score, total_candidate_score)

        # PHASE 2: Add 102-after-101 language course
        if not language_in_schedule:
            for total_candidate_score, base_score, course, code in lang_102_candidates:
                if has_schedule_conflict(course):
                    continue
                if self._is_cross_listed_duplicate(course, current_schedule_codes, all_courses_map):
                    continue
                if add_to_schedule(course, code, base_score, total_candidate_score):
                    break  # Only add one language course

        # PHASE 3: Fill with other candidates
        backup_candidates = []
        
        for total_candidate_score, base_score, course, code in other_candidates:
            if total_credits >= target_credits:
                break

            if self._has_time_conflict(course, schedule_blocks):
                continue
            
            if self._is_cross_listed_duplicate(course, current_schedule_codes, all_courses_map):
                continue

            cand_meta = self._get_course_metadata(course)
            cand_dept = cand_meta["department"]
            
            if cand_dept in IC_LANGUAGE_PREFIXES and language_in_schedule:
                continue

            if department_counts.get(cand_dept, 0) >= 2:
                backup_candidates.append((total_candidate_score, base_score, course, code))
                continue

            course_gers = course.get("ger") or []
            if isinstance(course_gers, str):
                course_gers = [course_gers]
            
            contributes_to_ger = any(g in remaining_gers for g in course_gers if g and g != "IC")
            
            is_major_must = code in remaining_must
            is_major_elective = any(
                code in group["courses"] and group["chosen"] < group["choose"]
                for group in remaining_electives
            )
            is_major_req = is_major_must or is_major_elective
            
            if not contributes_to_ger and not is_major_req:
                backup_candidates.append((total_candidate_score, base_score, course, code))
                continue

            if not add_to_schedule(course, code, base_score, total_candidate_score):
                backup_candidates.append((total_candidate_score, base_score, course, code))

        # Fill remaining from backup
        if total_credits < target_credits:
            for total_candidate_score, base_score, course, code in backup_candidates:
                if total_credits >= target_credits:
                    break
                
                cand_meta = self._get_course_metadata(course)
                cand_dept = cand_meta["department"]
                
                if cand_dept in IC_LANGUAGE_PREFIXES and language_in_schedule:
                    continue
                
                if self._has_time_conflict(course, schedule_blocks):
                    continue
                
                if self._is_cross_listed_duplicate(course, current_schedule_codes, all_courses_map):
                    continue

                add_to_schedule(course, code, base_score, total_candidate_score)

        balance_modifier = self._calculate_schedule_balance(schedule)
        total_score *= balance_modifier

        return total_score, schedule

    def _get_remaining_requirements(
        self,
        completed: Set[str],
        major_reqs: Dict
    ) -> Tuple[Set[str], List[Dict]]:
        must_courses = major_reqs.get("must") or []
        elective_groups = major_reqs.get("elective_groups") or []
        
        needed_must = set(must_courses) - completed

        needed_electives: List[Dict] = []
        for group in elective_groups:
            if not group or not isinstance(group, dict):
                continue
                
            courses_list = group.get("courses") or []
            if not isinstance(courses_list, list):
                continue
                
            courses_set = set(courses_list)
            choose = int(group.get("choose") or 0)

            completed_in_group = sum(1 for c in courses_set if c in completed)
            still_needed = max(0, choose - completed_in_group)
            if still_needed <= 0:
                continue

            remaining_courses = {c for c in courses_set if c not in completed}
            if not remaining_courses:
                continue

            needed_electives.append({
                "choose": still_needed,
                "courses": remaining_courses,
                "chosen": 0,
            })

        return needed_must, needed_electives

    def generate_recommendations(
        self,
        user_courses: Dict,
        user_prefs: Dict,
        all_courses: List[Dict],
        rmp_index: Dict[str, Any] = None,
        num_recommendations: int = 10,
        ger_lookup: Dict[str, List[str]] = None
    ) -> List[Dict]:
        
        try:
            # Clear caches at start of each run
            self._clear_caches()
            
            if not user_courses or not isinstance(user_courses, dict):
                return []
            if not user_prefs or not isinstance(user_prefs, dict):
                return []
            if not all_courses or not isinstance(all_courses, list):
                return []
            
            unique_courses_map = {}
            all_courses_map = {}
            for c in all_courses:
                if not c or not isinstance(c, dict):
                    continue
                code = normalize_course_code(c.get("code") or "")
                if code:
                    if code not in unique_courses_map:
                        unique_courses_map[code] = c
                    all_courses_map[code] = c
            
            all_courses = list(unique_courses_map.values())

            completed: Set[str] = set()
            
            course_field_mappings = [
                "incoming_transfer_courses", "incoming_test_courses", "emory_courses",
                "transfer_courses", "test_courses", "Transfer", "Test", "Emory"
            ]
            
            for field_name in course_field_mappings:
                courses = user_courses.get(field_name)
                if courses and isinstance(courses, list):
                    for code in courses:
                        if code:
                            completed.add(normalize_course_code(str(code)))
                elif courses and isinstance(courses, str):
                    completed.add(normalize_course_code(courses))

            degree_type = str(user_prefs.get("degreeType") or "BS").upper()
            major_reqs = CSBS_REQUIREMENTS if degree_type == "BS" else CSBA_REQUIREMENTS

            needed_must, needed_electives = self._get_remaining_requirements(completed, major_reqs)

            ic_status = self._get_ic_status(completed)
            if not ic_status or not isinstance(ic_status, dict):
                ic_status = {"fulfilled": False, "language_counts": {}, "best_language": None, "highest_completed": {}}

            year = str(user_prefs.get("year") or "Freshman")
            if year not in ["Freshman", "Sophomore", "Junior", "Senior"]:
                year = "Freshman"

            raw_credits = user_prefs.get("preferredCredits")
            if raw_credits is None:
                target_credits = 15
            elif isinstance(raw_credits, str):
                try:
                    target_credits = int(float(raw_credits))
                except:
                    target_credits = 15
            else:
                target_credits = int(raw_credits)
            
            is_overload = target_credits > 19
            max_credits = 21 if is_overload else 19
            target_credits = max(12, min(max_credits, target_credits))

            needed_gers = self._get_remaining_gers(completed, all_courses, GER_REQUIREMENTS, ic_status, year, ger_lookup)

            time_unavailable = user_prefs.get("timeUnavailable")
            if not isinstance(time_unavailable, list):
                time_unavailable = []
            unavailable_blocks = self._parse_time_unavailable(time_unavailable)
            time_pref = user_prefs.get("timePreference")

            interests = user_prefs.get("interests")
            if not isinstance(interests, list):
                interests = []

            potential_roots: List[Dict] = []

            for course in all_courses:
                if not course or not isinstance(course, dict):
                    continue
                    
                meta = self._get_course_metadata(course)
                course_code = meta["normalized_code"]
                course_dept = meta["department"]
                course_num = meta["course_number"]
                
                if not course_code or course_code in completed:
                    continue

                is_must_course = course_code in needed_must
                
                is_lang_102 = (
                    course_dept in IC_LANGUAGE_PREFIXES
                    and course_num == 102
                    and ic_status.get("highest_completed", {}).get(course_dept) == 101
                    and ic_status.get("language_counts", {}).get(course_dept, 0) == 1
                )
                
                has_conflict = self._has_time_conflict(course, unavailable_blocks)
                
                if has_conflict and not is_must_course and not is_lang_102:
                    continue

                try:
                    score = self._calculate_score(
                        course, course_code, needed_must, needed_electives, needed_gers,
                        interests, time_pref, completed, rmp_index, year, ic_status,
                        language_already_in_schedule=False
                    )

                    if score > 0:
                        course["recommendation_score"] = score
                        course["normalized_code"] = course_code
                        potential_roots.append(course)
                except Exception:
                    continue

            if not potential_roots:
                return []

            potential_roots.sort(key=lambda x: x.get("recommendation_score") or 0, reverse=True)
            
            # Deduplicate roots
            seen_codes: Set[str] = set()
            seen_title_times: Set[str] = set()
            deduplicated_roots: List[Dict] = []
            
            for root in potential_roots:
                root_code = normalize_course_code(root.get("code") or "")
                if not root_code or root_code in seen_codes:
                    continue
                
                cross_listed = root.get("cross_listed_with") or []
                if isinstance(cross_listed, str):
                    cross_listed = [cross_listed]
                
                is_cross_listed_dup = any(
                    normalize_course_code(cl) in seen_codes 
                    for cl in cross_listed if cl
                )
                
                if is_cross_listed_dup:
                    continue
                
                root_title = (root.get("title") or "").strip().lower()
                root_time = (root.get("time") or "").strip()
                title_time_key = f"{root_title}|{root_time}" if root_title and root_time else None
                
                if title_time_key and title_time_key in seen_title_times:
                    continue
                
                deduplicated_roots.append(root)
                seen_codes.add(root_code)
                for cl in cross_listed:
                    if cl:
                        seen_codes.add(normalize_course_code(cl))
                
                if title_time_key:
                    seen_title_times.add(title_time_key)
                
                if len(deduplicated_roots) >= 40:
                    break
            
            top_roots = deduplicated_roots

            heap = FibonacciHeap()

            for root in top_roots:
                try:
                    total_score, schedule = self._build_schedule_tree(
                        root, all_courses, all_courses_map, unavailable_blocks,
                        completed, needed_must, needed_electives, needed_gers,
                        interests, time_pref, rmp_index, year, ic_status,
                        target_credits, max_credits
                    )

                    if needed_must:
                        schedule_codes = {
                            normalize_course_code(c.get("code") or "")
                            for c in (schedule or [])
                        }
                        num_must_covered = len(schedule_codes & needed_must)
                        if num_must_covered > 0:
                            total_score = (total_score or 0) + num_must_covered * 120.0

                    # Schedule-level bonus for including 102 when 101 is done
                    if ic_status and isinstance(ic_status, dict):
                        highest_completed = ic_status.get("highest_completed", {})
                        language_counts = ic_status.get("language_counts", {})
                        
                        schedule_codes = {
                            normalize_course_code(c.get("code") or "")
                            for c in (schedule or [])
                        }
                        
                        for lang, count in language_counts.items():
                            if count == 1 and highest_completed.get(lang) == 101:
                                expected_102 = f"{lang}102"
                                if expected_102 in schedule_codes:
                                    total_score = (total_score or 0) + 100.0

                    total_credits = sum(parse_credits(c.get("credits")) for c in schedule)

                    schedule_obj = {
                        "root_course": root,
                        "total_score": total_score or 0,
                        "courses": schedule or [],
                        "course_count": len(schedule) if schedule else 0,
                        "total_credits": total_credits,
                    }

                    heap.insert(total_score or 0, schedule_obj)
                except Exception:
                    continue

            raw_recommendations = heap.extract_top_k(num_recommendations * 4) or []
            
            # Deduplicate schedules
            seen_schedules: Set[frozenset] = set()
            recommendations: List[Dict] = []
            
            for rec in raw_recommendations:
                courses = rec.get("courses") or []
                
                title_time_sig = frozenset(
                    f"{(c.get('title') or '').strip().lower()}|{(c.get('time') or '').strip()}"
                    for c in courses
                )
                
                if title_time_sig in seen_schedules:
                    continue
                
                is_too_similar = False
                
                current_lang = None
                for c in courses:
                    dept = get_department(c.get("code") or "")
                    if dept in IC_LANGUAGE_PREFIXES:
                        current_lang = dept
                        break
                
                course_codes = frozenset(
                    normalize_course_code(c.get("code") or "")
                    for c in courses
                )
                
                for existing in recommendations:
                    existing_courses = existing.get("courses") or []
                    existing_codes = frozenset(
                        normalize_course_code(c.get("code") or "")
                        for c in existing_courses
                    )
                    
                    existing_lang = None
                    for c in existing_courses:
                        dept = get_department(c.get("code") or "")
                        if dept in IC_LANGUAGE_PREFIXES:
                            existing_lang = dept
                            break
                    
                    if current_lang != existing_lang:
                        continue
                    
                    different_courses = len(course_codes ^ existing_codes)
                    
                    if different_courses < 4:
                        is_too_similar = True
                        break
                
                if is_too_similar:
                    continue
                
                seen_schedules.add(title_time_sig)
                recommendations.append(rec)
                
                if len(recommendations) >= num_recommendations:
                    break

            return recommendations
            
        except Exception:
            return []


def generate_schedule_for_user(
    shared_id: int,
    course_col,
    pref_col,
    enriched_courses_col,
    rmp_col=None,
    basic_courses_col=None,
    num_recommendations: int = 15
) -> Dict:

    try:
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
                "has_preferences": user_prefs is not None,
            }

        all_courses = list(enriched_courses_col.find({}))

        ger_lookup: Dict[str, List[str]] = {}
        if basic_courses_col is not None:
            basic_docs = list(basic_courses_col.find({}, {"code": 1, "ger": 1}))
            for doc in basic_docs:
                code = normalize_course_code(doc.get("code") or "")
                if not code:
                    continue
                ger = doc.get("ger") or []
                if isinstance(ger, str):
                    ger = [ger]
                elif not isinstance(ger, list):
                    ger = []
                ger_lookup[code] = ger

        rmp_index: Dict[str, Any] = {}
        if rmp_col is not None:
            engine_tmp = IntegratedRecommendationEngine()
            rmp_docs = list(
                rmp_col.find({}, {"name": 1, "rating": 1, "num_ratings": 1, "department": 1})
            )
            for doc in rmp_docs:
                name = doc.get("name")
                norm_name = engine_tmp._normalize_name(name)
                if not norm_name:
                    continue
                rmp_index[norm_name] = doc
                for k in engine_tmp._first_last_keys(norm_name):
                    if k not in rmp_index:
                        rmp_index[k] = doc

        engine = IntegratedRecommendationEngine()
        recommendations = engine.generate_recommendations(
            user_courses=user_courses,
            user_prefs=user_prefs,
            all_courses=all_courses,
            rmp_index=rmp_index,
            num_recommendations=num_recommendations,
            ger_lookup=ger_lookup if basic_courses_col is not None else None
        )

        formatted_schedules = []
        for schedule_obj in recommendations:
            root = schedule_obj.get("root_course") or {}
            courses = schedule_obj.get("courses") or []

            formatted_courses = []
            for course in courses:
                if not course:
                    continue
                formatted_courses.append({
                    "code": course.get("code"),
                    "title": course.get("title"),
                    "professor": course.get("professor"),
                    "credits": course.get("credits"),
                    "time": course.get("time"),
                    "meeting": course.get("meeting"),
                    "rmp": course.get("rmp"),
                    "score": round(course.get("recommendation_score") or 0, 2),
                    "ger": course.get("ger"),
                    "normalized_code": normalize_course_code(course.get("code") or ""),
                })

            formatted_schedules.append({
                "root_course_code": root.get("code"),
                "total_score": round(schedule_obj.get("total_score") or 0, 2),
                "courses": formatted_courses,
                "course_count": schedule_obj.get("course_count") or len(formatted_courses),
                "total_credits": schedule_obj.get("total_credits") or sum(
                    parse_credits(c.get("credits")) for c in formatted_courses
                ),
            })

        return {
            "success": True,
            "schedules": formatted_schedules,
            "count": len(formatted_schedules),
            "metadata": {
                "degree_type": user_prefs.get("degreeType"),
                "year": user_prefs.get("year"),
                "interests": user_prefs.get("interests"),
                "total_courses_processed": len(all_courses),
                "target_credits": user_prefs.get("preferredCredits") or 15,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }