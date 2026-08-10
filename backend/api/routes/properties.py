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
    skip: int = 0,
    limit: int = 20,
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
    total = await Property.find(final_query).count()
    properties = await Property.find(final_query).sort("-created_at").skip(skip).limit(limit).to_list()
    # Run enrichment in the background so we don't block the API response
    asyncio.create_task(_enrich_missing_card_content(properties))
    return {"status": "success", "data": properties, "total": total, "skip": skip, "limit": limit}

@router.get("/search")
async def search_properties(
    location: Optional[str] = None,
    bhk: Optional[str] = None,
    gated: bool = False,
    pet: bool = False,
    parking: bool = False,
    sort_by: str = "newest",
    furnishing: Optional[str] = None,
    min_sqft: Optional[int] = None,
    max_sqft: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
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
    if furnishing:
        conditions.append({"furnished_status": {"$regex": furnishing, "$options": "i"}})
    if min_sqft is not None or max_sqft is not None:
        sqft_query = {}
        if min_sqft is not None:
            sqft_query["$gte"] = min_sqft
        if max_sqft is not None and max_sqft > 0:
            sqft_query["$lte"] = max_sqft
        if sqft_query:
            conditions.append({"size_sqft": sqft_query})

    query = {}
    if len(conditions) == 1:
        query = conditions[0]
    elif len(conditions) > 1:
        query = {"$and": conditions}

    sort_mapping = {
        "newest": "-created_at",
        "price_asc": "+price",
        "price_desc": "-price"
    }
    sort_expr = sort_mapping.get(sort_by, "-created_at")

    total = await Property.find(query).count()
    search_query = Property.find(query).sort(sort_expr).skip(skip).limit(limit)

    results = await search_query.to_list()

    fallback_applied = False
    # If no exact BHK inventory exists for the location, gracefully fallback
    # to location-level results so users still see available listings.
    if requested_bhk and not results and skip == 0:
        fallback_query = {}
        if len(base_conditions) == 1:
            fallback_query = base_conditions[0]
        elif len(base_conditions) > 1:
            fallback_query = {"$and": base_conditions}

        total = await Property.find(fallback_query).count()
        results = await Property.find(fallback_query).sort(sort_expr).skip(skip).limit(limit).to_list()
        fallback_applied = True

    asyncio.create_task(_enrich_missing_card_content(results))
    return {
        "status": "success",
        "data": results,
        "total": total,
        "skip": skip,
        "limit": limit,
        "fallback_applied": fallback_applied
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

@router.get("/{property_id}/investment")
async def get_investment_analytics(property_id: str):
    if not ObjectId.is_valid(property_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    prop = await Property.get(ObjectId(property_id))
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
        
    rent = prop.price or 0
    # Estimate property value assuming 3% yield (typical for India residential)
    estimated_value = rent * 12 / 0.03 if rent else 0
    
    years = [1, 2, 3, 4, 5]
    appreciation_rate = 0.06 # 6% capital appreciation
    rent_increase_rate = 0.05 # 5% rental increase
    
    projected_values = [estimated_value * ((1 + appreciation_rate) ** y) for y in years]
    projected_rents = [rent * 12 * ((1 + rent_increase_rate) ** y) for y in years]
    
    return {
        "status": "success",
        "data": {
            "estimated_value": estimated_value,
            "rental_yield": 3.0,
            "annual_appreciation": appreciation_rate * 100,
            "projections": [
                {
                    "year": f"Year {y}",
                    "property_value": round(val),
                    "annual_rent": round(rnt)
                }
                for y, val, rnt in zip(years, projected_values, projected_rents)
            ]
        }
    }

from services.neighbourhood_chat_agent import NeighbourhoodChatAgent
chat_agent = NeighbourhoodChatAgent()

import httpx

@router.get("/commute/calculate")
async def calculate_commute(origin: str, destination: str):
    """Calculate commute using robust geocoding and OSRM for routing."""
    async with httpx.AsyncClient(verify=True) as client:
        # Geocode origin using our robust agent
        try:
            orig_lat, orig_lon = await chat_agent.geocode_address(origin)
            if not orig_lat or not orig_lon:
                return {"status": "error", "message": "Could not find origin location"}
        except Exception:
            return {"status": "error", "message": "Could not find origin location"}
            
        # Geocode destination using our robust agent
        try:
            dest_lat, dest_lon = await chat_agent.geocode_address(destination)
            if not dest_lat or not dest_lon:
                return {"status": "error", "message": "Could not find destination location"}
        except Exception:
            return {"status": "error", "message": "Could not find destination location"}
            
        # Get route from OSRM
        try:
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

@router.get("/{property_id}/similar")
async def get_similar_properties(property_id: str, limit: int = 3):
    if not ObjectId.is_valid(property_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    prop = await Property.get(ObjectId(property_id))
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    similar_props = []
    if prop.embedding:
        try:
            # Try Vector Search
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": prop.embedding,
                        "numCandidates": 100,
                        "limit": limit + 1
                    }
                },
                {
                    "$match": {
                        "_id": {"$ne": prop.id},
                        "is_fake": {"$ne": True}
                    }
                },
                {"$limit": limit}
            ]
            similar_props_docs = await Property.aggregate(pipeline).to_list()
            similar_props = [Property(**doc) for doc in similar_props_docs]
        except Exception as e:
            print(f"Vector search failed: {e}")
            
    # Fallback if vector search failed or no embedding
    if not similar_props:
        price_min = prop.price * 0.7
        price_max = prop.price * 1.3
        query = {
            "_id": {"$ne": prop.id},
            "is_fake": {"$ne": True},
            "locality": prop.locality,
            "price": {"$gte": price_min, "$lte": price_max}
        }
        similar_props = await Property.find(query).limit(limit).to_list()

    return {"status": "success", "data": similar_props}

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