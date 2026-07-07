"""
Base scraper with shared HTTP client, User-Agent rotation, and price parsing.
All platform-specific scrapers inherit from this class.
"""

import asyncio
import hashlib
import random
import re
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    """Abstract base class for all real estate platform scrapers."""

    PLATFORM_NAME: str = "unknown"
    RATE_LIMIT_DELAY: float = 1.5  # seconds between requests to same domain

    def __init__(self):
        self._last_request_time: float = 0

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _random_ua(self) -> str:
        return random.choice(USER_AGENTS)

    def _headers(self) -> dict:
        return {
            "User-Agent": self._random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

    async def _rate_limit(self):
        """Enforce minimum delay between requests to the same domain."""
        import time
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.monotonic()

    async def _fetch_page(self, url: str, timeout: float = 15.0) -> Optional[str]:
        """Fetch HTML content from a URL with retries."""
        await self._rate_limit()

        headers = self._headers()
        # Additional anti-bot headers
        headers.update({
            "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        })

        for attempt in range(2):
            try:
                # Always bypass verify due to local cert issues
                async with httpx.AsyncClient(
                    timeout=timeout, follow_redirects=True, verify=False
                ) as client:
                    response = await client.get(url, headers=headers)
                    if response.status_code in [403, 406]:
                        print(f"  [{self.PLATFORM_NAME}] {response.status_code} Forbidden/Not Acceptable for {url}")
                        # Rotate User Agent
                        headers["User-Agent"] = self._random_ua()
                        await asyncio.sleep(2.0)
                        continue
                    
                    if response.status_code in [403, 406, 429, 404, 400]:
                        return None
                    response.raise_for_status()
                    return response.text
            except httpx.HTTPStatusError as e:
                # Only print if it's an unexpected error code
                print(f"  [{self.PLATFORM_NAME}] HTTP error {e.response.status_code} for {url}")
                return None
            except Exception as e:
                if "CERTIFICATE_VERIFY_FAILED" not in str(e):
                    if attempt == 0:
                        print(f"  [{self.PLATFORM_NAME}] Retry after error: {e}")
                        await asyncio.sleep(2.0)
                        continue
                    print(f"  [{self.PLATFORM_NAME}] Failed to fetch {url}: {e}")
                return None
        return None

    async def _fetch_page_playwright(self, url: str, timeout: float = 20.0) -> Optional[str]:
        """Fallback to Playwright if httpx is blocked (e.g. 403/406)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None

        # Run playwright in a separate thread to avoid SelectorEventLoop NotImplementedError on Windows
        def _run_playwright_sync():
            async def _do_playwright():
                try:
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        page = await browser.new_page()
                        # Block images/fonts to speed up load
                        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())
                        
                        await page.set_extra_http_headers({"User-Agent": self._random_ua()})
                        await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                        await page.wait_for_timeout(1500)
                        
                        content = await page.content()
                        await browser.close()
                        return content
                except Exception as e:
                    print(f"  [{self.PLATFORM_NAME}] Playwright fetch failed: {e}")
                    return None

            import asyncio
            import sys
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            return asyncio.run(_do_playwright())

        try:
            return await asyncio.to_thread(_run_playwright_sync)
        except Exception as e:
            print(f"  [{self.PLATFORM_NAME}] Thread fetch failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Price parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_price(price_str: str) -> Optional[float]:
        """Parse Indian price strings like '₹ 45,000', '45000', '4.5 Lac', '₹45K', '₹1.4 Lac'."""
        if not price_str:
            return None

        text = str(price_str).strip()

        # Match multiplier notations FIRST (before any cleaning)
        # Handle Lac/Lakh notation (e.g. "₹1.4 Lac", "4.5 Lakh" = 140000, 450000)
        lac_match = re.search(r"([\d,.]+)\s*(?:lac|lakh|lacs|lakhs)\b", text, re.IGNORECASE)
        if lac_match:
            try:
                return float(lac_match.group(1).replace(",", "")) * 100_000
            except ValueError:
                pass

        # Handle Cr/Crore notation
        cr_match = re.search(r"([\d,.]+)\s*(?:cr|crore|crores)\b", text, re.IGNORECASE)
        if cr_match:
            try:
                return float(cr_match.group(1).replace(",", "")) * 10_000_000
            except ValueError:
                pass

        # Handle K notation (e.g. "45K", "₹45K")
        k_match = re.search(r"([\d,.]+)\s*k\b", text, re.IGNORECASE)
        if k_match:
            try:
                return float(k_match.group(1).replace(",", "")) * 1_000
            except ValueError:
                pass

        # Plain number — remove only currency symbols, commas, and common suffixes
        cleaned = re.sub(r"[₹$,]", "", text)
        cleaned = re.sub(r"\s*/\s*(?:month|mo|pm|per\s*month)\b.*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*(?:Security\s*Deposit|SD).*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        num_match = re.search(r"[\d.]+", cleaned)
        if num_match:
            try:
                val = float(num_match.group())
                if val > 100:  # Filter out position numbers like 1, 2, 3
                    return val
            except ValueError:
                pass

        return None

    # ------------------------------------------------------------------
    # BHK parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_bhk(text: str) -> Optional[str]:
        """Extract BHK config from text like '2 BHK', '2BHK Apartment', etc."""
        if not text:
            return None
        match = re.search(r"(\d+)\s*(BHK|bhk|RK|rk)", text)
        if match:
            suffix = "RK" if match.group(2).upper() == "RK" else "BHK"
            return f"{match.group(1)} {suffix}"
        return None

    # ------------------------------------------------------------------
    # Sqft parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_sqft(text: str) -> Optional[int]:
        """Extract square footage from text like '850 sqft', '850 sq.ft.', etc."""
        if not text:
            return None
        match = re.search(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|sft)", text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                pass
        return None

    # ------------------------------------------------------------------
    # External ID generation
    # ------------------------------------------------------------------

    def _make_external_id(self, unique_key: str) -> str:
        """Generate a deterministic external_id for deduplication."""
        prefix = self.PLATFORM_NAME[:2]
        hash_part = hashlib.sha1(unique_key.encode()).hexdigest()[:20]
        return f"{prefix}-{hash_part}"

    # ------------------------------------------------------------------
    # Image helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_image_url(url: str, base_url: str = "") -> Optional[str]:
        """Clean and validate image URL."""
        if not url:
            return None
        url = url.strip()
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/") and base_url:
            url = urljoin(base_url, url)
        if not url.startswith("http"):
            return None
        # Skip tracking pixels, icons, etc.
        skip = ["logo", "icon", "favicon", "sprite", "pixel", "tracking",
                "ad.", "ads.", "banner", "badge", "avatar", "1x1", ".svg", ".gif",
                "placeholder", "noimage", "no-image", "blank"]
        low = url.lower()
        if any(s in low for s in skip):
            return None
        return url

    # ------------------------------------------------------------------
    # Slug helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(text: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "unknown").strip().lower())
        return cleaned.strip("-") or "unknown"

    @staticmethod
    def _clean_city_name(city: str) -> str:
        """Clean complex district/city names like 'Mumbai City District' -> 'Mumbai'"""
        if not city:
            return ""
        # Common suffixes returned by map APIs
        suffixes_to_remove = [
            " city district", " district", " suburban", " urban", " rural", " city"
        ]
        city_lower = city.lower()
        for suffix in suffixes_to_remove:
            if city_lower.endswith(suffix):
                city_lower = city_lower[: -len(suffix)].strip()

        # Specific canonicalizations
        if city_lower in ["bengaluru", "bangaluru"]:
            city_lower = "bangalore"
        if city_lower in ["gurugram"]:
            city_lower = "gurgaon"
        
        return city_lower.title()

    # ------------------------------------------------------------------
    # Abstract method
    # ------------------------------------------------------------------

    @abstractmethod
    async def scrape(
        self, locality: str, city: str, bhk: str = "2 BHK", limit: int = 10
    ) -> list[dict]:
        """
        Scrape real property listings from this platform.

        Args:
            locality: e.g. "Bandra West"
            city: e.g. "Mumbai"
            bhk: e.g. "2 BHK"
            limit: max listings to return

        Returns:
            List of normalized property dicts ready for MongoDB insertion.
        """
        ...
