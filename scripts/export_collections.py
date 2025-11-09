from pymongo import MongoClient
import json, os
from datetime import datetime

# ====== CONFIGURATION ======
MONGO_URI = "YOUR_MONGODB_URI_HERE"  # 👈 replace with your full URI
DB_NAMES = ["DetailedCourses", "RateMyProfessors"]
COLLECTIONS = [
    ("DetailedCourses", "BasicCourses"),
    ("DetailedCourses", "DetailedCourses"),
    ("DetailedCourses", "Recommended"),
    ("RateMyProfessors", "Professors")
]
OUT_DIR = "mongo_exports"
# ============================

os.makedirs(OUT_DIR, exist_ok=True)
client = MongoClient("mongodb+srv://apere52:Melody339044@data.apz41ku.mongodb.net/")

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
