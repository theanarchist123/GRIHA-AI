"""
Live web scraper agent for Griha AI.

Architecture (v2 — Real Listings):
1. Run all 4 platform scrapers in PARALLEL:
   - MagicBricks (HTML scraping)
   - 99acres (HTML scraping)
   - NoBroker (embedded state + API + Playwright fallback)
   - Housing.com (Next.js data + HTML scraping)
2. Merge and deduplicate results across platforms
3. Save to MongoDB and stream to frontend via WebSocket
4. FALLBACK: DuckDuckGo search + Gemini extraction (only if all scrapers return 0)
"""

import asyncio
import hashlib
import json
import random
import re
from typing import Any, Optional
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import WebSocket

from database.models.property import Property
from services.scrapers import (
    MagicBricksScraper,
    NinetyNineAcresScraper,
    NoBrokerScraper,
    HousingScraper,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROPERTY_DOMAINS = (
    "magicbricks.com",
    "99acres.com",
    "nobroker.in",
    "housing.com",
    "commonfloor.com",
    "proptiger.com",
    "squareyards.com",
)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
]


class ScraperAgent:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

        # Initialize all platform scrapers
        self.scrapers = {
            "magicbricks": MagicBricksScraper(),
            "99acres": NinetyNineAcresScraper(),
            "nobroker": NoBrokerScraper(),
            "housing": HousingScraper(),
        }

    # ------------------------------------------------------------------
    # WebSocket helpers
    # ------------------------------------------------------------------

    async def send_update(self, progress: int, status: str, found_count: int = 0, new_property: dict = None):
        try:
            msg: dict = {
                "progress": progress,
                "status": status,
                "found_count": found_count,
            }
            if new_property is not None:
                msg["new_property"] = new_property
            await self.websocket.send_text(json.dumps(msg))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    def _extract_location_parts(self, location: str) -> tuple[str, str]:
        parts = [p.strip() for p in (location or "").split(",") if p.strip()]
        locality = parts[0] if parts else "Unknown Locality"
        city = parts[1] if len(parts) > 1 else (parts[0] if parts else "Mumbai")
        return locality, city

    def _extract_platform(self, source_url: str) -> str:
        host = (urlparse(source_url).netloc or "").lower()
        for domain in PROPERTY_DOMAINS:
            short = domain.split(".")[0]
            if short in host:
                return short
        return "web"

    # ------------------------------------------------------------------
    # MAIN SCRAPING WORKFLOW
    # ------------------------------------------------------------------

    async def _persist_properties(self, location: str, bhk: str) -> list[Property]:
        locality, city = self._extract_location_parts(location)
        fallback_bhk = bhk if bhk and bhk != "Any BHK" else "2 BHK"

        saved_properties: list[Property] = []

        # ================================================================
        # PHASE 1: Run all scrapers in PARALLEL
        # ================================================================
        await self.send_update(
            10,
            f"🔍 Searching MagicBricks, 99acres, NoBroker & Housing.com for {fallback_bhk} in {locality}, {city}...",
            0,
        )

        print(f"\n  [scraper] Starting parallel scrape for {fallback_bhk} in {locality}, {city}...")

        # Run all scrapers concurrently with individual timeouts
        async def _run_scraper(name: str, scraper):
            try:
                results = await asyncio.wait_for(
                    scraper.scrape(locality, city, fallback_bhk, limit=10),
                    timeout=30.0,
                )
                print(f"  [scraper] {name} returned {len(results)} listings")
                return results
            except asyncio.TimeoutError:
                print(f"  [scraper] {name} timed out")
                return []
            except Exception as e:
                print(f"  [scraper] {name} error: {e}")
                return []

        tasks = {
            name: asyncio.create_task(_run_scraper(name, scraper))
            for name, scraper in self.scrapers.items()
        }

        # Wait for all to complete
        all_results = {}
        for name, task in tasks.items():
            all_results[name] = await task

        # Merge all results
        all_listings: list[dict] = []
        seen_ids: set[str] = set()
        seen_names: set[str] = set()

        platform_counts = {}
        for platform_name, listings in all_results.items():
            count = 0
            for listing in listings:
                ext_id = listing.get("external_id", "")
                name_key = (listing.get("title", "").lower().strip(), listing.get("locality", "").lower())

                # Deduplicate by external_id AND by (title, locality)
                if ext_id in seen_ids or name_key in seen_names:
                    continue

                seen_ids.add(ext_id)
                seen_names.add(name_key)
                all_listings.append(listing)
                count += 1

            platform_counts[platform_name] = count

        total_found = len(all_listings)
        platform_summary = ", ".join(f"{name}: {count}" for name, count in platform_counts.items() if count > 0)

        print(f"  [scraper] Merged total: {total_found} unique listings ({platform_summary})")

        if total_found > 0:
            await self.send_update(
                40,
                f"✅ Found {total_found} real listings ({platform_summary}). Saving to database...",
                total_found,
            )
        else:
            await self.send_update(
                35,
                f"⚠️ No listings found on any platform. Trying web search fallback...",
                0,
            )

        # ================================================================
        # PHASE 2: Save all listings to MongoDB
        # ================================================================
        for idx, listing in enumerate(all_listings):
            pct = 40 + int((idx / max(total_found, 1)) * 45)

            try:
                external_id = listing["external_id"]
                existing = await Property.find_one(Property.external_id == external_id)

                if existing:
                    # Update existing
                    for key, value in listing.items():
                        if key != "external_id" and value is not None:
                            setattr(existing, key, value)
                    await existing.save()
                    saved_prop = existing
                    saved_properties.append(existing)
                else:
                    # Create new
                    new_prop = Property(**listing)
                    await new_prop.insert()
                    saved_prop = new_prop
                    saved_properties.append(new_prop)

                # Stream to frontend
                prop_id = str(saved_prop.id) if saved_prop.id else external_id
                await self.send_update(
                    pct,
                    f"✅ Saved: {listing['title']} ({listing['source_platform']})",
                    len(saved_properties),
                    new_property={
                        "id": prop_id,
                        "_id": prop_id,
                        "external_id": external_id,
                        "apartment_name": listing.get("apartment_name"),
                        "title": listing.get("title"),
                        "address": listing.get("address"),
                        "locality": listing.get("locality"),
                        "city": listing.get("city"),
                        "price": listing.get("price"),
                        "size_sqft": listing.get("size_sqft"),
                        "bhk": listing.get("bhk"),
                        "floor": listing.get("floor"),
                        "bathrooms": listing.get("bathrooms"),
                        "balconies": listing.get("balconies"),
                        "furnished_status": listing.get("furnished_status"),
                        "images": listing.get("images", []),
                        "amenities": listing.get("amenities", []),
                        "description": listing.get("description", ""),
                        "source_platform": listing.get("source_platform"),
                        "source_url": listing.get("source_url"),
                        "legal_status": "unknown",
                        "is_fake": False,
                        "listed_days_ago": 0,
                    },
                )

                print(f"    [saved] {listing['title']} — ₹{listing['price']:,.0f}/mo ({listing['source_platform']})")

            except Exception as e:
                print(f"    [error] Failed to save {listing.get('title', '?')}: {e}")
                continue

        # ================================================================
        # PHASE 3: DDG web search fallback (only if we got 0 from all scrapers)
        # ================================================================
        if len(saved_properties) < 3:
            await self.send_update(
                85,
                f"🌐 Trying web search for more listings in {locality}...",
                len(saved_properties),
            )

            try:
                ddg_query = f"{fallback_bhk} flat for rent in {locality} {city}"
                ddg_results = await self._ddg_search(ddg_query)
                print(f"  [phase3] DDG returned {len(ddg_results)} results")

                for item in ddg_results[:5]:
                    try:
                        html = await self._fetch_page(item["url"])
                        if not html:
                            continue
                        soup = BeautifulSoup(html, "lxml")

                        # Try to extract basic info from the page
                        title = soup.title.get_text(" ", strip=True) if soup.title else ""
                        if not title or len(title) < 5:
                            continue

                        # Look for price in the page
                        page_text = soup.get_text(" ", strip=True)[:3000]
                        price_match = re.search(r"₹\s*([\d,]+(?:\.\d+)?(?:\s*(?:K|Lac|Lakh))?)", page_text, re.IGNORECASE)
                        if not price_match:
                            continue

                        from services.scrapers.base_scraper import BaseScraper
                        price = BaseScraper.parse_price(price_match.group(1))
                        if not price:
                            continue

                        # Extract images
                        images = []
                        for img in soup.select("img[src]")[:5]:
                            src = img.get("src", "")
                            if src.startswith("http") and not any(s in src.lower() for s in ["logo", "icon", "pixel"]):
                                images.append(src)

                        ext_id = f"ddg-{hashlib.sha1(item['url'].encode()).hexdigest()[:18]}"

                        existing = await Property.find_one(Property.external_id == ext_id)
                        if not existing:
                            platform = self._extract_platform(item["url"])
                            new_prop = Property(
                                external_id=ext_id,
                                source_platform=platform,
                                source_url=item["url"],
                                title=title[:120],
                                apartment_name=title[:120],
                                address=f"{locality}, {city}",
                                locality=locality,
                                city=city,
                                price=price,
                                bhk=fallback_bhk,
                                images=images[:3],
                                is_fake=False,
                            )
                            await new_prop.insert()
                            saved_properties.append(new_prop)

                    except Exception:
                        continue
                    await asyncio.sleep(0.3)

            except Exception as e:
                print(f"  [phase3] DDG search failed: {e}")

        return saved_properties

    # ------------------------------------------------------------------
    # DDG Search fallback
    # ------------------------------------------------------------------

    async def _ddg_search(self, query: str) -> list[dict]:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://html.duckduckgo.com",
            "Referer": "https://html.duckduckgo.com/",
        }

        for attempt in range(2):
            try:
                verify = attempt == 0
                async with httpx.AsyncClient(
                    timeout=12.0, follow_redirects=True, verify=verify
                ) as client:
                    response = await client.post(url, data={"q": query, "b": ""}, headers=headers)
                    response.raise_for_status()
                    text = response.text
                    if "please try again" in text.lower() or "robot" in text.lower():
                        await asyncio.sleep(1.5)
                        continue
                    return self._parse_ddg_results(text)
            except Exception:
                await asyncio.sleep(0.8)
                continue
        return []

    def _parse_ddg_results(self, html: str) -> list[dict]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        rows: list[dict] = []
        seen: set[str] = set()

        for anchor in soup.select("a[href]"):
            href = anchor.get("href") or ""
            if not href:
                continue
            parsed = urlparse(href)
            if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.startswith("/l/"):
                target = parse_qs(parsed.query).get("uddg", [None])[0]
                if target:
                    href = unquote(target)

            host = (urlparse(href).netloc or "").lower()
            if not any(d in host for d in PROPERTY_DOMAINS):
                continue
            if href in seen:
                continue
            title = anchor.get_text(" ", strip=True)
            if len(title) < 5:
                continue
            rows.append({"title": title, "url": href, "snippet": ""})
            seen.add(href)
            if len(rows) >= 8:
                break
        return rows

    # ------------------------------------------------------------------
    # HTTP helper for DDG fallback
    # ------------------------------------------------------------------

    async def _fetch_page(self, url: str, timeout: float = 12.0) -> Optional[str]:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        }
        for attempt in range(2):
            try:
                verify = attempt == 0
                async with httpx.AsyncClient(
                    timeout=timeout, follow_redirects=True, headers=headers, verify=verify
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.text
            except Exception:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                return None
        return None

    # ------------------------------------------------------------------
    # Main workflow
    # ------------------------------------------------------------------

    async def run_scrape_workflow(self, location: str, bhk: str):
        await self.send_update(5, f"🚀 Starting live property search for {bhk} in {location}...")
        await asyncio.sleep(0.3)

        try:
            live_records = await self._persist_properties(location, bhk)
            live_saved = len(live_records)

            if live_saved > 0:
                # Try AI enrichment in background (non-blocking)
                try:
                    from services.gemini_property_content import GeminiPropertyContentService
                    content_service = GeminiPropertyContentService()
                    asyncio.create_task(content_service.enrich_recent(live_records))
                except Exception:
                    pass

                await asyncio.sleep(0.3)
                await self.send_update(
                    100,
                    f"✅ Done! {live_saved} real properties from MagicBricks, 99acres, NoBroker & Housing.com ready on your dashboard.",
                    live_saved,
                )
            else:
                await self.send_update(
                    100,
                    "⚠️ Could not find listings. Try a different locality (e.g., 'Bandra West, Mumbai').",
                    0,
                )

        except Exception as exc:
            print(f"  [error] Scraping workflow failed: {exc}")
            await self.send_update(
                100,
                f"❌ Error: {str(exc)[:100]}. Please retry.",
                0,
            )
