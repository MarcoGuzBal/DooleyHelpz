from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json, re, threading, math, argparse, platform, subprocess, tempfile, time, os, shutil

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
        page.goto("https://atlas.emory.edu/", timeout=20000)
        page.get_by_label("Keyword").fill(course_code)
        page.select_option("select#crit-srcdb", "Spring 2026")
        page.select_option("select#crit-camp", "Atlanta Campus")
        page.get_by_role("button", name="SEARCH").click()
        page.wait_for_selector("div.panel__info-bar", timeout=15000)

        link = page.locator("div.result.result--group-start a.result__link").first
        if not link or (hasattr(link, "count") and link.count() == 0):
            return False
        link.click(force=True)

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

# ---------- screen tiling ----------
def get_screen_size():
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        elif platform.system() == "Darwin":
            try:
                from AppKit import NSScreen  # type: ignore
                f = NSScreen.mainScreen().frame()
                return int(f.size.width), int(f.size.height)
            except Exception:
                return 2560, 1600
        else:
            try:
                out = subprocess.check_output(["xrandr"]).decode()
                m = re.search(r"current\s+(\d+)\s+x\s+(\d+)", out)
                if m:
                    return int(m.group(1)), int(m.group(2))
            except Exception:
                pass
            return 2560, 1600
    except Exception:
        return 2560, 1600

def compute_tiles(screen_w, screen_h, k):
    cols = math.ceil(math.sqrt(k * (screen_w / screen_h)))
    rows = math.ceil(k / cols)
    tile_w = screen_w // cols
    tile_h = screen_h // rows
    tiles = []
    for i in range(k):
        r = i // cols
        c = i % cols
        x = c * tile_w
        y = r * tile_h
        tiles.append(((x, y), (tile_w, tile_h)))
    return tiles

def process_batch_visual(courses_batch, tile, slow_mo_ms, total, stats, stats_lock, record_dir=None):
    permission_items = []
    with sync_playwright() as p:
        args = []
        (x, y), (w, h) = tile
        args += [f"--window-position={x},{y}", f"--window-size={w},{h}"]
        browser = p.chromium.launch(headless=False, slow_mo=slow_mo_ms, args=args)

        ctx_kwargs = {"viewport": {"width": w, "height": h}}
        if record_dir:
            os.makedirs(record_dir, exist_ok=True)
            ctx_kwargs["record_video_dir"] = record_dir

        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()

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
    print("FAST VISUAL ENRICH (TILED, TEMP BACKUP, ATOMIC WRITE)")
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

    # Temp backup, not alongside input
    tmpdir = Path(tempfile.gettempdir())
    backup = tmpdir / f"{Path(input_file).stem}.spring.backup.{int(time.time())}.jsonl"
    shutil.copy2(input_file, backup)
    print(f"Backup (temp): {backup}")

    if workers < 1:
        workers = 1
    batch_size = math.ceil(u / workers)
    batches = [unique_list[i:i + batch_size] for i in range(0, u, batch_size)]

    sw, sh = get_screen_size()
    tiles = compute_tiles(sw, sh, workers)

    print(f"Workers: {workers}  |  Screen: {sw}x{sh}  |  Tile: ~{tiles[0][1][0]}x{tiles[0][1][1]}  |  slow_mo={slow_mo}ms")

    stats_lock = threading.Lock()
    stats = {"completed": 0}
    permission_map = {}

    rec_dir = "videos" if record_video else None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = []
        for i, batch in enumerate(batches):
            tile = tiles[i]
            futures.append(ex.submit(process_batch_visual, batch, tile, slow_mo, u, stats, stats_lock, rec_dir))
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
        dir=str(out_dir),
        prefix=f"{out_path.stem}.", suffix=".tmp.jsonl"
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
