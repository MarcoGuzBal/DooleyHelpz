import json
from recommendation_engine import CourseRecommendationEngine


def create_sample_user_profile():
    return {
        'degree_type': 'BS',
        'major': 'Computer Science',
        'year': 'Junior',
        'graduation_term': {
            'season': 'Spring',
            'year': 2026
        },
        'preferred_credits': 15,
        'interests': ['Machine Learning', 'Web Development', 'Algorithms'],
        'time_unavailable': [
            {
                'day': 'Monday',
                'start_time': '8:00am',
                'end_time': '9:00am'
            },
            {
                'day': 'Wednesday',
                'start_time': '8:00am',
                'end_time': '9:00am'
            },
            {
                'day': 'Friday',
                'start_time': '1:00pm',
                'end_time': '5:00pm'
            }
        ],
        'priority_order': {
            'professor_rating': 1,
            'major_requirements': 2,
            'time_preference': 3,
            'ger_requirements': 4,
            'interests': 5
        },
        'preferred_time_of_day': 'afternoon'
    }


def create_sample_transcript():
    return [
        {'code': 'CS 170', 'term': 'Fall 2023'},
        {'code': 'CS 171', 'term': 'Spring 2024'},
        {'code': 'CS 253', 'term': 'Fall 2024'},
        {'code': 'MATH 210', 'term': 'Fall 2023'},
        {'code': 'MATH 211', 'term': 'Spring 2024'},
        {'code': 'ENG 101', 'term': 'Fall 2023'},
        {'code': 'ENG 181', 'term': 'Fall 2023'},
        {'code': 'HIST 110', 'term': 'Spring 2024'},
        {'code': 'PSYC 101', 'term': 'Fall 2024'},
        {'code': 'DANC 224R', 'term': 'Spring 2024'},
    ]


def create_sample_professor_ratings():
    return {
        'Luis Martinez': 4.5,
        'Erika Hall': 4.8,
        'Beverly Val Addo': 4.2,
        'Tara Shepard Myers': 4.6,
    }


def create_sample_major_requirements():
    return {
        'Computer Science': [
            'CS 170',
            'CS 171',
            'CS 253',
            'CS 255',
            'CS 323',
            'CS 377',
            'MATH 210',
            'MATH 211',
            'MATH 221',
        ]
    }


def display_recommendations(recommendations: list):
    print("\n" + "="*80)
    print("TOP COURSE RECOMMENDATIONS FOR SPRING 2026")
    print("="*80 + "\n")
    
    for i, course in enumerate(recommendations, 1):
        print(f"{i}. {course['code']} - {course['title']}")
        print(f"   Score: {course['recommendation_score']:.1f}/100")
        print(f"   Credits: {course['credits']}")
        
        if course.get('professor'):
            print(f"   Professor: {course['professor'].split(' Primary Instructor')[0].split('@')[0].strip()}")
        
        if course.get('schedule_location'):
            print(f"   Schedule: {course['schedule_location']}")
        
        if course.get('ger'):
            print(f"   GER: {course['ger']}")
        
        breakdown = course.get('score_breakdown', {})
        print(f"   Score Breakdown:")
        print(f"      - Professor Rating: {breakdown.get('professor_rating', 0):.2f}")
        print(f"      - Time Preference: {breakdown.get('time_preference', 0):.2f}")
        print(f"      - Major Requirements: {breakdown.get('major_requirements', 0):.2f}")
        print(f"      - GER Requirements: {breakdown.get('ger_requirements', 0):.2f}")
        print(f"      - Interests: {breakdown.get('interests', 0):.2f}")
        
        print()


def main():
    print("DooleyHelpz Course Recommendation System - Demo")
    print("Using Fibonacci Heap with Multi-Factor Heuristic\n")
    
    print("Loading Spring 2026 course catalog...")
    engine = CourseRecommendationEngine(
        course_catalog_path='spring_2026_scraped.jsonl'
    )
    print(f"Loaded {len(engine.courses)} courses\n")
    
    engine.professor_ratings = create_sample_professor_ratings()
    engine.major_requirements = create_sample_major_requirements()
    
    print("Creating sample user profile...")
    user_profile = create_sample_user_profile()
    print(f"  Degree: {user_profile['degree_type']} in {user_profile['major']}")
    print(f"  Year: {user_profile['year']}")
    print(f"  Target Credits: {user_profile['preferred_credits']}")
    print(f"  Interests: {', '.join(user_profile['interests'])}")
    
    print("\nParsing transcript...")
    transcript = create_sample_transcript()
    print(f"  Completed Courses: {len(transcript)}")
    
    print("\nGenerating recommendations using Fibonacci heap...")
    print("(This may take a moment as we score 1800+ courses)\n")
    
    recommendations = engine.generate_recommendations(
        user_profile=user_profile,
        transcript=transcript,
        num_recommendations=15
    )
    
    display_recommendations(recommendations)
    
    print("\n" + "="*80)
    print("SUGGESTED SCHEDULE")
    print("="*80 + "\n")
    
    schedule_result = engine.generate_schedule(recommendations, max_courses=5)
    
    print(f"Total Credits: {schedule_result['total_credits']}")
    print(f"\nCourses:")
    for course in schedule_result['courses']:
        print(f"  - {course['code']}: {course['title']} ({course['credits']} credits)")
    
    print(f"\nWeekly Schedule:")
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        courses_on_day = schedule_result['schedule'][day]
        if courses_on_day:
            print(f"\n  {day}:")
            for course in courses_on_day:
                print(f"    {course['time']} - {course['code']}: {course['title']}")
                print(f"              Location: {course['location']}")
    
    output_file = 'outputFib.json'
    with open(output_file, 'w') as f:
        json.dump({
            'user_profile': user_profile,
            'transcript': transcript,
            'recommendations': recommendations,
            'suggested_schedule': schedule_result
        }, f, indent=2)
    
    print(f"\n\nFull results exported to: {output_file}")


if __name__ == '__main__':
    main()
