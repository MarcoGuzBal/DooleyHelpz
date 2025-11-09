from pymongo import MongoClient

client = MongoClient("mongodb+srv://apere52:Melody339044@data.apz41ku.mongodb.net/")
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
