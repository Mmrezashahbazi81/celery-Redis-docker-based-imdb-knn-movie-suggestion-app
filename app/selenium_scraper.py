import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from database import SessionLocal
from models import Movie

# -----------------------------
# CONFIGURATION
# -----------------------------
# Base URL provided for the new layout
BASE_URL = "https://critics.com/thisyear/"

# Selenium host is retrieved from the environment for Docker compatibility
SELENIUM_HOST = os.getenv("SELENIUM_HOST", "localhost")

def get_driver():
    """Sets up the driver to work with the Selenium container."""
    chrome_options = Options()
    
    # Modern headless mode and resource management for containerized runs
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Standard User-Agent to avoid immediate bot detection
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Connect to the remote selenium service defined in docker-compose
    driver = webdriver.Remote(
        command_executor=f"http://{SELENIUM_HOST}:4444/wd/hub",
        options=chrome_options
    )
    return driver

def scrape_top_movies(limit):
    """
    Main scraping function using the new 'et_pb_blurb' logic.
    Saves results to the database defined in models.py.
    """
    print(f"[INFO] Starting Scrape: {BASE_URL} (limit={limit})")
    
    driver = get_driver()
    db = SessionLocal() # Open DB session
    count = 0

    try:
        driver.get(BASE_URL)
        time.sleep(3) # Wait for page load as per your logic

        # Find all movie blocks using the description selector
        movie_blocks = driver.find_elements(By.CSS_SELECTOR, "div.et_pb_blurb_description")
        print(f"[INFO] Found {len(movie_blocks)} movies in the list.")

        for block in movie_blocks:
            if count >= limit:
                break

            try:
                # 1. Extract Title and Year from the bolded paragraph
                title_p = block.find_element(By.CSS_SELECTOR, 'p[style*="font-weight: 600"]')
                name = title_p.find_element(By.TAG_NAME, "a").text.strip()
                
                # Extract and clean Year. 
                # Note: models.py expects an Integer for year.
                raw_year_text = title_p.text.split("|")[-1].strip()
                year_match = re.search(r"\d{4}", raw_year_text)
                year_int = int(year_match.group(0)) if year_match else None

                # 2. Extract Summary from the paragraph with specific margins
                summary_p = block.find_element(By.CSS_SELECTOR, 'p[style*="margin: 0px 15px 20px 15px"]')
                summary = summary_p.text.strip()

                # 3. Create and add the Movie object to session
                new_movie = Movie(
                    title=name,
                    summary=summary,
                    year=year_int,
                    rating=None # Rating not found in current block logic
                )
                db.add(new_movie)
                
                count += 1
                print(f"[{count}] Scraped: {name} ({year_int})")

            except Exception as block_err:
                print(f"[WARN] Failed to parse block: {block_err}")
                continue

        # Commit changes to the PostgreSQL database
        db.commit()
        print(f"[SUCCESS] Scraped and saved {count} movies.")

    except Exception as e:
        print(f"[ERROR] Critical scraper failure: {e}")
    finally:
        db.close()
        driver.quit()
        print("[INFO] Scraper session closed.")

if __name__ == "__main__":
    # Local debug entry point
    scrape_top_movies(limit=3)