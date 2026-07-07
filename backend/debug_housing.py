import asyncio, sys, json
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from services.scrapers.housing_scraper import HousingScraper

async def main():
    scraper = HousingScraper()
    url = scraper._build_search_urls("Bandra West", "Mumbai", "2 BHK")[0]
    print(f"URL: {url}")
    html = await scraper._fetch_page_playwright(url, timeout=25.0)
    if not html:
        print("No HTML returned")
        return
        
    print(f"Playwright returned {len(html)} chars")
    with open("_debug_housing_html.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    # Test json parsing
    import re
    state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;</script>', html, re.DOTALL)
    if state_match:
        print("Found __INITIAL_STATE__!")
        try:
            state = json.loads(state_match.group(1))
            search_results = state.get("search", {}).get("searchResults", [])
            print(f"Search results count: {len(search_results)}")
        except Exception as e:
            print(f"Parse error: {e}")
    else:
        print("No __INITIAL_STATE__ found")

asyncio.run(main())
