from pymongo import MongoClient
import os
from dotenv import load_dotenv
import pandas as pd
import json

input_path = "data/processed_basic_courses.json"

if __name__ == "__main__":
    with open(input_path, "r") as f:
        data = json.load(f)
    
    load_dotenv()
    uri = os.getenv("DB_URI")
    client = MongoClient(uri) #cluster
    db = client["BasicCourses"] # database
    col = db["BasicCourses"] #collection
    print("connected to the BasicCourses collection")

    db.drop_collection("BasicCourses")
    print("dropped existing BasicCourses collection")

    db.create_collection("BasicCourses")
    print("created BasicCourses collection")
    col.insert_many(data)
    print("Sucessfully inserted basic courses")
    
    col.create_index([("code", 1)], unique=True)
    print("created index")



   