# beforehand: check by hand the brackets are all matched and there is no /
import re

raw_req_path = "data/unique_raw_req.txt"
middle_req_path = "data/unique_middle_req.txt"


DEPT_RE    = re.compile(r'\b[A-Z]{2,}(?:_OX)?\b')
NUM_TOK_RE = re.compile(r'\b\d{3}[A-Z0-9]*[sS]?\.?')
ONE_PIECE_RE = re.compile(r'\b[A-Z]{2,}(?:_OX)?\d{3}[A-Z0-9]*[sS]?\.?\b')

REQ_KEYWORDS_RE = re.compile(
    rf"""
    (?:                                   
        prereq(?:uisite)?s?|          
        coreq(?:uisite)?s?|           
        co-?requisite[s]?|            
        permission(?:\s+required)?|   
        reserved|                     
        allowed|                      
        only|                         
        program\s*restriction[s]?|                      
        specstubus|                   
        \bBBA\b|                      
        ndbu\s*program|               
        cannot|                       
        can't                                        
    )
    """,
    re.IGNORECASE | re.VERBOSE
)


def keep_req(sen):
    code = sen.split(":")[0].strip()
    sen = sen[17:].strip()   
    sen = sen.replace("[", "(").replace("]", ")")

    sentences = sen.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    kept = []
    for s in sentences:
        # print(f"Processing sentence: {s}")
        if REQ_KEYWORDS_RE.search(s) or DEPT_RE.search(s) or NUM_TOK_RE.search(s) or ONE_PIECE_RE.search(s):
            kept.append(s)
            # print(f"  Keeping sentence.")
        # if REQ_KEYWORDS_RE.search(s):
        #     print(f"    Matched REQ_KEYWORDS_RE")
        # if DEPT_RE.search(s):
        #     print(f"    Matched DEPT_RE")
        # if NUM_TOK_RE.search(s):
        #     print(f"    Matched NUM_TOK_RE")
        # if ONE_PIECE_RE.search(s):
        #     print(f"    Matched ONE_PIECE_RE")


    output = ""
    if kept:
        output = '. '.join(kept).strip()
    return f"{code:<15}: {output}"


def clean_sen(sen):
    code = sen.split(":")[0].strip()
    sen = sen[17:].strip()

    sen = re.sub(r"as\s+(a\s+)?prerequisite(s)?\.?$", "", sen, flags=re.IGNORECASE)
    sen = re.sub(r"this course requires", "", sen, flags=re.IGNORECASE)
    sen = re.sub(r"s?[.,\s]*$", "", sen)
    
    sen = sen.replace("[", "(").replace("]", ")")
    sen = sen.strip()

    return f"{code:<15}: {sen}"   

    

if __name__ == "__main__":
    req_sen = []
    count = 0
    with open(raw_req_path, 'r') as file:
        for i, line in enumerate(file):
            sen = line.strip()
            sen = keep_req(sen)
            sen = clean_sen(sen)
            req_sen.append(sen)
            count += 1

            # if count >= 10:
            #     break
    
    with open(middle_req_path, 'w') as f:
        for sen in req_sen:
            f.write(sen + "\n")
    
    # print("Pattern:", REQ_KEYWORDS_RE.pattern)
    
    print("Total unique middle req sentences:", count)