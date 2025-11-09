from pymongo import MongoClient
import os
from dotenv import load_dotenv
import pandas as pd
import json

input_path = "data/processed_spring26_courses.json"

if __name__ == "__main__":
    with open(input_path, "r") as f:
        data = json.load(f)
    
    load_dotenv()
    uri = os.getenv("DB_URI")
    client = MongoClient(uri) #cluster
    db = client["DetailedCourses"] # database
    col = db["DetailedCourses"] #collection
    print("connected to the DetailedCourses collection")

    db.drop_collection("DetailedCourses")
    print("dropped existing DetailedCourses collection")

    db.create_collection("DetailedCourses")
    print("created DetailedCourses collection")
    col.insert_many(data)
    print("Sucessfully inserted detailed courses")
    
    # create index after manually deduplicate RUSS375W and ENVS285W
    # col.create_index([("code", 1), ("section", 1)], unique=True)
    # print("created index")



   