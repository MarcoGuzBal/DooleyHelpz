import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
if not MONGO_URI:
    raise EnvironmentError("MONGO_URI or MONGODB_URI not found. Add it to your .env or environment.")

client = MongoClient(MONGO_URI)
db = client["DetailedCourses"]
col = db["DetailedCourses"]

print("Succesfully connected to Collection.")

results = col.find({"code": "CHEM202L", "time": { "$regex": "W", "$options": "i" }}, {"_id": 0, "code": 1, "title": 1, "section": 1, "requirements": 1})
for doc in results:
    print(doc)