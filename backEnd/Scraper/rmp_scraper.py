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
    time.sleep(5)  
    initial_count = len(page.query_selector_all("div.SearchResultsPage__StyledResultsWrapper-vhbycj-4 a"))
    print(f"[{school_name}] Initial load: {initial_count} links found")
    
    if initial_count < 3:
        print(f"[{school_name}] Too few results, trying with search box...")
        try:
            search_box = page.query_selector('input[placeholder*="professor"]')
            if search_box:
                search_box.click()
                search_box.fill("")  # Empty search
                search_box.press("Enter")
                time.sleep(3)
                initial_count = len(page.query_selector_all("div.SearchResultsPage__StyledResultsWrapper-vhbycj-4 a"))
                print(f"[{school_name}] After search: {initial_count} links found")
        except:
            pass
    
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
        current_count = len(page.query_selector_all("div.SearchResultsPage__StyledResultsWrapper-vhbycj-4 a"))
        
        if current_count == prev_count:
            no_change_count += 1
            if no_change_count >= 5:
                print(f"[{school_name}] No new professors loaded after 5 attempts, stopping")
                break
        else:
            no_change_count = 0
            prev_count = current_count
        
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
        
        try:
            show_more_button = page.query_selector('button:has-text("Show More")')
            if show_more_button:
                if show_more_button.is_visible():
                    is_disabled = page.evaluate("(btn) => btn.disabled", show_more_button)
                    if not is_disabled:
                        try:
                            show_more_button.click(force=True, timeout=2000)
                        except:
                            try:
                                show_more_button.scroll_into_view_if_needed()
                                time.sleep(0.3)
                                show_more_button.click(timeout=2000)
                            except:
                                pass
                    else:
                        print(f"[{school_name}] Show More button disabled")
                        break
                else:
                    
                    pass
            else:
                if iteration > 10:  
                    print(f"[{school_name}] No Show More button found")
                    break
        except Exception as e:
            if iteration % 50 == 0 and iteration > 0:
                print(f"[{school_name}] Iteration {iteration}: {current_count} professors")
        
        iteration += 1
        
        if iteration % 50 == 0:
            print(f"[{school_name}] Iteration {iteration}: loaded {current_count} professors")
        
        time.sleep(0.8)
    
    print(f"[{school_name}] Finished loading, extracting professor URLs...")
    
    all_prof_urls = []
    all_prof_names = []
    
    result_a_tags = page.query_selector_all("div.SearchResultsPage__StyledResultsWrapper-vhbycj-4 a")
    print(f"[{school_name}] Found {len(result_a_tags)} total links, filtering for professors...")
    
    for a in result_a_tags:
        href = a.get_attribute("href")
        if href and "/professor/" in href:
            full_url = f"https://www.ratemyprofessors.com{href}"
            name_div = a.query_selector("div.CardName__StyledCardName-sc-1gyrgim-0")
            name = name_div.inner_text().strip() if name_div else "Unknown"
            
            if full_url not in all_prof_urls:
                all_prof_urls.append(full_url)
                all_prof_names.append(name)
    
    print(f"[{school_name}] ✓ Total professors found: {len(all_prof_urls)} after {iteration} iterations")
    return all_prof_urls, all_prof_names

def scrape_professor_page(page, prof_url):
    max_retries = 2
    for attempt in range(max_retries):
        try:
            page.goto(prof_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(1.5)
            
            name_elem = page.query_selector("div.NameTitle__Name-dowf0z-0")
            name = name_elem.inner_text().strip() if name_elem else "N/A"
            
            rating_elem = page.query_selector("div.RatingValue__Numerator-qw8sqy-2")
            rating = rating_elem.inner_text().strip() if rating_elem else "N/A"
            
            if not rating or rating == "N/A":
                no_ratings_elem = page.query_selector("div:has-text('No ratings yet')")
                if no_ratings_elem:
                    rating = "No rating"
            
            num_ratings_elem = page.query_selector("a[href='#ratingsList']")
            num_ratings = "0"
            if num_ratings_elem:
                text = num_ratings_elem.inner_text().strip()
                match = re.search(r'(\d+)\s+rating', text, re.I)
                if match:
                    num_ratings = match.group(1)
            
            dept_elem = page.query_selector("div.NameTitle__Title-dowf0z-1 a")
            department = dept_elem.inner_text().strip() if dept_elem else "N/A"
            
            reviews = []
            review_cards = page.query_selector_all("div.Rating__RatingBody-sc-1rhvpxz-0")
            
            for card in review_cards:
                try:
                    # Quality rating
                    quality_elem = card.query_selector("div.CardNumRating__CardNumRatingNumber-sc-17t4b9u-2")
                    quality = quality_elem.inner_text().strip() if quality_elem else "N/A"
                    
                    # Course name - extract just the course code
                    course_elem = card.query_selector("div.RatingHeader__StyledClass-sc-1dlkqw1-3")
                    course_raw = course_elem.inner_text().strip() if course_elem else "N/A"
                    
                    # Try to extract course code pattern (e.g., "CS 170", "MATH 211")
                    course_code = "N/A"
                    course_match = re.search(r'\b([A-Z]{2,10})\s*(\d{3,4}[A-Z]*)\b', course_raw, re.I)
                    if course_match:
                        course_code = f"{course_match.group(1).upper()} {course_match.group(2).upper()}"
                    else:
                        course_code = course_raw  # Keep original if no pattern match
                    
                    # Date
                    date_elem = card.query_selector("div.TimeStamp__StyledTimeStamp-sc-9q2r30-0")
                    date = date_elem.inner_text().strip() if date_elem else "N/A"
                    
                    # Review comment
                    comment_elem = card.query_selector("div.Comments__StyledComments-dzzyvm-0")
                    comment = comment_elem.inner_text().strip() if comment_elem else ""
                    
                    # Tags (would take again, difficulty, etc.)
                    tags = []
                    tag_elems = card.query_selector_all("span.Tag-bs9vf4-0")
                    for tag in tag_elems:
                        tags.append(tag.inner_text().strip())
                    
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
            
            prof_data = scrape_professor_page(page, prof_url)
            if prof_data:
                prof_data["school"] = school_name
                prof_data["url"] = prof_url
                local_results.append(prof_data)
            
            with stats_lock:
                stats["completed"] += 1
                stats["total_reviews"] += len(prof_data.get("reviews", [])) if prof_data else 0
                
                if stats["completed"] % 25 == 0 or stats["completed"] == 1:
                    print(f"[Worker {worker_id}] Progress: {stats['completed']} professors scraped, {stats['total_reviews']} reviews")
            
            time.sleep(0.5)
        
        browser.close()
    
    with stats_lock:
        results_list.extend(local_results)
    
    print(f"[Worker {worker_id}] Finished - scraped {len(local_results)} professors")

def run(output_file, workers=6):
    print("=" * 60)
    print("RATE MY PROFESSOR SCRAPER - OPTIMIZED")
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
    print("Step 3: Scraping professor pages (workers help each other)...")
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
    
    ap = argparse.ArgumentParser(description="Scrape Rate My Professor with reviews - OPTIMIZED")
    ap.add_argument("--output", default="rmp_data.jsonl", help="Output file path")
    ap.add_argument("--workers", type=int, default=6, help="Number of parallel workers (default: 6)")
    args = ap.parse_args()
    
    run(args.output, args.workers)