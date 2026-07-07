"""
Test each scraper individually with a well-known location to find what's broken.
Run: python test_scrapers.py
"""
import asyncio
import sys
import json
import time

# Windows event loop policy fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from services.scrapers.magicbricks_scraper import MagicBricksScraper
from services.scrapers.ninetyninacres_scraper import NinetyNineAcresScraper
from services.scrapers.nobroker_scraper import NoBrokerScraper
from services.scrapers.housing_scraper import HousingScraper
from services.scrapers.base_scraper import BaseScraper

# Test with a well-known location that definitely has listings
LOCALITY = "Vangaon"
CITY = "Palghar"
BHK = "2 BHK"


async def test_magicbricks_raw():
    """Test: does MagicBricks even return HTML? What does the HTML look like?"""
    print("\n" + "="*70)
    print("TEST 1: MagicBricks - Raw HTTP fetch")
    print("="*70)
    scraper = MagicBricksScraper()
    url = scraper._build_search_url(LOCALITY, CITY, BHK)
    print(f"  URL: {url}")
    
    html = await scraper._fetch_page(url, timeout=20.0)
    if not html:
        print("  ❌ httpx returned NO HTML")
        print("  Trying Playwright...")
        html = await scraper._fetch_page_playwright(url, timeout=20.0)
        if not html:
            print("  ❌ Playwright also returned NO HTML")
            return
        print(f"  ✅ Playwright returned {len(html)} chars")
    else:
        print(f"  ✅ httpx returned {len(html)} chars")
    
    # Check what's in the HTML
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    
    # Check for JSON-LD
    jsonld = soup.select('script[type="application/ld+json"]')
    print(f"  JSON-LD scripts found: {len(jsonld)}")
    for i, j in enumerate(jsonld[:2]):
        try:
            data = json.loads(j.string or "")
            if isinstance(data, dict):
                print(f"    [{i}] type={data.get('@type', 'unknown')}, keys={list(data.keys())[:6]}")
            elif isinstance(data, list):
                print(f"    [{i}] array of {len(data)} items")
        except:
            print(f"    [{i}] parse error")
    
    # Check for card elements
    selectors = [
        "div.mb-srp__card", "div[data-card]", "div.mb-srp__list",
        "article.srpCard", "div.property-card", "li.SRCard__container"
    ]
    for sel in selectors:
        cards = soup.select(sel)
        if cards:
            print(f"  Card selector '{sel}': {len(cards)} cards found")
    
    # Check title
    title = soup.title.get_text(strip=True) if soup.title else ""
    print(f"  Page title: {title[:80]}")
    
    # Check for "no results" indicators
    text = soup.get_text(" ", strip=True).lower()
    no_result_phrases = ["no results", "no properties", "no matching", "sorry", "we couldn't find", "0 results"]
    for phrase in no_result_phrases:
        if phrase in text:
            print(f"  ⚠️ Found '{phrase}' in page text - this is a 'no results' page!")
    
    # Save first 5000 chars for inspection
    with open("_debug_mb_html.txt", "w", encoding="utf-8") as f:
        f.write(html[:5000])
    print("  Saved first 5000 chars to _debug_mb_html.txt")


async def test_magicbricks_scraper():
    """Test: does the full scraper extract listings?"""
    print("\n" + "="*70)
    print("TEST 2: MagicBricks - Full scraper")
    print("="*70)
    scraper = MagicBricksScraper()
    start = time.time()
    results = await scraper.scrape(LOCALITY, CITY, BHK, limit=5)
    elapsed = time.time() - start
    print(f"  Results: {len(results)} listings in {elapsed:.1f}s")
    for r in results[:3]:
        print(f"    - {r['title'][:50]} | ₹{r['price']:,.0f} | {r['bhk']}")


async def test_magicbricks_playwright():
    """Test: does MagicBricks work when using Playwright for the fetch?"""
    print("\n" + "="*70)
    print("TEST 3: MagicBricks - Playwright fetch + extraction")
    print("="*70)
    scraper = MagicBricksScraper()
    url = scraper._build_search_url(LOCALITY, CITY, BHK)
    print(f"  URL: {url}")
    
    html = await scraper._fetch_page_playwright(url, timeout=25.0)
    if not html:
        print("  ❌ Playwright returned NO HTML")
        return
    
    print(f"  ✅ Playwright returned {len(html)} chars")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    
    # Try extracting with each strategy
    jsonld = scraper._extract_from_jsonld(soup, LOCALITY, CITY, BHK, url)
    print(f"  JSON-LD: {len(jsonld)} listings")
    
    cards = scraper._extract_from_cards(soup, LOCALITY, CITY, BHK, url)
    print(f"  Cards: {len(cards)} listings")
    
    scripts = scraper._extract_from_scripts(soup, LOCALITY, CITY, BHK, url)
    print(f"  Scripts: {len(scripts)} listings")
    
    total = len(jsonld) + len(cards) + len(scripts)
    if total > 0:
        all_listings = jsonld + cards + scripts
        for r in all_listings[:3]:
            print(f"    - {r['title'][:50]} | ₹{r['price']:,.0f}")
    else:
        # Save HTML for debugging
        with open("_debug_mb_pw_html.txt", "w", encoding="utf-8") as f:
            f.write(html[:10000])
        print("  Saved Playwright HTML to _debug_mb_pw_html.txt")


async def test_99acres():
    """Test: 99acres full scraper"""
    print("\n" + "="*70)
    print("TEST 4: 99acres - Full scraper")
    print("="*70)
    scraper = NinetyNineAcresScraper()
    start = time.time()
    results = await scraper.scrape(LOCALITY, CITY, BHK, limit=5)
    elapsed = time.time() - start
    print(f"  Results: {len(results)} listings in {elapsed:.1f}s")
    for r in results[:3]:
        print(f"    - {r['title'][:50]} | ₹{r['price']:,.0f} | {r['bhk']}")


async def test_housing():
    """Test: Housing.com full scraper"""
    print("\n" + "="*70)
    print("TEST 5: Housing.com - Full scraper")
    print("="*70)
    scraper = HousingScraper()
    start = time.time()
    results = await scraper.scrape(LOCALITY, CITY, BHK, limit=5)
    elapsed = time.time() - start
    print(f"  Results: {len(results)} listings in {elapsed:.1f}s")
    for r in results[:3]:
        print(f"    - {r['title'][:50]} | ₹{r['price']:,.0f} | {r['bhk']}")


async def test_nobroker():
    """Test: NoBroker full scraper"""
    print("\n" + "="*70)
    print("TEST 6: NoBroker - Full scraper")
    print("="*70)
    scraper = NoBrokerScraper()
    start = time.time()
    results = await scraper.scrape(LOCALITY, CITY, BHK, limit=5)
    elapsed = time.time() - start
    print(f"  Results: {len(results)} listings in {elapsed:.1f}s")
    for r in results[:3]:
        print(f"    - {r['title'][:50]} | ₹{r['price']:,.0f} | {r['bhk']}")


async def main():
    print("=" * 70)
    print(f"SCRAPER DIAGNOSTIC TEST")
    print(f"Location: {LOCALITY}, {CITY} | BHK: {BHK}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Test 1: MagicBricks raw HTML
    await test_magicbricks_raw()
    
    # Test 2: MagicBricks full scraper
    await test_magicbricks_scraper()
    
    # Test 3: MagicBricks via Playwright
    await test_magicbricks_playwright()
    
    # Test 4: 99acres
    await test_99acres()
    
    # Test 5: Housing.com
    await test_housing()
    
    # Test 6: NoBroker
    await test_nobroker()
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
