import os
from flask import Flask, jsonify, request, g
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

last_incoming_courses = []
last_emory_courses = []
last_all_courses = []

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

    # Try the new separated format first
    incoming = data.get("incoming_courses")
    emory = data.get("emory_courses")

    if incoming is not None or emory is not None:
        # Default to empty lists if missing
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
