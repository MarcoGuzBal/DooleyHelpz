from pymongo import MongoClient
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "dooleyhelpz"

c = MongoClient(MONGO_URI)
db = c[DB_NAME]

db.catalog.delete_many({})

db.catalog.insert_many([
    {"code": "CS 170", "title": "Intro to CS", "prereqs": [], "exclusions": []},
    {"code": "CS 171", "title": "Data Structures", "prereqs": [["CS 170"]], "exclusions": []},
    {"code": "CS 253", "title": "Systems", "prereqs": [["CS 171"]], "exclusions": []},
    {"code": "MATH 111", "title": "Calc I", "prereqs": [], "exclusions": []},
    {"code": "CS 255", "title": "Algorithms",
     "prereqs": [["CS 171"], ["MATH 111", "MATH 112"]],
     "exclusions": []}
])

print("Seeded", db.catalog.count_documents({}), "courses")
