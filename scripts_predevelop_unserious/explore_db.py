from pymongo import MongoClient
import os
from dotenv import load_dotenv
import datetime
import pprint


# --- helper functions start ---
def ensure_indexes(col):
  col.create_index([("code", 1), ("section", 1)], unique=True)

def upsert_courses(col, courses): # upsert then update indexes. lowkey make sure indexes are updated first
  existing_keys = set(
    (doc["code"], doc.get("section"))
    for doc in col.find({}, {"_id": 0, "code": 1, "section": 1})
  )

  insert_docs = []
  record = {"inserted": 0, "updated": 0}

  for c in courses:
    key = (c.get("code"), c.get("section"))

    if key in existing_keys: # update
      filter = {"code": c.get("code"), "section": c.get("section")}
      c = {k: v for k, v in c.items() if k != "_id"} # make sure not to update _id

      res = col.update_one(filter, {"$set": c})
      record["updated"] += 1
      print(f"Updated {filter}, record[updated]={record['updated']}")
    else: # insert
      insert_docs.append(c)

  if insert_docs:
    print(f"Inserting {len(insert_docs)} new documents...")
    res = col.insert_many(insert_docs, ordered=False)
    record["inserted"] = len(res.inserted_ids)
    print(f"Inserted {record['inserted']} documents.")

  ensure_indexes(col)
  return record

# --- helper functions end ---










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
  ensure_indexes(col)
  '''
  course = {
      "code": "CS170",
      "title": "Intro to Computer Science",
      "section": "1",
      "credits": 3.0,
      "typically_offered": ["fall", "spring"],
      "prerequisites": ["MATH111"],
      "ger": ["Math/QR", "STEM"],
      "instruction_method": "in-person",
      "time": "MW 10:00-11:15am",
      "professor": "Dr. Fossati",
      "location": "MSC E301"
  }

  # courses = [{
  #     "code": "CS497R",
  #     "title": "Independent Research",
  #     "section": "3",
  #     "credits": "1-4",
  #     "typically_offered": ["fall", "spring", "summer"],
  #     "prerequisites": ["CS224"],
  #     "ger": ["Experiential Learning"],
  #     "instruction_method": "independent study",
  #     "time": "Arranged",
  #     "professor": "Dr. Zhao",
  #     "location": "MSC W401"
  #   },
  #   {
  #     "code": "ENG190",
  #     "title": "First-Year Seminar: Literature & Society",
  #     "section": None,
  #     "credits": 0.5,
  #     "typically_offered": ["fall"],
  #     "prerequisites": [],
  #     "ger": ["First-Year Seminar", "Humanities", "Writing"],
  #     "instruction_method": "in-person",
  #     "time": "TTh 1:00-2:15pm",
  #     "professor": "Dr. Lee",
  #     "location": "Callaway S101"
  #   }]
  courses = [{
      "code": "CS170",
      "title": "Intro to Computer Science",
      "section": "2",
      "credits": 3.0,
      "typically_offered": ["fall", "spring"],
      "prerequisites": ["MATH111"],
      "ger": ["Math/QR", "STEM"],
      "instruction_method": "in-person",
      "time": "TTh 11:30am-12:45pm",
      "professor": "Dr. Smith",
      "location": "MSC W201"
    },
    {
      "code": "CS170",
      "title": "Intro to Computer Science",
      "section": "3",
      "credits": 3.0,
      "typically_offered": ["fall", "spring"],
      "prerequisites": ["MATH111"],
      "ger": ["Math/QR", "STEM"],
      "instruction_method": "in-person",
      "time": "MWF 2:00-2:50pm",
      "professor": "Dr. Johnson",
      "location": "MSC N105"
    }
  ]
  # col.insert_one(course)
  # print("inserted one course")
  # col.insert_many(courses)
  # print("inserted many courses")

  # 4. index
  col.create_index([("code", 1), ("section", 1)], unique=True)
'''

  # 5. query
  # print("finding all courses with code CS170")
  results = col.find({"code": "CS170"}, {"_id": 0, "code": 1, "title": 1, "section": 1, "professor": 1})
  # _id is included by default, so we set it to 0 to exclude it
  # results = col.find()
  # for r in results:
  #   pprint.pprint(r)

  profs = col.distinct("professor", {"code": "CS170"})

  # print(profs)

  '''
  find(filter, projection)
  distinct(field, filter)
  '''

  # 6. upsert
    # result = col.update_one(
    #     {"code": "CS170", "section": "1"},     # filter 条件
    #     {"$set": {"professor": "Dr. NewName"}}, # 更新内容
    #     upsert=True
    # )

  courses_to_upsert = [
    {
      "code": "CS224",
      "title": "Data Structures and Algorithms",
      "section": "1",
      "credits": 3.0,
      "typically_offered": ["fall", "spring"],
      "prerequisites": ["CS170"],
      "ger": ["STEM", "Math/QR"],
      "instruction_method": "in-person",
      "time": "MW 1:00-2:15pm",
      "professor": "Dr. Barker",
      "location": "MSC E220"
    },
    {
      "code": "MATH211",
      "title": "Multivariable Calculus",
      "section": "2",
      "credits": 4.0,
      "typically_offered": ["fall", "spring", "summer"],
      "prerequisites": ["MATH112"],
      "ger": ["Math/QR"],
      "instruction_method": "in-person",
      "time": "TTh 9:00-10:15am",
      "professor": "Dr. Chen",
      "location": "MSC N210"
    },
    {
      "code": "CS170",
      "title": "Intro to Computer Science",
      "section": "1",
      "credits": 3.0,
      "typically_offered": ["fall", "spring"],
      "prerequisites": ["MATH111"],
      "ger": ["Math/QR", "STEM"],
      "instruction_method": "in-person",
      "time": "MW 17:30-18:45pm it's a new time!",
      "professor": "Dr. Fossati but updated!",
      "location": "MSC E301"
    },
    {
      "code": "PHYS152",
      "title": "Physics II: Electricity and Magnetism",
      "section": "1",
      "credits": 4.0,
      "typically_offered": ["spring"],
      "prerequisites": ["PHYS151", "MATH111"],
      "ger": ["STEM", "Natural Science"],
      "instruction_method": "in-person",
      "time": "MWF 11:30am-12:20pm",
      "professor": "Dr. Patel",
      "location": "MSC W115"
    },
    {
      "code": "ENG205",
      "title": "Shakespeare and His Contemporaries",
      "section": "3",
      "credits": 3.0,
      "typically_offered": ["fall"],
      "prerequisites": ["ENG101"],
      "ger": ["Humanities", "Writing"],
      "instruction_method": "in-person",
      "time": "TTh 2:30-3:45pm",
      "professor": "Dr. Williams",
      "location": "Callaway S220"
    }
  ]
  # record = upsert_courses(col, courses_to_upsert)
  # print(record)