import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import sys
from pathlib import Path
import re

app = Flask(__name__)
# CORS configuration - allow all origins for API routes
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Type"],
     supports_credentials=False)

load_dotenv()
uri = os.getenv("MONGODB_URI")

client = MongoClient(uri)

# User data collections
users_db = client["Users"]
user_col = users_db['Users']
course_col = users_db['TestCourses']
pref_col = users_db['UserPreferences']
schedules_col = users_db['SavedSchedules']  # NEW: For storing saved schedules
user_schedules_col = users_db['UserSchedules']  # NEW: For storing user-generated schedules

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


# Helper function to normalize uid (already a string, just return it)
def normalize_uid(uid):
    """Ensure uid is a string."""
    return str(uid) if uid else None


# Helper function to create uid query
def get_uid_query(uid):
    """Return a query that matches uid."""
    if not uid:
        return {}
    return {"uid": uid}


# Handle CORS for all requests
@app.before_request
def handle_cors():
    """Handle CORS preflight requests and set headers."""
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.status_code = 200
    else:
        response = None
    
    # If not an OPTIONS request, return None to let the route handle it
    # The after_request will add CORS headers to all responses
    return response


@app.after_request
def after_request(response):
    """Add CORS headers to all responses."""
    # Use set instead of add to replace existing headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


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
    
    # Normalize uid (Firebase UID from client)
    if isinstance(data, dict) and "uid" in data:
        data["uid"] = normalize_uid(data["uid"])
    
    last_userCourses = data if isinstance(data, dict) else {"value": data}
    
    try:
        uid = None
        if isinstance(data, dict):
            uid = data.get("uid")

        result = course_col.insert_one(last_userCourses)
        
        return {
            "message": "Courses received successfully!",
            "received_fields": list(data.keys()) if isinstance(data, dict) else [],
            "uid": uid,
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
    
    # Normalize uid (Firebase UID from client)
    if isinstance(data, dict) and "uid" in data:
        data["uid"] = normalize_uid(data["uid"])
    
    try:
        uid = None
        if isinstance(data, dict):
            uid = data.get("uid")

        # Use update_one with upsert=True to support both insert and update
        result = pref_col.update_one(
            {"uid": uid},
            {"$set": data},
            upsert=True
        )
        last_preferences = data if isinstance(data, dict) else {"value": data}
        
        response = {
            "success": True,
            "message": "Preferences saved successfully!",
            "received_fields": list(data.keys()) if isinstance(data, dict) else [],
            "uid": uid
        }
        if result.upserted_id:
            response["upserted"] = str(result.upserted_id)
        else:
            response["modified_count"] = result.modified_count
        
        return response, 200
        
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return {"success": False, "error": "Failed to save data"}, 500


@app.route("/api/preferences", methods=["GET"])
def viewUserPreferences():
    if last_preferences is None:
        return {"message": "No preferences saved yet."}, 404
    return {"message": "Last saved preferences", "preferences": last_preferences}, 200


# Get all user data for a Firebase UID
@app.route("/api/user-data/<uid>", methods=["GET", "OPTIONS"])
def get_user_data(uid):
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        return response
    
    try:
        uid = normalize_uid(uid)
        uid_query = get_uid_query(uid)
        
        # Get latest courses
        user_courses = course_col.find_one(
            uid_query,
            sort=[("_id", -1)]
        )
        
        # Get latest preferences
        user_prefs = pref_col.find_one(
            uid_query,
            sort=[("_id", -1)]
        )
        
        # Get saved schedules from UserSchedules collection (new format with multiple schedules)
        saved_schedule = user_schedules_col.find_one(
            uid_query,
            sort=[("_id", -1)]
        )
        
        # Fallback to old SavedSchedules collection if not found
        if not saved_schedule:
            saved_schedule = schedules_col.find_one(
                uid_query,
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


# Save a selected schedule
@app.route("/api/save-schedule", methods=["POST"])
def save_schedule():
    try:
        data = request.get_json()
        uid = data.get("uid")
        schedules = data.get("schedules")
        selected_index = data.get("selected_index", 0)
        
        if not uid or schedules is None:
            return jsonify({
                "success": False,
                "error": "uid and schedules required"
            }), 400
        
        # Normalize uid
        uid = normalize_uid(uid)
        uid_query = get_uid_query(uid)
        
        # Upsert - update if exists, insert if not to UserSchedules collection
        result = user_schedules_col.update_one(
            uid_query,
            {"$set": {
                "uid": uid,
                "schedules": schedules,
                "selected_index": selected_index,
                "updated_at": __import__('datetime').datetime.utcnow()
            }},
            upsert=True
        )
        
        return jsonify({
            "success": True,
            "message": "Schedules saved successfully",
            "upserted": result.upserted_id is not None,
            "schedules_count": len(schedules) if isinstance(schedules, list) else 0
        }), 200
        
    except Exception as e:
        print(f"Error saving schedule: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Get saved schedule
@app.route("/api/saved-schedule/<uid>", methods=["GET", "OPTIONS"])
def get_saved_schedule(uid):
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        return response
    
    try:
        uid = normalize_uid(uid)
        uid_query = get_uid_query(uid)
        
        # Try new UserSchedules collection first
        saved_schedule = user_schedules_col.find_one(
            uid_query,
            sort=[("_id", -1)]
        )
        
        # Fallback to old SavedSchedules
        if not saved_schedule:
            saved_schedule = schedules_col.find_one(
                uid_query,
                sort=[("_id", -1)]
            )
        
        if saved_schedule:
            saved_schedule["_id"] = str(saved_schedule["_id"])
            return jsonify({
                "success": True,
                "schedules": saved_schedule.get("schedules"),
                "selected_index": saved_schedule.get("selected_index", 0),
                # Backward compatibility
                "schedule": saved_schedule.get("schedule") or (saved_schedule.get("schedules") or [None])[0]
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


# Modify schedule (add/remove courses and regenerate)
@app.route("/api/modify-schedule", methods=["POST"])
def modify_schedule():
    if not RECO_ENGINE_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Recommendation engine not available."
        }), 500
    
    try:
        data = request.get_json()
        uid = data.get("uid")
        action = data.get("action")  # "add" or "remove"
        course_code = data.get("course_code")
        priority_rank = data.get("priority_rank")  # For add action
        current_schedule = data.get("current_schedule", [])
        
        if not uid or not action or not course_code:
            return jsonify({
                "success": False,
                "error": "uid, action, and course_code required"
            }), 400
        
        # Normalize uid and create query
        uid = normalize_uid(uid)
        uid_query = get_uid_query(uid)
        
        # Get user data
        user_courses = course_col.find_one(
            uid_query,
            sort=[("_id", -1)]
        )
        
        user_prefs = pref_col.find_one(
            uid_query,
            sort=[("_id", -1)]
        )
        
        if not user_prefs:
            return jsonify({
                "success": False,
                "error": "User preferences not found"
            }), 404
        
        # Modify preferences to include locked courses
        locked_courses = user_prefs.get("locked_courses", [])
        removed_courses = user_prefs.get("removed_courses", [])
        
        # Normalize course code
        course_code_normalized = course_code.upper().replace(" ", "")
        
        if action == "add":
            if course_code_normalized not in [c.get("code", "").upper().replace(" ", "") for c in locked_courses]:
                locked_courses.append({
                    "code": course_code_normalized,
                    "priority": priority_rank or 1
                })
            # Remove from removed list if present
            removed_courses = [c for c in removed_courses if c.upper().replace(" ", "") != course_code_normalized]
        elif action == "remove":
            if course_code_normalized not in [c.upper().replace(" ", "") for c in removed_courses]:
                removed_courses.append(course_code_normalized)
            # Remove from locked list if present
            locked_courses = [c for c in locked_courses if c.get("code", "").upper().replace(" ", "") != course_code_normalized]
        
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
            uid=uid,
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


# NEW: Search courses (for adding to schedule) - with whitespace handling
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
        
        # Normalize query - remove extra spaces and handle "CS 350" -> "CS350" pattern
        query_normalized = re.sub(r'\s+', '', query).upper()
        query_with_space = re.sub(r'([A-Z]+)\s*(\d+)', r'\1 \2', query.upper()).strip()
        
        # Search by code or title with multiple patterns
        search_filter = {
            "$or": [
                # Match normalized code (no spaces)
                {"code": {"$regex": query_normalized, "$options": "i"}},
                # Match with optional space between letters and numbers
                {"code": {"$regex": query_with_space, "$options": "i"}},
                # Match original query in title
                {"title": {"$regex": query, "$options": "i"}},
                # Match normalized in title
                {"title": {"$regex": query_normalized, "$options": "i"}}
            ]
        }
        
        courses = list(enriched_courses_col.find(
            search_filter,
            {"_id": 0, "code": 1, "title": 1, "credits": 1, "time": 1, "professor": 1, "ger": 1, "meeting": 1}
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
        uid = data.get("uid")
        num_recommendations = data.get("num_recommendations", 10)
        
        if not uid:
            return jsonify({
                "success": False,
                "error": "uid required"
            }), 400
        
        # Normalize uid
        uid = normalize_uid(uid)
        
        result = generate_schedule_for_user(
            uid=uid,
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


# Register user UID in MongoDB when they sign up
@app.route("/api/register-user", methods=["POST"])
def register_user():
    """
    Save user information to MongoDB Users collection when they register.
    Called from frontend after Firebase registration is successful.
    """
    try:
        data = request.get_json()
        uid = data.get("uid")
        
        if not uid:
            return jsonify({
                "success": False,
                "error": "uid is required"
            }), 400
        
        # Normalize uid
        uid = normalize_uid(uid)
        
        # Check if user already exists
        existing_user = user_col.find_one({"uid": uid})
        
        if existing_user:
            # User already registered, just return success
            return jsonify({
                "success": True,
                "message": "User already registered",
                "uid": uid
            }), 200
        
        # Create new user document
        user_doc = {
            "uid": uid,
            "created_at": __import__('datetime').datetime.utcnow(),
            "updated_at": __import__('datetime').datetime.utcnow()
        }
        
        result = user_col.insert_one(user_doc)
        
        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "uid": uid,
            "user_id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"Error registering user: {e}")
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