from pymongo import MongoClient

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)   
db = client["DetailedCourses"]
col = db["DetailedCourses"]

print("Succesfully connected to Collection.")

results = col.find({"code": "CHEM202L", "time": { "$regex": "W", "$options": "i" }}, {"_id": 0, "code": 1, "title": 1, "section": 1, "requirements": 1})
for doc in results:
    print(doc)