import sys
import os
from typing import Dict, Any, List
from bson import ObjectId

# Add current directory to path to import modules
sys.path.append(os.path.dirname(__file__))

from integrated_recommendation_engine import IntegratedRecommendationEngine

# Mock Data based on User Input
PREFERENCES_DATA = [
    {
        "_id": ObjectId("691bd659cf9b4173b5906017"),
        "degreeType": "BA",
        "year": "Junior",
        "semester": "Spring",
        "preferredCredits": 15,
        "interests": ["Software Engineering"],
        "timeUnavailable": [{"day": "Friday", "start": "15:00", "end": "16:00"}],
        "timePreference": ["08:00", "18:00"],
        "shared_id": 553897
    },
    {
        "_id": ObjectId("691bd6a8cf9b4173b5906019"),
        "degreeType": "BA",
        "year": "Sophomore",
        "semester": "Spring",
        "preferredCredits": 18,
        "interests": ["Software Engineering"],
        "timeUnavailable": [],
        "timePreference": ["08:00", "22:00"],
        "shared_id": 682755
    },
    {
        "_id": ObjectId("691bd6accf9b4173b590601a"),
        "degreeType": "BA",
        "year": "Sophomore",
        "semester": "Spring",
        "preferredCredits": 18,
        "interests": ["Software Engineering"],
        "timeUnavailable": [],
        "timePreference": ["08:00", "22:00"],
        "shared_id": 682755
    },
    {
        "_id": ObjectId("691cec1da362589a2cb8e9c8"),
        "degreeType": "BS",
        "year": "Sophomore",
        "semester": "Spring",
        "preferredCredits": 16,
        "interests": ["AI/ML", "Software Engineering"],
        "timeUnavailable": [
            {"day": "Tuesday", "start": "14:30", "end": "19:00"},
            {"day": "Thursday", "start": "14:30", "end": "19:00"}
        ],
        "timePreference": ["08:30", "17:30"],
        "shared_id": 475327
    }
]

COURSES_DATA = [
    {
        "_id": ObjectId("691bd609cf9b4173b5906015"),
        "incoming_transfer_courses": ["CHEM151", "CHEM150", "CHEM150L", "MATH271", "MATH111", "ENGRD101"],
        "incoming_test_courses": ["PSYC111", "QTM999XFR", "HIST999XFR"],
        "emory_courses": ["CS170", "ECON101", "ECS101", "HLTH100", "PE173", "PORT190", "SPAN318", "BUS290", "BUS350", "CS171", "ECON112", "MATH112", "SPAN302W", "ACT200", "BUS300", "BUS365", "BUS380", "BUS381", "BUS390A", "BUS390B", "CS253", "MATH221", "BUS383", "BUS390C", "BUS390F", "CS224", "CS255", "FIN320", "ISOM352", "LACS102", "CS326", "CS370", "CS377", "FIN323", "ISOM355", "MKT340"],
        "shared_id": 553897
    },
    {
        "_id": ObjectId("691bd656cf9b4173b5906016"),
        "incoming_transfer_courses": ["MATH220", "MATH221", "SCI143", "CS171", "MATH151", "MATH111", "MATH152", "MATH112", "POLS285"],
        "incoming_test_courses": [],
        "emory_courses": ["CS170", "ECON101", "ECS101", "HLTH100", "PE130", "SOC190", "CS224", "CS253", "CS255", "ENGRD101", "HLTH200", "REL250", "AAS285", "CS326", "CS370", "CS377", "RUSS101"],
        "shared_id": 682755
    },
    {
        "_id": ObjectId("691bd66ccf9b4173b5906018"),
        "incoming_transfer_courses": ["MATH220", "MATH221", "SCI143", "CS171", "MATH151", "MATH111", "MATH152", "MATH112", "POLS285"],
        "incoming_test_courses": [],
        "emory_courses": ["CS170", "ECON101", "ECS101", "HLTH100", "PE130", "SOC190", "CS224", "CS253", "CS255", "ENGRD101", "HLTH200", "REL250", "AAS285", "CS326", "CS370", "CS377", "RUSS101"],
        "shared_id": 682755
    },
    {
        "_id": ObjectId("691ceb7aa362589a2cb8e9c7"),
        "incoming_transfer_courses": [],
        "incoming_test_courses": ["MATH112Z", "CHN102", "CS170", "ECON112", "ECON101", "PHYS141", "QTM999XFR", "MATH111"],
        "emory_courses": ["CS171", "ECON215", "ECS101", "ENGRD101", "HLTH100", "MATH190", "MATH221", "CS224", "CS253", "MATH211", "PE414R", "CS211", "CS255", "CS326", "CS370", "CS497R", "MATH212"],
        "shared_id": 475327
    },
    {
        "_id": ObjectId("691d3a8e15a7c9144fcf88e4"),
        "incoming_transfer_courses": ["MATH220", "MATH221", "SCI143", "CS171", "MATH151", "MATH111", "MATH152", "MATH112", "POLS285"],
        "incoming_test_courses": [],
        "emory_courses": ["CS170", "ECON101", "ECS101", "HLTH100", "PE130", "SOC190", "CS224", "CS253", "CS255", "ENGRD101", "HLTH200", "REL250", "AAS285", "CS326", "CS370", "CS377", "RUSS101"],
        "shared_id": 682755
    },
    {
        "_id": ObjectId("691d3a9015a7c9144fcf88e5"),
        "incoming_transfer_courses": ["MATH220", "MATH221", "SCI143", "CS171", "MATH151", "MATH111", "MATH152", "MATH112", "POLS285"],
        "incoming_test_courses": [],
        "emory_courses": ["CS170", "ECON101", "ECS101", "HLTH100", "PE130", "SOC190", "CS224", "CS253", "CS255", "ENGRD101", "HLTH200", "REL250", "AAS285", "CS326", "CS370", "CS377", "RUSS101"],
        "shared_id": 682755
    }
]

# Dummy Course Catalog
ALL_COURSES = [
    {
        "code": "CS350", "title": "Systems Programming", "credits": 3,
        "meeting": {"days": ["M", "W"], "start_min": 600, "end_min": 675}, # 10:00 - 11:15
        "rmp": {"rating": 4.5},
        "prerequisites": [["CS253", "CS255"]]
    },
    {
        "code": "CS450", "title": "Systems Programming II", "credits": 3,
        "meeting": {"days": ["T", "Th"], "start_min": 840, "end_min": 915}, # 14:00 - 15:15
        "rmp": {"rating": 3.0},
        "prerequisites": [["CS350"]]
    },
    {
        "code": "CS370", "title": "Computer Science Practicum", "credits": 3,
        "meeting": {"days": ["F"], "start_min": 540, "end_min": 600},
        "rmp": {"rating": 5.0},
        "prerequisites": [["CS253"]]
    },
    {
        "code": "CS325", "title": "Artificial Intelligence", "credits": 3,
        "meeting": {"days": ["M", "W"], "start_min": 840, "end_min": 915},
        "rmp": {"rating": 4.8},
        "prerequisites": [["CS253"]]
    },
    {
        "code": "CS485", "title": "Advanced Topics", "credits": 3,
        "meeting": {"days": ["T", "Th"], "start_min": 600, "end_min": 675},
        "rmp": {"rating": 2.0},
        "prerequisites": [["CS253"]]
    }
]

class MockCollection:
    def __init__(self, data):
        self.data = data

    def find_one(self, query, sort=None):
        # Simple mock implementation of find_one with sort
        filtered = [d for d in self.data if d.get("shared_id") == query.get("shared_id")]
        
        if not filtered:
            return None
            
        if sort:
            key, direction = sort[0]
            # Sort by _id (assuming ObjectId comparison works, which it does)
            filtered.sort(key=lambda x: x[key], reverse=(direction == -1))
            
        return filtered[0] if filtered else None
    
    def find(self, query):
        return self.data

def test_user(shared_id, name):
    print(f"\n--- Testing User: {name} (Shared ID: {shared_id}) ---")
    
    course_col = MockCollection(COURSES_DATA)
    pref_col = MockCollection(PREFERENCES_DATA)
    enriched_courses_col = MockCollection(ALL_COURSES)
    
    # Manually simulate what generate_schedule_for_user does to verify the "find_one" logic
    user_courses = course_col.find_one({"shared_id": shared_id}, sort=[("_id", -1)])
    user_prefs = pref_col.find_one({"shared_id": shared_id}, sort=[("_id", -1)])
    
    print(f"Selected User Courses ID: {user_courses['_id']}")
    print(f"Selected User Prefs ID:   {user_prefs['_id']}")

    print("User Courses:")
    print(f"  Transfer: {user_courses.get('incoming_transfer_courses', [])}")
    print(f"  Test: {user_courses.get('incoming_test_courses', [])}")
    print(f"  Emory: {user_courses.get('emory_courses', [])}")
    
    # Verify against expected latest IDs
    if shared_id == 682755:
        assert str(user_courses['_id']) == "691d3a9015a7c9144fcf88e5", "Failed to select latest courses for 682755"
        assert str(user_prefs['_id']) == "691bd6accf9b4173b590601a", "Failed to select latest prefs for 682755"
        print("SUCCESS: Correctly selected latest duplicate entries.")
    
    engine = IntegratedRecommendationEngine()
    recs = engine.generate_recommendations(
        user_courses=user_courses,
        user_prefs=user_prefs,
        all_courses=ALL_COURSES,
        num_recommendations=5
    )
    
    print(f"Generated {len(recs)} recommendations:")
    for r in recs:
        print(f" - {r['code']}: Score {r['recommendation_score']:.2f} (RMP: {r.get('rmp', {}).get('rating')})")

if __name__ == "__main__":
    test_user(682755, "Duplicate User")
    test_user(553897, "Junior User")
    test_user(475327, "Sophomore User")
