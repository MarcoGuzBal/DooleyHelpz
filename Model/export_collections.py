from pymongo import MongoClient
import json, os
from datetime import datetime

# ====== CONFIGURATION ======
MONGO_URI = "YOUR_MONGODB_URI_HERE"  # 👈 replace with your full URI
DB_NAMES = ["DetailedCourses", "RateMyProfessors"]
COLLECTIONS = [
    ("DetailedCourses", "BasicCourses"),
    ("DetailedCourses", "DetailedCourses"),
    ("RateMyProfessors", "Professors")
]
OUT_DIR = "mongo_exports"
# ============================

os.makedirs(OUT_DIR, exist_ok=True)
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../backEnd/.env'))
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)

for db_name, col_name in COLLECTIONS:
    db = client[db_name]
    col = db[col_name]
    try:
        docs = list(col.find({}))
        out_path = os.path.join(
            OUT_DIR,
            f"{db_name}_{col_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2, default=str)
        print(f"✅ Exported {len(docs)} docs → {out_path}")
    except Exception as e:
        print(f"⚠️ Failed to export {db_name}.{col_name}: {e}")
