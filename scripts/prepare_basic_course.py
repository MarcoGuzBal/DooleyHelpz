from prepare_spring26_courses import normalize_code, normalize_typically_offered
from clean_ger import match_ger_labels
from build_requirement_dictionary import get_dict
import json
from pprint import pprint
import re

basic_path = "data/courses_basic.jsonl"
requirements_dctionary_path = "data/requirement_dictionary.json"
output_path = "data/processed_basic_courses.json"
raw_courses = []
requirements_dctionary = {}

if __name__ == "__main__":
    start = 0
    items = []
    with open(requirements_dctionary_path, "r") as f:
        requirements_dctionary = json.load(f)

    with open(basic_path, 'r') as file:
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
        

        item = {
            "code": code,                        
            "title": obj.get("title"),                 
            "type": obj.get("type"),                        
            "credits": obj.get("credits"),                         
            "typically_offered": typically_offered,
            "ger": labels,
            "requirements": requirements,                       
        }

        items.append(item)
    
    with open(output_path, "w") as f:
        json.dump(items, f, indent=4)