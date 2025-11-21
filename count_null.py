from pymongo import MongoClient

import os
from dotenv import load_dotenv
load_dotenv('backEnd/.env')
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)
col = client["DetailedCourses"]["CoursesEnriched"]

total = col.count_documents({})
null_ratings = col.count_documents({
    "$or": [
        {"rmp_primary.rating": {"$exists": False}},
        {"rmp_primary.rating": None},
    ]
})
null_profs = col.count_documents({
    "$or": [
        {"professor": {"$exists": False}},
        {"professor": None},
        {"professor": ""},
    ]
})

print(f"Total: {total}")
print(f"Null Ratings: {null_ratings} ({(null_ratings/total)*100:.2f}%)")
print(f"Null Professors: {null_profs} ({(null_profs/total)*100:.2f}%)")
