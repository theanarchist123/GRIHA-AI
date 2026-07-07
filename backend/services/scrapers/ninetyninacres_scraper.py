"""
99acres scraper — extracts real property listings from search result pages.

URL pattern:
  https://www.99acres.com/{n}-bhk-flats-for-rent-in-{locality}-{city}-ffid

Data sources:
  1. JSON-LD structured data
  2. Inline __INITIAL_STATE__ / __NEXT_DATA__ in <script> tags
  3. Listing card HTML with CSS selectors
"""

import json
import re
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


class NinetyNineAcresScraper(BaseScraper):
    PLATFORM_NAME = "99acres"
    RATE_LIMIT_DELAY = 2.0

    def _build_search_urls(self, locality: str, city: str, bhk: str) -> list[str]:
        """Build multiple URL patterns to try, since 99acres URL formats vary."""
        bhk_num = re.search(r"(\d+)", bhk)
        n = bhk_num.group(1) if bhk_num else "2"

        loc_slug = self._slugify(locality)
        clean_city = self._clean_city_name(city)
        city_slug = self._slugify(clean_city)

        return [
            f"https://www.99acres.com/search/property/rent/{loc_slug}-{city_slug}?city=&preference=R&bedroom_num={n}",
            f"https://www.99acres.com/rent-property-in-{loc_slug}-{city_slug}-ffid",
            f"https://www.99acres.com/{n}-bhk-flats-for-rent-in-{loc_slug}-{city_slug}-ffid",
            f"https://www.99acres.com/flats-for-rent-in-{loc_slug}-{city_slug}-ffid",
        ]

    async def scrape(
        self, locality: str, city: str, bhk: str = "2 BHK", limit: int = 10
    ) -> list[dict]:
        urls = self._build_search_urls(locality, city, bhk)

        html = None
        used_url = urls[0]
        
        # Phase 1: Try all URLs with httpx only (fast, no Playwright)
        for url in urls:
            print(f"  [99acres] Trying: {url}")
            html = await self._fetch_page(url, timeout=12.0)

            if html and len(html) > 2000 and "property" in html.lower():
                used_url = url
                break
            html = None

        # Phase 2: If ALL httpx attempts failed, try Playwright ONCE with best URL
        if not html:
            best_url = urls[0]
            print(f"  [99acres] All httpx failed, trying Playwright once: {best_url}")
            html = await self._fetch_page_playwright(best_url, timeout=15.0)
            if html and len(html) > 2000:
                used_url = best_url
            else:
                html = None

        if not html:
            print("  [99acres] No valid HTML from any URL pattern")
            return []

        soup = BeautifulSoup(html, "lxml")
        listings: list[dict] = []

        # Strategy 1: JSON-LD
        jsonld = self._extract_from_jsonld(soup, locality, city, bhk, used_url)
        listings.extend(jsonld)
        if jsonld:
            print(f"  [99acres] JSON-LD: {len(jsonld)} listings")

        # Strategy 2: Inline script data
        if len(listings) < limit:
            script_data = self._extract_from_scripts(soup, locality, city, bhk, used_url)
            existing_ids = {l["external_id"] for l in listings}
            for sd in script_data:
                if sd["external_id"] not in existing_ids:
                    listings.append(sd)
                    existing_ids.add(sd["external_id"])
            if script_data:
                print(f"  [99acres] Script data: {len(script_data)} listings")

        # Strategy 3: HTML cards
        if len(listings) < limit:
            cards = self._extract_from_cards(soup, locality, city, bhk, used_url)
            existing_ids = {l["external_id"] for l in listings}
            for c in cards:
                if c["external_id"] not in existing_ids:
                    listings.append(c)
                    existing_ids.add(c["external_id"])
            if cards:
                print(f"  [99acres] HTML cards: {len(cards)} listings")

        print(f"  [99acres] Total: {len(listings[:limit])} listings")
        return listings[:limit]

    # ------------------------------------------------------------------
    # JSON-LD
    # ------------------------------------------------------------------

    def _extract_from_jsonld(
        self, soup: BeautifulSoup, locality: str, city: str, bhk: str, page_url: str
    ) -> list[dict]:
        results = []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if data.get("@type") in ("Apartment", "Residence", "Product", "RealEstateListing", "SingleFamilyResidence"):
                    items = [data]
                elif "itemListElement" in data:
                    items = [e.get("item", e) for e in data["itemListElement"] if isinstance(e, dict)]

            for item in items:
                if not isinstance(item, dict):
                    continue
                listing = self._normalize_item(item, locality, city, bhk, page_url)
                if listing:
                    results.append(listing)

        return results

    def _normalize_item(
        self, item: dict, locality: str, city: str, bhk: str, page_url: str
    ) -> Optional[dict]:
        name = item.get("name", "").strip()
        if not name or len(name) < 3:
            return None

        price = None
        offers = item.get("offers", {})
        if isinstance(offers, dict):
            price = self.parse_price(str(offers.get("price", "")))
        if not price:
            price = self.parse_price(str(item.get("price", "")))
        if not price:
            return None

        images = []
        img = item.get("image")
        if isinstance(img, str):
            images = [img]
        elif isinstance(img, list):
            for i in img:
                if isinstance(i, str):
                    images.append(i)
                elif isinstance(i, dict):
                    url = i.get("url") or i.get("contentUrl") or ""
                    if url:
                        images.append(url)
        images = [u for u in images if u and u.startswith("http")][:5]

        listing_url = item.get("url") or page_url
        if listing_url and not listing_url.startswith("http"):
            listing_url = f"https://www.99acres.com{listing_url}"

        sqft = self.parse_sqft(str(item.get("floorSize", {}).get("value", "") if isinstance(item.get("floorSize"), dict) else item.get("floorSize", "")))

        external_id = self._make_external_id(f"99-{name}-{locality}-{bhk}")

        return {
            "external_id": external_id,
            "source_platform": "99acres",
            "source_url": listing_url,
            "title": name[:120],
            "apartment_name": name[:120],
            "address": f"{name}, {locality}, {city}",
            "locality": locality,
            "city": city,
            "price": price,
            "size_sqft": sqft,
            "bhk": self.parse_bhk(name) or bhk,
            "floor": None,
            "bathrooms": item.get("numberOfBathroomsTotal") or item.get("bathrooms"),
            "balconies": None,
            "furnished_status": None,
            "images": images,
            "amenities": [],
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
    # Inline script data (__INITIAL_STATE__ / __NEXT_DATA__)
    # ------------------------------------------------------------------

    def _extract_from_scripts(
        self, soup: BeautifulSoup, locality: str, city: str, bhk: str, page_url: str
    ) -> list[dict]:
        results = []

        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;\s*</script>',
            r'window\.__NEXT_DATA__\s*=\s*({.*?})\s*;\s*</script>',
            r'"listingData"\s*:\s*(\[.*?\])',
            r'"propertyData"\s*:\s*(\[.*?\])',
        ]

        html_str = str(soup)
        for pattern in patterns:
            match = re.search(pattern, html_str, re.DOTALL)
            if not match:
                continue
            try:
                data = json.loads(match.group(1))
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    # Navigate nested structures
                    for key_path in [
                        ["props", "pageProps", "listings"],
                        ["props", "pageProps", "properties"],
                        ["data", "listings"],
                        ["listingData"],
                        ["searchResults"],
                    ]:
                        current = data
                        for key in key_path:
                            if isinstance(current, dict) and key in current:
                                current = current[key]
                            else:
                                current = None
                                break
                        if isinstance(current, list) and len(current) > 0:
                            items = current
                            break

                for item in items[:20]:
                    if not isinstance(item, dict):
                        continue
                    listing = self._normalize_script_item(item, locality, city, bhk, page_url)
                    if listing:
                        results.append(listing)
                if results:
                    break
            except (json.JSONDecodeError, TypeError):
                continue

        return results

    def _normalize_script_item(
        self, item: dict, locality: str, city: str, bhk: str, page_url: str
    ) -> Optional[dict]:
        name = (
            item.get("name") or item.get("title") or item.get("projectName") or
            item.get("society") or item.get("buildingName") or ""
        ).strip()
        if not name or len(name) < 3:
            return None

        price = self.parse_price(str(
            item.get("price") or item.get("rent") or item.get("expectedPrice") or
            item.get("rentPerMonth") or item.get("formattedPrice") or ""
        ))
        if not price:
            return None

        images = []
        photos = item.get("images") or item.get("photos") or item.get("thumbnailUrl") or []
        if isinstance(photos, str):
            images = [photos]
        elif isinstance(photos, list):
            for p in photos:
                if isinstance(p, str) and p.startswith("http"):
                    images.append(p)
                elif isinstance(p, dict):
                    url = p.get("url") or p.get("largeThumbnail") or p.get("originalUrl") or ""
                    if url and url.startswith("http"):
                        images.append(url)
        images = images[:5]

        listing_url = item.get("url") or item.get("propertyUrl") or page_url
        if listing_url and not listing_url.startswith("http"):
            listing_url = f"https://www.99acres.com{listing_url}"

        sqft = None
        area = item.get("carpetArea") or item.get("builtUpArea") or item.get("superBuiltUpArea") or item.get("area")
        if area:
            sqft = self.parse_sqft(str(area))
            if not sqft:
                try:
                    sqft = int(float(str(area)))
                except (ValueError, TypeError):
                    pass

        external_id = self._make_external_id(f"99-{name}-{locality}-{bhk}")

        return {
            "external_id": external_id,
            "source_platform": "99acres",
            "source_url": listing_url,
            "title": name[:120],
            "apartment_name": name[:120],
            "address": f"{name}, {locality}, {city}",
            "locality": item.get("locality") or locality,
            "city": city,
            "price": price,
            "size_sqft": sqft,
            "bhk": self.parse_bhk(str(item.get("bhk", "") or item.get("bedrooms", ""))) or bhk,
            "floor": item.get("floor"),
            "bathrooms": item.get("bathrooms") or item.get("bathroom"),
            "balconies": item.get("balconies") or item.get("balcony"),
            "furnished_status": item.get("furnishing") or item.get("furnishingStatus"),
            "images": images,
            "amenities": item.get("amenities") if isinstance(item.get("amenities"), list) else [],
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
    # HTML card extraction
    # ------------------------------------------------------------------

    def _extract_from_cards(
        self, soup: BeautifulSoup, locality: str, city: str, bhk: str, page_url: str
    ) -> list[dict]:
        results = []

        card_selectors = [
            "div[class*='srp__card']",
            "div[class*='projectTuple']",
            "div[class*='srpTuple']",
            "div[class*='property-card']",
            "div[class*='listing-card']",
            "article[class*='property']",
        ]

        cards = []
        for sel in card_selectors:
            cards = soup.select(sel)
            if cards:
                break

        for card in cards:
            title_el = card.select_one("h2, h3, [class*='title'], [class*='name'], [class*='heading']")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)
            if not title or len(title) < 3:
                continue

            price_el = card.select_one("[class*='price'], [class*='Price'], [class*='rent']")
            price = self.parse_price(price_el.get_text(strip=True) if price_el else "")
            if not price:
                continue

            sqft_el = card.select_one("[class*='area'], [class*='size']")
            sqft = self.parse_sqft(sqft_el.get_text(strip=True) if sqft_el else "")

            images = []
            for img in card.select("img[src], img[data-src]"):
                src = img.get("data-src") or img.get("src") or ""
                clean = self._clean_image_url(src, page_url)
                if clean:
                    images.append(clean)

            link = card.select_one("a[href]")
            listing_url = page_url
            if link:
                href = link.get("href", "")
                if href.startswith("http"):
                    listing_url = href
                elif href.startswith("/"):
                    listing_url = f"https://www.99acres.com{href}"

            external_id = self._make_external_id(f"99-{title}-{locality}")

            results.append({
                "external_id": external_id,
                "source_platform": "99acres",
                "source_url": listing_url,
                "title": title[:120],
                "apartment_name": title[:120],
                "address": f"{title}, {locality}, {city}",
                "locality": locality,
                "city": city,
                "price": price,
                "size_sqft": sqft,
                "bhk": self.parse_bhk(card.get_text(" ", strip=True)) or bhk,
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

        return results
