import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import os
from dotenv import load_dotenv

app = Flask(__name__)

CORS(app)

load_dotenv()
uri = os.getenv("MONGODB_URI")

client = MongoClient(uri) #cluster

db = client["Users"] # database
user_col = db['TestUsers']
course_col = db['TestCourses']
pref_col = db['TestPreferences']

last_userCourses = None
last_preferences = None

@app.route("/")
def home():
    return "Hello from Flask!"

@app.route("/api/userCourses", methods=["POST"])
def userCourses():
    global last_userCourses
    if not request.is_json:
        return {"error": "Send JSON (Content-Type: application/json)."}, 400

    data = request.get_json(silent=True)
    last_userCourses = data if isinstance(data, dict) else {"value": data}

    print("Received JSON data:", data)
    try:
        # attach or generate a shared_id so this submission can be linked
        shared_id = None
        if isinstance(data, dict):
            shared_id = data.get("shared_id")

        course_col.insert_one(last_userCourses)
    except Exception as e:
        print(e)
        return {"error": "Failed to save data"}, 500

    # Return a success response with the received fields
    return {
        "message": "Preferences received successfully!",
        "received_fields": list(data.keys()) if isinstance(data, dict) else [],
        "shared_id": shared_id,
    }, 200
    
@app.route("/api/userCourses", methods=["GET"])
def viewUserCourses():
    if last_userCourses is None:
        return {"message": "No preferences saved yet."}, 404
    return {"message": "Last saved preferences", "userCourses": last_userCourses}, 200

    
@app.route("/api/preferences", methods=["POST"])
def userPreferences():
    if not request.is_json:
        return {"error": "Send JSON (Content-Type: application/json)."}, 400

    data = request.get_json(silent=True)
    
    print("Received JSON data:", data)
    
    try:
        shared_id = None
        if isinstance(data, dict):
            shared_id = data.get("shared_id")

        pref_col.insert_one(data)
    except Exception as e:
        print(e)
        return {"error": "Failed to save data"}, 500
    global last_preferences
    last_preferences = data if isinstance(data, dict) else {"value": data}
    
    # Return a success response with the received fields
    return {
        "message": "Preferences received successfully!",
        "received_fields": list(data.keys()) if isinstance(data, dict) else [],
        "shared_id": shared_id,
    }, 200
    
@app.route("/api/preferences", methods=["GET"])
def viewUserPreferences():
    # GET should return the last saved preferences (POST stores them)
    if last_preferences is None:
        return {"message": "No preferences saved yet."}, 404
    return {"message": "Last saved preferences", "preferences": last_preferences}, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
