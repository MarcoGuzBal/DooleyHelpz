from pymongo import MongoClient
import os
from dotenv import load_dotenv


if __name__ == "__main__":
    # 1. load .env
    load_dotenv()
    uri = os.getenv("TEST_DB_URI")

    # 2. connect to MongoDB
    client = MongoClient(uri) #cluster
    print("created client")  

    # 3. choose database and collection
    db = client["testdb"] # database
    col = db["courses_detailed"] #collection

    # 4. insert
    course = {
        "code": "CS170",
        "title": "Intro to Computer Science",
        "section": "1",
        "credits": 3.0,
        "professor": "Dr. Smith"
    }
    col.insert_one(course)
    # to insert multiple documents, use col.insert_many(documents_list)


    # 5. query
    # print("finding all courses with code CS170")
    results = col.find({"code": "CS170"}, {"_id": 0, "code": 1, "title": 1, "section": 1, "professor": 1}) #so it only shows code, title, section, professor
    # _id is included by default, so we set it to 0 to exclude it
    
    # 6. index
    col.create_index([("code", 1), ("section", 1)], unique=True) # an example of joint index on code and section