import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('backEnd/.env')
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)

db = client["DetailedCourses"]
print("Collections in DetailedCourses db:")
print(db.list_collection_names())

# Check if there is another db
print("\nDatabases:")
print(client.list_database_names())
