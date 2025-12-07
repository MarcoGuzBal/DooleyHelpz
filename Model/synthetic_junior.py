import random
from typing import List, Set, Dict
from track_graduation import get_regex

PREREQS: Dict[str, list[list[str]]] = {
    "CS325": [["CS224"], ["CS253"]],
    "CS326": [["CS170"], ["CS171"], ["CS224"], ["CS253"]],
    "CS329": [["CS171"]],
    "CS334": [["CS224"], ["CS253"], ["MATH221"]],
    "CS350": [["CS253"], ["CS255"]],
    "CS370": [["CS253"]],
    "CS377": [["CS253"]],
}

cs_classes = get_regex("^CS")
cs_classes = [c for c in cs_classes if "_OX" not in c]

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
        "CW": 0.6,
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

ger_dictionary = {'HA': ['CHN271W', 'CHN275', 'CL100', 'CL102', 'CL150', 'CL202', 'CL204', 'CL210', 'CL221', 'CL222', 'CL225', 'CL226', 'CL327W', 'HIST104', 'HIST107', 'HIST150', 'HIST200W', 'HIST206W', 'HIST207', 'HIST218', 'HIST226', 'HIST231', 'HIST234', 'HIST239', 'HIST247', 'HIST267W', 'IDS200W', 'IDS216W', 'IDS285W', 'ENG150', 'ENG205', 'ENG210W', 'ENG215', 'ENG216', 'ENG250W', 'ENG255W', 'ENG256W', 'ENG261', 'ENG262W', 'ENG270W', 'ENG271W', 'ENG275W', 'ENG290W', 'ENGRD221RW', 'CPLT201W', 'CPLT202W', 'DANC220', 'PORT285W', 'REL100R', 'REL110', 'REL121', 'REL200R', 'REL210R', 'REL244W', 'REL250', 'JPN270', 'JS101', 'JS180', 'JS218', 'JS280', 'JS281', 'KRN227W', 'LACS102', 'LACS200', 'LACS226', 'LACS270W', 'MUS283', 'FILM101', 'FILM102', 'FILM107', 'FILM201', 'FILM202', 'FILM203', 'FILM204', 'FILM207', 'FILM208', 'FILM212', 'FILM214', 'FILM255', 'FILM272', 'FILM278W', 'GER218', 'GER280', 'HIST103', 'AAS215', 'AAS239', 'AAS261', 'AAS262W', 'AAS267W', 'AFS263', 'AFS282', 'AMST201W', 'AMST226', 'AMST285', 'ANT185', 'RUSS271W', 'RUSS272', 'SPAN285W', 'THEA100', 'THEA210W', 'THEA215', 'THEA216', 'THEA223', 'THEA224', 'THEA250', 'THEA289', 'WGS200', 'WGS210', 'WGS214', 'WGS275', 'PHIL100', 'PHIL111', 'PHIL115', 'PHIL116', 'PHIL120', 'PHIL123', 'PHIL124', 'PHIL127', 'PHIL130', 'PHIL133', 'PHIL134', 'PHIL200W', 'PHIL202W', 'PHIL204W', 'PHIL220W', 'POLS201', 'POLS202', 'MESAS100', 'MESAS102', 'MESAS200W', 'MESAS202W', 'MESAS225', 'MESAS234', 'MESAS244W', 'MUS114', 'MUS121', 'MUS122', 'MUS200', 'MUS204', 'MUS215', 'MUS221', 'MUS222', 'MUS260', 'MUS260W', 'MUS282'], 'SS': ['HIST145', 'HIST214', 'HIST221', 'HIST228', 'HIST254', 'HIST270', 'HLTH210', 'HLTH250', 'ENVS224', 'ENVS227', 'EAS228', 'ECON101', 'ECON112', 'ECON201', 'ECON212', 'ECON215', 'ECON231', 'PSYC111', 'PSYC205', 'PSYC211', 'PSYC212', 'JPN232W', 'JPN234', 'JS270', 'LING101', 'LING201', 'LING234', 'HIST100', 'AAS247', 'AAS259', 'AFS221', 'AMST228', 'ANT101', 'ANT202', 'ANT203', 'ANT204', 'ANT205', 'ANT207', 'ANT230', 'ANT231', 'ANT265', 'RUSS270W', 'SOC101', 'SOC221', 'SOC230', 'SOC245', 'SOC247', 'SOC250', 'WGS265', 'POLS100', 'POLS110', 'POLS111', 'POLS120', 'POLS150', 'POLS208', 'POLS227', 'POLS238', 'POLS272', 'POLS285', 'MESAS204', 'MESAS238', 'MESAS254', 'MESAS272', 'MESAS275'], 'NS': ['CHEM150', 'CHEM202', 'CHEM202Z', 'CHEM203', 'CHEM203Z', 'IDS205W', 'ENVS120', 'ENVS140', 'ENVS219', 'ENVS222', 'ENVS232', 'ENVS239', 'ENVS240', 'PSYC110', 'PSYC207', 'PSYC209', 'PSYC210', 'PSYC215', 'PSYC223', 'MATH170', 'NBB201', 'NBB220', 'ANT200', 'ANT210', 'BIOL120', 'BIOL141', 'BIOL142', 'SUST125', 'PHYS115', 'PHYS116', 'PHYS121', 'PHYS125', 'PHYS220', 'PHYS222', 'PHYS234', 'MUS220'], 'QR': ['CS110', 'CS170', 'CS171', 'CS224', 'CS253', 'CS255', 'ECON220', 'QTM100', 'QTM110', 'QTM200', 'QTM220', 'MATH111', 'MATH112', 'MATH116', 'MATH210', 'MATH211', 'MATH212', 'MATH221', 'PHIL110', 'MATH250', 'MATH276'], 'ETHN': ['CL226', 'HIST104', 'HIST206W', 'HIST207', 'HIST218', 'HIST221', 'HIST222', 'HIST226', 'HIST228', 'HIST234', 'HIST239', 'HIST263W', 'HIST267W', 'HIST270', 'HIST332', 'HIST336', 'HIST338', 'HIST342', 'HIST360', 'HIST363W', 'HIST378', 'HIST384', 'IDS190', 'ENG210W', 'ENG250W', 'ENG261', 'ENG262W', 'ENG270W', 'ENG271W', 'ENG275W', 'ENG356W', 'ENG359W', 'ENG366W', 'ENG375W', 'ENG389', 'ENGRD328W', 'ENVS310', 'CL487W', 'EAS228', 'ECON451', 'PORT190', 'PSYC333', 'ITAL190', 'ITAL375W', 'JS218', 'JS270', 'JS280', 'JS281', 'JS338', 'JS347W', 'JS348W', 'JS435', 'KRN227W', 'LACS101', 'LACS102', 'LACS200', 'LACS226', 'LACS263W', 'LACS265W', 'LACS336', 'LACS360', 'LACS363W', 'LACS378', 'LING342', 'LING347', 'MUS303', 'MUS376W', 'MUS382W', 'NRSG335', 'FILM214', 'FREN313', 'GER218', 'GER280', 'HEBR435', 'AAS100', 'AAS190', 'AAS239', 'AAS247', 'AAS259', 'AAS261', 'AAS262W', 'AAS267W', 'AAS272', 'AAS285', 'AAS303', 'AAS347', 'AAS375', 'AAS384', 'AAS385', 'AFS221', 'AFS222', 'AFS282', 'AFS378', 'AFS386', 'AFS389', 'AFS389W', 'AMST226', 'AMST228', 'AMST336', 'AMST385W', 'ANT347', 'ANT376W', 'ANT378', 'SOC247', 'SPAN485W', 'THEA366W', 'WGS214', 'WGS222', 'WGS378W', 'PHIL124', 'PHIL385', 'POLS285', 'POLS349', 'MESAS102', 'MESAS190', 'MESAS202W', 'MESAS234', 'MESAS275', 'MESAS313', 'MESAS332', 'MESAS347W', 'MESAS348W', 'MESAS378W', 'MUS204'], 'IC': ['CHN101', 'CHN102', 'CHN103', 'CHN201', 'CHN202', 'CHN203', 'CHN301', 'CHN302', 'CHN303W', 'CHN351', 'CHN401W', 'CHN402W', 'CHN403W', 'HNDI101', 'HNDI102', 'HNDI201', 'HNDI202', 'HNDI301W', 'PORT101', 'PORT102', 'PORT110', 'PORT201', 'PORT202', 'PORT212', 'PORT302W', 'PORT303W', 'ITAL101', 'ITAL102', 'ITAL110', 'ITAL201', 'ITAL202', 'ITAL301W', 'ITAL302W', 'ITAL470W', 'JPN101', 'JPN102', 'JPN201', 'JPN202', 'JPN301', 'JPN302', 'JPN401', 'JPN402', 'JS435', 'KRN101', 'KRN102', 'KRN201', 'KRN202', 'KRN301', 'KRN302', 'KRN303', 'KRN401', 'KRN402', 'KRN403', 'LAT101', 'LAT102', 'LAT201', 'LAT202', 'LAT311', 'LAT370', 'LING303', 'LING304', 'FREN101', 'FREN102', 'FREN201', 'FREN203', 'FREN310W', 'FREN313', 'FREN314', 'FREN331', 'FREN351', 'FREN460W', 'FREN488W', 'GER101', 'GER102', 'GER201', 'GER202', 'GER301', 'GER302', 'GER380', 'GER380W', 'GRK101', 'GRK102', 'GRK201', 'GRK202', 'GRK313', 'HEBR101', 'HEBR102', 'HEBR201', 'HEBR202', 'HEBR301W', 'HEBR302W', 'HEBR435', 'AFS302W', 'ARAB101', 'ARAB102', 'ARAB201', 'ARAB202', 'ARAB301', 'ARAB302', 'ARAB401W', 'ARAB402W', 'RUSS101', 'RUSS102', 'RUSS201', 'RUSS202', 'RUSS401', 'SPAN101', 'SPAN102', 'SPAN111', 'SPAN201', 'SPAN202', 'SPAN212', 'SPAN217R', 'SPAN300', 'SPAN301', 'SPAN302W', 'SPAN303', 'SPAN304', 'SPAN305', 'SPAN311', 'SPAN318', 'SPAN330', 'TBT101', 'TBT102', 'THEA363', 'PERS101', 'PERS102', 'PERS201', 'PERS202', 'PERS301', 'PERS302W'], 'CW': ['BIOL247LW', 'BIOL373W', 'BIOL495BW', 'CHEM495BW', 'CHN271W', 'CHN303W', 'CHN401W', 'CHN402W', 'CHN403W', 'CL327W', 'HIST200W', 'HIST206W', 'HIST267W', 'HIST398RW', 'HIST414W', 'HIST417W', 'HIST442W', 'HIST448W', 'HIST487RW', 'HIST488RW', 'HIST489RW', 'HIST495BW', 'HIST497W', 'HLTH381W', 'HLTH485W', 'HLTH495BW', 'IDS200W', 'IDS205W', 'IDS216W', 'IDS220RW', 'IDS285W', 'IDS385W', 'IDS495BW', 'ENG210W', 'ENG250W', 'ENG255W', 'ENG256W', 'ENG262W', 'ENG270W', 'ENG271W', 'ENG275W', 'ENG290W', 'ENG375W', 'ENG495BW', 'ENGCW397RW', 'ENGCW495BW', 'ENGRD201W', 'ENGRD220W', 'ENGRD221RW', 'ENGRD226W', 'ENGRD230W', 'ENGRD302W', 'ENGRD316W', 'ENGRD328W', 'ENGRD367W', 'ENGRD411RW', 'ENVS247LW', 'ENVS255W', 'ENVS285W', 'ENVS352W', 'ENVS373W', 'CL495BW', 'CPLT201W', 'CPLT202W', 'CPLT495BW', 'CS371W', 'CS495BW', 'DANC429W', 'DANC454W', 'EAS495BW', 'ECON310W', 'ECON410W', 'ECON411W', 'ECON496RW', 'ECON499RW', 'POLS448W', 'POLS495BW', 'POLS496RW', 'PORT285W', 'PORT303W', 'PORT485W', 'PSYC473W', 'PSYC495BW', 'QTM240W', 'QTM302W', 'QTM385W', 'QTM495BW', 'QTM496RW', 'REES375W', 'REL244W', 'REL300W', 'REL490W', 'ITAL301W', 'ITAL302W', 'ITAL470W', 'JPN232W', 'JS347W', 'JS348W', 'JS417W', 'JS448W', 'KRN227W', 'LACS270W', 'LAT495BW', 'LING212W', 'LING413W', 'LING495BW', 'MUS382W', 'NBB370W', 'NBB495BW', 'NBB497W', 'ENVS494RW', 'ENVS495BW', 'ENVS499RW', 'FILM278W', 'FILM495BW', 'FREN310W', 'FREN460W', 'FREN488W', 'GER380W', 'GRK495BW', 'HEBR301W', 'HEBR302W', 'AAS262W', 'AAS267W', 'AAS495BW', 'AFS489W', 'AMST201W', 'AMST489W', 'AMST495BW', 'ANT377W', 'ANT455W', 'ANT495BW', 'ARAB401W', 'RUSS270W', 'RUSS271W', 'RUSS365W', 'SOC355W', 'SOC457W', 'SOC495BW', 'SPAN285W', 'SPAN302W', 'SPAN413W', 'SPAN485W', 'SPAN495BW', 'THEA210W', 'THEA377W', 'THEA410W', 'THEA429W', 'WGS378W', 'WGS454W', 'WGS495BW', 'PERS302W', 'PHIL200W', 'PHIL202W', 'PHIL204W', 'PHIL220W', 'PHIL488W', 'PHIL495BW', 'PHYS444W', 'PHYS445W', 'PHYS495BW', 'MESAS200W', 'MESAS202W', 'MESAS244W', 'MESAS347W', 'MESAS348W', 'MESAS378W', 'MESAS448W', 'MUS260W'], 'XA': ['BIOL495A', 'BIOL499R', 'CBSC370B', 'CHEM495A', 'CHEM496R', 'CHEM499R', 'CHN495A', 'HIST398R', 'HIST398RW', 'HIST494R', 'HIST495A', 'HIST497', 'HIST497W', 'HLTH399R', 'HLTH495A', 'HLTH499R', 'IDS485R', 'IDS495A', 'IDS499R', 'ENG496R', 'ENVS370B', 'ENVS491', 'CL495A', 'CS495A', 'CS497R', 'DANC207R', 'DANC250', 'EAS495A', 'ECON310W', 'ECON495A', 'ECON499RW', 'POLS387R', 'POLS396R', 'POLS496RW', 'PSYC495A', 'PSYC499R', 'QTM495A', 'QTM496R', 'QTM496RW', 'REES495A', 'REES497R', 'JS495A', 'LAT495A', 'LING495A', 'LING497R', 'LING499R', 'MUS300R', 'MUS310R', 'MUS320R', 'MUS340', 'MUS347', 'MUS349R', 'MUS384', 'MUS390R', 'MUS399R', 'MUS440', 'MUS443R', 'MUS490R', 'NBB495A', 'NBB499R', 'ENVS494R', 'ENVS494RW', 'ENVS495A', 'ENVS497R', 'ENVS499R', 'ENVS499RW', 'FILM326', 'FILM399R', 'FILM495A', 'FREN497R', 'AMST499R', 'ANT377W', 'ANT495A', 'ANT495BW', 'ANT497R', 'SIRE299R', 'SOC370B', 'SOC494R', 'SOC495A', 'SOC497R', 'THEA326', 'THEA370R', 'THEA377W', 'THEA397R', 'THEA497R', 'WGS495A', 'PHIL495A', 'PHYS444W', 'PHYS445W', 'PHYS495A', 'PHYS499R', 'POLS370B', 'MATH497R', 'MATH499R', 'MESAS495A', 'MUS235', 'MUS240']}

CORE_GER_REQUIRED = ["ENGRD101", "ECS101", "HLTH100", "PE130", "MATH190"]
CS_MATH_CORE = [
    "MATH111", "MATH112", "MATH221",
    "CS170", "CS171", "CS224", "CS253", "CS255"
]

ADV_CS_WITH_PROB = [
    ("CS326", 0.9),  # lowered from 1.0 to be more realistic
    ("CS350", 0.7),
    ("CS370", 0.70),
    ("CS377", 0.70),
    ("CS334", 0.60),
    ("CS325", 0.65),
    ("CS329", 0.60),
]

MATH_ELECTIVES = [
    ("MATH211", 0.6),
    ("MATH212", 0.6),
    ("MATH250", 0.5),
    ("MATH315", 0.5),
]


TARGET_COUNTS_BY_YEAR: Dict[str, tuple[int, int]] = {
    "sophomore": (17, 22),
    "junior":    (28, 33),
    "senior":    (39, 44),
}



def get_ger_courses(year):
    probs = GER_PROBS_BY_YEAR[year]
    ger_courses = set()
    for ger_key, prob in probs.items():
        # 这次样本要不要满足这个 GER
        if random.random() >= prob:
            continue

        # 随机补一门
        ger_course = random.choice(ger_dictionary[ger_key])
        if ger_course in ger_courses:
            ger_course = random.choice(ger_dictionary[ger_key])
        
        ger_courses.add(ger_course)
        print(f"Added GER {ger_key} course: {ger_course}")

        if ger_key == "IC" or ger_key == "CW":
            if random.random() >= prob:
                continue

            # 随机补一门
            ger_course = random.choice(ger_dictionary[ger_key])
            if ger_course in ger_courses:
                ger_course = random.choice(ger_dictionary[ger_key])
            
            ger_courses.add(ger_course)
            print(f"Added GER {ger_key} course: {ger_course}")

    return ger_courses


def generate_emory_courses_for_year(
    year: str,
    incoming_test_courses: List[str],
) -> List[str]:
    """
    流程（更直观版）：
      1. 规范 incoming（MATH112Z -> MATH112）并放入课程集合
      2. 加入固定 GER 核心（ENGRD101, ECS101, HLTH100 等）
      3. 根据 GER_PROBS_BY_YEAR 决定本样本要满足哪些 GER，并补课保证覆盖
      4. 加入 CS/MATH core（按概率 0.9）
      5. 加入 advanced CS / math electives（有先修就按概率加）
      6. 根据 year 的目标 Emory 课程数量（不算 incoming），用通识/随便选修补齐或删掉非核心课
    """

    assert year in TARGET_COUNTS_BY_YEAR, f"Unknown year: {year}"

    # --- Step 1: 规范 incoming，并作为“已经上的课” ---
    normalized_incoming = [
        "MATH112" if c == "MATH112Z" else c
        for c in incoming_test_courses
    ]
    incoming_set = set(normalized_incoming)

    # 所有课程集合（incoming + Emory）
    courses: Set[str] = set(incoming_set)

    # --- Step 2: 必修 GER（ENGRD101, ECS101, HLTH100 等） ---
    courses.update(CORE_GER_REQUIRED)

    # --- Step 3: 先搞 GER 覆盖（HA/SS/NS/QR/ETHN/IC/CW/XA）---
    ger_courses = get_ger_courses(year)
    courses.update(ger_courses)

    # --- Step 4: CS/MATH core（按统一概率）---
    for c in CS_MATH_CORE:
        if random.random() < 0.90:
            courses.add(c)

    # --- Step 5: advanced CS & math electives ---
    for cs_code, prob in ADV_CS_WITH_PROB:
        if has_prereqs(cs_code, courses) and random.random() < prob:
            courses.add(cs_code)

    for math_code, prob in MATH_ELECTIVES:
        if random.random() < prob:
            courses.add(math_code)

    # --- Step 6: 统一调总数（只看 Emory 课，不包括 incoming）---

    min_target, max_target = TARGET_COUNTS_BY_YEAR[year]
    min_target += len(incoming_set)
    max_target += len(incoming_set)

    if len(courses) < min_target:
        print("Too few courses, adding more electives...")
        target = min_target + random.randint(0, 4)
        ger_keys = ["HA", "SS", "NS", "QR", "ETHN", "IC", "CW", "XA"]
        ger_pool = {c for key in ger_keys for c in ger_dictionary[key]}
        while len(courses) < target:
            if random.random() < 0.6:
                while True:
                    new_cs_course = random.choice(cs_classes)
                    if new_cs_course not in courses:
                        courses.add(new_cs_course)
                        break
            else:
                courses.add(ger_pool.pop())
    
    elif len(courses) > max_target:
        # 如果超出上限，随机删掉一些非核心课程
        print("Too many courses, removing some electives...")
        target = max_target - random.randint(0, 3)
        removable = [c for c in (courses - incoming_set) if c not in CORE_GER_REQUIRED + CS_MATH_CORE]
        while len(courses) > target and removable:
            courses.remove(removable.pop())

    return courses - incoming_set

def create_student(id, incoming_test, emory_courses):
    obj = {
        "shared_id": f"{id:06d}",
        "emory_courses": list(emory_courses),
        "incoming_test_courses": incoming_test,
        "incoming_transfer_courses": [],
        
    }
    return obj


if __name__ == "__main__":
    from synthetic_data_generation import wrapper_genrate_incoming_test_for_freshman
    from pprint import pprint

    seniors = []
    incoming_test_courses = wrapper_genrate_incoming_test_for_freshman(10, 100)
    start = 31
    for incoming in incoming_test_courses:
        emory_courses = generate_emory_courses_for_year("senior", incoming)
        student = create_student(start, incoming, emory_courses)
        seniors.append(student)
        start += 1

        print("Incoming test courses:")
        pprint(incoming)
        print("Generated Emory courses:")
        pprint(emory_courses)
        print("total courses (excluding incoming):", len(emory_courses))
        print()


    print("Generated sophomores data:")
    pprint(seniors)

    # with open("data/synthetic_juniors.json", "w") as f:
    #     import json
    #     json.dump(juniors, f, indent=4)


    # juniors = []
    # incoming_test_courses = wrapper_genrate_incoming_test_for_freshman(10, 90)
    # start = 21
    # for incoming in incoming_test_courses:
    #     emory_courses = generate_emory_courses_for_year("junior", incoming)
    #     student = create_student(start, incoming, emory_courses)
    #     juniors.append(student)
    #     start += 1

    #     print("Incoming test courses:")
    #     pprint(incoming)
    #     print("Generated Emory courses:")
    #     pprint(emory_courses)
    #     print("total courses (excluding incoming):", len(emory_courses))
    #     print()


    # print("Generated sophomores data:")
    # pprint(juniors)

    # with open("data/synthetic_juniors.json", "w") as f:
    #     import json
    #     json.dump(juniors, f, indent=4)






    