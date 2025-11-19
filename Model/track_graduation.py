from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pprint import pprint
uri = "mongodb+srv://apere52:Melody339044@data.apz41ku.mongodb.net/"
client1 = MongoClient(uri) #cluster
client2 = MongoClient(uri)
db = client1["BasicCourses"] # database
col = db["BasicCourses"] #collection
db2 = client2["DetailedCourses"] # database
col2 = db2["DetailedCourses"] #collection
print("Succesfully connected to detailed courses.")
CSBA_major_dictionary = {
    "must": ["MATH111", "MATH112", "MATH221", "CS170", "CS171", 'CS224', 'CS253',
             'CS255', 'CS326', 'CS350'],
    "elective_groups": [
        {
            "choose": 1,
            "courses": ["CS370", "CS371W"],
        },
        {
            "choose": 2,
            "courses": ["CS325", "CS329", "CS334", "CS377"],
        },
        {
            "choose": 2,
            "courses": ['CS312', 'CS325', 'CS326', 'CS329', 'CS334', 'CS350', 'CS370', 'CS371W', 'CS377', 'CS385', 'CS424', 'CS441', 'CS443', 'CS444', 'CS452', 'CS463', 'CS470', 'CS480', 'CS485', 'CS495A', 'CS495BW', 'CS497R', 'CS498R'],
        }
    ]
}
CSBS_major_requirements = {
    "must": ["MATH111", "MATH112", "MATH221", "CS170", "CS171", "CS224", "CS253", "CS255", "CS326", "CS350"],
    "elective_groups": [
        {
            "choose": 1,
            "courses": ["CS370", "CS371W"],
        },
        {
            "choose": 1,
            "courses": ["CS325", "CS329", "CS334", "CS377"],
        },
        {
            "choose": 2,
            "courses": ['CS312', 'CS325', 'CS326', 'CS329', 'CS334', 'CS350', 'CS370', 'CS371W', 'CS377', 'CS385'], # remove CS 323 since only made for AI Minor
        },
        {
            "choose": 1, # cascading matters!
            "courses": ['CS312', 'CS325', 'CS326', 'CS329', 'CS334', 'CS350', 'CS370', 'CS371W', 'CS377', 'CS385', "MATH315", "MATH346", "MATH347", "MATH351", "MATH361", "MATH362"], # remove CS 323 since only made for AI Minor
        },
        {
            "choose": 3,
            "courses": ['CS424', 'CS441', 'CS443', 'CS444', 'CS452', 'CS463', 'CS470', 'CS480', 'CS485', 'CS495A', 'CS495BW', 'CS497R', 'CS498R'],
        }
    ]
}
Blue_GER = {
    "ECS": 1,
    "HLTH": 1,    # freshman fall
    "FS": 1,
    "FW": 1,      # can be fulfilled by incoming test credits
    "PE": 1,      # end of first year
    "HA": 1,
    "NS": 1,
    "QR": 1,
    "SS": 1,      # end of second year
    "IC": 2,      # annoying: 2 classes must be the same language
                  # recommended to be taken in a row
                  # Zimo cannot use CHN as IC because it's her native language
                  # otherwise one of 2 classes can be filfilled by incoming test credits
    "ETHN": 1,    # end of third year
    "CW": 2,
    "XA": 1       # end of fourth year
}
ger_due = {
    "freshman fall": ['ECS', 'HLTH'],
    "end of first year": ['FS', 'FW', 'PE'],
    "end of second year": ['HA', 'NS', 'QR', 'SS'],
    "end of third year": ['IC', 'ETHN'],
    "end of fourth year": ['CW', 'XA']
}
incoming_courses = [
    "MATH111",
    "MATH112Z",
    "CHN102",
    "CS170",
    "ECON112",
    "ECON101",
    "PHYS141",
    "QTM999XFR"
]
emory_courses = [
    "CS171",
    "ECON215",
    "ECS101",
    "ENGRD101",
    "HLTH100",
    "MATH190",
    "MATH221",
    "CS224",
    "CS253",
    "MATH211",
    "PHYS152",
    "PE414R",
    "CS211",
    "CS255",
    "CS326",
    "CS370",
    "CS497R",
    "CS371W",
    "MATH212"
]
courses = incoming_courses + emory_courses
def getridofZ(course_code):
    if course_code.endswith('Z'):
        return course_code[:-1]
    return course_code
def get_regex(pattern):
    query = {"code": {"$regex": pattern}}
    results = col.find(query, {"_id": 0, "code": 1})
    return [r["code"] for r in results]
def track_major(courses):
    for course in courses:
        for req in list(CSBA_major_dictionary["must"]):
            if course == req:
                CSBA_major_dictionary["must"].remove(req)
                break
        else:
            for group in CSBA_major_dictionary["elective_groups"]:
                if group["choose"] == 0:
                    continue
                for req in list(group["courses"]):
                    if course == req:
                        group["courses"].remove(req)
                        group["choose"] -= 1
                        break
def ger_fulfilled(incoming_courses, emory_courses, countic):
    fw_fulfilled = False
    ic_fulfilled = False
    for course in incoming_courses:
        c = getridofZ(course)
        query = {"code": c}
        result = col.find_one(query, {"_id": 0, "ger": 1})
        result2 = col2.find_one(query, {"_id": 0, "ger": 1})
        ger_tags = None
        if result and result.get("ger"):
            ger_tags = result.get("ger")
        elif result2 and result2.get("ger"):
            ger_tags = result2.get("ger")
        if not ger_tags:
            continue
        if not fw_fulfilled and "FW" in ger_tags and Blue_GER["FW"] > 0:
            Blue_GER["FW"] -= 1
            fw_fulfilled = True
        if countic and not ic_fulfilled and "IC" in ger_tags and Blue_GER["IC"] > 0:
            Blue_GER["IC"] -= 1
            ic_fulfilled = True
        
    for course in emory_courses:
        query = {"code": course}
        result = col.find_one(query, {"_id": 0, "ger": 1})
        result2 = col2.find_one(query, {"_id": 0, "ger": 1})
        if result and result.get("ger") and result.get("ger") != []:
            for ger in result["ger"]:
                if ger in Blue_GER and Blue_GER[ger] > 0:
                    Blue_GER[ger] -= 1
        else:
            if result2 and result2.get("ger") and result2.get("ger") != []:
                for ger in result2["ger"]:
                    if ger in Blue_GER and Blue_GER[ger] > 0:
                        Blue_GER[ger] -= 1

def ger_needed_soon(year, term): ## year = Freshman, Sophomore, Junior, Senior & term = Fall, Spring
    due_ger = []
    if year == "Freshman" and term == "Fall":
        due_ger = ger_due["freshman fall"]
    elif year == "Freshman" and term == "Spring":
        due_ger = ger_due["end of first year"]
    elif year == "Sophomore" and (term == "Fall" or term == "Spring"):
        due_ger = ger_due["end of second year"]
    elif year == "Junior" and (term == "Fall" or term == "Spring"):
        due_ger = ger_due["end of third year"]
    elif year == "Senior" and (term == "Fall" or term == "Spring"):
        due_ger = ger_due["end of fourth year"]
    due_ger = [g for g in due_ger if Blue_GER[g] > 0]
    return due_ger
# main function to get major_left, ger_due, ger_left
def track_grad(incoming_courses, emory_courses, year, term, countic):
    incoming_courses = [getridofZ(course) for course in incoming_courses]
    courses = incoming_courses + emory_courses
    ger_due = []
    ger_left = []
    track_major(courses)
    major_must = [req for req in CSBA_major_dictionary["must"]]
    major_elec = []
    major_elec = [
        group for group in CSBA_major_dictionary["elective_groups"]
        if group["choose"] > 0
    ]
    # major_left = major_must + major_elec
    ger_fulfilled(incoming_courses, emory_courses, countic)
    ger_due_tags = ger_needed_soon(year, term)
    for ger, count in Blue_GER.items():
        if ger in ger_due_tags:
            ger_due.append({ger: count})
            ger_left.append({ger: count})
        elif count > 0:
            ger_left.append({ger: count})
    return major_must, major_elec, ger_due, ger_left
# print(get_regex('^CS3'))
# print(get_regex('^CS4'))
## ---------- Checks for GERs ----------##
# print("Remaining Blue GERs:")
# ger_fulfilled(courses)
# for ger, count in Blue_GER.items():
#     if count > 0:
#         print(f"  - {ger}: {count} more class(es) needed")
## ---------- Checks for Major Requirements ----------##
#print("Remaining CSBA Major Requirements:")
#track_major(courses)
#for req in CSBA_major_dictionary["must"]:
    #print(f"  - {req}")
#for req in CSBA_major_dictionary["elective_groups"]:
 #   print(f"  - Choose {req['choose']} from: {', '.join(req['courses'])}")
# print("Check GERs needed soon:")
# print(ger_needed_soon(courses, "Sophomore", "Spring"))
major_must, major_elec, ger_due, ger_left = track_grad(incoming_courses, emory_courses, "Sophomore", "Spring", True)
print("major_must:")
pprint(major_must)
print("\nmajor_elec:")
pprint(major_elec)
print("\nger_due:")
pprint(ger_due)
print("\nger_left:")
pprint(ger_left)
# print("\nblue_ger:")
# pprint(Blue_GER)
# print("\nmajor:")
# pprint(CSBA_major_dictionary)