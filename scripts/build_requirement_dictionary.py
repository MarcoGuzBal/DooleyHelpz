import re
import json
from pprint import pprint
import ast

# --- config ---
# input_path = "data/course_detailed_correct_prereq.jsonl" 
raw_path = "data/unique_raw_req.txt"
cleaned_path = "data/unique_cleaned_req.txt"
existing_req_path = "data/requirement_dictionary.json"
middle_dctionary_path = "data/req_middle_dictionary.json"

with open(existing_req_path, "r") as f:
    existing_req = json.load(f)

with open(middle_dctionary_path, "r") as f:
    middle_dict = json.load(f)

with open(raw_path, "r") as f:
    raw_data = f.readlines()

with open(cleaned_path, "r") as f:
    data = f.readlines()



LOGICAL_TOKENS = ["AND", "OR", "and", "or", "(", ")"]
DEPT_RE    = re.compile(r'^[A-Z]{2,}(?:_OX)?$')
NUM_TOK_RE = re.compile(r'^\d{3}[A-Z0-9]*[sS]?\.?$')
ONE_PIECE_RE = re.compile(r'^[A-Z]{2,}(?:_OX)?\d{3}[A-Z0-9]*[sS]?\.?$')

common_cases = ["Permission of the department required", "BBA & SPECSTUBUS students allowed to enroll", "This section is reserved for students in the BBA program", 
                "BBA and SPECSTUBUS students can enroll", "SPECSTUBUS students can enroll"]

# --- helpfer functions start ---
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
        elif t in ("s", "s.", ","):
            i += 1
        else:
            return None

    return out_tokens

def merge_or_clause(ca, cb):
        seen = set()
        merged = []
        for x in ca + cb:
            if x not in seen:
                seen.add(x)
                merged.append(x)
        return merged         
    
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
    stack = []
    for t in output:
        if t not in ('AND', 'OR'):
            stack.append([[t]])
        else:
            if len(stack) < 2:
                raise ValueError("Lack of another course")
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
# --- helper functions end ---





# --- main function ---
def get_req(sen):
    note = None
    sens = sen.split(". ")
    for i in range(len(sens)):
        s = sens[i].strip()
        if s in common_cases:
            if note is None:
                note = s
            else:
                note += ". " + s
            sens[i] = ""
        else:
            sens[i] = s
    
    sen = ". ".join([s for s in sens if s])

    if sen.strip() == "":
        return get_dict(None, None, None, note)
    if sen in middle_dict:
        return middle_dict[sen]
    
    out_tokens = tokenize(sen)
    if out_tokens:
        prereq = parse_and_normalize(out_tokens)
        obj = get_dict(prereq, None, None, note)
    else:
        prereq = validate("Enter prereq (1 to force input): ")
        coreq = validate("Enter coreq (1 to force input): ")
        antireq = validate("Enter antireq (1 to force input): ")
        print("Current sentence:", sen)
        add_note = input("Enter note (f to paste sentence): ")
        
        if add_note == "f":
            add_note = sen
        
        if add_note.strip() != "":
            if note is None:
                note = add_note.strip()
            else:
                note = add_note.strip() + ". " + note

        obj = get_dict(prereq, coreq, antireq, note)
        middle_dict[sen] = obj
    
    return obj

        





# --- main ---
if __name__ == "__main__":
    try:
        start = 661
        # in case exception occurs we can resume
        
        
        for i in range(start, len(data)):
        #for i in range(start, start + 5):
            sen = data[i]
            print(i+1, sen)
            raw = raw_data[i][17:].strip()
            sen = sen[17:].strip()
            obj = get_req(sen)
            if raw not in existing_req:
                existing_req[raw] = obj
            print(obj)
            start += 1
            print("\n")
    
    except KeyboardInterrupt:
        print("Keyboard Interrupt. Saving progress...")
        

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}. Saving progress...")
    
    finally:
        with open(existing_req_path, "w") as f:
            json.dump(existing_req, f, indent=4)
        with open(middle_dctionary_path, "w") as f:
            json.dump(middle_dict, f, indent=4)
        print("new start:", start)
        print("Progress saved.")

    