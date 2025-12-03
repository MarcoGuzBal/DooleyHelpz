import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Prefer MONGO_URI or MONGODB_URI from environment (no hard-coded credentials)
MONGO_URI = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
if not MONGO_URI:
    raise EnvironmentError("MONGO_URI or MONGODB_URI not found. Add it to your .env file or environment.")

client = MongoClient(MONGO_URI)
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
