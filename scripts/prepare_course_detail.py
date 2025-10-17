import json
import re
from pprint import pprint

input_path = "data/course_detailed_correct_prereq.jsonl"
existing_req_path = "data/req_dict.json"
output_path = "data/tidy_course_detail.json"


def match_ger_labels(code, raw):   
    code = code.lower()
    raw = raw.replace("Requirement Designation:", "").strip().lower()
    labels = []

    # course code based matching
    if code.endswith("W"):
        labels.append("WRT")
    if code == "ecs101":
        labels.append("ECS")
    if code == "hlth100":
        labels.append("HLTH")

    # main matching
    if re.search(r"first.*year.*seminar|\bfsem\b", raw):
        labels.append("FS")

    if re.search(r"first.*year.*writing|\bfwrt\b", raw):
        labels.append("FW")

    if re.search(r"cont.*comm.*writing|\bcw\b", raw):
        labels.append("CW")
    
    if re.search(r"natural.*sciences", raw):
        labels.append("NS")
    
    if re.search(r"soc.*sciences?", raw):
        labels.append("SS")

    if re.search(r"intercult.*comm", raw):
        labels.append("IC")

    if re.search(r"exp.*application", raw):
        labels.append("XA")

    if re.search(r"ethn", raw):
        labels.append("ETHN")

    if re.search(r"health", raw):
        labels.append("HLTH")


    # gold ger incorporated. gold ger filters checked before blue ger filters
    if re.search(r"cont.*comm|\bcw\b", raw):
        labels.append("CW")
    elif re.search(r"with writing|cont.*writ", raw):
        labels.append("WRT")

    if re.search(r"history.*society.*cultures|\bhsc\b", raw):
        labels.append("HSC")
    elif re.search(r"\bhscw\b", raw):
        labels.extend(["HSC", "WRT"])

    if re.search(r"humanities.*arts.*performance|\bhap\b", raw):
        labels.append("HAP")
    elif re.search(r"\bhapw\b", raw):
        labels.extend(["HAP", "WRT"])
    elif re.search(r"humanities.*arts", raw):
        labels.append("HA")
    elif re.search(r"humanities.*arts.*language|\bhal\b", raw):
        labels.append("HAL")
    elif re.search(r"\bhalw\b", raw):
        labels.extend(["HAL", "WRT"])
    elif re.search(r"humanities.*arts", raw):
        labels.append("HA")

    if re.search(r"math.*quantit.*reasoning|\bmqr\b", raw):
        labels.append("MQR")
    elif re.search(r"\bmqrw\b", raw):
        labels.extend(["MQR", "WRT"])
    elif re.search(r"quantit.*reasoning", raw):
        labels.append("QR")

    if re.search(r"science.*nature.*technology.*lab|\bsntl\b", raw):
        labels.append("SNTL")
    elif re.search(r"\bsnlw\b", raw):
        labels.extend(["SNTL", "WRT"])
    elif re.search(r"science.*nature.*technology|\bsnt\b", raw):
        labels.append("SNT")
    elif re.search(r"\bsntw\b", raw):
        labels.extend(["SNT", "WRT"])
    
    if re.search(r"physical education and dance", raw):
        labels.append("PED")
    elif re.search(r"physical education", raw):
        labels.append("PE")
    
    if re.search(r"principles of physical fitness", raw):
        labels.append("PPF")
    
    labels = list(set(labels))  # remove duplicates
    labels.sort()

    if labels == []:
        labels = ["❌"]

    return labels

def store_json():
    with open(output_path, "w") as f:
        json.dump(items, f, indent=2)

if __name__ == "__main__":
    items = []

    with open(existing_req_path, "r") as f:
        existing_req = json.load(f)

    with open(input_path, 'r') as f:
        data = [json.loads(line) for line in f]
    
    start = 0
    for i in range(start, len(data)):
        try:
            obj = data[i]
            
            code = obj.get("code")
            num = (int)(re.search(r"(\d{3})", code).group(1))
            if num >= 500: # filter grad school courses
                print("skipped", i, code)
                continue
            
            print(i, code)
            prereq = [[]]
            labels = []

            if obj.get("ger"):
                raw = ""
                for word in obj["ger"]:
                    raw += word + ' '
                raw = raw.replace("Requirement Designation:", "").strip().lower()
                labels = match_ger_labels(code, raw)

            sen = obj.get("prerequisites_sentence")
            print("sen: ", sen)
            req = {}
            if sen:
                if sen in existing_req:
                    req = existing_req[sen]
                else:
                    k = input("unmatched req. Enter key: ")
                    req = existing_req[k]
                
            item = {
                "code": code,                        
                "title": obj.get("title"),                 
                "section": obj.get("section"),                         
                "credits": obj.get("credits"),                         
                "typically_offered": obj.get("typically_offered"),
                "requirements": req,         
                "ger": labels,                    
                "instruction_method": obj.get("instruction_method"),      
                "time": obj.get("time"),             
                "professor": obj.get("professor"),          
                "location": obj.get("location")    
            }

            pprint(item)
            items.append(item)
        
        except Exception as e:
            print("Error:", e, "Storing json...")
            store_json()
    
    print("SUCCESS!!!")
    store_json()
    

            