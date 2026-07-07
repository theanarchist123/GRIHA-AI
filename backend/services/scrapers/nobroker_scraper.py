"""
NoBroker scraper — extracts real property listings.

NoBroker is a React SPA. The HTML page embeds initial listing data in:
  window.nb.appState.listPage.listPageProperties

Strategy:
  1. Fetch HTML with httpx and extract embedded JSON state from <script> tags
  2. If that fails, try NoBroker's internal API endpoints
  3. Last resort: Playwright headless browser to render JS and extract DOM
"""

import json
import re
import base64
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


# NoBroker city codes
NOBROKER_CITIES = {
    "mumbai": "mumbai",
    "bangalore": "bangalore",
    "bengaluru": "bangalore",
    "pune": "pune",
    "chennai": "chennai",
    "hyderabad": "hyderabad",
    "delhi": "delhi",
    "noida": "noida",
    "gurgaon": "gurgaon",
    "gurugram": "gurgaon",
    "kolkata": "kolkata",
    "ahmedabad": "ahmedabad",
}


class NoBrokerScraper(BaseScraper):
    PLATFORM_NAME = "nobroker"
    RATE_LIMIT_DELAY = 2.0

    def _get_city_code(self, city: str) -> str:
        clean_city = self._clean_city_name(city).lower().strip()
        return NOBROKER_CITIES.get(clean_city, clean_city)

    def _build_search_url(self, locality: str, city: str, bhk: str) -> str:
        city_code = self._get_city_code(city)
        loc_encoded = quote(locality)
        return (
            f"https://www.nobroker.in/property/rent/{city_code}/{loc_encoded}"
            f"?searchParam=W3t9XQ==&type=rent&orderBy=added_date%20desc"
        )

    def _build_api_url(self, locality: str, city: str, bhk: str) -> str:
        """Build NoBroker's internal API URL."""
        city_code = self._get_city_code(city)
        bhk_num = re.search(r"(\d+)", bhk)
        n = bhk_num.group(1) if bhk_num else "2"

        return (
            f"https://www.nobroker.in/api/v3/multi/property/filter"
            f"?city={city_code}&type=rent&sharedAccomodation=0"
            f"&orderBy=added_date%20desc&latLongFilter=false"
            f"&pageNo=1&searchParam=ABS&limit=15"
            f"&radius=2.0&rent=0,500000&bhk={n}"
        )

    async def scrape(
        self, locality: str, city: str, bhk: str = "2 BHK", limit: int = 10
    ) -> list[dict]:
        listings: list[dict] = []

        # Strategy 1: Try to extract embedded state from the HTML page
        page_url = self._build_search_url(locality, city, bhk)
        print(f"  [nobroker] Fetching page: {page_url}")

        html = await self._fetch_page(page_url, timeout=20.0)
        if html and len(html) > 3000:
            embedded = self._extract_from_embedded_state(html, locality, city, bhk, page_url)
            if embedded:
                listings.extend(embedded)
                print(f"  [nobroker] Embedded state: {len(embedded)} listings")

        # Strategy 2: Try the internal API
        if len(listings) < 3:
            api_url = self._build_api_url(locality, city, bhk)
            print(f"  [nobroker] Trying API: {api_url}")
            api_listings = await self._try_api(api_url, locality, city, bhk)
            existing_ids = {l["external_id"] for l in listings}
            for al in api_listings:
                if al["external_id"] not in existing_ids:
                    listings.append(al)
                    existing_ids.add(al["external_id"])
            if api_listings:
                print(f"  [nobroker] API: {len(api_listings)} listings")

        # Strategy 3: Playwright as last resort
        if len(listings) < 3:
            print("  [nobroker] Trying Playwright fallback...")
            pw_listings = await self._try_playwright(locality, city, bhk, page_url)
            existing_ids = {l["external_id"] for l in listings}
            for pl in pw_listings:
                if pl["external_id"] not in existing_ids:
                    listings.append(pl)
                    existing_ids.add(pl["external_id"])
            if pw_listings:
                print(f"  [nobroker] Playwright: {len(pw_listings)} listings")

        print(f"  [nobroker] Total: {len(listings[:limit])} listings")
        return listings[:limit]

    # ------------------------------------------------------------------
    # Strategy 1: Extract from embedded React state
    # ------------------------------------------------------------------

    def _extract_from_embedded_state(
        self, html: str, locality: str, city: str, bhk: str, page_url: str
    ) -> list[dict]:
        results = []

        # Look for window.nb, window.__NEXT_DATA__, or any embedded state
        patterns = [
            r'window\.nb\s*=\s*({.*?})\s*;\s*</script>',
            r'window\.__NEXT_DATA__\s*=\s*({.*?})\s*;\s*</script>',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;\s*</script>',
            r'window\.initialState\s*=\s*({.*?})\s*;\s*</script>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if not match:
                continue
            try:
                data = json.loads(match.group(1))
                # Navigate to listing data
                prop_list = self._find_nobroker_listings(data)
                for item in prop_list[:20]:
                    listing = self._normalize_nobroker_item(item, locality, city, bhk, page_url)
                    if listing:
                        results.append(listing)
                if results:
                    break
            except (json.JSONDecodeError, TypeError) as e:
                print(f"  [nobroker] JSON parse error: {e}")
                continue

        # Also try to find JSON arrays in script blocks
        if not results:
            soup = BeautifulSoup(html, "lxml")
            for script in soup.select("script:not([src])"):
                text = script.string or ""
                if "propertyData" not in text and "listPage" not in text and "otherParams" not in text:
                    continue
                # Try to extract listing arrays
                for arr_pattern in [
                    r'"properties"\s*:\s*(\[.*?\])',
                    r'"listPageProperties"\s*:\s*(\[.*?\])',
                    r'"cardData"\s*:\s*(\[.*?\])',
                ]:
                    arr_match = re.search(arr_pattern, text, re.DOTALL)
                    if arr_match:
                        try:
                            items = json.loads(arr_match.group(1))
                            for item in items[:20]:
                                listing = self._normalize_nobroker_item(item, locality, city, bhk, page_url)
                                if listing:
                                    results.append(listing)
                        except (json.JSONDecodeError, TypeError):
                            continue

        return results

    def _find_nobroker_listings(self, data: dict) -> list:
        """Navigate NoBroker's state tree to find the listing array."""
        if not isinstance(data, dict):
            return []

        # Try known paths
        paths = [
            ["appState", "listPage", "listPageProperties"],
            ["props", "pageProps", "properties"],
            ["data", "properties"],
            ["listPage", "properties"],
            ["searchResults"],
        ]

        for path in paths:
            current = data
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    current = None
                    break
            if isinstance(current, list) and len(current) > 0:
                return current

        # Fallback: recursively search for arrays of objects with property-like keys
        return self._recursive_find_listings(data, depth=0)

    def _recursive_find_listings(self, data, depth: int = 0) -> list:
        if depth > 5:
            return []
        if isinstance(data, list) and len(data) > 2:
            if isinstance(data[0], dict):
                keys = set(data[0].keys())
                property_keys = {"rent", "price", "title", "propertyTitle", "society", "locality", "propertyType"}
                if keys & property_keys:
                    return data
        if isinstance(data, dict):
            for val in data.values():
                result = self._recursive_find_listings(val, depth + 1)
                if result:
                    return result
        return []

    def _normalize_nobroker_item(
        self, item: dict, locality: str, city: str, bhk: str, page_url: str
    ) -> Optional[dict]:
        if not isinstance(item, dict):
            return None

        name = (
            item.get("title") or item.get("propertyTitle") or
            item.get("society") or item.get("buildingName") or
            item.get("projectName") or ""
        ).strip()
        if not name or len(name) < 2:
            return None

        price = self.parse_price(str(
            item.get("rent") or item.get("price") or
            item.get("expectedRent") or item.get("formattedPrice") or ""
        ))
        if not price:
            return None

        # Images
        images = []
        photos = item.get("photos") or item.get("images") or item.get("thumbnailImage") or []
        if isinstance(photos, str):
            images = [photos]
        elif isinstance(photos, list):
            for p in photos:
                if isinstance(p, str):
                    url = p if p.startswith("http") else f"https://images.nobroker.in/images/{p}"
                    images.append(url)
                elif isinstance(p, dict):
                    url = p.get("url") or p.get("imagesMap", {}).get("original") or p.get("thumbnailImage") or ""
                    if url:
                        if not url.startswith("http"):
                            url = f"https://images.nobroker.in/images/{url}"
                        images.append(url)
        images = [u for u in images if u and u.startswith("http")][:5]

        # Thumbnail as fallback
        if not images:
            thumb = item.get("thumbnailImage") or item.get("thumbnail") or ""
            if thumb:
                if not thumb.startswith("http"):
                    thumb = f"https://images.nobroker.in/images/{thumb}"
                images = [thumb]

        # URL
        prop_id = item.get("id") or item.get("propertyId") or ""
        listing_url = page_url
        if prop_id:
            city_code = self._get_city_code(city)
            listing_url = f"https://www.nobroker.in/property/rent/{city_code}/{self._slugify(locality)}/{prop_id}"

        # BHK
        nb_bhk = item.get("bhk") or item.get("type") or ""
        detected_bhk = self.parse_bhk(str(nb_bhk)) or bhk

        sqft = None
        area = item.get("propertySize") or item.get("carpet_area") or item.get("builtUpArea")
        if area:
            try:
                sqft = int(float(str(area)))
            except (ValueError, TypeError):
                sqft = self.parse_sqft(str(area))

        # Furnishing
        furnishing = item.get("furnishing") or item.get("furnishType") or ""
        furnished_map = {
            "FULLY_FURNISHED": "Fully Furnished",
            "SEMI_FURNISHED": "Semi Furnished",
            "NOT_FURNISHED": "Unfurnished",
            "UNFURNISHED": "Unfurnished",
        }
        furnished_status = furnished_map.get(furnishing.upper(), furnishing if furnishing else None)

        # Amenities
        amenities = []
        amenities_map = item.get("amenitiesMap") or item.get("amenities") or {}
        if isinstance(amenities_map, dict):
            for key, val in amenities_map.items():
                if val and val != "false" and val is not False:
                    amenities.append(key.replace("_", " ").title())
        elif isinstance(amenities_map, list):
            amenities = [str(a) for a in amenities_map]

        external_id = self._make_external_id(f"nb-{prop_id or name}-{locality}-{bhk}")

        return {
            "external_id": external_id,
            "source_platform": "nobroker",
            "source_url": listing_url,
            "title": name[:120],
            "apartment_name": name[:120],
            "address": f"{name}, {locality}, {city}",
            "locality": item.get("locality") or locality,
            "city": city,
            "price": price,
            "size_sqft": sqft,
            "bhk": detected_bhk,
            "floor": item.get("floor"),
            "bathrooms": item.get("bathroom") or item.get("bathrooms"),
            "balconies": item.get("balcony") or item.get("balconies"),
            "furnished_status": furnished_status,
            "images": images,
            "amenities": amenities[:6],
            "description": str(item.get("description", ""))[:500],
            "listed_days_ago": 0,
            "is_fake": False,
            "fake_confidence": 0.0,
            "photo_red_flags": [],
            "legal_status": "unknown",
            "rera_registered": False,
            "rera_number": None,
        }

    # ------------------------------------------------------------------
    # Strategy 2: Internal API
    # ------------------------------------------------------------------

    async def _try_api(
        self, api_url: str, locality: str, city: str, bhk: str
    ) -> list[dict]:
        import httpx

        headers = {
            **self._headers(),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.nobroker.in/",
            "Origin": "https://www.nobroker.in",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                response = await client.get(api_url, headers=headers)
                if response.status_code != 200:
                    return []

                data = response.json()
                if not isinstance(data, dict):
                    return []

                # NoBroker API returns { data: [...properties...], otherParams: {...} }
                properties = data.get("data") or data.get("properties") or []
                if not isinstance(properties, list):
                    return []

                results = []
                for item in properties[:15]:
                    listing = self._normalize_nobroker_item(item, locality, city, bhk, api_url)
                    if listing:
                        results.append(listing)
                return results

        except Exception as e:
            print(f"  [nobroker] API error: {e}")
            return []

    # ------------------------------------------------------------------
    # Strategy 3: Playwright fallback
    # ------------------------------------------------------------------

    async def _try_playwright(
        self, locality: str, city: str, bhk: str, page_url: str
    ) -> list[dict]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("  [nobroker] Playwright not installed, skipping")
            return []

        # Run playwright in a separate thread to avoid SelectorEventLoop NotImplementedError on Windows
        def _run_playwright_sync():
            async def _do_playwright():
                results = []
                try:
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        page = await browser.new_page()
                        await page.set_extra_http_headers({"User-Agent": self._random_ua()})

                        await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(3000)

                        # Try to extract state from the page context
                        try:
                            state_data = await page.evaluate("""
                                () => {
                                    if (window.nb && window.nb.appState && window.nb.appState.listPage) {
                                        return JSON.stringify(window.nb.appState.listPage.listPageProperties || []);
                                    }
                                    if (window.__NEXT_DATA__) {
                                        return JSON.stringify(window.__NEXT_DATA__);
                                    }
                                    return null;
                                }
                            """)
                            if state_data:
                                data = json.loads(state_data)
                                if isinstance(data, list):
                                    for item in data[:15]:
                                        listing = self._normalize_nobroker_item(item, locality, city, bhk, page_url)
                                        if listing:
                                            results.append(listing)
                        except Exception as e:
                            print(f"  [nobroker] Playwright state extraction error: {e}")

                        # Fallback: parse the rendered HTML
                        if not results:
                            content = await page.content()
                            soup = BeautifulSoup(content, "lxml")

                            # NoBroker card selectors
                            for card_sel in ["div[class*='card-info']", "article[class*='property']", "div[data-card-id]"]:
                                cards = soup.select(card_sel)
                                if cards:
                                    for card in cards[:15]:
                                        title_el = card.select_one("h2, h3, [class*='title'], [class*='heading']")
                                        price_el = card.select_one("[class*='price'], [class*='rent']")
                                        if title_el and price_el:
                                            title = title_el.get_text(strip=True)
                                            price = self.parse_price(price_el.get_text(strip=True))
                                            if title and price:
                                                images = []
                                                for img in card.select("img[src]"):
                                                    clean = self._clean_image_url(img.get("src", ""), page_url)
                                                    if clean:
                                                        images.append(clean)

                                                external_id = self._make_external_id(f"nb-{title}-{locality}")
                                                results.append({
                                                    "external_id": external_id,
                                                    "source_platform": "nobroker",
                                                    "source_url": page_url,
                                                    "title": title[:120],
                                                    "apartment_name": title[:120],
                                                    "address": f"{title}, {locality}, {city}",
                                                    "locality": locality,
                                                    "city": city,
                                                    "price": price,
                                                    "size_sqft": None,
                                                    "bhk": bhk,
                                                    "floor": None,
                                                    "bathrooms": None,
                                                    "balconies": None,
                                                    "furnished_status": None,
                                                    "images": images[:5],
                                                    "amenities": [],
                                                    "description": "",
                                                    "listed_days_ago": 0,
                                                    "is_fake": False,
                                                    "fake_confidence": 0.0,
                                                    "photo_red_flags": [],
                                                    "legal_status": "unknown",
                                                    "rera_registered": False,
                                                    "rera_number": None,
                                                })
                                    break

                        await browser.close()

                except Exception as e:
                    print(f"  [nobroker] Playwright error: {e}")
                return results

            import asyncio
            import sys
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            return asyncio.run(_do_playwright())

        try:
            import asyncio
            return await asyncio.to_thread(_run_playwright_sync)
        except Exception as e:
            print(f"  [nobroker] Thread fetch failed: {e}")
            return []
