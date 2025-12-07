import json
import random
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from pprint import pprint
from track_graduation import CSBS_major_dictionary, get_regex

load_dotenv()
uri = os.getenv("DB_URI")
client = MongoClient(uri)
user_db = client["Users"]
courses_col = user_db["TestCourses"]
preferences_col = user_db["TestPreferences"]
basic_data = client["BasicCourses"]
basic_col = basic_data["BasicCourses"]
detail_data = client["DetailedCourses"]
detail_col = detail_data["DetailedCourses"]

out_path = "data/synthetic_pref.json"


INCOMING_POOL = {
    "MATH111": "MATH111",
    "MATH112Z": "MATH112Z",
    "ECON101": "ECON101",
    "ECON112": "ECON112",
    "MUS114": "MUS114",
    "MUS121": "MUS121",
    "PHYS141": "PHYS141",
    "PHYS142": "PHYS142",
    "PHYS151": "PHYS151",
    "PHYS152": "PHYS152",
    "PSYC111": "PSYC111",
    "BIOL141": "BIOL141",
    "CHEM150": "CHEM150",
    "CHEM150L": "CHEM150L",
    "CS170": "CS170",
    "FILM101": "FILM101",
    "MATH112Z": "MATH112Z",
    "THEA100": "THEA100",
    "CHN102": "CHN102",
    "FREN201": "FREN201",
    "GER102": "GER102",
    "ITAL102": "ITAL102",
    "JPN102": "JPN102",
    "LAT102": "LAT102",
    "SPAN102": "SPAN102",
    "ARAB102": "ARAB102",
    "GRK102": "GRK102",
    "HNDI102": "HNDI102",
    "KOR102": "KOR102",
    "PORT102": "PORT102",
    "RUSS102": "RUSS102",
    "AAS238": "AAS238",
    "ARTHIST101": "ARTHIST101",
    "ARTVIS103": "ARTVIS103",
    "ARTVIS109": "ARTVIS109",
    "CPLT101": "CPLT101",
    "ENGRD101": "ENGRD101",
    "ENVS130": "ENVS130",
}

# Grouped views for easier sampling
MATH_CODES = ["MATH111", "MATH112Z"]
SCIENCE_CODES = ["PHYS141", "PHYS142", "PHYS151", "PHYS152", "BIOL141", "CHEM150"]  # CHEM150L handled as pair
ECON_CODES = ["ECON101", "ECON112"]
CS_CODES = ["CS170"]
HUMANITIES_CODES = [
    "PSYC111", "FILM101", "THEA100", "AAS238",
    "ARTHIST101", "ARTVIS103", "ARTVIS109",
    "CPLT101"
]
ENGRD_CODE = ["ENGRD101"]
LANGUAGE_CODES = [
    "CHN102", "FREN201", "GER102", "ITAL102", "JPN102",
    "LAT102", "SPAN102", "ARAB102", "GRK102", "HNDI102",
    "KOR102", "PORT102", "RUSS102"
]
MUSIC_CODES = ["MUS114", "MUS121"]

def get_requirements():
   
    list_mathcs_courses = get_regex("^CS")
    list_mathcs_courses += ["MATH111", "MATH112", "MATH221"]
    # pprint(list_cs_courses)
    
    for code in list_mathcs_courses:
        if "CS_OX" in code:
            continue
        query = {"code": code}
        result = detail_col.find_one(query, {"_id": 0, "requirements": 1, "type": 1})
        if not result:
            result = basic_col.find_one(query, {"_id": 0, "requirements": 1, "type": 1})
        if result:
            print()
            pprint(code)
            pprint(result["type"])
            pprint(result["requirements"])


def generate_synthetic_preferences():
    # random seed for reproducibility
    random.seed(42)

    # year → expected graduation year mapping
    years_info = [
        ("Freshman", "2029"),
        ("Sophomore", "2028"),
        ("Junior", "2027"),
        ("Senior", "2026"),
    ]

    # fixed priority enum values
    priority_vals = [
        "PROFESSOR_RATING",
        "TIME_PREFERENCE",
        "MAJOR_REQUIREMENTS",
        "GER_REQUIREMENTS",
        "INTERESTS",
    ]

    # possible interest options
    interests_all = ["AI/ML", "Software Engineering", "Robotics", "Data Science"]

    # weekdays allowed for timeUnavailable
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    prefs = []
    sid = 1  # shared_id counter

    for year_name, grad_year in years_info:
        for i in range(10):  # generate 10 entries per class year
            shared_id = f"{sid:06d}"
            sid += 1

            degreeType = random.choice(["BA", "BS"])

            # semester distribution rule:
            # Seniors: exactly first 4 Spring, remaining Fall
            # Others: ~85% Fall, ~15% Spring
            if year_name == "Senior":
                semester = "Spring" if i < 4 else "Fall"
            else:
                semester = "Fall" if random.random() < 0.85 else "Spring"

            # preferredCredits distribution:
            # mostly 14–18, some 12/13, very few 19–22
            r = random.random()
            if r < 0.1:
                preferredCredits = random.choice([12, 13])
            elif r < 0.9:
                preferredCredits = random.randint(14, 18)
            else:
                preferredCredits = random.randint(19, 22)

            # interests: choose 0–3 items
            k = random.choice([0, 1, 1, 2, 2, 3])
            interests = random.sample(interests_all, k) if k > 0 else []

            # timePreference: earliest 08–11, latest between earliest+4 and 21
            earliest_hour = random.randint(8, 11)
            latest_hour = random.randint(
                earliest_hour + 4, min(21, earliest_hour + 10)
            )
            timePreference = [
                f"{earliest_hour:02d}:00",
                f"{latest_hour:02d}:00",
            ]

            # timeUnavailable: 0–2 weekday blocks
            blocks = []
            num_blocks = random.choice([0, 0, 0, 1, 1, 2])  # biased toward 0–1
            for _ in range(num_blocks):
                day = random.choice(weekdays)
                start_hour = random.randint(8, 17)
                end_hour = random.randint(start_hour + 1, min(21, start_hour + 4))
                blocks.append(
                    {
                        "day": day,
                        "start": f"{start_hour:02d}:00",
                        "end": f"{end_hour:02d}:00",
                    }
                )

            # shuffle priority order
            priorityOrder = priority_vals[:]
            random.shuffle(priorityOrder)

            prefs.append(
                {
                    "shared_id": shared_id,
                    "degreeType": degreeType,
                    "year": year_name,
                    "expectedGraduation": {
                        "semester": semester,
                        "year": grad_year,
                    },
                    "preferredCredits": preferredCredits,
                    "interests": interests,
                    "timePreference": timePreference,
                    "timeUnavailable": blocks,
                    "priorityOrder": priorityOrder,
                }
            )

    # store final JSON array
    
    with open(out_path, "w") as f:
        json.dump(prefs, f, indent=4)


def generate_synthetic_courses():
    pass

def wrapper_genrate_incoming_test_for_freshman(n, seed) -> list[str]:
    random.seed(seed)
    objs = []
    for i in range(n):
        objs.append(generate_incoming_test_for_freshman())
    return objs

def choose_total_incoming_tests() -> int:
    """
    Decide how many incoming_test_courses a freshman has.
    Distribution (CS-heavy population):
      - ~30%: 0 courses
      - ~40%: 2–4 courses
      - ~20%: 5–8 courses
      - ~10%: 9–11 courses
    """
    r = random.random()
    if r < 0.30:
        return 0
    elif r < 0.70:
        return random.randint(2, 4)
    elif r < 0.90:
        return random.randint(5, 8)
    else:
        return random.randint(9, 11)


def generate_incoming_test_for_freshman() -> list[str]:
    """
    Generate a realistic incoming_test_courses list for a CS freshman.
    Rules:
      - Uses the provided pool of course codes.
      - MATH112Z never appears without MATH111.
      - CHEM150 and CHEM150L always appear together.
      - Bias toward Math / Science / Econ / CS.
    """
    total_target = choose_total_incoming_tests()
    if total_target == 0:
        return []

    courses: set[str] = set()

    # 1) Math block: MATH111 very common, MATH112Z only if MATH111 is present.
    if random.random() < 0.8:  # ~80% freshmen have at least MATH111
        courses.add("MATH111")
        # MATH112Z appears only tied to MATH111, maybe 40% of those
        if random.random() < 0.4:
            courses.add("MATH112Z")

    # 2) Science block: high probability for at least one science AP.
    # We'll try to add up to 1–3 science items, respecting CHEM150/CHEM150L pairing.
    if random.random() < 0.7:  # 70% have science test credit
        num_science = random.choice([1, 2, 2, 3])  # bias to 2
        for _ in range(num_science):
            if len(courses) >= total_target:
                break
            code = random.choice(SCIENCE_CODES)
            if code == "CHEM150":
                # enforce CHEM150 + CHEM150L pair
                courses.add("CHEM150")
                courses.add("CHEM150L")
            else:
                courses.add(code)

    # 3) Econ: common among CS students.
    if random.random() < 0.5:  # ~50% have Econ AP
        courses.add(random.choice(ECON_CODES))

    # 4) CS170: some AP CS A people.
    if random.random() < 0.2:  # ~20% have CS AP
        courses.add("CS170")

    # 5) Humanities / ENGRD / PSYC
    if random.random() < 0.35:  # ~35% have at least one humanities test credit
        num_hum = random.choice([1, 1, 2])  # 1 or 2
        for _ in range(num_hum):
            if len(courses) >= total_target:
                break
            courses.add(random.choice(HUMANITIES_CODES))
    if random.random() < 0.20:
        courses.add("ENGRD101")

    # 6) Language credits (lower probability for this CS-heavy population)
    if random.random() < 0.25:
        courses.add(random.choice(LANGUAGE_CODES))

    # 7) Music credits (rare)
    if random.random() < 0.1:
        courses.add(random.choice(MUSIC_CODES))

    # If we still have fewer than target, top up with random choices from the whole pool,
    # while still respecting the special constraints.
    pool_all_simple = list(INCOMING_POOL.values())

    def add_random_course_respecting_constraints():
        code = random.choice(pool_all_simple)
        # special handling for MATH112Z and CHEM150
        if code == "MATH112Z":
            if "MATH111" not in courses:
                # ensure MATH111 too
                courses.add("MATH111")
            courses.add("MATH112Z")
        elif code == "CHEM150":
            courses.add("CHEM150")
            courses.add("CHEM150L")
        elif code == "CHEM150L":
            # if we randomly hit CHEM150L alone, add the pair
            courses.add("CHEM150")
            courses.add("CHEM150L")
        else:
            courses.add(code)

    # top-up loop
    safety_counter = 0
    while len(courses) < total_target and safety_counter < 50:
        add_random_course_respecting_constraints()
        safety_counter += 1

    # It's possible we slightly exceed total_target because of pairs; that's okay.
    return sorted(courses)





if __name__ == "__main__":
    # print("connected to cols successfully")
    # ids_cursor = preferences_col.find({}, {"_id": 0, "shared_id": 1})
    # ids_list = [doc["shared_id"] for doc in ids_cursor]
    # ids = list(dict.fromkeys(ids_list))
    # pre_list = []
    # for id in ids:
    #     pre = preferences_col.find_one({"shared_id": id})
    #     pre_list.append(pre)
    
    # pprint(pre_list)

    print("connected to cols successfully")
    ids_cursor = courses_col.find({}, {"_id": 0, "shared_id": 1})
    ids_list = [doc["shared_id"] for doc in ids_cursor]
    ids = list(dict.fromkeys(ids_list))
    c_list = []
    for id in ids:
        c = courses_col.find_one({"shared_id": id})
        c_list.append(c)
    
    # pprint(c_list)

    print(get_regex("^PE"))
    # generate_synthetic_preferences()
    # wrapper_genrate_incoming_test_for_freshman(10)
    
    

    