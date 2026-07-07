"""
Housing.com scraper — extracts real property listings from search result pages.

URL pattern:
  https://housing.com/in/rent/{locality}-{city}
  https://housing.com/in/rent/{locality_slug}-in-{city_slug}

Data sources:
  1. JSON-LD structured data
  2. __NEXT_DATA__ in <script id="__NEXT_DATA__">
  3. HTML listing cards
"""

import json
import re
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


class HousingScraper(BaseScraper):
    PLATFORM_NAME = "housing"
    RATE_LIMIT_DELAY = 2.0

    def _build_search_urls(self, locality: str, city: str, bhk: str) -> list[str]:
        import re
        bhk_num = re.search(r"(\d+)", str(bhk))
        n = bhk_num.group(1) if bhk_num else "2"
        loc_slug = self._slugify(locality)
        loc_slug_underscore = locality.lower().replace(" ", "_")
        clean_city = self._clean_city_name(city)
        city_slug = self._slugify(clean_city)

        return [
            f"https://housing.com/in/rent/{city_slug}/{loc_slug_underscore}",
            f"https://housing.com/in/rent/{loc_slug}-{city_slug}/{n}-bhk",
            f"https://housing.com/in/rent/{n}-bhk-in-{loc_slug}-{city_slug}",
            f"https://housing.com/in/rent/{loc_slug}-in-{city_slug}",
            f"https://housing.com/in/rent/search?q={quote(f'{locality},{city}')}&type=rent&bhk={n}",
        ]

    async def scrape(
        self, locality: str, city: str, bhk: str = "2 BHK", limit: int = 10
    ) -> list[dict]:
        urls = self._build_search_urls(locality, city, bhk)

        html = None
        used_url = urls[0]
        
        # Phase 1: Try all URLs with httpx only (fast, no Playwright)
        for url in urls:
            print(f"  [housing] Trying: {url}")
            html = await self._fetch_page(url, timeout=12.0)

            if html and len(html) > 2000:
                used_url = url
                break
            html = None

        # Phase 2: If ALL httpx attempts failed, try Playwright ONCE with best URL
        if not html:
            best_url = urls[0]
            print(f"  [housing] All httpx failed, trying Playwright once: {best_url}")
            html = await self._fetch_page_playwright(best_url, timeout=15.0)
            if html and len(html) > 2000:
                used_url = best_url
            else:
                html = None

        if not html:
            print("  [housing] No valid HTML from any URL pattern")
            return []

        soup = BeautifulSoup(html, "lxml")
        listings: list[dict] = []

        # Strategy 1: __NEXT_DATA__ (Housing.com is a Next.js app)
        next_data = self._extract_from_next_data(soup, locality, city, bhk, used_url)
        if next_data:
            listings.extend(next_data)
            print(f"  [housing] __NEXT_DATA__: {len(next_data)} listings")

        # Strategy 2: JSON-LD
        if len(listings) < limit:
            jsonld = self._extract_from_jsonld(soup, locality, city, bhk, used_url)
            existing_ids = {l["external_id"] for l in listings}
            for jl in jsonld:
                if jl["external_id"] not in existing_ids:
                    listings.append(jl)
                    existing_ids.add(jl["external_id"])
            if jsonld:
                print(f"  [housing] JSON-LD: {len(jsonld)} listings")

        # Strategy 3: HTML card parsing
        if len(listings) < limit:
            cards = self._extract_from_cards(soup, locality, city, bhk, used_url)
            existing_ids = {l["external_id"] for l in listings}
            for c in cards:
                if c["external_id"] not in existing_ids:
                    listings.append(c)
                    existing_ids.add(c["external_id"])
            if cards:
                print(f"  [housing] HTML cards: {len(cards)} listings")

        print(f"  [housing] Total: {len(listings[:limit])} listings")
        return listings[:limit]

    # ------------------------------------------------------------------
    # __NEXT_DATA__ extraction
    # ------------------------------------------------------------------

    def _extract_from_next_data(
        self, soup: BeautifulSoup, locality: str, city: str, bhk: str, page_url: str
    ) -> list[dict]:
        results = []
        next_data_script = soup.select_one('script#__NEXT_DATA__')
        if not next_data_script:
            return results

        try:
            data = json.loads(next_data_script.string or "")
        except (json.JSONDecodeError, TypeError):
            return results

        # Navigate through Next.js data structure
        page_props = data.get("props", {}).get("pageProps", {})
        listings_data = self._find_listings_in_data(page_props)

        for item in listings_data[:20]:
            listing = self._normalize_housing_item(item, locality, city, bhk, page_url)
            if listing:
                results.append(listing)

        return results

    def _find_listings_in_data(self, data) -> list:
        """Recursively find property listing arrays."""
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            sample = data[0]
            property_keys = {"title", "name", "price", "rent", "projectName", "propertyName", "rentPerMonth", "displayPrice"}
            if property_keys & set(sample.keys()):
                return data

        if isinstance(data, dict):
            for key in ["listings", "properties", "searchResults", "results", "data", "hits", "cards"]:
                if key in data:
                    sub = self._find_listings_in_data(data[key])
                    if sub:
                        return sub
            for val in data.values():
                if isinstance(val, (dict, list)):
                    sub = self._find_listings_in_data(val)
                    if sub:
                        return sub
        return []

    def _normalize_housing_item(
        self, item: dict, locality: str, city: str, bhk: str, page_url: str
    ) -> Optional[dict]:
        if not isinstance(item, dict):
            return None

        name = (
            item.get("title") or item.get("name") or
            item.get("projectName") or item.get("societyName") or
            item.get("buildingName") or ""
        ).strip()
        if not name or len(name) < 3:
            return None

        price = self.parse_price(str(
            item.get("price") or item.get("rent") or
            item.get("rentPerMonth") or item.get("displayPrice") or
            item.get("expectedRent") or ""
        ))
        if not price:
            return None

        # Images
        images = []
        img = item.get("images") or item.get("photos") or item.get("coverImage") or item.get("imageUrl")
        if isinstance(img, str):
            images = [img]
        elif isinstance(img, list):
            for i in img:
                if isinstance(i, str):
                    images.append(i)
                elif isinstance(i, dict):
                    url = i.get("url") or i.get("src") or i.get("original") or ""
                    if url:
                        images.append(url)
        images = [u for u in images if u and u.startswith("http")][:5]

        # URL
        listing_url = item.get("url") or item.get("detailUrl") or item.get("propertyUrl") or page_url
        if listing_url and not listing_url.startswith("http"):
            listing_url = f"https://housing.com{listing_url}"

        sqft = None
        area = item.get("carpetArea") or item.get("superBuiltUpArea") or item.get("builtUpArea") or item.get("area")
        if area:
            sqft = self.parse_sqft(str(area))
            if not sqft:
                try:
                    sqft = int(float(str(area)))
                except (ValueError, TypeError):
                    pass

        detected_bhk = self.parse_bhk(str(item.get("bhk", "") or item.get("bedrooms", ""))) or bhk

        external_id = self._make_external_id(f"hc-{name}-{locality}-{bhk}")

        return {
            "external_id": external_id,
            "source_platform": "housing",
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
    # JSON-LD extraction
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
                if data.get("@type") in ("Apartment", "Residence", "Product", "RealEstateListing"):
                    items = [data]
                elif "itemListElement" in data:
                    items = [e.get("item", e) for e in data["itemListElement"] if isinstance(e, dict)]

            for item in items:
                listing = self._normalize_housing_item(item, locality, city, bhk, page_url)
                if listing:
                    results.append(listing)

        return results

    # ------------------------------------------------------------------
    # HTML card extraction
    # ------------------------------------------------------------------

    def _extract_from_cards(
        self, soup: BeautifulSoup, locality: str, city: str, bhk: str, page_url: str
    ) -> list[dict]:
        results = []

        card_selectors = [
            "div[class*='listing-card']",
            "div[class*='property-card']",
            "div[class*='search-card']",
            "article[class*='property']",
            "div[data-listing-id]",
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
                    listing_url = f"https://housing.com{href}"

            external_id = self._make_external_id(f"hc-{title}-{locality}")

            results.append({
                "external_id": external_id,
                "source_platform": "housing",
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
