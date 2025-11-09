from pymongo import MongoClient

uri = "mongodb+srv://apere52:Melody339044@data.apz41ku.mongodb.net/"
client = MongoClient(uri)   
db = client["DetailedCourses"]
col = db["DetailedCourses"]

print("Succesfully connected to Collection.")

results = col.find({"code": "CHEM202L", "time": { "$regex": "W", "$options": "i" }}, {"_id": 0, "code": 1, "title": 1, "section": 1, "requirements": 1})
for doc in results:
    print(doc)