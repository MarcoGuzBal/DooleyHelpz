import json
import re

spring26_path = "data/courses_spring_2026.jsonl" 
basic_courses_path = "data/courses_basic.jsonl"
raw_req_path = "data/unique_raw_req.txt"
middle_req_path = "data/unique_middle_req.txt"



if __name__ == "__main__":
    req_sen = []
    seen = set()
    count = 0
    with open(spring26_path, 'r') as file:
        for i, line in enumerate(file):
            obj = json.loads(line)
            code = obj.get("code")
            num = (int)(re.search(r"(\d{3})", code).group(1))
            # print(code, num)
            if num >= 500: # filter grad school courses
                continue
            
            sen = obj.get("requirement_sentence")
            
            if not sen or sen in seen:
                continue

            s = f"{code:<15}: {sen.strip()}"
            req_sen.append(s)
            count += 1
            seen.add(sen)

            # if count >= 30:
            #     print("i:", i)
            #     break
    
    with open(basic_courses_path, 'r') as file:
        for i, line in enumerate(file):
            obj = json.loads(line)
            code = obj.get("code")
            num = (int)(re.search(r"(\d{3})", code).group(1))
            # print(code, num)
            if num >= 500: # filter grad school courses
                continue
            
            sen = obj.get("requirement_sentence")
            
            if not sen or sen in seen:
                continue

            s = f"{code:<15}: {sen.strip()}"
            req_sen.append(s)
            count += 1
            seen.add(sen)

            # if count >= 30:
            #     print("i:", i)
            #     break
    
    with open(raw_req_path, 'w') as f:
        for sen in req_sen:
            f.write(sen + "\n")
    
    print("Total unique raw req sentences:", count)
    