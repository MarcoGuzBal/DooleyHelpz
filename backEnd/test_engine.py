import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Add FibHeap to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'FibHeap'))

from integrated_recommendation_engine import IntegratedRecommendationEngine, normalize_course_code

load_dotenv()
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)
db = client["DetailedCourses"]
enriched_courses_col = db["DetailedCourses"]

def test_engine():
    print("Fetching courses...")
    all_courses = list(enriched_courses_col.find({}))
    print(f"Fetched {len(all_courses)} courses.")

    user_courses = {
        "incoming_transfer_courses": ["MATH 111"],
        "incoming_test_courses": ["CS 170"],
        "emory_courses": ["CS 171", "CS 224"]
    }

    user_prefs = {
        "degreeType": "BS",
        "year": "Sophomore",
        "interests": ["Software Engineering"],
        "timeUnavailable": [],
        "timePreference": ["08:00", "18:00"]
    }

    print("Initializing Engine...")
    engine = IntegratedRecommendationEngine()
    
    print("Generating Recommendations...")
    recs = engine.generate_recommendations(
        user_courses=user_courses,
        user_prefs=user_prefs,
        all_courses=all_courses,
        num_recommendations=5
    )
    
    print(f"Generated {len(recs)} recommendations.")
    for i, rec in enumerate(recs):
        print(f"{i+1}. {rec.get('code')} - Score: {rec.get('recommendation_score')}")

if __name__ == "__main__":
    test_engine()
