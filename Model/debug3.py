


# from pymongo import MongoClient
# from dotenv import load_dotenv
# import os

# load_dotenv()

# # connect to MongoDB
# client = MongoClient(os.getenv("DB_URI"))
# db = client["BasicCourses"]
# collection = db["BasicCourses"]

# print("Connected to MongoDB")

# pe125 = {
#   "code": "PE125",
#   "title": "Play Emory",
#   "type": None,
#   "credits": "1",
#   "typically_offered": ["fall", "spring", "summer"],
#   "ger": ["PE"],
#   "requirements": {
#     "prereq": None,
#     "coreq": None,
#     "antireq": None,
#     "notes": None
#   },
#   "permission_required": False,
#   "cross_listed_with": []
# }

# result = collection.insert_one(pe125)
# print("Inserted ID:", result.inserted_id)

