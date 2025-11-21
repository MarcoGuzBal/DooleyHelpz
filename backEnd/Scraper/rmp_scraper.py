import json, re, time, threading
from queue import Queue
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OXFORD_SCHOOL_ID = "2633"
EMORY_SCHOOL_ID = "340"

def get_all_professor_urls_via_scrolling(page, school_id, school_name):
    url = f"https://www.ratemyprofessors.com/search/professors/{school_id}"
    
    print(f"[{school_name}] Loading search page...")
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    
    # Wait for results to appear (more robust)
    try:
        page.wait_for_selector("a[href*='/professor/']", timeout=10000)
    except:
        print(f"[{school_name}] Warning: No professors found initially")
    
    time.sleep(3)
    
    # Close any popups
    print(f"[{school_name}] Checking for popups...")
    try:
        close_selectors = ['button[aria-label="Close"]', 'button.close', '.bx-close', '[class*="bx-close"]']
        for selector in close_selectors:
            try:
                close_btn = page.query_selector(selector)
                if close_btn and close_btn.is_visible():
                    close_btn.click()
                    print(f"  ✓ Closed popup")
                    time.sleep(1)
                    break
            except:
                continue
    except:
        pass
    
    print(f"[{school_name}] Scrolling and clicking 'Show More' to load all professors...")
    
    prev_count = 0
    no_change_count = 0
    iteration = 0
    max_iterations = 500
    
    while iteration < max_iterations:
        # Use more flexible selector - just look for professor links
        current_links = page.query_selector_all("a[href*='/professor/']")
        current_count = len(current_links)
        
        if current_count == prev_count:
            no_change_count += 1
            if no_change_count >= 5:
                print(f"[{school_name}] No new professors loaded after 5 attempts, stopping")
                break
        else:
            no_change_count = 0
            prev_count = current_count
        
        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
        
        # Try to click "Show More" button (multiple possible selectors)
        try:
            show_more_selectors = [
                'button:has-text("Show More")',
                'button:text-is("Show More")',
                '[data-testid="show-more-button"]',
                'button[class*="Buttons__Button"]'
            ]
            
            clicked = False
            for selector in show_more_selectors:
                try:
                    show_more_button = page.query_selector(selector)
                    if show_more_button and show_more_button.is_visible():
                        is_disabled = page.evaluate("(btn) => btn.disabled", show_more_button)
                        if not is_disabled:
                            show_more_button.click(force=True, timeout=2000)
                            clicked = True
                            time.sleep(1)
                            break
                except:
                    continue
            
            if not clicked and iteration > 10:
                # No button found after several iterations
                break
                
        except Exception as e:
            if iteration % 50 == 0 and iteration > 0:
                print(f"[{school_name}] Iteration {iteration}: {current_count} professors")
        
        iteration += 1
        
        if iteration % 50 == 0:
            print(f"[{school_name}] Iteration {iteration}: loaded {current_count} professors")
    
    print(f"[{school_name}] Finished loading, extracting professor URLs...")
    
    all_prof_urls = []
    all_prof_names = []
    
    # Get all professor links
    result_a_tags = page.query_selector_all("a[href*='/professor/']")
    print(f"[{school_name}] Found {len(result_a_tags)} total professor links")
    
    seen_urls = set()
    for a in result_a_tags:
        href = a.get_attribute("href")
        if href and "/professor/" in href:
            full_url = f"https://www.ratemyprofessors.com{href}"
            
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            # Try multiple selectors for name
            name = "Unknown"
            try:
                # Try multiple possible name selectors
                name_selectors = [
                    "div[class*='CardName']",
                    "div[class*='TeacherCard__StyledName']",
                    ".TeacherCard__StyledName",
                    "h3",
                    "strong"
                ]
                for selector in name_selectors:
                    name_elem = a.query_selector(selector)
                    if name_elem:
                        name = name_elem.inner_text().strip()
                        if name:
                            break
            except:
                pass
            
            all_prof_urls.append(full_url)
            all_prof_names.append(name)
    
    print(f"[{school_name}] ✓ Total professors found: {len(all_prof_urls)} after {iteration} iterations")
    return all_prof_urls, all_prof_names

def scrape_professor_page(page, prof_url):
    """Scrape a professor page - with review pagination to get ALL reviews"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            page.goto(prof_url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for content to load
            try:
                page.wait_for_selector("div[class*='RatingValue'], div:has-text('No ratings yet')", timeout=8000)
            except:
                pass
            
            time.sleep(1.5)
            
            # Extract professor info - use flexible selectors
            name = "N/A"
            name_selectors = ["div[class*='NameTitle__Name']", "h1", "div[class*='TeacherInfo__Name']"]
            for selector in name_selectors:
                name_elem = page.query_selector(selector)
                if name_elem:
                    name = name_elem.inner_text().strip()
                    if name:
                        break
            
            # Rating
            rating = "N/A"
            rating_selectors = ["div[class*='RatingValue__Numerator']", "div[class*='RatingValue']"]
            for selector in rating_selectors:
                rating_elem = page.query_selector(selector)
                if rating_elem:
                    rating = rating_elem.inner_text().strip()
                    if rating:
                        break
            
            if not rating or rating == "N/A":
                no_ratings_elem = page.query_selector("div:has-text('No ratings yet')")
                if no_ratings_elem:
                    rating = "No rating"
            
            # Number of ratings
            num_ratings = "0"
            num_selectors = ["a[href='#ratingsList']", "div[class*='RatingValue']:has-text('rating')"]
            for selector in num_selectors:
                num_ratings_elem = page.query_selector(selector)
                if num_ratings_elem:
                    text = num_ratings_elem.inner_text().strip()
                    match = re.search(r'(\d+)\s+rating', text, re.I)
                    if match:
                        num_ratings = match.group(1)
                        break
            
            # Department
            department = "N/A"
            dept_selectors = ["div[class*='NameTitle__Title'] a", "a[href*='/school/']"]
            for selector in dept_selectors:
                dept_elem = page.query_selector(selector)
                if dept_elem:
                    department = dept_elem.inner_text().strip()
                    if department:
                        break
            
            # ===== CRITICAL: Load ALL reviews by scrolling =====
            reviews = []
            
            # Scroll to reviews section
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(1)
            except:
                pass
            
            # Load more reviews by clicking "Load More" buttons
            print(f"    Loading all reviews...")
            prev_review_count = 0
            no_change_iterations = 0
            max_review_iterations = 50
            
            for _ in range(max_review_iterations):
                # Count current reviews - use flexible selector
                review_selectors = [
                    "div[class*='Rating__RatingBody']",
                    "div[class*='Rating__StyledRating']",
                    "li[class*='Rating']"
                ]
                
                current_reviews = []
                for selector in review_selectors:
                    current_reviews = page.query_selector_all(selector)
                    if len(current_reviews) > 0:
                        break
                
                current_count = len(current_reviews)
                
                if current_count == prev_review_count:
                    no_change_iterations += 1
                    if no_change_iterations >= 3:
                        break
                else:
                    no_change_iterations = 0
                    prev_review_count = current_count
                
                # Scroll down
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.5)
                
                # Try to click "Load More" button
                load_more_clicked = False
                load_more_selectors = [
                    'button:has-text("Load More")',
                    'button:has-text("Show More")',
                    'button[class*="Buttons__Button"]:has-text("More")'
                ]
                
                for selector in load_more_selectors:
                    try:
                        load_more_btn = page.query_selector(selector)
                        if load_more_btn and load_more_btn.is_visible():
                            load_more_btn.click(timeout=2000)
                            load_more_clicked = True
                            time.sleep(1)
                            break
                    except:
                        continue
                
                if not load_more_clicked and no_change_iterations >= 2:
                    break
            
            # Now extract ALL reviews
            review_cards = current_reviews  # Use the last set we found
            print(f"    Found {len(review_cards)} total reviews")
            
            for card in review_cards:
                try:
                    # Quality rating
                    quality = "N/A"
                    quality_selectors = [
                        "div[class*='CardNumRating__CardNumRatingNumber']",
                        "div[class*='CardNumRating']"
                    ]
                    for selector in quality_selectors:
                        quality_elem = card.query_selector(selector)
                        if quality_elem:
                            quality = quality_elem.inner_text().strip()
                            if quality:
                                break
                    
                    # Course name
                    course_raw = "N/A"
                    course_selectors = [
                        "div[class*='RatingHeader__StyledClass']",
                        "div[class*='Class']"
                    ]
                    for selector in course_selectors:
                        course_elem = card.query_selector(selector)
                        if course_elem:
                            course_raw = course_elem.inner_text().strip()
                            if course_raw:
                                break
                    
                    # Extract course code
                    course_code = "N/A"
                    course_match = re.search(r'\b([A-Z]{2,10})\s*(\d{3,4}[A-Z]*)\b', course_raw, re.I)
                    if course_match:
                        course_code = f"{course_match.group(1).upper()} {course_match.group(2).upper()}"
                    else:
                        course_code = course_raw
                    
                    # Date
                    date = "N/A"
                    date_selectors = ["div[class*='TimeStamp']", "time", "span[class*='Date']"]
                    for selector in date_selectors:
                        date_elem = card.query_selector(selector)
                        if date_elem:
                            date = date_elem.inner_text().strip()
                            if date:
                                break
                    
                    # Comment
                    comment = ""
                    comment_selectors = ["div[class*='Comments']", "div[class*='Comment']", "p"]
                    for selector in comment_selectors:
                        comment_elem = card.query_selector(selector)
                        if comment_elem:
                            comment = comment_elem.inner_text().strip()
                            if comment:
                                break
                    
                    # Tags
                    tags = []
                    tag_selectors = ["span[class*='Tag']", "span[class*='tag']", "div[class*='Tag']"]
                    for selector in tag_selectors:
                        tag_elems = card.query_selector_all(selector)
                        if tag_elems:
                            for tag in tag_elems:
                                tag_text = tag.inner_text().strip()
                                if tag_text:
                                    tags.append(tag_text)
                            break
                    
                    reviews.append({
                        "quality": quality,
                        "course": course_code,
                        "date": date,
                        "comment": comment,
                        "tags": tags
                    })
                except Exception as e:
                    print(f"    Error parsing review: {e}")
                    continue
            
            return {
                "name": name,
                "rating": rating,
                "num_ratings": num_ratings,
                "department": department,
                "reviews": reviews
            }
        
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt + 1}/{max_retries} for {prof_url}")
                time.sleep(2)
                continue
            else:
                print(f"  Error scraping professor page {prof_url}: {e}")
                return None
    
    return None

def scrape_professor_batch_from_queue(prof_queue, worker_id, stats, stats_lock, results_list):
    local_results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        while True:
            try:
                prof_url, prof_name, school_name = prof_queue.get(block=False)
            except:
                break
            
            if prof_url is None:
                break
            
            print(f"[Worker {worker_id}] Scraping: {prof_name}")
            prof_data = scrape_professor_page(page, prof_url)
            if prof_data:
                prof_data["school"] = school_name
                prof_data["url"] = prof_url
                local_results.append(prof_data)
            
            with stats_lock:
                stats["completed"] += 1
                stats["total_reviews"] += len(prof_data.get("reviews", [])) if prof_data else 0
                
                if stats["completed"] % 10 == 0 or stats["completed"] == 1:
                    print(f"[Worker {worker_id}] Progress: {stats['completed']} professors scraped, {stats['total_reviews']} reviews")
            
            time.sleep(0.5)
        
        browser.close()
    
    with stats_lock:
        results_list.extend(local_results)
    
    print(f"[Worker {worker_id}] Finished - scraped {len(local_results)} professors")

def run(output_file, workers=6):
    print("=" * 60)
    print("RATE MY PROFESSOR SCRAPER - FIXED VERSION")
    print("=" * 60)
    print(f"Using {workers} parallel workers")
    print("Step 1: Loading all professor URLs via pagination...")
    print("=" * 60)
    
    all_professors = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        emory_urls, emory_names = get_all_professor_urls_via_scrolling(page, EMORY_SCHOOL_ID, "Emory Atlanta")
        all_professors["Emory Atlanta"] = list(zip(emory_urls, emory_names))
        
        oxford_urls, oxford_names = get_all_professor_urls_via_scrolling(page, OXFORD_SCHOOL_ID, "Emory Oxford")
        all_professors["Emory Oxford"] = list(zip(oxford_urls, oxford_names))
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("Step 2: Creating work queue...")
    print("=" * 60)
    
    prof_queue = Queue()
    for school_name, profs in all_professors.items():
        for url, name in profs:
            prof_queue.put((url, name, school_name))
    
    total_profs = prof_queue.qsize()
    print(f"Total professors to scrape: {total_profs}")
    print(f"Using {workers} workers pulling from shared queue")
    
    print("\n" + "=" * 60)
    print("Step 3: Scraping professor pages (with ALL reviews)...")
    print("=" * 60)
    
    stats_lock = threading.Lock()
    stats = {"completed": 0, "total_reviews": 0}
    results_list = []
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for worker_id in range(1, workers + 1):
            futures.append(executor.submit(scrape_professor_batch_from_queue, prof_queue, worker_id, stats, stats_lock, results_list))
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Worker error: {e}")
    
    elapsed = time.time() - start_time
    
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w", encoding="utf-8") as f:
        for result in results_list:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)
    print(f"Total professors: {len(results_list)}")
    print(f"Total reviews: {stats['total_reviews']}")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"Output: {out_path}")

if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser(description="Scrape Rate My Professor with ALL reviews - FIXED")
    ap.add_argument("--output", default="rmp_data.jsonl", help="Output file path")
    ap.add_argument("--workers", type=int, default=6, help="Number of parallel workers (default: 6)")
    args = ap.parse_args()
    
    run(args.output, args.workers)