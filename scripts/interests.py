from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pprint import pprint

out_path = "data/cs_courses.txt"

load_dotenv()
uri = os.getenv("DB_URI")
client = MongoClient(uri)
db = client["DetailedCourses"] # database
col = db["DetailedCourses"] #collection

results = col.find({"code": {"$regex": "^CS"}})

# with open(out_path, 'w') as file:
#     for r in results:
#         file.write(f"{r['code']:<10} {r['section']: <5} {r['title']}\n")


AI_ML = [
    "CS211-1",   # Introduction to Artificial Intelligence
    "CS312-1",   # Computing, AI, Ethics, and Soc
    "CS323-1",   # Machine Learning Applications
    "CS325-1",   # Artificial Intelligence
    "CS329-1",   # Computational Linguistics
    "CS334-1",   # Machine Learning
    "CS334-2",   # Machine Learning
    "CS443-1",   # Text Processing with Neural Networks
    "CS470-1",   # Data Mining
    "CS485-1",   # Deep Learning on Graphs
    "CS485-3",   # AI and Simulations
]

Software_Engineering = [
    "CS350-1",   # Systems Programming
    "CS350-2",   # Systems Programming
    "CS370-1",   # Computer Science Practicum
    "CS370-2",   # Computer Science Practicum
    "CS377-1",   # Database Systems
    "CS377-2",   # Database Systems
    "CS385-1",   # Enabling User Interaction
    "CS452-1",   # Operating Systems
]

Robotics = [
    # Lowkey no classes about robotics
]

Data_Science = [
    "CS323-1",   # Machine Learning Applications
    "CS329-1",   # Computational Linguistics
    "CS334-1",   # Machine Learning
    "CS334-2",   # Machine Learning
    "CS377-1",   # Database Systems
    "CS377-2",   # Database Systems
    "CS441-1",   # Information Visualization
    "CS443-1",   # Text Processing with Neural Networks
    "CS470-1",   # Data Mining
    "CS485-1",   # Deep Learning on Graphs
]
