import random
from typing import List, Set, Dict
from synthetic_data_generation import wrapper_genrate_incoming_test_for_freshman, basic_col
from pprint import pprint

from dotenv import load_dotenv
import os
from pymongo import MongoClient
from track_graduation import CSBS_major_dictionary, get_regex

load_dotenv()
uri = os.getenv("DB_URI")
client = MongoClient(uri)
user_db = client["Users"]
courses_col = user_db["TestCourses"]
preferences_col = user_db["TestPreferences"]


GER_PROBS_BY_YEAR: Dict[str, Dict[str, float]] = {
    "sophomore": {
        # sophomore-level GERs: first push at 0.75
        "HA": 0.75,
        "SS": 0.75,
        "NS": 0.75,
        "QR": 0.75,

        # junior-level GERs: almost none at sophomore stage
        "ETHN": 0.2,   # tiny chance someone starts early
        "IC":   0.2,

        # senior-level GERs: basically 0 at this stage
        "CW": 0.2,
        "XA": 0.1,
    },

    "junior": {
        # sophomore-level GERs: if still missing, harder push (prob ↑)
        "HA": 0.95,
        "SS": 0.95,
        "NS": 0.95,
        "QR": 0.95,

        # junior-level GERs (your numbers)
        "ETHN": 0.7,   # junior-level GER = 0.25
        "IC":   0.8,   # IC one course this year

        # senior-level GERs: a small chance to start early
        "CW": 0.4,
        "XA": 0.3,
    },

    "senior": {
        # sophomore-level GERs: last chance, highest probability
        "HA": 0.98,
        "SS": 0.98,
        "NS": 0.98,
        "QR": 0.98,

        # junior-level GERs: still allow/force completion if missing
        "ETHN": 0.95,   # higher than junior to reflect “must be done”
        "IC":   0.95,   # same 0.3 as junior → two IC ≈ 0.09 total

        # senior-level GERs (your numbers)
        "CW": 0.7,
        "XA": 0.6,
    },
}

# --- prerequisite map: only include courses we will actually use ---
PREREQS: Dict[str, list[list[str]]] = {
    "CS325": [["CS224"], ["CS253"]],
    "CS326": [["CS170"], ["CS171"], ["CS224"], ["CS253"]],
    "CS329": [["CS171"]],
    "CS334": [["CS224"], ["CS253"], ["MATH221"]],
    "CS350": [["CS253"], ["CS255"]],
    "CS370": [["CS253"]],
    "CS377": [["CS253"]],
}

# Required GER courses that almost every student takes early
CORE_GER_REQUIRED = ["ENGRD101", "ECS101", "HLTH100", "PE130", "MATH190"]

# Common but not strictly mandatory (we treat them as "likely")
COMMON_BUT_NOT_STRICT = ["PE130", "MATH190"]

# Core major courses that every CS student should finish early
CS_MATH_CORE = [
    "MATH111", "MATH112", "MATH221",
    "CS170", "CS171", "CS224", "CS253", "CS255"
]

# Advanced CS courses with probability (only added if prereqs are satisfied)
ADV_CS_WITH_PROB = [
    ("CS326", 0.65),  # lowered from 1.0 to be more realistic
    ("CS350", 0.60),
    ("CS370", 0.80),
    ("CS377", 0.70),
    ("CS334", 0.40),
    ("CS325", 0.35),
    ("CS329", 0.30),
]

# Optional math electives
MATH_ELECTIVES = [
    ("MATH211", 0.5),
    ("MATH212", 0.5),
    ("MATH250", 0.4),
    ("MATH315", 0.4),
]


def get_ger_codes(ger: str) -> Dict[str, List[str]]:
    """
    Query the basic_col collection for courses whose GER array contains `ger`,
    and return a dict like {ger: [list of non-Oxford course codes]}.
    """
    query = {"ger": ger}
    projection = {"_id": 0, "code": 1}

    cursor = basic_col.find(query, projection)
    results = [doc["code"] for doc in cursor]

    # filter out Oxford courses
    results = [code for code in results if "_OX" not in code]

    return {ger: results}


# Build GER dictionary: {"HA": [...], "SS": [...], "NS": [...], "QR": [...]}
ger_dictionary: Dict[str, List[str]] = {}
ger_dictionary.update(get_ger_codes("HA"))
ger_dictionary.update(get_ger_codes("SS"))
ger_dictionary.update(get_ger_codes("NS"))
ger_dictionary.update(get_ger_codes("QR"))
# above is sophomore-level GERs
ger_dictionary.update(get_ger_codes("ETHN"))
ger_dictionary.update(get_ger_codes("IC")) # needs 2 for completion
# above is junior-level GERs
ger_dictionary.update(get_ger_codes("CW")) # needs 2 for completion
ger_dictionary.update(get_ger_codes("XA"))
# above is senior-level GERs



# Protected core: courses we do NOT want to drop when swapping in GER courses
PROTECTED_CORE: Set[str] = set(CORE_GER_REQUIRED + CS_MATH_CORE)


def has_prereqs(course: str, taken: Set[str]) -> bool:
    """
    Check if a course's prerequisite groups are satisfied.

    Each prereq group is a list of acceptable alternatives.
    A group is satisfied if *any* code within that group is present.
    """
    if course not in PREREQS:
        return True  # no prereqs = always allowed
    for group in PREREQS[course]:
        # Ignore OX codes; treat only Emory equivalents as valid
        if not any(code in taken for code in group if not code.endswith("_OX")):
            return False
    return True


def integrate_ger_categories(
    courses: Set[str],
    ger_pools: Dict[str, List[str]],
    take_prob: float = 0.75,
    protected: Set[str] | None = None,
) -> Set[str]:
    """
    For each GER area (HA, SS, NS, QR), with probability `take_prob`,
    ensure the student has at least one course from that GER area.

    If a GER area is selected but currently not satisfied, we:
      - add one random course from that GER pool
      - remove one non-core course (not in `protected`) to keep total count unchanged
    """
    if protected is None:
        protected = set()

    def has_ger(ger_key: str) -> bool:
        """Check if `courses` already contains at least one course in this GER area."""
        pool = set(ger_pools.get(ger_key, []))
        return any(c in pool for c in courses)

    def pick_replaceable_course() -> str | None:
        """
        Pick a course that is safe to drop (i.e., not in `protected`).
        Returns None if no safe course is available.
        """
        replaceable = [c for c in courses if c not in protected]
        if not replaceable:
            return None
        return random.choice(replaceable)

    for ger_key in ["HA", "SS", "NS", "QR"]:
        # Decide whether this student "should" have this GER area satisfied
        if random.random() >= take_prob:
            continue  # skip this GER for this student

        # Already satisfied: do nothing
        if has_ger(ger_key):
            continue

        pool = ger_pools.get(ger_key, [])
        if not pool:
            continue

        # Choose one GER course to add
        ger_course = random.choice(pool)

        # If it's already in the transcript, nothing to change
        if ger_course in courses:
            continue

        # To keep total count unchanged, drop one non-core course
        to_drop = pick_replaceable_course()
        if to_drop is None:
            # No safe course to drop; to strictly preserve size, we skip
            continue

        courses.remove(to_drop)
        courses.add(ger_course)

    return courses


def generate_sophomore_emory_courses(incoming_test_courses: List[str]) -> List[str]:
    """
    Generate a realistic list of `emory_courses` for a CS sophomore.

    Rules:
    - Start with incoming test courses (merged into the transcript)
    - Normalize MATH112Z -> MATH112
    - Always include required GER courses (ENGRD101, ECS101, HLTH100)
    - Always include core CS/MATH courses for major progress
    - Add PE130 and MATH190 with moderate probability
    - Add advanced CS if prereqs are satisfied + probability threshold
    - Add some math electives
    - Then integrate HA/SS/NS/QR GER courses without changing total count
    """

    # Normalize MATH112Z to MATH112 in the Emory transcript
    if "MATH112Z" in incoming_test_courses:
        incoming_test_courses = [
            "MATH112" if c == "MATH112Z" else c
            for c in incoming_test_courses
        ]

    # Start with incoming test courses
    courses: Set[str] = set(incoming_test_courses)

    # (1) Required GER courses
    courses.update(CORE_GER_REQUIRED)

    # (2) Core CS / Math courses
    for c in CS_MATH_CORE:
        courses.add(c)

    # (3) Common but not mandatory lower-level courses
    if "PE130" not in courses and random.random() < 0.7:
        courses.add("PE130")
    if "MATH190" not in courses and random.random() < 0.5:
        courses.add("MATH190")

    # (4) Advanced CS courses (check prereqs + probability)
    for cs_code, prob in ADV_CS_WITH_PROB:
        if has_prereqs(cs_code, courses) and random.random() < prob:
            courses.add(cs_code)

    # (5) Math electives
    for math_code, prob in MATH_ELECTIVES:
        if random.random() < prob:
            courses.add(math_code)

    # Optionally you can enforce a loose minimum size before GER integration,
    # but this step is not strictly required. If you do want it, uncomment
    # and adjust the logic below.

    # desired_min = 18  # target minimum number of courses
    # current_n = len(courses)
    # if current_n < desired_min:
    #     # If you have a generic elective pool, you can top up here.
    #     pass

    # (6) Integrate HA / SS / NS / QR courses WITHOUT changing total count
    courses = integrate_ger_categories(
        courses=courses,
        ger_pools=ger_dictionary,
        take_prob=0.75,          # roughly 3 out of 4 GER areas on average
        protected=PROTECTED_CORE,
    )

    return sorted(courses)


if __name__ == "__main__":
    # Example: generate 5 random sophomores using your freshman incoming_test generator
    # random.seed(42)

    # incoming_tests_list = wrapper_genrate_incoming_test_for_freshman(5, 10)

    # for i, test_courses in enumerate(incoming_tests_list):
    #     emory_courses = generate_sophomore_emory_courses(test_courses)
    #     print(f"\n--- Sophomore {i+1} ---")
    #     print("Incoming Test Courses:")
    #     pprint(sorted(test_courses))
    #     print("Generated Emory Courses:")
    #     pprint(emory_courses)

    print(ger_dictionary)

    # If you later want to insert into Mongo, you can do something like:
    # docs = []
    # for idx, test_courses in enumerate(incoming_tests_list, start=1):
    #     shared_id = f"{idx:06d}"  # or whatever scheme you want
    #     docs.append({
    #         "shared_id": shared_id,
    #         "emory_courses": generate_sophomore_emory_courses(test_courses),
    #         "incoming_test_courses": test_courses,
    #         "incoming_transfer_courses": [],
    #     })
    # courses_col.insert_many(docs)