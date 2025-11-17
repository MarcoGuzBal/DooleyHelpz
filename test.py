from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.getenv("DB_URI")
client = MongoClient(uri, serverSelectionTimeoutMS=15000)

try:
    print(client.admin.command("ping"))
    print("✅ Connected without SRV!")
except Exception as e:
    print("❌ Error:", e)
