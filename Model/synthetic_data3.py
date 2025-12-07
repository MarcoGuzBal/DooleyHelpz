from synthetic_data2 import GER_PROBS_BY_YEAR, ger_dictionary, CORE_GER_REQUIRED, CS_MATH_CORE, ADV_CS_WITH_PROB, MATH_ELECTIVES, PROTECTED_CORE, has_prereqs
import random
from typing import List, Set, Dict
from synthetic_data_generation import wrapper_genrate_incoming_test_for_freshman, basic_col
from pprint import pprint
from dotenv import load_dotenv
import os


# Target number of Emory courses (excluding incoming/test)
TARGET_COUNTS_BY_YEAR: Dict[str, tuple[int, int]] = {
    "sophomore": (14, 19),
    "junior":    (24, 29),
    "senior":    (34, 39),
}

GER_ELECTIVES_POOL = [
    "ECON101", "ECON112", "PSYC110", "PSYC111",
    "SOC190", "AAS190", "REL250", "AAS285",
    "PORT190", "KRN101", "KRN102", "LAT101",
    "SPAN318", "ENVS140", "LING201", "ARTVIS120",
    "PE173", "PE125", "PE164",
]


def integrate_ger_categories(
    courses: Set[str],
    ger_pools: Dict[str, List[str]],
    ger_probs_for_year: Dict[str, float],
    protected: Set[str] | None = None,
) -> Set[str]:
    """
    For each GER area listed in `ger_probs_for_year`, use its probability
    to decide whether this student should satisfy that GER.

    If a GER area is selected but currently not satisfied, we:
      - add one random course from that GER pool
      - remove one non-core course (not in `protected`)
        to keep total count unchanged.
    """
    if protected is None:
        protected = set()

    def has_ger(ger_key: str) -> bool:
        pool = set(ger_pools.get(ger_key, []))
        return any(c in pool for c in courses)

    def pick_replaceable_course() -> str | None:
        replaceable = [c for c in courses if c not in protected]
        if not replaceable:
            return None
        return random.choice(replaceable)

    for ger_key, prob in ger_probs_for_year.items():
        if random.random() >= prob:
            continue  # this GER not enforced for this student

        if has_ger(ger_key):
            continue  # already has at least one course in this GER

        pool = ger_pools.get(ger_key, [])
        if not pool:
            continue

        ger_course = random.choice(pool)
        
        if ger_course in courses:
            continue

        to_drop = pick_replaceable_course()
        if to_drop is None:
            # no safe course to drop → to keep count fixed, skip
            continue

        courses.remove(to_drop)
        courses.add(ger_course)
        print(f"added GER {ger_key} course:", ger_course)

    return courses


def generate_emory_courses_for_year(
    year: str,
    incoming_test_courses: List[str],
) -> List[str]:
    """
    Generic generator for sophomore / junior / senior Emory courses.

    Steps:
      1. Start from incoming (normalized, e.g. MATH112Z -> MATH112).
      2. Add CS/MATH core + common required GER (ENGRD101, ECS101, HLTH100).
      3. Add some advanced CS + math electives (depending on prereqs).
      4. Integrate GER (HA/SS/NS/QR/ETHN/IC/CW/XA) using per-year probs,
         but keep total number of courses fixed during this step.
      5. Finally, top up or trim with generic electives so that the total
         number of Emory courses (excluding incoming) is within the
         target range for that year.
    """
    assert year in TARGET_COUNTS_BY_YEAR, f"Unknown year: {year}"

    # --- Step 1: normalize incoming and seed the set ---
    if "MATH112Z" in incoming_test_courses:
        incoming_test_courses = [
            "MATH112" if c == "MATH112Z" else c
            for c in incoming_test_courses
        ]
    courses: Set[str] = set(incoming_test_courses)

    # --- Step 2 + 3: core GER + CS/MATH core + common lower-level courses ---

    # 2a) Required GER (ENGRD101, ECS101, HLTH100)
    courses.update(CORE_GER_REQUIRED)

    # 2b) CS/MATH core
    for c in CS_MATH_CORE:
        if random.random() < 0.90:
            courses.add(c)

    
    # --- Step 4: integrate GER areas (HA/SS/NS/QR/ETHN/IC/CW/XA) ---
    courses = integrate_ger_categories(
        courses=courses,
        ger_pools=ger_dictionary,
        ger_probs_for_year=GER_PROBS_BY_YEAR[year],
        protected=PROTECTED_CORE,
    )


    # --- Step 3: advanced CS & math electives ---
    for cs_code, prob in ADV_CS_WITH_PROB:
        # you can make this year-dependent later if you want:
        # e.g. boost probs for juniors/seniors
        if has_prereqs(cs_code, courses) and random.random() < prob:
            courses.add(cs_code)

    for math_code, prob in MATH_ELECTIVES:
        if random.random() < prob:
            courses.add(math_code)

    
    # --- Step 5: adjust total number to target range with generic electives ---

    # current Emory course count (excluding incoming)
    # Note: incoming courses are already in `courses`,
    # so "excluding incoming" means: pick a target and then
    # adjust based on len(courses) - len(incoming_test_courses) if you want.
    # For simplicity, we just control len(courses) directly here.

    min_target, max_target = TARGET_COUNTS_BY_YEAR[year]
    target_total = random.randint(min_target, max_target) + len(incoming_test_courses)

    # pool for generic electives (non-core) to add if we are short
    # you can merge GER_ELECTIVES_POOL + some HA/SS/NS courses etc.
    generic_elective_pool = list(set(
        GER_ELECTIVES_POOL
        + ger_dictionary.get("HA", [])
        + ger_dictionary.get("SS", [])
        + ger_dictionary.get("NS", [])
    ))

    # a helper to pick a non-core course to drop
    def pick_replaceable_course() -> str | None:
        replaceable = [c for c in courses if c not in PROTECTED_CORE]
        if not replaceable:
            return None
        return random.choice(replaceable)

    # If we have fewer than target_total, add electives
    while len(courses) < target_total and generic_elective_pool:
        code = random.choice(generic_elective_pool)
        courses.add(code)

    # If we have more than target_total, drop non-core courses
    safety = 0
    while len(courses) > target_total and safety < 100:
        to_drop = pick_replaceable_course()
        if to_drop is None:
            break
        courses.remove(to_drop)
        safety += 1

    return sorted(courses)


if __name__ == "__main__":
    incoming_test_courses = wrapper_genrate_incoming_test_for_freshman(5, 10)
    for incoming in incoming_test_courses:
        emory_courses = generate_emory_courses_for_year("sophomore", incoming)
        # emory_courses = generate_emory_courses_for_year("junior", incoming)
        # emory_courses = generate_emory_courses_for_year("senior", incoming)
        print("Generated Emory courses:")
        pprint(emory_courses)
        print("total courses (including incoming):", len(emory_courses))
        print()