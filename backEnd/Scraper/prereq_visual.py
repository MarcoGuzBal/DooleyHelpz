from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json, re, threading, math, argparse, tempfile, time, os, shutil, platform, subprocess


def _norm_ws(t: str) -> str:
    t = t or ""
    t = re.sub(r'[\u2010-\u2015]', '-', t)       
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def _strip_equiv_transfer(t: str) -> str:
    # strip common tails like "or equivalent transfer credit as prerequisite/as a prerequisite."
    t = re.sub(r'\s*\bor\s+equivalent\s+transfer\s+credit\s+as\s+(?:a\s+)?prerequisite\.?', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\bor\s+equivalent\s+transfer\s+credit\b\.?', '', t, flags=re.IGNORECASE)
    return t.strip()

def _trim_braces(t: str) -> str:
    return re.sub(r'^[\{\[]\s*|\s*[\}\]]$', '', t)


COURSE_RE = re.compile(r'\b([A-Z]{2,5})(?:[\s_\-]*(OX))?\s*([0-9]{3}[A-Z]{0,3})\b', re.IGNORECASE)

def _norm_code(subj: str, ox: str | None, num: str) -> str:
    subj = subj.lower()
    num  = num.upper()
    return f"{subj}_ox {num}" if ox else f"{subj} {num}"

def _mark_courses(text: str) -> tuple[str, list[str]]:
    codes = []
    def repl(m):
        code = _norm_code(m.group(1), m.group(2), m.group(3))
        codes.append(code)
        return f"[{code}]"
    return COURSE_RE.sub(repl, text), codes

def _tokenize(marked: str):
    i, n, out = 0, len(marked), []
    while i < n:
        ch = marked[i]
        if ch.isspace():
            i += 1; continue
        if ch in '()':
            out.append(ch); i += 1; continue
        if marked[i:i+3].lower() == 'and' and (i+3 == n or not marked[i+3].isalpha()):
            out.append('AND'); i += 3; continue
        if marked[i:i+2].lower() == 'or' and (i+2 == n or not marked[i+2].isalpha()):
            out.append('OR'); i += 2; continue
        m = re.match(r'\[([^\]]+)\]', marked[i:])
        if m:
            out.append(('COURSE', m.group(1))); i += m.end(); continue
        i += 1
    return out

def _split_top_level_by_AND(tokens):
    depth = 0
    seg, segs = [], []
    for t in tokens:
        if t == '(':
            depth += 1; seg.append(t); continue
        if t == ')':
            depth = max(0, depth - 1); seg.append(t); continue
        if t == 'AND' and depth == 0:
            if seg: segs.append(seg); seg = []
            continue
        seg.append(t)
    if seg: segs.append(seg)
    return segs

def _extract_or_bucket(seg_tokens):
    bucket = []
    for t in seg_tokens:
        if isinstance(t, tuple) and t[0] == 'COURSE':
            c = t[1]
            if c not in bucket:
                bucket.append(c)
    return bucket

def sentence_to_groups(sentence: str):
    if not sentence:
        return []
    core = _strip_equiv_transfer(_trim_braces(_norm_ws(sentence)))
    marked, _ = _mark_courses(core)
    toks = _tokenize(marked)
    segs = _split_top_level_by_AND(toks)
    groups = []
    for seg in segs:
        b = _extract_or_bucket(seg)
        if b:
            groups.append(b)
    return groups


def search_query_for(code: str) -> str:
    if not code:
        return ""
    m = re.match(r'^\s*([A-Za-z]{2,5})(?:_?OX)?\s*([0-9]{3}[A-Za-z]{0,3})\s*$', str(code))
    if not m:
        return re.sub(r'([A-Za-z])([0-9])', r'\1 \2', str(code)).strip()
    return f"{m.group(1).upper()} {m.group(2).upper()}"



def fetch_prereq_sentence(page, course_code: str) -> str:
    q = search_query_for(course_code)
    if not q:
        return ""

    page.goto("https://atlas.emory.edu/", timeout=20000)

    kw = page.get_by_label("Keyword")
    kw.fill("")
    kw.fill(q)

    page.select_option("select#crit-srcdb", "Spring 2026")
    page.select_option("select#crit-camp", "Atlanta Campus")
    page.get_by_role("button", name="SEARCH").click()
    page.wait_for_selector("div.panel__info-bar", timeout=15000)

    link = page.locator("div.result.result--group-start a.result__link").first
    try:
        if hasattr(link, "count") and link.count() == 0:
            return ""
    except Exception:
        pass
    link.scroll_into_view_if_needed()
    link.click(force=True)

    # Wait for inline details to appear; do NOT wait for navigation
    try:
        page.wait_for_selector("xpath=//h3[normalize-space()='Registration Restrictions']", timeout=10000)
    except Exception:
        # Some pages lag; short extra wait then check
        page.wait_for_timeout(1000)
        if not page.locator("xpath=//h3[normalize-space()='Registration Restrictions']").first.is_visible():
            return ""


    js = r"""
    () => {
      function norm(s){ return (s||"").replace(/\s+/g," ").trim(); }
      const h = Array.from(document.querySelectorAll("h3"))
        .find(el => el.textContent && el.textContent.trim().toLowerCase() === "registration restrictions");
      if (!h) return "";
      let sec = h.closest("section,div");
      if (!sec) sec = h.parentElement;
      if (!sec) return "";
      for (const b of sec.querySelectorAll("button,a")) {
        const t = (b.textContent||"").toLowerCase();
        if (/(show\s*more|expand|more)/i.test(t)) { try { b.click(); } catch(e) {} }
      }
      // remove the heading label from the captured text
      let raw = norm(sec.textContent || "");
      raw = raw.replace(/^\s*Registration Restrictions\s*:?\s*/i, "");
      return norm(raw);
    }
    """
    raw = page.evaluate(js)
    text = _trim_braces(_strip_equiv_transfer(_norm_ws(raw)))
    return text


def process_batch_visual(courses_batch, slow_mo_ms, total, stats, stats_lock, record_dir=None):
    out = []
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

        for course in courses_batch:
            page = context.new_page()
            code = str(course.get("code") or "").strip()
            try:
                sent = fetch_prereq_sentence(page, code)
                groups = sentence_to_groups(sent)
                out.append((code, sent, groups))
            except Exception:
                out.append((code, "", []))
            finally:
                try:
                    page.close()
                except Exception:
                    pass

            with stats_lock:
                stats["completed"] += 1
                if stats["completed"] % 50 == 0:
                    print(f"Progress: {stats['completed']}/{total}")

        context.close()
        browser.close()
    return out

def run(input_file, output_file, workers, slow_mo, record_video):
    print("=" * 60)
    print("PREREQ GROUPS (VISIBLE CHROME, FRESH PAGE PER COURSE, PARSE 'REGISTRATION RESTRICTIONS')")
    print("=" * 60)

    # Load
    courses = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                courses.append(json.loads(line))

    uniq = {}
    for c in courses:
        code = c.get("code")
        if code and code not in uniq:
            uniq[code] = c
    unique_list = list(uniq.values())
    u = len(unique_list)
    print(f"Loaded {len(courses)} sections | Unique courses: {u}")

    # Backup input to temp
    tmpdir = Path(tempfile.gettempdir())
    backup = tmpdir / f"{Path(input_file).stem}.backup.{int(time.time())}.jsonl"
    shutil.copy2(input_file, backup)
    print(f"Backup (temp): {backup}")

    workers = max(1, int(workers))
    batch_size = math.ceil(u / workers)
    batches = [unique_list[i:i + batch_size] for i in range(0, u, batch_size)]

    stats_lock = threading.Lock()
    stats = {"completed": 0}
    result_map = {}

    rec_dir = "videos" if record_video else None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = []
        for batch in batches:
            futures.append(ex.submit(process_batch_visual, batch, slow_mo, u, stats, stats_lock, rec_dir))
        for fut in as_completed(futures):
            for code, sent, groups in fut.result():
                if code:
                    result_map[code] = (sent, groups)

    found = 0
    for c in courses:
        code = c.get("code")
        sent, groups = result_map.get(code, ("", []))
        if sent: found += 1
        c["prerequisites_sentence"] = sent
        c["prerequisites_groups"] = groups

    out_path = Path(output_file)
    out_dir = out_path.parent if out_path.parent.as_posix() != "" else Path.cwd()
    os.makedirs(out_dir, exist_ok=True)
    tmp_out = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=str(out_dir),
                                          prefix=f"{out_path.stem}.", suffix=".tmp.jsonl")
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

    print(f"Saved: {out_path}")
    print(f"Found prerequisite sentences for {found}/{u} unique courses")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="spring_2026_atlanta_complete.jsonl")
    ap.add_argument("--output", default="spring_2026_atlanta_with_prereqs.jsonl")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--slow-mo", type=int, default=150)
    ap.add_argument("--record-video", action="store_true")
    args = ap.parse_args()
    run(args.input, args.output, args.workers, args.slow_mo, args.record_video)
