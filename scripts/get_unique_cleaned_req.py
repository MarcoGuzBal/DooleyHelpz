# beforehand: check by hand the brackets are all matched and there is no /
import re
from scripts.build_requirement_dictionary import tokenize

middle_req_path = "data/unique_middle_req.txt"
cleaned_req_path = "data/unique_cleaned_req.txt"
common_cases = ["Permission of the department required", "BBA & SPECSTUBUS students allowed to enroll", "This section is reserved for students in the BBA program", 
                "(Permission Required Prior to Enrollment)", "(Permission Required Prior to Enrollment) Permission of the department required",
                "Program restrictions apply This section is reserved for students in the BBA program", "BBA or SPECSTUBUS students This section is reserved for students in the BBA program"]

def check_common_cases(s):
    if s in common_cases or tokenize(s):
        return s
    elif s == "Biology 142 + 142L":
        return "BIOL 142 and BIOL 142L"
    else:
        return None

def human_check(sentence, i):
    output = ""
    code = sentence.split(":")[0].strip()
    sen = sentence[17:].strip()

    if not sen:
        return sentence
    
    sentences = sen.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    print(f"\n{i+1}: Course Code: {code}")
    for s in sentences:
        s = re.sub(r"as\s+(a\s+)?prerequisite(s)?\.?$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"s?[.,\s]*$", "", s)
        s = re.sub(r'or equivalent transfer credit', '', s, flags=re.IGNORECASE)
        s = s.strip()
        if check_common_cases(s):
            output += s + ". "
            print(f"Auto-accepted: {s}")
            continue

        asked = ask(s)
        if asked:
            output += asked + ". "
    
    output = output[:-2]
    return f"{code:<15}: {output}"
    

def ask(sen):
    ans = input(f"Keep? (y/n/1): {sen}\n")
    if ans.lower() == 'y':
        return sen
    elif ans.lower() == 'n':
        return ""
    elif ans.lower() == '1':
        output = input("Manual Input: ")
        if output.strip() == "":
            print("Invalid input. Try again.")
            return ask(sen)
        return output
    else:
        print("Invalid input. Try again.")
        return ask(sen)
    
    


if __name__ == "__main__":
    req_sen = []
    start = 658

    with open(cleaned_req_path, 'r') as f:
        for i, line in enumerate(f):
            if i < start:
                req_sen.append(line.strip())
            else:
                break
    
    try: 
        with open(middle_req_path, 'r') as file:
            for i, line in enumerate(file):
                sen = line.strip()
                if i < start:
                    continue
                            
                sen = human_check(sen, i)
                req_sen.append(sen)
                start += 1

                # if start >= 10:
                #     break
    except KeyboardInterrupt:
        print("Keyboard Interrupt detected. Saving partial results...")

    except Exception as e:
        print(f"Error processing line {start}: {e}")
    
    
    finally:
        with open(cleaned_req_path, 'w') as f:
            for sen in req_sen:
                f.write(sen + "\n")
        
        print("Results saved")
        print("new start:", start)

    # print("\n\n\nSUCCESS!")
    print("\n\n\nTotal unique cleaned req sentences:", start)