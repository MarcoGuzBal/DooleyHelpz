import os
from flask import Flask, jsonify, request, 
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "dooleyhelpz")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

last_incoming_courses = []
last_emory_courses = []
last_all_courses = []

def validate_user_schema(data):
    errors = []
    
    if "degree_type" in data and data["degree_type"] is not None:
        if not isinstance(data["degree_type"], str):
            errors.append("degree_type must be a string")
    
    if "major" not in data or data["major"] is None:
        data["major"] = []
    elif not isinstance(data["major"], list):
        errors.append("major must be an array")
    
    if "minor" not in data or data["minor"] is None:
        data["minor"] = []
    elif not isinstance(data["minor"], list):
        errors.append("minor must be an array")
    
    if "year" in data and data["year"] is not None:
        if not isinstance(data["year"], (int, str)):
            errors.append("year must be an integer or string")
    
    if "expected_grad_term" in data and data["expected_grad_term"] is not None:
        if not isinstance(data["expected_grad_term"], str):
            errors.append("expected_grad_term must be a string")
    
    if "preference_order" not in data or data["preference_order"] is None:
        data["preference_order"] = []
    elif not isinstance(data["preference_order"], list):
        errors.append("preference_order must be an array")
    
    if "interest_tags" not in data or data["interest_tags"] is None:
        data["interest_tags"] = []
    elif not isinstance(data["interest_tags"], list):
        errors.append("interest_tags must be an array")
    
    if "transcript" not in data or data["transcript"] is None:
        data["transcript"] = {
            "expected_grad_year": None,
            "courses": []
        }
    elif not isinstance(data["transcript"], dict):
        errors.append("transcript must be an object")
    else:
        transcript = data["transcript"]
        
        if "expected_grad_year" not in transcript:
            transcript["expected_grad_year"] = None
        elif transcript["expected_grad_year"] is not None:
            if not isinstance(transcript["expected_grad_year"], (int, str)):
                errors.append("transcript.expected_grad_year must be an integer or string")
        
        if "courses" not in transcript or transcript["courses"] is None:
            transcript["courses"] = []
        elif not isinstance(transcript["courses"], list):
            errors.append("transcript.courses must be an array")
    
    return data, errors

def prereqs_ok(prereqs, have):
    if not prereqs:
        return True
    for group in prereqs:
        if not any(p in have for p in group):
            return False
    return True

@app.route("/")
def home():
    return "Hello from Flask!"

@app.route("/api/userCourses", methods=["POST"])
def userCourses():
    global last_incoming_courses, last_emory_courses, last_all_courses
    if not request.is_json:
        return {"error": "Send JSON (Content-Type: application/json)."}, 400
    data = request.get_json(silent=True)
    if data is None:
        return {"error": "Bad JSON."}, 400
    incoming = data.get("incoming_courses")
    emory = data.get("emory_courses")
    if incoming is not None or emory is not None:
        if incoming is None:
            incoming = []
        if emory is None:
            emory = []
        # # Basic list checks (very simple)
        # if type(incoming) is not list:
        #     return {"error": "incoming_courses must be a list."}, 400
        # if type(emory) is not list:
        #     return {"error": "emory_courses must be a list."}, 400
        last_incoming_courses = incoming
        last_emory_courses = emory
        last_all_courses = incoming + emory
        return jsonify({
            "message": "OK",
            "counts": {
                "incoming": len(incoming),
                "emory": len(emory),
                "total": len(last_all_courses)
            },
            "incoming_courses": incoming,
            "emory_courses": emory
        }), 200
    
@app.route("/api/userCourses", methods=["GET"])
def viewUserCourses():
    return jsonify({
        "message": "Last uploaded course list",
        "all_courses": last_all_courses,
        "emory_courses": last_emory_courses,
        "incoming_courses": last_incoming_courses,
    }), 200

@app.route('/api/users/<username>', methods=['POST'])
def upsert_user(username):
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "No JSON data provided"}), 400
        
        validated_data, errors = validate_user_schema(payload)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400
        
        validated_data["username"] = username
        
        db.users.update_one(
            {"username": username},
            {"$set": validated_data},
            upsert=True
        )
        
        return '', 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<username>/eligible', methods=['GET'])
def get_eligible(username):
    try:
        user = db.users.find_one({"username": username})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        have = set(user.get("transcript", {}).get("courses", []))
        
        eligible = []
        blocked = {}
        
        for course in db.catalog.find({}):
            code = course.get("code")
            if not code or code in have:
                continue
            
            exclusions = set(course.get("exclusions") or [])
            if exclusions & have:
                blocked[code] = "excluded"
                continue
            
            if prereqs_ok(course.get("prereqs") or [], have):
                eligible.append(code)
            else:
                blocked[code] = "missing_prereqs"
        
        eligible.sort()
        
        return jsonify({
            "username": username,
            "eligible": eligible,
            "blocked": blocked
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)