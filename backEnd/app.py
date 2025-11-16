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

# 2. connect to MongoDB
client = MongoClient(uri) #cluster
print("created client")  

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

    # Return a success response with the received fields
    return {
        "message": "Preferences received successfully!",
        "received_fields": list(data.keys()),  # Return the list of received fields
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
    global last_preferences
    last_preferences = data if isinstance(data, dict) else {"value": data}

    # Return a success response with the received fields
    return {
        "message": "Preferences received successfully!",
        "received_fields": list(data.keys()),  # Return the list of received fields
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
