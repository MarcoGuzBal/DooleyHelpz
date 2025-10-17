import re
import json
from typing import List
from pprint import pprint
import ast


input_path = "data/course_detailed_correct_prereq.jsonl" 
raw_prereq_path = "data/unique_prereq.txt"
middle_prereq_path = "data/middle_prereq.txt"
existing_req_path = "data/req_dict.json"
LOGICAL_TOKENS = ["AND", "OR", "and", "or", "(", ")"]
# SPECIAL_CASES = ["can't", "cannot", "corequisite", "co-requisite", "permission", "any", "reserved", "bba", "only", "not"]

DEPT_RE    = re.compile(r'^[A-Z]{2,}(?:_OX)?$')
NUM_TOK_RE = re.compile(r'^\d{3}[A-Z0-9]*[sS]?\.?$')
ONE_PIECE_RE = re.compile(r'^[A-Z]{2,}(?:_OX)?\d{3}[A-Z0-9]*[sS]?\.?$')

def get_dict(prereq, coreq, antireq, notes):
    obj = {
        "prereq": prereq,
        "coreq": coreq,
        "antireq": antireq,
        "notes": notes
    }
    return obj




def clean_tail(s):
    s = re.sub(r'[.,;:!?)]*$', '', s)
    s = re.sub(r'[sS]$', '', s)
    return s


def tokenize(s):
    s = re.sub(r'([()/])', r' \1 ', s)
    
    tokens = s.split()

    out_tokens = []

    i = 0
    while (i < len(tokens)):
        t = tokens[i]

        if t in LOGICAL_TOKENS:
            out_tokens.append(t.upper())
            i += 1

        elif ONE_PIECE_RE.match(t.upper()):
            course = clean_tail(t).upper()
            out_tokens.append(course)
            i += 1

        
        elif DEPT_RE.match(t.upper()) and i + 1 < len(tokens) and NUM_TOK_RE.match(tokens[i+1].upper()):
            course = clean_tail(t + tokens[i+1]).upper()
            out_tokens.append(course)
            i += 2
            
        
        elif t in ("s", "s."):
            i += 1
        
        else:
            return None

    return out_tokens
            
    
def parse_and_normalize(tokens):
    # convert to postfix
    prec = {'AND': 2, 'OR': 1} # operator precedence: AND > OR
    output = []
    ops = []
    for t in tokens:
        if t in ('AND', 'OR'):
            while ops and ops[-1] != '(' and prec[ops[-1]] >= prec[t]:
                output.append(ops.pop())
            ops.append(t)
        elif t == '(':
            ops.append(t)
        elif t == ')':
            while ops and ops[-1] != '(':
                output.append(ops.pop())
            if not ops:
                raise ValueError("unmatched brackets, lack of '('")
            ops.pop() 
        else: # course name
            output.append(t)
    while ops:
        op = ops.pop()
        if op in ('(', ')'):
            raise ValueError("unmatched brackets")
        output.append(op)

    # get cnf
    def merge_or_clause(ca: List[str], cb: List[str]) -> List[str]:
        seen = set()
        merged = []
        for x in ca + cb:
            if x not in seen:
                seen.add(x)
                merged.append(x)
        return merged

    stack = []
    for t in output:
        if t not in ('AND', 'OR'):
            stack.append([[t]])
        else:
            if len(stack) < 2:
                raise ValueError("表达式错误：操作数不足")
            b = stack.pop()
            a = stack.pop()
            if t == 'AND':
                stack.append(a + b)
            else:  # OR
                # distributive law!
                res = []
                for ca in a:
                    for cb in b:
                        res.append(merge_or_clause(ca, cb))
                stack.append(res)

    if len(stack) != 1:
        raise ValueError("Error in expression")
    return stack[0]

def validate(prompt):
    while True:
        prompt += " (1 to force input): "
        sen = input(prompt)
        if sen == "":
            return None
        elif sen == "1":
            s = input("    - Enter forced list: ")
            try:
                l = ast.literal_eval(s)
                return l
            except:
                return validate(prompt)

        tokens = tokenize(sen)
        if tokens:
            req = parse_and_normalize(tokens)
            return req


def get_req(sen):
    out_tokens = tokenize(sen)
    if out_tokens:
        prereq = parse_and_normalize(out_tokens)
        obj = get_dict(prereq, None, None, None)
    else:
        prereq = validate("Enter prereq")
        coreq = validate("Enter coreq")
        antireq = validate("Enter antireq")
        note = input("Enter note (f to paste sentence): ")
        if note == "":
            note = None
        elif note == "f":
            note = sen.strip()

        obj = get_dict(prereq, coreq, antireq, note)
    
    return obj

        


if __name__ == "__main__":
    try:
        start = 209
        with open(existing_req_path, "r") as f:
            existing_req = json.load(f)

        with open(raw_prereq_path, "r") as f:
            raw_data = f.readlines()
        
        with open(middle_prereq_path, "r") as f:
            data = f.readlines()

        for i in range(start, len(data)):
            sen = data[i]
            print(i+1, sen)
            raw = raw_data[i].strip()
            sen = sen.split(":")[-1]
            obj = get_req(sen)
            if raw not in existing_req:
                existing_req[raw] = obj
            print(obj)
            print("\n")
    
        with open(existing_req_path, "w") as f:
            json.dump(existing_req, f, indent=4)
    
    except KeyboardInterrupt:
        print("Keyboard Interrupt. Saving progress...")
        with open(existing_req_path, "w") as f:
            json.dump(existing_req, f, indent=4)

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}. Saving progress...")
        with open(existing_req_path, "w") as f:
            json.dump(existing_req, f, indent=4)
    

    # test case 2
    # tests = ["(BIOL 142 and BIOL 142L) or BIOL_OX 142WE", 
    #          "(BIOL 142 or BIOL_OX 142) and BIOL 142Ls.", "(CS 170 or CS_OX 170) and (MATH 111 or MATH_OX 111)s.",
    #          " MATH_OX 117 or MATH 207 or MATH_OX 207 or MATH 362 or ECON 220 or ECON_OX 220 or QTM 100 or QTM_OX 100 or QTM 110 or QTM_OX 110 or SOC 275 or QTM 999XFR or QTM_OX ELEC as prereq. SPECSTUBUS stud.can enroll. Students enrolled or who took ISOM 350 can't take BUS 350.This section is reserved for students in the Emory College Liberal Arts and Sciences program.",
    #          "MKT 340 or SPECSTUBUS studentsThis section is reserved for students in the BBA program."]
    # for t in tests:
    #     print(t)
    #     pprint(get_req(t))
    #     print()
    