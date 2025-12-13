from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json, re, threading, math, argparse, os, tempfile, time, shutil

CANVAS_W = 2560
CANVAS_H = 1600
ORIGIN_X = 0
ORIGIN_Y = 0

SHRINK_W = 4
SHRINK_H = 4

def dept_key(code):
    m = re.match(r"\s*([A-Za-z]+)", str(code) if code is not None else "")
    return (m.group(1).upper() if m else "")

def detect_campus(location, code):
    campuses = []
    if location:
        loc_lower = str(location).lower()
        if "oxford" in loc_lower:
            campuses.append("Oxford")
        else:
            campuses.append("Atlanta")
    if code and ("_OX" in str(code).upper() or str(code).upper().endswith("OX")):
        if "Oxford" not in campuses:
            campuses.append("Oxford")
    return campuses if campuses else ["Atlanta"]

def detect_restrictions(code, has_permission_text):
    restrictions = {"permission_required": bool(has_permission_text),
                    "level": "undergraduate",
                    "major_only": []}
    if code:
        nums = re.findall(r"\d+", str(code))
        if nums:
            num = int(nums[0])
            if num >= 500:
                restrictions["level"] = "graduate"
            elif num >= 400:
                restrictions["level"] = "advanced"
    return restrictions

def check_permission_for_course_fast(page, course_code):
    try:
        q = dept_key(course_code)
        if not q:
            return False

        page.goto("https://atlas.emory.edu/", timeout=20000)
        page.get_by_label("Keyword").fill(q) 
        page.select_option("select#crit-srcdb", "Spring 2026")
        page.select_option("select#crit-camp", "Atlanta Campus")
        page.get_by_role("button", name="SEARCH").click()
        page.wait_for_selector("div.panel__info-bar", timeout=15000)

        links = page.locator("div.result.result--group-start a.result__link")
        if links.count() == 0:
            return False
        links.first.click(force=True)

        def looks_like_sections(resp):
            try:
                rt = resp.request.resource_type
            except Exception:
                rt = ""
            url = resp.url.lower()
            return (rt in ("xhr", "fetch")) and any(k in url for k in ("section", "class", "details", "course"))
        resp = page.wait_for_response(looks_like_sections, timeout=15000)

        data = None
        try:
            data = resp.json()
        except Exception:
            data = None

        sections = []
        if isinstance(data, dict):
            for k in ("sections", "data", "classes", "courseSections", "results"):
                v = data.get(k)
                if isinstance(v, list):
                    sections = v
                    break
            if not sections:
                try:
                    sections = list(data.values())
                except Exception:
                    sections = []
        elif isinstance(data, list):
            sections = data

        for s in sections or []:
            notes = " ".join([
                str(s.get("notes") or ""),
                str(s.get("classNotes") or ""),
                str(s.get("enrollmentRequirements") or ""),
                str(s.get("consent") or ""),
                str(s.get("requisites") or ""),
            ]).lower()
            if ("permission required prior to enrollment" in notes) or ("consent" in notes):
                return True

        for sec in page.locator("a.course-section").all()[:5]:
            try:
                sec.scroll_into_view_if_needed()
                sec.click(force=True)
                page.wait_for_timeout(150)
                text = (page.locator("[class*='note']").first.text_content() or "").lower()
                if ("permission required prior to enrollment" in text) or ("consent" in text):
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False

def exact_grid_for_k(k):
    if k == 12:
        return 4, 3
    cols = int(math.floor(math.sqrt(k * (CANVAS_W / CANVAS_H))))
    cols = max(1, cols)
    rows = math.ceil(k / cols)
    if cols * rows < k:
        cols += 1
    return cols, rows

def compute_tiles_exact(k, cols=None, rows=None):
    if cols is None or rows is None:
        cols, rows = exact_grid_for_k(k)

    base_w = CANVAS_W // cols
    rem_w = CANVAS_W - base_w * cols
    col_w = [base_w + (1 if i < rem_w else 0) for i in range(cols)]

    base_h = CANVAS_H // rows
    rem_h = CANVAS_H - base_h * rows
    row_h = [base_h + (1 if i < rem_h else 0) for i in range(rows)]

    x_off = [ORIGIN_X]
    for i in range(1, cols):
        x_off.append(x_off[-1] + col_w[i-1])
    y_off = [ORIGIN_Y]
    for i in range(1, rows):
        y_off.append(y_off[-1] + row_h[i-1])

    tiles = []
    for i in range(k):
        r = i // cols
        c = i % cols
        x = x_off[c]
        y = y_off[r]
        w = max(200, col_w[c] - SHRINK_W)
        h = max(200, row_h[r] - SHRINK_H)
        tiles.append(((int(x), int(y)), (int(w), int(h))))
    return tiles

def set_window_bounds_outer(context, page, x, y, w, h):
    session = context.new_cdp_session(page)
    info = session.send("Browser.getWindowForTarget")
    wid = info.get("windowId")
    if wid is None:
        return
    session.send("Browser.setWindowBounds", {
        "windowId": wid,
        "bounds": {"left": int(x), "top": int(y), "width": int(w), "height": int(h), "windowState": "normal"}
    })

def process_batch_visual(courses_batch, tile, slow_mo_ms, total, stats, stats_lock, record_dir=None):
    permission_items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=slow_mo_ms,
            args=[
                "--force-device-scale-factor=1",
                "--high-dpi-support=1",
                "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-features=CalculateNativeWinOcclusion",
            ],
        )
        ctx_kwargs = {}
        if record_dir:
            os.makedirs(record_dir, exist_ok=True)
            ctx_kwargs["record_video_dir"] = record_dir
        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()

        (x, y), (w, h) = tile
        set_window_bounds_outer(context, page, x, y, w, h)

        for course in courses_batch:
            code = course.get("code") or ""
            try:
                has_permission = check_permission_for_course_fast(page, code)
            except Exception:
                has_permission = False

            campuses = detect_campus(course.get("location"), code)
            restr = detect_restrictions(code, has_permission)
            permission_items.append((code, campuses, restr))

            with stats_lock:
                stats["completed"] += 1
                if stats["completed"] % 50 == 0:
                    print(f"Progress: {stats['completed']}/{total}")

        context.close()
        browser.close()
    return permission_items

def run(input_file, output_file, workers, slow_mo, record_video):
    print("=" * 60)
    print("FAST VISUAL ENRICH (exact tiling, dept-only query, atomic write)")
    print("=" * 60)

    courses = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                courses.append(json.loads(line))
    n = len(courses)
    print(f"Loaded {n} sections")

    unique_courses = {}
    for c in courses:
        code = c.get("code")
        if code and code not in unique_courses:
            unique_courses[code] = c
    unique_list = list(unique_courses.values())
    u = len(unique_list)
    print(f"Unique courses: {u}")

    tmpdir = Path(tempfile.gettempdir())
    backup = tmpdir / f"{Path(input_file).stem}.spring.backup.{int(time.time())}.jsonl"
    shutil.copy2(input_file, backup)
    print(f"Backup (temp): {backup}")

    workers = max(1, int(workers))
    batch_size = math.ceil(u / workers)
    batches = [unique_list[i:i + batch_size] for i in range(0, u, batch_size)]

    tiles = compute_tiles_exact(workers, cols=4, rows=3) if workers == 12 else compute_tiles_exact(workers)
    tiles = tiles[:workers]
    print(f"Workers: {workers} | First tile: {tiles[0][1][0]}x{tiles[0][1][1]} | slow_mo={slow_mo}ms")

    stats_lock = threading.Lock()
    stats = {"completed": 0}
    permission_map = {}
    rec_dir = "videos" if record_video else None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = []
        for i, batch in enumerate(batches):
            futures.append(ex.submit(process_batch_visual, batch, tiles[i], slow_mo, u, stats, stats_lock, rec_dir))
        for fut in as_completed(futures):
            for code, campuses, restr in fut.result():
                permission_map[code] = {"campuses": campuses, "restrictions": restr}

    for c in courses:
        code = c.get("code")
        if code in permission_map:
            c["campuses"] = permission_map[code]["campuses"]
            c["restrictions"] = permission_map[code]["restrictions"]
        else:
            c["campuses"] = detect_campus(c.get("location"), code)
            c["restrictions"] = detect_restrictions(code, False)

    out_path = Path(output_file)
    out_dir = out_path.parent if out_path.parent.as_posix() != "" else Path.cwd()
    os.makedirs(out_dir, exist_ok=True)
    tmp_out = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False,
        dir=str(out_dir), prefix=f"{out_path.stem}.", suffix=".tmp.jsonl"
    )
    try:
        with tmp_out as f:
            for c in courses:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        os.replace(tmp_out.name, out_path)
    finally:
        try:
            if os.path.exists(tmp_out.name):
                os.remove(tmp_out.name)
        except Exception:
            pass

    perm_count = sum(1 for c in courses if c["restrictions"]["permission_required"])
    grad_count = sum(1 for c in courses if c["restrictions"]["level"] == "graduate")
    oxford_count = sum(1 for c in courses if "Oxford" in c["campuses"])

    print(f"Saved: {out_path}")
    print(f"Stats: permission={perm_count}  graduate={grad_count}  oxford={oxford_count}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="spring_2026_atlanta_course_detailed.jsonl")
    ap.add_argument("--output", default="spring_2026_atlanta_complete.jsonl")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--slow-mo", type=int, default=150)
    ap.add_argument("--record-video", action="store_true")
    args = ap.parse_args()
    run(args.input, args.output, args.workers, args.slow_mo, args.record_video)
