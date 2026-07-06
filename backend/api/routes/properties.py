import re
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from database.models.property import Property
from bson import ObjectId
from services.gemini_property_content import GeminiPropertyContentService

router = APIRouter(prefix="/api/properties", tags=["Properties"])
content_service = GeminiPropertyContentService()


def _normalize_location(location: Optional[str]) -> Optional[str]:
    if not location:
        return None
    parts = [part.strip() for part in location.split(",") if part.strip()]
    return parts[0] if parts else None


def _build_location_clause(location: Optional[str]) -> Optional[dict]:
    if not location:
        return None

    raw = location.strip()
    if not raw:
        return None

    # Use the locality (first part before comma) as the primary search term.
    # Don't split "Mumbai" or "West" individually — they're too broad.
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    locality = parts[0] if parts else raw

    or_conditions: list[dict] = []
    # Match against the locality name (most specific)
    pattern = re.escape(locality)
    for field in ("locality", "city", "address", "apartment_name"):
        or_conditions.append({field: {"$regex": pattern, "$options": "i"}})

    return {"$or": or_conditions} if or_conditions else None


def _real_listings_guard() -> list[dict]:
    return [
        {"is_fake": {"$ne": True}},
        {"external_id": {"$not": {"$regex": r"^scraped-", "$options": "i"}}},
        {"source_url": {"$not": {"$regex": r"example\\.com", "$options": "i"}}},
    ]


async def _enrich_missing_card_content(properties: list[Property], limit: int = 6) -> None:
    pending = [prop for prop in properties if not prop.ai_card_summary][:limit]
    for prop in pending:
        try:
            await content_service.enrich_property(prop)
        except Exception:
            continue

@router.get("/")
async def list_properties(
    location: Optional[str] = None,
    bhk: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
):
    query = {}
    location_clause = _build_location_clause(location)
    if location_clause:
        query.update(location_clause)
    if bhk and bhk != "Any BHK":
        query["bhk"] = {"$regex": bhk.split()[0], "$options": "i"}
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None and max_price > 0:
            price_query["$lte"] = max_price
        if price_query:
            query["price"] = price_query

    conditions = _real_listings_guard()
    if query:
        conditions.append(query)

    final_query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    properties = await Property.find(final_query).sort("-created_at").to_list()
    # Run enrichment in the background so we don't block the API response
    asyncio.create_task(_enrich_missing_card_content(properties))
    return {"status": "success", "data": properties}

@router.get("/search")
async def search_properties(
    location: Optional[str] = None,
    bhk: Optional[str] = None,
    gated: bool = False,
    pet: bool = False,
    parking: bool = False,
):
    conditions = _real_listings_guard()
    location_clause = _build_location_clause(location)
    if location_clause:
        conditions.append(location_clause)
    base_conditions = list(conditions)

    requested_bhk = bhk if bhk and bhk != "Any BHK" else None
    if bhk and bhk != "Any BHK":
        conditions.append({"bhk": {"$regex": bhk.split()[0], "$options": "i"}})

    if gated:
        conditions.append({"amenities": {"$elemMatch": {"$regex": "gated", "$options": "i"}}})
    if pet:
        conditions.append({"amenities": {"$elemMatch": {"$regex": "pet", "$options": "i"}}})
    if parking:
        conditions.append({"amenities": {"$elemMatch": {"$regex": "parking", "$options": "i"}}})

    query = {}
    if len(conditions) == 1:
        query = conditions[0]
    elif len(conditions) > 1:
        query = {"$and": conditions}

    search_query = Property.find(query).sort("-created_at")

    results = await search_query.to_list()

    fallback_applied = False
    # If no exact BHK inventory exists for the location, gracefully fallback
    # to location-level results so users still see available listings.
    if requested_bhk and not results:
        fallback_query = {}
        if len(base_conditions) == 1:
            fallback_query = base_conditions[0]
        elif len(base_conditions) > 1:
            fallback_query = {"$and": base_conditions}

        results = await Property.find(fallback_query).sort("-created_at").to_list()
        fallback_applied = True

    asyncio.create_task(_enrich_missing_card_content(results))
    return {
        "status": "success",
        "results": results,
        "meta": {
            "requested_bhk": requested_bhk,
            "fallback_applied": fallback_applied,
        },
    }

@router.get("/{property_id}")
async def get_property(property_id: str):
    if not ObjectId.is_valid(property_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    property = await Property.get(ObjectId(property_id))
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    if not property.ai_detail_overview or not property.ai_card_summary:
        asyncio.create_task(content_service.enrich_property(property))
        
    return {"status": "success", "data": property}

@router.get("/{property_id}/move-in-cost")
async def get_move_in_cost(property_id: str):
    if not ObjectId.is_valid(property_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    prop = await Property.get(ObjectId(property_id))
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
        
    city = (prop.city or "").lower()
    rent = prop.price or 0
    
    # Heuristics for Indian cities
    deposit_months = 2
    if "bangalore" in city or "bengaluru" in city:
        deposit_months = 5 # Standard BLR
    elif "mumbai" in city:
        deposit_months = 3 # Standard MUM
    
    deposit = rent * deposit_months
    brokerage = rent * 1 # Usually 1 month
    advance_rent = rent * 1 # 1st month rent
    society_transfer = 5000
    moving_painting = 8000
    
    return {
        "status": "success",
        "data": {
            "breakdown": [
                {"label": f"Security Deposit ({deposit_months} months)", "value": deposit, "type": "refundable"},
                {"label": "1st Month Rent in Advance", "value": advance_rent, "type": "rent"},
                {"label": "Brokerage (1 month)", "value": brokerage, "type": "fee"},
                {"label": "Society Move-in/Transfer Charges", "value": society_transfer, "type": "fee"},
                {"label": "Painting & Cleaning (Estimated)", "value": moving_painting, "type": "fee"}
            ],
            "total": deposit + brokerage + advance_rent + society_transfer + moving_painting,
            "deposit": deposit,
            "fees": brokerage + society_transfer + moving_painting,
            "advance_rent": advance_rent
        }
    }

import httpx

@router.get("/commute/calculate")
async def calculate_commute(origin: str, destination: str):
    """Calculate commute using Nominatim for geocoding and OSRM for routing."""
    async with httpx.AsyncClient(verify=False) as client:
        # Geocode origin
        try:
            orig_res = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": origin, "format": "json", "limit": 1},
                headers={"User-Agent": "GrihaAI/1.0"}
            )
            orig_data = orig_res.json()
            if not orig_data:
                return {"status": "error", "message": "Could not find origin location"}
            orig_lat, orig_lon = float(orig_data[0]["lat"]), float(orig_data[0]["lon"])
            
            # Geocode destination
            dest_res = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": destination, "format": "json", "limit": 1},
                headers={"User-Agent": "GrihaAI/1.0"}
            )
            dest_data = dest_res.json()
            if not dest_data:
                return {"status": "error", "message": "Could not find destination location"}
            dest_lat, dest_lon = float(dest_data[0]["lat"]), float(dest_data[0]["lon"])
            
            # Get route from OSRM
            osrm_url = f"http://router.project-osrm.org/route/v1/driving/{orig_lon},{orig_lat};{dest_lon},{dest_lat}?overview=false"
            route_res = await client.get(osrm_url)
            route_data = route_res.json()
            
            if route_data.get("code") == "Ok" and route_data.get("routes"):
                duration_sec = route_data["routes"][0]["duration"]
                distance_m = route_data["routes"][0]["distance"]
                
                # Estimate public transit (usually 1.5x driving time + walking in Indian cities)
                transit_sec = duration_sec * 1.5 + 900 # Add 15 mins walking
                
                return {
                    "status": "success",
                    "data": {
                        "driving": {
                            "duration_mins": round(duration_sec / 60),
                            "distance_km": round(distance_m / 1000, 1)
                        },
                        "transit": {
                            "duration_mins": round(transit_sec / 60)
                        }
                    }
                }
            else:
                return {"status": "error", "message": "Could not calculate route"}
                
        except Exception as e:
            print(f"Commute error: {e}")
            return {"status": "error", "message": "Error calculating commute"}

import random

@router.get("/{property_id}/reviews")
async def get_property_reviews(property_id: str):
    """Return mock community/society reviews for the property."""
    if not ObjectId.is_valid(property_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    prop = await Property.get(ObjectId(property_id))
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
        
    # Generate stable mock data based on property ID
    random.seed(property_id)
    
    score_safety = round(random.uniform(3.5, 4.9), 1)
    score_maintenance = round(random.uniform(3.0, 4.8), 1)
    score_water = round(random.uniform(3.5, 4.7), 1)
    
    total_reviews = random.randint(12, 145)
    overall_rating = round((score_safety + score_maintenance + score_water) / 3, 1)
    
    reviews = [
        {"user": "Rahul S.", "date": "2 months ago", "rating": 5, "text": "Very peaceful society, great security. Zero water cuts so far."},
        {"user": "Sneha P.", "date": "5 months ago", "rating": 4, "text": "Good amenities but visitor parking is a bit of a hassle. Maintenance team is responsive."},
        {"user": "Amit K.", "date": "8 months ago", "rating": 3, "text": "Walls are a bit thin, can hear neighbors sometimes. Otherwise okay for the rent."},
    ]
    
    random.shuffle(reviews)
    
    return {
        "status": "success",
        "data": {
            "overall_rating": overall_rating,
            "total_reviews": total_reviews,
            "categories": {
                "Safety & Security": score_safety,
                "Maintenance": score_maintenance,
                "Water & Power": score_water
            },
            "recent_reviews": reviews[:random.randint(2,3)]
        }
    }