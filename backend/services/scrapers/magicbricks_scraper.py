"""
MagicBricks scraper — extracts real property listings from search result pages.

URL pattern:
  https://www.magicbricks.com/property-for-rent/residential-real-estate?
    bedroom={n}&proptype=Multistorey-Apartment,Builder-Floor-Apartment
    &cityName={city}&localityName={locality}

Data sources within the page:
  1. JSON-LD structured data in <script type="application/ld+json">
  2. Listing card HTML: div.mb-srp__card
  3. __NEXT_DATA__ or inline JS state objects
"""

import json
import re
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


class MagicBricksScraper(BaseScraper):
    PLATFORM_NAME = "magicbricks"
    RATE_LIMIT_DELAY = 2.0

    def _build_search_url(self, locality: str, city: str, bhk: str) -> str:
        bhk_num = re.search(r"(\d+)", bhk)
        bedroom = bhk_num.group(1) if bhk_num else "2"
        clean_city = self._clean_city_name(city)

        return (
            f"https://www.magicbricks.com/property-for-rent/residential-real-estate"
            f"?bedroom={bedroom}"
            f"&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment"
            f"&cityName={quote(clean_city)}"
            f"&localityName={quote(locality)}"
            f"&pType=RENT"
        )

    async def scrape(
        self, locality: str, city: str, bhk: str = "2 BHK", limit: int = 10
    ) -> list[dict]:
        url = self._build_search_url(locality, city, bhk)
        print(f"  [magicbricks] Fetching: {url}")

        html = await self._fetch_page(url, timeout=20.0)
        if not html:
            print("  [magicbricks] No HTML returned")
            return []

        soup = BeautifulSoup(html, "lxml")
        listings: list[dict] = []

        # Strategy 1: Try JSON-LD structured data
        jsonld_listings = self._extract_from_jsonld(soup, locality, city, bhk, url)
        if jsonld_listings:
            listings.extend(jsonld_listings)
            print(f"  [magicbricks] JSON-LD extracted {len(jsonld_listings)} listings")

        # Strategy 2: Try parsing listing card HTML
        if len(listings) < limit:
            card_listings = self._extract_from_cards(soup, locality, city, bhk, url)
            # Dedupe by external_id
            existing_ids = {l["external_id"] for l in listings}
            for cl in card_listings:
                if cl["external_id"] not in existing_ids:
                    listings.append(cl)
                    existing_ids.add(cl["external_id"])
            print(f"  [magicbricks] Card HTML extracted {len(card_listings)} listings")

        # Strategy 3: Try inline script data (window.__INITIAL_STATE__, etc.)
        if len(listings) < 3:
            script_listings = self._extract_from_scripts(soup, locality, city, bhk, url)
            existing_ids = {l["external_id"] for l in listings}
            for sl in script_listings:
                if sl["external_id"] not in existing_ids:
                    listings.append(sl)
                    existing_ids.add(sl["external_id"])
            print(f"  [magicbricks] Script data extracted {len(script_listings)} listings")

        print(f"  [magicbricks] Total: {len(listings[:limit])} listings")
        return listings[:limit]

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
                # Array of Apartment objects (second JSON-LD script on MagicBricks)
                items = [d for d in data if isinstance(d, dict) and d.get("@type") in ("Apartment", "Residence", "Product", "RealEstateListing")]
            elif isinstance(data, dict):
                if data.get("@type") in ("Apartment", "Residence", "Product", "RealEstateListing"):
                    items = [data]
                elif data.get("@type") == "ItemList" and "itemListElement" in data:
                    # Skip ItemList — these only have position/url/name, no price data
                    continue
                elif "mainEntity" in data:
                    me = data["mainEntity"]
                    items = me if isinstance(me, list) else [me]

            for item in items:
                if not isinstance(item, dict):
                    continue
                listing = self._normalize_jsonld_item(item, locality, city, bhk, page_url)
                if listing:
                    results.append(listing)

        return results

    def _normalize_jsonld_item(
        self, item: dict, locality: str, city: str, bhk: str, page_url: str
    ) -> Optional[dict]:
        name = item.get("name") or item.get("item", {}).get("name") or ""
        if not name or len(name) < 3:
            return None

        # Price
        price = None
        offers = item.get("offers") or item.get("item", {}).get("offers") or {}
        if isinstance(offers, dict):
            price = self.parse_price(str(offers.get("price", "")))
        if not price:
            price = self.parse_price(str(item.get("price", "")))
        if not price:
            return None

        # Images
        images = []
        img = item.get("image")
        if isinstance(img, str):
            images = [img]
        elif isinstance(img, list):
            images = [i if isinstance(i, str) else i.get("url", "") for i in img]
        images = [u for u in images if u and u.startswith("http")]

        # URL
        listing_url = item.get("url") or page_url

        external_id = self._make_external_id(f"mb-{name}-{locality}-{bhk}")

        return {
            "external_id": external_id,
            "source_platform": "magicbricks",
            "source_url": listing_url,
            "title": name.strip()[:120],
            "apartment_name": name.strip()[:120],
            "address": f"{name}, {locality}, {city}",
            "locality": locality,
            "city": city,
            "price": price,
            "size_sqft": self.parse_sqft(str(item.get("floorSize", ""))),
            "bhk": bhk,
            "floor": None,
            "bathrooms": None,
            "balconies": None,
            "furnished_status": None,
            "images": images[:5],
            "amenities": [],
            "description": (item.get("description") or "")[:500],
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

        # MagicBricks uses various card selectors depending on page version
        card_selectors = [
            "div.mb-srp__card",
            "div[data-card]",
            "div.mb-srp__list",
            "article.srpCard",
            "div.property-card",
            "li.SRCard__container",
        ]

        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                break

        for card in cards:
            listing = self._parse_card(card, locality, city, bhk, page_url)
            if listing:
                results.append(listing)

        return results

    def _parse_card(
        self, card, locality: str, city: str, bhk: str, page_url: str
    ) -> Optional[dict]:
        # Title / Project name
        title_el = (
            card.select_one("h2") or
            card.select_one("h3") or
            card.select_one("[class*='title']") or
            card.select_one("[class*='name']") or
            card.select_one("a[title]")
        )
        title = ""
        if title_el:
            title = title_el.get_text(" ", strip=True) or title_el.get("title", "")
        if not title or len(title) < 3:
            return None

        # Price — prefer the specific amount element over the broader price container
        price_el = (
            card.select_one("[class*='price--amount']") or
            card.select_one("[class*='price']") or
            card.select_one("[class*='Price']") or
            card.select_one("[class*='rent']")
        )
        price = self.parse_price(price_el.get_text(strip=True) if price_el else "")
        if not price:
            # Try text search
            all_text = card.get_text(" ", strip=True)
            price_match = re.search(r"₹\s*([\d,]+(?:\.\d+)?(?:\s*(?:K|Lac|Lakh|Cr|Crore))?)", all_text, re.IGNORECASE)
            if price_match:
                price = self.parse_price(price_match.group(1))
        if not price:
            return None

        # Sqft
        sqft = None
        sqft_el = card.select_one("[class*='area']") or card.select_one("[class*='size']")
        if sqft_el:
            sqft = self.parse_sqft(sqft_el.get_text(strip=True))
        if not sqft:
            sqft = self.parse_sqft(card.get_text(" ", strip=True))

        # BHK from card
        card_bhk = self.parse_bhk(card.get_text(" ", strip=True)) or bhk

        # Images
        images = []
        for img in card.select("img[src], img[data-src]"):
            src = img.get("data-src") or img.get("src") or ""
            clean = self._clean_image_url(src, page_url)
            if clean:
                images.append(clean)
        images = images[:5]

        # Listing URL
        link_el = card.select_one("a[href]")
        listing_url = page_url
        if link_el:
            href = link_el.get("href", "")
            if href.startswith("http"):
                listing_url = href
            elif href.startswith("/"):
                listing_url = f"https://www.magicbricks.com{href}"

        # Furnishing
        furnished = None
        text = card.get_text(" ", strip=True)
        if "fully furnished" in text.lower():
            furnished = "Fully Furnished"
        elif "semi furnished" in text.lower() or "semi-furnished" in text.lower():
            furnished = "Semi Furnished"
        elif "unfurnished" in text.lower():
            furnished = "Unfurnished"

        external_id = self._make_external_id(f"mb-{title}-{locality}")

        return {
            "external_id": external_id,
            "source_platform": "magicbricks",
            "source_url": listing_url,
            "title": title[:120],
            "apartment_name": title[:120],
            "address": f"{title}, {locality}, {city}",
            "locality": locality,
            "city": city,
            "price": price,
            "size_sqft": sqft,
            "bhk": card_bhk,
            "floor": None,
            "bathrooms": None,
            "balconies": None,
            "furnished_status": furnished,
            "images": images,
            "amenities": [],
            "description": "",
            "listed_days_ago": 0,
            "is_fake": False,
            "fake_confidence": 0.0,
            "photo_red_flags": [],
            "legal_status": "unknown",
            "rera_registered": False,
            "rera_number": None,
        }

    # ------------------------------------------------------------------
    # Script data extraction (fallback)
    # ------------------------------------------------------------------

    def _extract_from_scripts(
        self, soup: BeautifulSoup, locality: str, city: str, bhk: str, page_url: str
    ) -> list[dict]:
        """Try to find listing data embedded in inline <script> tags."""
        results = []

        for script in soup.select("script:not([src])"):
            text = script.string or ""
            if len(text) < 200:
                continue

            # Look for JSON arrays that look like listings
            for pattern in [
                r'resultList\s*[=:]\s*(\[.*?\])\s*[;\n]',
                r'propertyList\s*[=:]\s*(\[.*?\])\s*[;\n]',
                r'searchResults\s*[=:]\s*(\[.*?\])\s*[;\n]',
                r'listings\s*[=:]\s*(\[.*?\])\s*[;\n]',
            ]:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        if isinstance(data, list):
                            for item in data[:15]:
                                if isinstance(item, dict):
                                    listing = self._normalize_script_item(item, locality, city, bhk, page_url)
                                    if listing:
                                        results.append(listing)
                    except (json.JSONDecodeError, TypeError):
                        continue

        return results

    def _normalize_script_item(
        self, item: dict, locality: str, city: str, bhk: str, page_url: str
    ) -> Optional[dict]:
        """Normalize a property object found in inline script data."""
        # Try various key names
        name = (
            item.get("projectName") or item.get("societyName") or
            item.get("name") or item.get("title") or
            item.get("propertyName") or ""
        )
        if not name or len(name) < 3:
            return None

        price = self.parse_price(str(
            item.get("price") or item.get("rent") or
            item.get("expectedRent") or item.get("formattedPrice") or ""
        ))
        if not price:
            return None

        sqft = self.parse_sqft(str(item.get("carpetArea") or item.get("superArea") or item.get("area") or ""))

        images = []
        img = item.get("imageUrl") or item.get("image") or item.get("photos") or item.get("images")
        if isinstance(img, str):
            images = [img]
        elif isinstance(img, list):
            images = [i if isinstance(i, str) else (i.get("url") or i.get("imageUrl") or "") for i in img]
        images = [u for u in images if u and u.startswith("http")][:5]

        listing_url = item.get("url") or item.get("detailUrl") or item.get("propertyUrl") or page_url
        if listing_url and not listing_url.startswith("http"):
            listing_url = f"https://www.magicbricks.com{listing_url}"

        external_id = self._make_external_id(f"mb-{name}-{locality}-{bhk}")

        return {
            "external_id": external_id,
            "source_platform": "magicbricks",
            "source_url": listing_url,
            "title": name[:120],
            "apartment_name": name[:120],
            "address": f"{name}, {locality}, {city}",
            "locality": locality,
            "city": city,
            "price": price,
            "size_sqft": sqft,
            "bhk": self.parse_bhk(str(item.get("bedrooms", ""))) or bhk,
            "floor": item.get("floor"),
            "bathrooms": item.get("bathrooms"),
            "balconies": item.get("balconies"),
            "furnished_status": item.get("furnishing") or item.get("furnishStatus"),
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
