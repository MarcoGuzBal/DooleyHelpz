import re, json, sys, argparse, threading, math, time
from playwright.sync_api import sync_playwright, Route, Request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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

def parse_all_sections_div(text: str):
    text = (text or "").strip()
    if not text:
        return []
    text = re.sub(r'^Class Nbr\s+Section #?\s+Type\s+Campus\s+Meets\s+Instructor\s+Status\s*',
                  '', text, flags=re.I)
    chunks = re.split(r'(?=\b\d{4,6}\s+[A-Z]?\d+[A-Z]?\s+[A-Z]{2,5}\b)', text)
    out = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        m = re.match(
            r'(?P<class>\d{4,6})\s+(?P<section>[A-Z]?\d+[A-Z]?)\s+'
            r'(?P<type>[A-Z]{2,5})\s+(?P<campus>\S+)\s+(?P<rest>.*)$', c)
        if not m:
            continue
        out.append({
            "class_nbr": m.group("class"),
            "section_hint": m.group("section"),
            "type": m.group("type"),
            "campus_raw": m.group("campus"),
        })
    return out

def click_section_by_class(page, class_nbr: str) -> bool:
    try:
        h3 = page.locator("h3:has-text('All Sections')").first
        container = h3.locator("xpath=following-sibling::*[1]")
        link = container.locator(f"a:has-text('{class_nbr}')").first
        if link.count() == 0:
            return False
        link.scroll_into_view_if_needed()
        link.click(timeout=3000)
        time.sleep(0.8)
        return True
    except:
        return False

def fallback_click_by_section_label(page, section_hint: str) -> bool:
    try:
        detail = page.locator("[class*='detail']").first
        cand = detail.locator(f"a:has-text('{section_hint}')").first
        if cand.count() == 0:
            return False
        cand.scroll_into_view_if_needed()
        cand.click(timeout=2500)
        page.wait_for_selector(re.compile(rf"Section\s+{re.escape(section_hint)}\b", re.I), timeout=3000)
        return True
    except:
        return False

def extract_professor(inst_block: str, include_email: bool) -> str | None:
    if not inst_block:
        return None

    blk = " ".join(s.strip() for s in inst_block.splitlines() if s.strip())
    em = re.search(r'[\w\.-]+@[\w\.-]+\.\w{2,}', blk)
    window = blk[:em.start()] if em else blk

    window = re.sub(r'\b(Instructors?|Primary Instructor)\b', '', window, flags=re.I)
    window = re.sub(r'[:•\-–—]+', ' ', window)
    window = re.sub(r'\s+', ' ', window).strip()

    name = ""
    m_full = re.search(r'([A-Z][A-Za-z\'\-\._]+(?:\s+[A-Z][A-Za-z\'\-\._]+){1,3})', window)
    if m_full:
        name = m_full.group(1).strip()

    if not name or len(name.split()) < 2:
        m_init = re.search(r'([A-Z]\.\s*[A-Z][A-Za-z\'\-\._]+)', window)
        if m_init:
            name = m_init.group(1).replace(" .", ".").strip()

    if not name or len(name) < 3:
        toks = window.split()
        if len(toks) >= 2:
            name = " ".join(toks[-3:])

    if not name or name.lower().startswith("varies"):
        return None

    prof = name
    if include_email and em:
        prof += f" {em.group(0)}"
    if re.search(r'\bPrimary Instructor\b', blk, re.I) and "Primary Instructor" not in prof:
        prof += " Primary Instructor"

    return prof

def section_details(page, include_email: bool):
    panel_text = page.locator("[class*='detail']").first.inner_text()
    m = re.search(r'Section\s+([A-Z]?\d+[A-Z]?),\s*Class\s+Nbr', panel_text, re.I)
    section = m.group(1) if m else ""

    inst_block = block_after_heading(page, "Instructors")
    professor = extract_professor(inst_block, include_email)

    sched_block = block_after_heading(page, "Schedule and Location")
    schedule_location = norm(sched_block) if sched_block else None

    return section, professor, schedule_location

def campus_from_code(code: str) -> str:
    return "Oxford" if "_OX" in (code or "") else "Atlanta"

def campus_from_raw(cell: str) -> str:
    cell = (cell or "").upper()
    if "ATL@ATLANTA" in cell: return "Atlanta"
    if "OXF@OXFORD" in cell:  return "Oxford"
    return ""


def scrape_course(page, course_code: str, term: str, include_email: bool):
    results = []
    
    try:
        page.goto("https://atlas.emory.edu/", timeout=12000)
        page.get_by_label("Keyword").fill(course_code)
        page.select_option("select#crit-srcdb", term)
        try:
            page.select_option("select#crit-campus",
                               label="Oxford Campus" if "_OX" in course_code else "Atlanta Campus")
        except:
            pass
        page.get_by_role("button", name="SEARCH").click()
        page.wait_for_selector("div.panel__info-bar", timeout=8000)

        link = page.locator("div.result.result--group-start a.result__link").first
        if link.count() == 0:
            return results
        link.click(timeout=4000)
        page.wait_for_selector("h3:has-text('All Sections')", timeout=6000)

        code_txt, title = get_code_and_title(page)
        credits = field_value(page, "Credit Hours")
        ger = field_value(page, "Requirement Designation") or field_value(page, "General Education Requirement") or ""
        instr_method = field_value(page, "Instruction Method")
        typ_off = field_value(page, "Typically Offered") or None

        reg = block_after_heading(page, "Registration Restrictions")
        sec_text = block_after_heading(page, "All Sections")
        sections = parse_all_sections_div(sec_text)

        if not sections:
            section, professor, sched_loc = section_details(page, include_email)
            notes = block_after_heading(page, "Class Notes")
            requirement_sentence = norm(" ".join([x for x in (reg, notes) if x]))
            results.append({
                "code": code_txt, "title": title, "section": section or "n/a", "type": "n/a",
                "credits": credits, "typically_offered": typ_off, "ger": ger,
                "instruction_method": instr_method, "professor": professor,
                "schedule_location": sched_loc, "campus": campus_from_code(code_txt),
                "requirement_sentence": requirement_sentence,
            })
            return results

        first_section = sections[0] if sections else None
        class_notes = ""
        if first_section:
            click_section_by_class(page, first_section["class_nbr"])
            class_notes = block_after_heading(page, "Class Notes")
            if not ger:
                ger = field_value(page, "Requirement Designation") or ""

        requirement_sentence = norm(" ".join([x for x in (reg, class_notes) if x]))

        for s in sections:
            ok = click_section_by_class(page, s["class_nbr"])
            if not ok:
                fallback_click_by_section_label(page, s["section_hint"])
            section, professor, sched_loc = section_details(page, include_email)
            results.append({
                "code": code_txt, "title": title, "section": section or s["section_hint"], "type": s["type"],
                "credits": credits, "typically_offered": typ_off, "ger": ger,
                "instruction_method": instr_method, "professor": professor,
                "schedule_location": sched_loc, 
                "campus": campus_from_raw(s["campus_raw"]) or campus_from_code(code_txt),
                "requirement_sentence": requirement_sentence,
            })

        return results

    except Exception as e:
        print(f"Error scraping {course_code}: {e}", file=sys.stderr)
        return results


def process_batch(courses_batch, term, include_email, batch_id, total, stats, stats_lock):
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=10)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(6000)

        def handle_popup(popup):
            if popup != page:
                try:
                    popup.close()
                except:
                    pass
        context.on("page", handle_popup)

        def _route(route: Route, request: Request):
            if request.resource_type in ("image", "font", "media"):
                return route.abort()
            return route.continue_()
        page.route("**/*", _route)

        for course_code in courses_batch:
            try:
                course_results = scrape_course(page, course_code, term, include_email)
                results.extend(course_results)
            except Exception as e:
                print(f"Error scraping {course_code}: {str(e)[:100]}", file=sys.stderr)

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

def run(input_file, output_file, workers, term, include_email, test_limit):
    print("=" * 60)
    print("PARALLEL BATCH SCRAPER")
    print("=" * 60)

    courses = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                code = normalize_code(obj.get("code", ""))
                if get_course_number(code) <= 500:
                    courses.append(code)

    courses = list(dict.fromkeys(courses))

    if test_limit:
        courses = courses[:test_limit]
        print(f"TEST MODE: Limited to {len(courses)} courses")

    n = len(courses)
    print(f"Processing {n} unique courses (numbers <= 500)")

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
            futures.append(ex.submit(process_batch, batch, term, include_email, batch_id, n, stats, stats_lock))
        
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

    print(f"\nCompleted! Saved {len(all_results)} section records to: {out_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="spring_2026_atlanta_with_requirements.jsonl")
    ap.add_argument("--output", default="spring_2026_scraped.jsonl")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--term", default="Spring 2026")
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    
    run(args.input, args.output, args.workers, args.term, 
        include_email=not args.no_email, test_limit=50 if args.test else None)