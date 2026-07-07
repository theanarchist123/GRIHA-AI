import asyncio
import sys
from services.scrapers.base_scraper import BaseScraper

class TestScraper(BaseScraper):
    async def scrape(self, locality, city, bhk, limit): 
        return []

ts = TestScraper()
html = asyncio.run(ts._fetch_page_playwright('https://example.com'))
print('Playwright executed successfully:', html is not None)
