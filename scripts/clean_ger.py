import re
import json

input_path = "data/course_detailed_complete.jsonl" 
# just a copy of 
# backEnd/Scraper/spring_2026_atlanta_complete.jsonl in the main branch
# cuz I don't know github that well...
output_path = "data/unique_ger_out.txt"

# --- ger labels and their full names starts ---
# Blue GER: FS, FW, CW, HA, NS, QR, SS, IC, ETHN, XA, ECS, HLTH, PE
blue_ger_labels = {
    "FS": "First Year Seminar",
    "FW": "First Year Writing",
    "CW": "Continuing Communication & Writing",
    "HA": "Humanities & Arts",
    "NS": "Natural Science",
    "QR": "Quantitative Reasoning",
    "SS": "Social Science",
    "IC": "Intercultural Communication",
    "ETHN": "Race and Ethnicity",
    "XA": "Experience and Application",
    "ECS": "ECS 101",
    "HLTH": "HLTH 100",
    "PE": "Physical Education",
}

# Gold GER: FS, FW, WRT, MQR, SNT, SNTL, HSC, HAP, HAL, HLTH, PED, PPF, ETHN
gold_ger_labels = {
    "FS": "First-Year Seminar",  # absorbed in blue ger      
    "FW": "First-Year Writing",    # absorbed in blue ger   
    "WRT": "Continuing Writing",   
    "MQR": "Math & Quantitative Reasoning",   
    "SNT": "Science, Nature, Technology", 
    "SNTL": "Science, Nature, Technology with Lab",     
    "HSC": "History, Society, Cultures",    
    "HAP": "Humanities, Arts, Performance",  
    "HAL": "Humanities, Arts, Language", 
    "HLTH": "HLTH 100",    # absorbed in blue ger     
    "PED": "Physical Education and Dance", 
    "PPF": "Principles of Physical Fitness",
    "ETHN": "Race and Ethnicity",
}
# --- ger labels and their full names ends ---






# --- main cleaning function starts ---
# input: line["code"], ger raw string obtained by combining line["ger"]
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

# --- main cleaning function ends ---














if __name__ == "__main__":
    lines = []
    out = ""

    with open(input_path, 'r') as file:
        lines = [json.loads(line) for line in file if json.loads(line).get("ger")]

    print(f"GER lines: {len(lines)}")

    for i in range(0, len(lines)):
        line = lines[i]
        code = line["code"]
        raw = ""
        for word in line["ger"]:
            raw += word + ' '
        raw = raw.replace("Requirement Designation:", "").strip().lower()
        labels = match_ger_labels(code, raw)
        labels_str = "["
        labels_str += ", ".join(labels)
        labels_str += "]"
        out += f"{i+1:<6}{line['code']:<12}{labels_str:<20} <-- {raw}\n"
    

    with open(output_path, 'w') as f:
        f.write(out)
    

