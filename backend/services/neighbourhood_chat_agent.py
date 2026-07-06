import json
import math
import traceback
import asyncio
from typing import List, Dict, Any, Tuple

import httpx
from config import settings

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000  # returns meters

OLLAMA_API_KEY = "308b136d86a3491d98b0d7332865bf42.naSRy7f_Xvvz7MMWykJi5gM6"

class NeighbourhoodChatAgent:
    def __init__(self):
        self.model = "nemotron-3-nano:30b"

    async def _ollama_generate(self, prompt: str, format_json: bool = False) -> str:
        """Helper to call Ollama Cloud API."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        if format_json:
            payload["format"] = "json"
            
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                "https://ollama.com/api/chat",
                json=payload,
                headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
                timeout=60.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def geocode_address(self, address: str) -> Tuple[float, float]:
        """Fetch lat/lng for a property address using Nominatim OpenStreetMap."""
        # Simple fallback for Mumbai coordinates if geocoding fails
        fallback = (19.0760, 72.8777)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "GrihaAI/1.0"}
        try:
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.get(url, params=params, headers=headers, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                if data and len(data) > 0:
                    return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception as e:
            print(f"[Geocode Error] {e}")
            
        # Try a simpler address (locality + city)
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if len(parts) >= 2:
            simpler_address = f"{parts[-2]}, {parts[-1]}"
            params["q"] = simpler_address
            try:
                async with httpx.AsyncClient(verify=False) as client:
                    resp = await client.get(url, params=params, headers=headers, timeout=10.0)
                    resp.raise_for_status()
                    data = resp.json()
                    if data and len(data) > 0:
                        return float(data[0]["lat"]), float(data[0]["lon"])
            except Exception:
                pass

        return fallback

    async def extract_search_terms(self, query: str) -> List[str]:
        """Uses Ollama to convert a user question into place search terms."""
        prompt = f"""
You are converting a user's question about a neighbourhood into search terms for finding nearby places.
User Query: "{query}"

What kind of places is the user looking for?
Return ONLY a valid JSON array of simple search term strings.
Examples:
- "where is the nearest supermarket" -> ["supermarket"]
- "hospitals nearby" -> ["hospital", "clinic"]
- "parks and gardens" -> ["park", "garden"]
- "metro station" -> ["metro station", "railway station"]
- "schools" -> ["school"]
- "restaurants and cafes" -> ["restaurant", "cafe"]

Return ONLY the JSON array, no markdown, no explanation.
        """
        try:
            raw = await self._ollama_generate(prompt, format_json=True)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            terms = json.loads(raw)
            if isinstance(terms, list):
                return [str(t) for t in terms]
        except Exception as e:
            print(f"[Search Term Extract Error] {e}")
        return ["supermarket"]  # default fallback

    async def fetch_nearby_places(self, lat: float, lng: float, search_terms: List[str], radius: int = 1500) -> List[Dict]:
        """Fetch POIs using Nominatim search API (much more reliable than Overpass)."""
        offset = radius / 111000.0
        south, north = lat - offset, lat + offset
        west, east = lng - offset, lng + offset

        all_results = []
        async with httpx.AsyncClient(verify=False) as client:
            for term in search_terms:
                try:
                    resp = await client.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={
                            "q": term,
                            "format": "json",
                            "limit": 5,
                            "viewbox": f"{west},{north},{east},{south}",
                            "bounded": 1,
                        },
                        headers={"User-Agent": "GrihaAI/1.0 (contact@griha.ai)"},
                        timeout=10.0
                    )
                    resp.raise_for_status()
                    places = resp.json()
                    
                    for place in places:
                        pt_lat = float(place.get("lat", 0))
                        pt_lng = float(place.get("lon", 0))
                        if not pt_lat or not pt_lng:
                            continue
                        
                        display = place.get("display_name", "Unnamed")
                        name = display.split(",")[0].strip()  # First part is the place name
                        distance_m = int(haversine(lat, lng, pt_lat, pt_lng))
                        
                        all_results.append({
                            "name": name,
                            "lat": pt_lat,
                            "lng": pt_lng,
                            "distance_m": distance_m,
                            "tags": {"type": term}
                        })
                    
                    # Nominatim rate limit: 1 request per second
                    await asyncio.sleep(1.1)
                    
                except Exception as e:
                    print(f"[Nominatim Search Error] {term}: {e}")
                    continue

        # Sort by distance
        all_results.sort(key=lambda x: x["distance_m"])

        # Deduplicate by name
        seen = set()
        filtered = []
        for r in all_results:
            if r["name"] not in seen:
                seen.add(r["name"])
                filtered.append(r)

        return filtered[:10]

    async def chat(self, property_id: str, property_address: str, property_title: str, query: str) -> Dict[str, Any]:
        """Full pipeline: Geocode -> Extract Intent -> Nominatim Search -> Ollama Format."""
        lat, lng = await self.geocode_address(property_address)
        
        search_terms = await self.extract_search_terms(query)
        pois = await self.fetch_nearby_places(lat, lng, search_terms)
        
        # Format a conversational response
        poi_summary = ""
        for p in pois:
            poi_summary += f"- {p['name']} (Distance: {p['distance_m']}m)\n"
            
        prompt = f"""
You are a helpful real estate assistant (Griha AI).
The user asked: "{query}" about the property at "{property_title}" ({property_address}).

I searched the map and found these nearby places:
{poi_summary if poi_summary else "None found within 3km."}

Respond to the user naturally and concisely. Highlight the closest or most relevant options.
If no places were found, politely state that. Don't mention OpenStreetMap or Overpass API.

Limit response to 2-3 short paragraphs.
"""
        try:
            answer = await self._ollama_generate(prompt)
        except Exception as e:
            print(f"[Ollama Chat Error] {e}")
            answer = f"I found {len(pois)} places nearby based on your query."
            
        return {
            "answer": answer,
            "property_center": {"lat": lat, "lng": lng, "address": property_address},
            "markers": pois
        }
