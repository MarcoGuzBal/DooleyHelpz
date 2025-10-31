from clean_ger import match_ger_labels
from build_requirement_dictionary import get_dict
import json
from pprint import pprint
import re

spring26_path = "data/courses_spring_2026.jsonl"
requirements_dctionary_path = "data/requirement_dictionary.json"
output_path = "data/processed_spring26_courses.json"
raw_courses = []
requirements_dctionary = {}


def normalize_code(code):
    parts = code.split()
    out = "".join(parts).upper()
    return out

def normalize_typically_offered(sen):
    sen = sen.lower()
    out = []
    if "fall" in sen:
        out.append("fall")
    if "spring" in sen:
        out.append("spring")
    if "summer" in sen:
        out.append("summer")
    return out

def get_time_location(code, sen):
    if sen is None:
        return None, None
    if " in " not in sen:
        if "-" in sen or "am" in sen or "pm" in sen:
            return sen.strip(), None
        else:
            print(code, "❌ error parsing schedule_location:", sen)
            return None, None
    
    parts = sen.split(" in ")
    time = parts[0].strip()
    location = parts[1].strip()
    return time, location

def get_professor_professor_email(code, sen):
    try:
        if sen is None:
            return None, None
        
        parts = sen.split("Primary Instructor")
        
        parts = parts[0].strip().split(" ")
        prof = ""
        email = None
        for part in parts:
            if "@" in part and "." in part:
                email = part.strip()
            else:
                prof += part.strip() + " "
        prof = prof.strip()
        return prof, email
    except Exception as e:
        print(code, "❌ error parsing professor:", sen)
        print("   ", e)
        return None, None
    

if __name__ == "__main__":
    start = 0
    items = []
    with open(requirements_dctionary_path, "r") as f:
        requirements_dctionary = json.load(f)

    with open(spring26_path, 'r') as file:
        lines = [json.loads(line) for line in file if line.strip()]
    


    for i in range(start, len(lines)):
        obj = lines[i]
        code = obj.get("code")
        
        num = (int)(re.search(r"(\d{3})", code).group(1))
        if num >= 500: # filter grad school courses
            continue
        
        code = normalize_code(code)
        typically_offered = obj.get("typically_offered")
        if typically_offered:
            typically_offered = normalize_typically_offered(typically_offered)
            # print(code, "typically_offered normalized to:", typically_offered)
        ger_sen = obj.get("ger")
        if ger_sen:
            labels = match_ger_labels(code, ger_sen)
        else:
            labels = None
        req_sen = obj.get("requirement_sentence", "").strip()
        requirements = {}
        if req_sen == "":
            requirements = get_dict(None, None, None, None)
        else:
            requirements = requirements_dctionary.get(req_sen)
        
        time, location = get_time_location(code, obj.get("schedule_location"))
        prof, email = get_professor_professor_email(code, obj.get("professor"))


        item = {
            "code": code,                        
            "title": obj.get("title"),                 
            "section": obj.get("section"),
            "type": obj.get("type"),                        
            "credits": obj.get("credits"),                         
            "typically_offered": typically_offered,
            "ger": labels,
            "requirements": requirements,                       
            "instruction_method": obj.get("instruction_method"),
            "campus": obj.get("campus"),     
            "time": time,                 
            "location": location,
            "professor": prof, 
            "professor_email": email   
        }

        items.append(item)
    
    with open(output_path, "w") as f:
        json.dump(items, f, indent=4)




