"""Debug: what does MagicBricks price text actually look like?"""
import asyncio, sys, json
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from services.scrapers.magicbricks_scraper import MagicBricksScraper
from bs4 import BeautifulSoup

async def main():
    scraper = MagicBricksScraper()
    url = scraper._build_search_url("Bandra West", "Mumbai", "2 BHK")
    html = await scraper._fetch_page(url, timeout=20.0)
    if not html:
        print("No HTML returned")
        return
    
    soup = BeautifulSoup(html, "lxml")
    
    # Check JSON-LD structure
    print("=== JSON-LD ANALYSIS ===")
    for i, script in enumerate(soup.select('script[type="application/ld+json"]')[:3]):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                items = data.get("itemListElement", [])
                print(f"ItemList with {len(items)} items")
                for item in items[:2]:
                    print(f"  Keys: {list(item.keys())}")
                    print(f"  Full item: {json.dumps(item, indent=2)[:500]}")
            elif isinstance(data, list):
                print(f"Array of {len(data)} items")
                if data:
                    print(f"  First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
                    print(f"  First item: {json.dumps(data[0], indent=2)[:500]}")
        except:
            pass
    
    # Check card HTML structure
    print("\n=== CARD HTML ANALYSIS ===")
    cards = soup.select("div.mb-srp__card")[:3]
    print(f"Found {len(soup.select('div.mb-srp__card'))} cards total")
    
    for i, card in enumerate(cards):
        print(f"\n--- Card {i+1} ---")
        
        # Title
        title_el = card.select_one("h2") or card.select_one("h3")
        print(f"  Title: {title_el.get_text(' ', strip=True)[:80] if title_el else 'NONE'}")
        
        # All price-related elements
        for sel in ["[class*='price']", "[class*='Price']", "[class*='rent']", "[class*='Rent']"]:
            els = card.select(sel)
            for el in els:
                classes = el.get("class", [])
                text = el.get_text(strip=True)
                print(f"  Price sel='{sel}': class={classes} text='{text[:80]}'")
        
        # Check all text with rupee symbol
        import re
        card_text = card.get_text(" ", strip=True)
        rupee_matches = re.findall(r'(?:Rs\.?|₹)\s*[\d,]+(?:\.\d+)?(?:\s*(?:K|Lac|Lakh|Cr|Crore|/\s*month|/\s*mo))?', card_text, re.IGNORECASE)
        print(f"  Rupee patterns found: {rupee_matches[:5]}")
        
        # Dump first 300 chars of card text
        print(f"  Card text (first 300): {card_text[:300]}")

asyncio.run(main())
