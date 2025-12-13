# debug_cs377_prereqs.py

from pprint import pprint

from Courses_Qualified_new import (
    COL_DETAILED,
    COL_ENRICHED,
    fetch_user_doc,
)

# If these exist in your file, import them too:
try:
    from Courses_Qualified_new import (
        get_requirements_for_code,
        prereqs_satisfied_from_requirements,
        run_track_grad_for_user,
    )
except ImportError:
    get_requirements_for_code = None
    prereqs_satisfied_from_requirements = None
    run_track_grad_for_user = None

print("=== 1) DetailedCourses.DetailedCourses → CS377 ===")
doc_det = COL_DETAILED.find_one(
    {"code": "CS377"},
    {"code": 1, "title": 1, "requirements": 1, "prerequisites": 1, "ger": 1}
)
pprint(doc_det)

print("\n=== 2) DetailedCourses.CoursesEnriched → CS377 ===")
doc_enr = COL_ENRICHED.find_one(
    {"code": "CS377"},
    {"code": 1, "title": 1, "requirements": 1, "prerequisites": 1, "ger": 1}
)
pprint(doc_enr)

print("\n=== 3) Synthetic student 000005 completed_codes ===")
user_doc = fetch_user_doc("000005")

if run_track_grad_for_user is not None:
    major_must, major_elec_groups, ger_due, ger_left, completed_codes = \
        run_track_grad_for_user(user_doc)
    print("completed_codes for 000005:")
    pprint(sorted(completed_codes))
else:
    print("run_track_grad_for_user not imported; can't show completed_codes.")

if get_requirements_for_code is not None and prereqs_satisfied_from_requirements is not None:
    print("\n=== 4) requirements + prereq check for CS377 (old requirements-based logic) ===")
    req_377 = get_requirements_for_code("CS377")
    print("requirements for CS377 as fetched by get_requirements_for_code:")
    pprint(req_377)

    if run_track_grad_for_user is not None:
        ok = prereqs_satisfied_from_requirements(req_377, completed_codes)
        print(f"\nprereqs_satisfied_from_requirements for CS377 w/ 000005? {ok}")
    else:
        print("Can't run prereqs_satisfied_from_requirements because completed_codes not computed.")
else:
    print("\nget_requirements_for_code / prereqs_satisfied_from_requirements not available.")
