import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import sys
from pathlib import Path

app = Flask(__name__)
CORS(app)

load_dotenv()
uri = os.getenv("MONGODB_URI")

client = MongoClient(uri)

# User data collections
users_db = client["Users"]
user_col = users_db['TestUsers']
course_col = users_db['TestCourses']
pref_col = users_db['TestPreferences']

# Course data collections
courses_db = client["DetailedCourses"]
enriched_courses_col = courses_db["CoursesEnriched"]

# Import the integrated recommendation engine
sys.path.insert(0, str(Path(__file__).parent))

try:
    from integrated_recommendation_engine import generate_schedule_for_user
    RECO_ENGINE_AVAILABLE = True
    print("Loaded integrated recommendation engine with Fibonacci heap")
except ImportError as e:
    print(f"Could not load recommendation engine: {e}")
    RECO_ENGINE_AVAILABLE = False

# Cache for last submitted data
last_userCourses = None
last_preferences = None


@app.route("/")
def home():
    return jsonify({
        "message": "DooleyHelpz Backend API",
        "version": "3.0 - Fibonacci Heap Edition",
        "recommendation_engine": "available" if RECO_ENGINE_AVAILABLE else "unavailable",
        "endpoints": {
            "user_courses": "/api/userCourses (POST, GET)",
            "preferences": "/api/preferences (POST, GET)",
            "generate_schedule": "/api/generate-schedule (POST)",
            "health": "/api/health (GET)"
        }
    })


@app.route("/api/health")
def health_check():
    try:
        users_db.command('ping')
        courses_db.command('ping')
        
        return jsonify({
            "status": "healthy",
            "mongodb": "connected",
            "recommendation_engine": "available" if RECO_ENGINE_AVAILABLE else "unavailable",
            "collections": {
                "user_courses": course_col.count_documents({}),
                "user_preferences": pref_col.count_documents({}),
                "enriched_courses": enriched_courses_col.count_documents({})
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route("/api/userCourses", methods=["POST"])
def userCourses():
    global last_userCourses
    
    if not request.is_json:
        return {"error": "Send JSON (Content-Type: application/json)."}, 400

    data = request.get_json(silent=True)
    last_userCourses = data if isinstance(data, dict) else {"value": data}

    print("Received user courses:", data)
    
    try:
        shared_id = None
        if isinstance(data, dict):
            shared_id = data.get("shared_id")

        result = course_col.insert_one(last_userCourses)
        
        return {
            "message": "Courses received successfully!",
            "received_fields": list(data.keys()) if isinstance(data, dict) else [],
            "shared_id": shared_id,
            "inserted_id": str(result.inserted_id)
        }, 200
        
    except Exception as e:
        print(f"Error saving courses: {e}")
        return {"error": "Failed to save data"}, 500


@app.route("/api/userCourses", methods=["GET"])
def viewUserCourses():
    if last_userCourses is None:
        return {"message": "No courses saved yet."}, 404
    return {"message": "Last saved courses", "userCourses": last_userCourses}, 200


@app.route("/api/preferences", methods=["POST"])
def userPreferences():
    global last_preferences
    
    if not request.is_json:
        return {"error": "Send JSON (Content-Type: application/json)."}, 400

    data = request.get_json(silent=True)
    print("Received preferences:", data)
    
    try:
        shared_id = None
        if isinstance(data, dict):
            shared_id = data.get("shared_id")

        result = pref_col.insert_one(data)
        last_preferences = data if isinstance(data, dict) else {"value": data}
        
        return {
            "message": "Preferences received successfully!",
            "received_fields": list(data.keys()) if isinstance(data, dict) else [],
            "shared_id": shared_id,
            "inserted_id": str(result.inserted_id)
        }, 200
        
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return {"error": "Failed to save data"}, 500


@app.route("/api/preferences", methods=["GET"])
def viewUserPreferences():
    if last_preferences is None:
        return {"message": "No preferences saved yet."}, 404
    return {"message": "Last saved preferences", "preferences": last_preferences}, 200


@app.route("/api/generate-schedule", methods=["POST"])
def generate_schedule():
    if not RECO_ENGINE_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Recommendation engine not available."
        }), 500
    
    try:
        data = request.get_json()
        shared_id = data.get("shared_id")
        num_recommendations = data.get("num_recommendations", 15)
        
        if not shared_id:
            return jsonify({
                "success": False,
                "error": "shared_id required"
            }), 400
        
        result = generate_schedule_for_user(
            shared_id=shared_id,
            course_col=course_col,
            pref_col=pref_col,
            enriched_courses_col=enriched_courses_col,
            num_recommendations=num_recommendations
        )
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    
    print(f"\n{'='*60}")
    print(f"Backend Server Starting")
    print(f"Fibonacci Heap Edition")
    print(f"{'='*60}")
    print(f"Server: http://localhost:{port}")
    print(f"Debug mode: {debug}")
    print(f"MongoDB: Connected")
    print(f"Recommendation Engine: {'Available' if RECO_ENGINE_AVAILABLE else 'Not Available'}")
    print(f"\n Endpoints:")
    print(f"  POST /api/userCourses       - Upload transcript data")
    print(f"  POST /api/preferences        - Set preferences")
    print(f"  POST /api/generate-schedule  - Generate recommendations")
    print(f"  GET  /api/health             - Health check")
    print(f"{'='*60}\n")
    
    app.run(host="0.0.0.0", port=port, debug=debug)