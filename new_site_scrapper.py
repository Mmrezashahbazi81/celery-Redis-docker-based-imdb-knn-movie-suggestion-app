from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# -----------------------------
# SETUP SELENIUM
# -----------------------------
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# -----------------------------
# OPEN THE PAGE
# -----------------------------
url = "https://critics.com/thisyear/"   # <-- replace with actual page URL
driver.get(url)

time.sleep(3)  # wait for page to load

# -----------------------------
# FIND ALL MOVIE BLOCKS
# -----------------------------
movie_blocks = driver.find_elements(By.CSS_SELECTOR, "div.et_pb_blurb_description")

print(f"Found {len(movie_blocks)} movies\n")

# -----------------------------
# EXTRACT DATA
# -----------------------------
for block in movie_blocks:
    # Title + Year
    title_p = block.find_element(By.CSS_SELECTOR, 'p[style*="font-weight: 600"]')
    name = title_p.find_element(By.TAG_NAME, "a").text.strip()
    year = title_p.text.split("|")[-1].strip()

    # Summary
    summary_p = block.find_element(By.CSS_SELECTOR, 'p[style*="margin: 0px 15px 20px 15px"]')
    summary = summary_p.text.strip()

    print("Movie:", name)
    print("Year:", year)
    print("Summary:", summary)
    print("-" * 80)

driver.quit()
