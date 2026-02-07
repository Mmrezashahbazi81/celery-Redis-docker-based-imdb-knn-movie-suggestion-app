from celery_app import celery
from selenium_scraper import scrape_top_movies

@celery.task
def add(x, y):
    return x + y


@celery.task
def scrape_movies_task(limit=250):
    return scrape_top_movies(limit=limit)