from celery_app import celery
from selenium_scraper import scrape_top_movies
from classifier import build_and_save_classifier

@celery.task
def add(x, y):
    return x + y

@celery.task
def scrape_movies_task(limit):
    """
    1. Run the Selenium Scraper to populate PostgreSQL.
    2. Rebuild the NLP model and update Redis Cache.
    """
    print(f"[CELERY] Starting scrape task (limit={limit})")
    
    # Step 1: Scrape
    scrape_top_movies(limit=limit)
    
    # Step 2: Update NLP "Brain"
    build_and_save_classifier()
    
    return f"Successfully scraped {limit} movies and updated the classifier cache."