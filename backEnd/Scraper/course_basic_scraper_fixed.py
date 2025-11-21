import re, json, sys, argparse, threading, math, time
from playwright.sync_api import sync_playwright, Route, Request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TERMS = [
    "Spring 2026", "Fall 2025", "Summer 2025", "Spring 2025",
    "Fall 2024", "Summer 2024", "Spring 2024",
    "Fall 2023", "Summer 2023", "Spring 2023",
]


def norm(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '')).strip()

def block_after_heading(page, heading: str) -> str:
    try:
        h = page.locator(f"h3:has-text('{heading}'), h2:has-text('{heading}')").first
        sec = h.locator("xpath=following-sibling::*[1]")
        return norm(sec.inner_text())
    except:
        return ""

def field_value(page, label: str) -> str:
    try:
        panel = page.locator("[class*='detail']").first
        lines = [l.strip() for l in panel.inner_text().split("\n")]
        for i, line in enumerate(lines):
            if re.match(fr'^{re.escape(label)}\s*:?', line, re.I):
                val = norm(re.sub(fr'^{re.escape(label)}\s*:?', '', line, flags=re.I))
                if val:
                    return val
                if i + 1 < len(lines) and len(lines[i+1]) < 200:
                    return norm(lines[i+1])
        return ""
    except:
        return ""

def get_code_and_title(page):
    panel = page.locator("[class*='detail']").first
    text = panel.inner_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    lines = [l for l in lines if not re.search(r'Section\s+[A-Z]?\d+[A-Z]?,\s*Class\s+Nbr', l, re.I)]
    
    code_rows = [i for i, l in enumerate(lines)
                 if re.match(r'^[A-Z]{2,10}(?:_OX)?\s+\d{3}[A-Z]?$', l)]
    code, title = "", ""
    if len(code_rows) >= 2:
        i = code_rows[1]
        code = lines[i]
        title = lines[i+1] if i+1 < len(lines) else ""
    elif len(code_rows) == 1:
        i = code_rows[0]
        code = lines[i]
        title = lines[i+1] if i+1 < len(lines) else ""
    
    return code, title


def scrape_course_basic(page, course_code: str, term: str):
   
    try:
        page.goto("https://atlas.emory.edu/", timeout=10000)
        page.get_by_label("Keyword").fill(course_code)
        page.select_option("select#crit-srcdb", term)
        page.get_by_role("button", name="SEARCH").click()
        page.wait_for_selector("div.panel__info-bar", timeout=6000)

        link = page.locator("div.result.result--group-start a.result__link").first
        if link.count() == 0:
            return None
            
        link.click(timeout=3000)
        time.sleep(0.8)  # Let page load

        code_txt, title = get_code_and_title(page)
        credits = field_value(page, "Credit Hours")
        ger = field_value(page, "Requirement Designation") or field_value(page, "General Education Requirement") or ""
        typ_off = field_value(page, "Typically Offered") or ""

        reg = block_after_heading(page, "Registration Restrictions")
        notes = block_after_heading(page, "Class Notes")
        requirement_sentence = norm(" ".join([x for x in (reg, notes) if x]))

        return {
            "code": code_txt,
            "title": title,
            "credits": credits,
            "typically_offered": typ_off,
            "ger": ger,
            "requirement_sentence": requirement_sentence,
        }

    except Exception:
        return None


def process_batch(courses_batch, terms, batch_id, total, stats, stats_lock):
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=10)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(5000)

        def _route(route: Route, request: Request):
            if request.resource_type in ("image", "font", "media"):
                return route.abort()
            return route.continue_()
        page.route("**/*", _route)

        def handle_popup(popup):
            if popup != page:
                try:
                    popup.close()
                except:
                    pass
        context.on("page", handle_popup)

        for course_code in courses_batch:

            found = False
            for term in terms:
                try:
                    result = scrape_course_basic(page, course_code, term)
                    if result:
                        results.append(result)
                        found = True
                        break  
                except Exception:
                    continue  

            with stats_lock:
                stats["completed"] += 1
                if stats["completed"] % 10 == 0 or stats["completed"] == total:
                    print(f"Progress: {stats['completed']}/{total}")

        try:
            page.close()
            context.close()
            browser.close()
        except:
            pass

    return results


def normalize_code(raw: str) -> str:
    if not raw:
        return ""
    m = re.search(r'\b([A-Za-z]{2,10})(?:_?(OX))?\s*([0-9]{3}[A-Za-z]{0,3})\b', raw)
    if not m:
        return re.sub(r'([A-Za-z])([0-9])', r'\1 \2', raw).upper().strip()
    subj, ox, num = m.group(1), m.group(2), m.group(3)
    return f"{subj.upper()}{'_OX' if ox else ''} {num.upper()}"

def get_course_number(code: str) -> int:
    m = re.search(r'(\d{3})', code)
    return int(m.group(1)) if m else 0


def run(input_file, output_file, workers, test_limit):
    print("=" * 60)
    print("BASIC COURSE INFO SCRAPER")
    print("Searches multiple semesters until course found")
    print("Output: code, title, credits, typically_offered, ger, requirement_sentence")
    print("=" * 60)

    courses = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    obj = json.loads(line)
                    code = normalize_code(obj.get("code", ""))
                except:
                    code = normalize_code(line.strip())
                
                # Filter: only courses with numbers < 500
                if get_course_number(code) < 500:
                    courses.append(code)

    courses = list(dict.fromkeys(courses))

    if test_limit:
        courses = courses[:test_limit]
        print(f"TEST MODE: Limited to {len(courses)} courses")

    n = len(courses)
    print(f"Processing {n} unique courses (numbers < 500)")
    print(f"Searching terms: {', '.join(TERMS)}")

    if n == 0:
        print("No courses to process!")
        return

    workers = max(1, min(int(workers), n))
    batch_size = n // workers
    remainder = n % workers

    batches = []
    start_idx = 0
    for i in range(workers):
        size = batch_size + (1 if i < remainder else 0)
        batches.append(courses[start_idx:start_idx + size])
        start_idx += size

    print(f"Using {workers} workers with batch sizes: {[len(b) for b in batches]}")

    stats_lock = threading.Lock()
    stats = {"completed": 0}
    all_results = []

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = []
        for batch_id, batch in enumerate(batches):
            futures.append(ex.submit(process_batch, batch, TERMS, batch_id, n, stats, stats_lock))
        
        for fut in as_completed(futures):
            try:
                batch_results = fut.result()
                all_results.extend(batch_results)
            except Exception as e:
                print(f"Worker error: {e}")

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w", encoding="utf-8") as f:
        for result in all_results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"\nCompleted! Saved {len(all_results)} course records to: {out_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="unique_course_codes.jsonl")
    ap.add_argument("--output", default="basic_coursess.jsonl")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    
    run(args.input, args.output, args.workers, test_limit=50 if args.test else None)