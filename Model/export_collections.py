from pymongo import MongoClient
import json, os
from dotenv import load_dotenv
from datetime import datetime

# ====== CONFIGURATION ======
load_dotenv()

# Read URI from environment first, otherwise fall back to the current placeholder.
MONGO_URI = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI") or "YOUR_MONGODB_URI_HERE"
DB_NAMES = ["DetailedCourses", "RateMyProfessors"]
COLLECTIONS = [
    ("DetailedCourses", "BasicCourses"),
    ("DetailedCourses", "DetailedCourses"),
    ("RateMyProfessors", "Professors")
]
OUT_DIR = "mongo_exports"
# ============================

os.makedirs(OUT_DIR, exist_ok=True)
if not MONGO_URI or MONGO_URI == "YOUR_MONGODB_URI_HERE":
    raise EnvironmentError("MONGO_URI or MONGODB_URI not set. Add it to your .env or environment to use this script safely.")

client = MongoClient(MONGO_URI)

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
