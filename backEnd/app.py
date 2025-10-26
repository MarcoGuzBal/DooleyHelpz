import os
from flask import Flask, jsonify, request, g
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

last_courses = []

@app.route("/")
def home():
    return "Hello from Flask!"

@app.route("/api/userCourses", methods=["POST"])
def userCourses():
    global last_courses
    data = request.get_json(force=True)
    courses = data.get("courses", [])
    
    last_courses = courses

    print("Received courses:", courses)

    if data:
        return jsonify({
            "message": "Courses received successfully!",
            "count": len(courses),
            "courses": courses
        }), 200
    else:
        return {'error': 'Invalid JSON or empty request body'}, 400
    
@app.route("/api/userCourses", methods=["GET"])
def viewUserCourses():
    return jsonify({
        "message": "Last uploaded course list",
        "courses": last_courses
    }), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
