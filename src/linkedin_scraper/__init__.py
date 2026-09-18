"""A LinkedIn scraper on Bright Data's Scraper API."""

from .scrape import Outcome, attribute, clean_slug, profile_url, rows, scrape, write

__all__ = ["Outcome", "attribute", "clean_slug", "profile_url", "rows", "scrape", "write"]
__version__ = "0.1.0"
