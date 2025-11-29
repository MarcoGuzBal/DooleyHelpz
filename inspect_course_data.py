import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pprint

load_dotenv('backEnd/.env')
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)

db = client["DetailedCourses"]
col = db["DetailedCourses"]

print("Sample Course Data:")
sample = col.find_one({"code": "CS170"}) # Try to find a known course
if sample:
    pprint.pprint(sample)
else:
    print("CS170 not found, showing first document:")
    pprint.pprint(col.find_one())
