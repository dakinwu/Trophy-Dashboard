import cloudscraper

from app.config import settings


def create_session():
    session = cloudscraper.create_scraper()
    session.headers.update({"User-Agent": settings.scrape_user_agent})
    return session
