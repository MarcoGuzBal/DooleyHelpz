from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pprint import pprint
import os
from dotenv import load_dotenv
from track_graduation import track_grad
from pprint import pprint

load_dotenv()
uri = os.getenv("DB_URI")
client = MongoClient(uri)
db = client["DetailedCourses"]
enriched = db["CoursesEnriched"]
detailed = db["DetailedCourses"]
user_db = client["Users"]
courses_col = user_db["TestCourses"]
preferences_col = user_db["TestPreferences"]

def get_raw_info(shared_id):
    print(f"""\n\n\n
    +-------+
    | {id} |
    +-------+
    """)
    user_preferences = preferences_col.find_one({"shared_id": shared_id})
    user_courses = courses_col.find_one({"shared_id": shared_id})
    if not user_courses:
        raise ValueError("id unmatched!!")
    incoming_test = user_courses["incoming_test_courses"]
    pprint(incoming_test)
    incoming_transfer = user_courses["incoming_transfer_courses"]
    pprint(incoming_transfer)
    emory_courses = user_courses["emory_courses"]
    pprint(emory_courses)

    # pprint(user_preferences)
    major = "CS" + user_preferences["degreeType"]
    year = user_preferences["year"]
    term = user_preferences["expectedGraduation"]["semester"]
    countic = True
    print(major, year, term)
    
    major_must, major_elec, ger_due, ger_left = track_grad(major, incoming_test, incoming_transfer, emory_courses, year, term, countic)
    print("major_must:")
    pprint(major_must)
    print("\nmajor_elec:")
    pprint(major_elec)
    print("\nger_due:")
    pprint(ger_due)
    print("\nger_left:")
    pprint(ger_left)

if __name__ == "__main__":
    
    print("connected to cols successfully")
    ids_cursor = courses_col.find({}, {"_id": 0, "shared_id": 1})
    ids_cursor = preferences_col.find({}, {"_id": 0, "shared_id": 1})
    ids_list = [doc["shared_id"] for doc in ids_cursor]
    ids = list(dict.fromkeys(ids_list))
    pprint(ids)
    print(f"total ids: {len(ids)}")

    # id = ids[4]
    # get_raw_info(id)
    # get_raw_info(475327)

    





