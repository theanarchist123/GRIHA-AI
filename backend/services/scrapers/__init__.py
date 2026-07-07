# Scrapers package for Griha AI
from .base_scraper import BaseScraper
from .magicbricks_scraper import MagicBricksScraper
from .ninetyninacres_scraper import NinetyNineAcresScraper
from .nobroker_scraper import NoBrokerScraper
from .housing_scraper import HousingScraper

__all__ = [
    "BaseScraper",
    "MagicBricksScraper",
    "NinetyNineAcresScraper",
    "NoBrokerScraper",
    "HousingScraper",
]
