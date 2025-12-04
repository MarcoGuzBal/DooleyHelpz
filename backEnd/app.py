import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import sys
from pathlib import Path

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

load_dotenv()
uri = os.getenv("MONGODB_URI")

client = MongoClient(uri)

# User data collections
users_db = client["Users"]
user_col = users_db['TestUsers']
course_col = users_db['TestCourses']
pref_col = users_db['TestPreferences']
schedules_col = users_db['SavedSchedules']  # NEW: For storing saved schedules

# Course data collections
courses_db = client["DetailedCourses"]
enriched_courses_col = courses_db["DetailedCourses"]

# BasicCourses for GER lookup
basic_courses_db = client["BasicCourses"]
basic_courses_col = basic_courses_db["BasicCourses"]

# RMP for professor ratings
rmp_db = client["RMP"]
rmp_col = rmp_db["RMP"]

# Import the integrated recommendation engine
sys.path.insert(0, str(Path(__file__).parent / "FibHeap"))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from integrated_recommendation_engine import generate_schedule_for_user
    RECO_ENGINE_AVAILABLE = True
    print("Loaded integrated recommendation engine with Fibonacci heap")
except ImportError as e:
    print(f"Could not load recommendation engine from FibHeap: {e}")
    try:
        from integrated_recommendation_engine import generate_schedule_for_user
        RECO_ENGINE_AVAILABLE = True
        print("Loaded integrated recommendation engine (fallback)")
    except ImportError as e2:
        print(f"Could not load recommendation engine: {e2}")
        RECO_ENGINE_AVAILABLE = False

# Cache for last submitted data
last_userCourses = None
last_preferences = None


# Helper function to normalize shared_id for consistent querying
def get_shared_id_query(shared_id):
    try:
        int_id = int(shared_id)
        return {"$or": [{"shared_id": int_id}, {"shared_id": str(int_id)}]}
    except (ValueError, TypeError):
        return {"shared_id": shared_id}


# Helper function to normalize shared_id for storage (always store as int)
def normalize_shared_id(shared_id):
    try:
        return int(shared_id)
    except (ValueError, TypeError):
        return shared_id


@app.route("/")
def home():
    return jsonify({
        "message": "DooleyHelpz Backend API",
        "version": "3.1 - Fibonacci Heap Edition",
        "recommendation_engine": "available" if RECO_ENGINE_AVAILABLE else "unavailable",
        "endpoints": {
            "user_courses": "/api/userCourses (POST, GET)",
            "preferences": "/api/preferences (POST, GET)",
            "generate_schedule": "/api/generate-schedule (POST)",
            "get_user_data": "/api/user-data/<shared_id> (GET)",
            "save_schedule": "/api/save-schedule (POST)",
            "get_saved_schedule": "/api/saved-schedule/<shared_id> (GET)",
            "modify_schedule": "/api/modify-schedule (POST)",
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
                "enriched_courses": enriched_courses_col.count_documents({}),
                "basic_courses": basic_courses_col.count_documents({}),
                "rmp": rmp_col.count_documents({})
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
    
    if isinstance(data, dict) and "shared_id" in data:
        data["shared_id"] = normalize_shared_id(data["shared_id"])
    
    last_userCourses = data if isinstance(data, dict) else {"value": data}
    
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
    
    if isinstance(data, dict) and "shared_id" in data:
        data["shared_id"] = normalize_shared_id(data["shared_id"])
    
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


@app.route("/api/user-data/<int:shared_id>", methods=["GET"])
def get_user_data(shared_id):
    try:
        # Use helper to query both int and string versions of shared_id
        shared_id_query = get_shared_id_query(shared_id)
        
        # Get latest courses
        user_courses = course_col.find_one(
            shared_id_query,
            sort=[("_id", -1)]
        )
        
        # Get latest preferences
        user_prefs = pref_col.find_one(
            shared_id_query,
            sort=[("_id", -1)]
        )
        
        # Get saved schedule if any
        saved_schedule = schedules_col.find_one(
            shared_id_query,
            sort=[("_id", -1)]
        )
        
        # Remove MongoDB _id fields for JSON serialization
        if user_courses and "_id" in user_courses:
            user_courses["_id"] = str(user_courses["_id"])
        if user_prefs and "_id" in user_prefs:
            user_prefs["_id"] = str(user_prefs["_id"])
        if saved_schedule and "_id" in saved_schedule:
            saved_schedule["_id"] = str(saved_schedule["_id"])
        
        return jsonify({
            "success": True,
            "has_courses": user_courses is not None,
            "has_preferences": user_prefs is not None,
            "has_saved_schedule": saved_schedule is not None,
            "courses": user_courses,
            "preferences": user_prefs,
            "saved_schedule": saved_schedule
        }), 200
        
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# NEW: Save a selected schedule
@app.route("/api/save-schedule", methods=["POST"])
def save_schedule():
    try:
        data = request.get_json()
        shared_id = data.get("shared_id")
        schedule = data.get("schedule")
        
        if not shared_id or not schedule:
            return jsonify({
                "success": False,
                "error": "shared_id and schedule required"
            }), 400
        
        # Normalize shared_id
        shared_id = normalize_shared_id(shared_id)
        shared_id_query = get_shared_id_query(shared_id)
        
        # Upsert - update if exists, insert if not
        result = schedules_col.update_one(
            shared_id_query,
            {"$set": {
                "shared_id": shared_id,
                "schedule": schedule,
                "updated_at": __import__('datetime').datetime.utcnow()
            }},
            upsert=True
        )
        
        return jsonify({
            "success": True,
            "message": "Schedule saved successfully",
            "upserted": result.upserted_id is not None
        }), 200
        
    except Exception as e:
        print(f"Error saving schedule: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# NEW: Get saved schedule
@app.route("/api/saved-schedule/<int:shared_id>", methods=["GET"])
def get_saved_schedule(shared_id):
    try:
        shared_id_query = get_shared_id_query(shared_id)
        
        saved_schedule = schedules_col.find_one(
            shared_id_query,
            sort=[("_id", -1)]
        )
        
        if saved_schedule:
            saved_schedule["_id"] = str(saved_schedule["_id"])
            return jsonify({
                "success": True,
                "schedule": saved_schedule.get("schedule")
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "No saved schedule found"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# NEW: Modify schedule (add/remove courses and regenerate)
@app.route("/api/modify-schedule", methods=["POST"])
def modify_schedule():
    if not RECO_ENGINE_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Recommendation engine not available."
        }), 500
    
    try:
        data = request.get_json()
        shared_id = data.get("shared_id")
        action = data.get("action")  # "add" or "remove"
        course_code = data.get("course_code")
        priority_rank = data.get("priority_rank")  # For add action
        current_schedule = data.get("current_schedule", [])
        
        if not shared_id or not action or not course_code:
            return jsonify({
                "success": False,
                "error": "shared_id, action, and course_code required"
            }), 400
        
        # Normalize shared_id and create query
        shared_id = normalize_shared_id(shared_id)
        shared_id_query = get_shared_id_query(shared_id)
        
        # Get user data
        user_courses = course_col.find_one(
            shared_id_query,
            sort=[("_id", -1)]
        )
        
        user_prefs = pref_col.find_one(
            shared_id_query,
            sort=[("_id", -1)]
        )
        
        if not user_courses or not user_prefs:
            return jsonify({
                "success": False,
                "error": "User data not found"
            }), 404
        
        # Modify preferences to include locked courses
        locked_courses = user_prefs.get("locked_courses", [])
        removed_courses = user_prefs.get("removed_courses", [])
        
        if action == "add":
            if course_code not in [c.get("code") for c in locked_courses]:
                locked_courses.append({
                    "code": course_code,
                    "priority": priority_rank or 1
                })
            # Remove from removed list if present
            removed_courses = [c for c in removed_courses if c != course_code]
        elif action == "remove":
            if course_code not in removed_courses:
                removed_courses.append(course_code)
            # Remove from locked list if present
            locked_courses = [c for c in locked_courses if c.get("code") != course_code]
        
        # Update preferences
        pref_col.update_one(
            {"_id": user_prefs["_id"]},
            {"$set": {
                "locked_courses": locked_courses,
                "removed_courses": removed_courses
            }}
        )
        
        # Regenerate schedule with modifications
        result = generate_schedule_for_user(
            shared_id=shared_id,
            course_col=course_col,
            pref_col=pref_col,
            enriched_courses_col=enriched_courses_col,
            rmp_col=rmp_col,
            basic_courses_col=basic_courses_col,
            num_recommendations=10
        )
        
        return jsonify(result), 200 if result.get("success") else 400
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# NEW: Search courses (for adding to schedule)
@app.route("/api/search-courses", methods=["GET"])
def search_courses():
    try:
        query = request.args.get("q", "").strip()
        limit = int(request.args.get("limit", 20))
        
        if not query:
            return jsonify({
                "success": True,
                "courses": []
            }), 200
        
        # Search by code or title
        search_filter = {
            "$or": [
                {"code": {"$regex": query, "$options": "i"}},
                {"title": {"$regex": query, "$options": "i"}}
            ]
        }
        
        courses = list(enriched_courses_col.find(
            search_filter,
            {"_id": 0, "code": 1, "title": 1, "credits": 1, "time": 1, "professor": 1, "ger": 1}
        ).limit(limit))
        
        return jsonify({
            "success": True,
            "courses": courses,
            "count": len(courses)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


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
        num_recommendations = data.get("num_recommendations", 10)
        
        if not shared_id:
            return jsonify({
                "success": False,
                "error": "shared_id required"
            }), 400
        
        # Normalize shared_id
        shared_id = normalize_shared_id(shared_id)
        
        result = generate_schedule_for_user(
            shared_id=shared_id,
            course_col=course_col,
            pref_col=pref_col,
            enriched_courses_col=enriched_courses_col,
            rmp_col=rmp_col,
            basic_courses_col=basic_courses_col,
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
    # Use PORT env variable (Fly.io sets this)
    port = int(os.getenv("PORT", "8080"))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    
    print(f"\n{'='*60}")
    print(f"DooleyHelpz Backend Server Starting...")
    print(f"   (Fibonacci Heap Edition)")
    print(f"{'='*60}")
    print(f"Server: http://localhost:{port}")
    print(f"Debug mode: {debug}")
    print(f"MongoDB: Connected")
    print(f"Recommendation Engine: {'Available' if RECO_ENGINE_AVAILABLE else 'Not Available'}")
    print(f"\nEndpoints:")
    print(f"  POST /api/userCourses        - Upload transcript data")
    print(f"  POST /api/preferences        - Set preferences")
    print(f"  POST /api/generate-schedule  - Generate recommendations")
    print(f"  GET  /api/user-data/<id>     - Get all user data")
    print(f"  POST /api/save-schedule      - Save selected schedule")
    print(f"  POST /api/modify-schedule    - Add/remove courses")
    print(f"  GET  /api/search-courses     - Search available courses")
    print(f"  GET  /api/health             - Health check")
    print(f"{'='*60}\n")
    
    app.run(host="0.0.0.0", port=port, debug=debug)