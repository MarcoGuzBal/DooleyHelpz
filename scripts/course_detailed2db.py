from pymongo import MongoClient
import os
from dotenv import load_dotenv
import pandas as pd
import json

input_path = "data/spring_2026_course_detail.json"

if __name__ == "__main__":
    with open(input_path, "r") as f:
        data = json.load(f)
    
    load_dotenv()
    uri = os.getenv("DB_URI")
    client = MongoClient(uri) #cluster
    db = client["DetailedCourses"] # database
    col = db["DetailedCourses"] #collection
    print("connected to the DetailedCourses collection")

    # col.insert_many(data)
    # print("Sucessfully inserted detailed courses")
    # col.create_index([("code", 1), ("section", 1)], unique=True)

    # print("created index")



    pipeline = [
        {"$match": {"code": {"$ne": None}, "section": {"$ne": None}}},
        {"$group": {
            "_id": {"code": "$code", "section": "$section"},
            "ids": {"$push": "$_id"},
            "count": {"$sum": 1}
        }},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"_id.code": 1, "_id.section": 1}}
    ]

    dups = list(col.aggregate(pipeline))

    print(f"Found {len(dups)} duplicated (code, section) groups\n")

    for d in dups:
        code = d["_id"]["code"]
        section = d["_id"]["section"]
        count = d["count"]
        print(f"{code} - {section} ({count} docs)")
        print("IDs:", ", ".join(str(i) for i in d["ids"]))
        print("-" * 60)