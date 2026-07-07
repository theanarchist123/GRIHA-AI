"""
Neighbourhood API Routes — Gemini-powered locality intelligence.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from services.neighbourhood_agent import NeighbourhoodAgent
from services.neighbourhood_chat_agent import NeighbourhoodChatAgent
from database.models.property import Property
from bson import ObjectId

router = APIRouter(prefix="/api/neighbourhood", tags=["Neighbourhood"])
neighbourhood_agent = NeighbourhoodAgent()
chat_agent = NeighbourhoodChatAgent()

class ChatRequest(BaseModel):
    property_id: str
    query: str

@router.post("/chat")
async def chat_with_neighbourhood(req: ChatRequest):
    """Interactive chat with map markers."""
    try:
        # Convert string to ObjectId for Beanie lookup
        prop = await Property.get(ObjectId(req.property_id))
    except Exception:
        # Fallback if property_id is not valid ObjectId
        prop = await Property.find_one(Property.external_id == req.property_id)
        
    if not prop:
        # If still not found, we can try by locality? But we need a property for exact location
        raise HTTPException(404, "Property not found")
        
    # Get address or locality to geocode
    address = prop.address if prop.address else f"{prop.locality}, {prop.city}"
    
    try:
        res = await chat_agent.chat(
            property_id=str(prop.id), 
            property_address=address, 
            property_title=prop.title, 
            query=req.query
        )
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")

@router.get("/amenities/{property_id}")
async def get_nearby_amenities(property_id: str):
    """Fetch nearby amenities for map markers."""
    try:
        # Convert string to ObjectId for Beanie lookup
        prop = await Property.get(ObjectId(property_id))
    except Exception:
        prop = await Property.find_one(Property.external_id == property_id)
        
    if not prop:
        raise HTTPException(404, "Property not found")
        
    address = prop.address if prop.address else f"{prop.locality}, {prop.city}"
    
    try:
        lat, lng = await chat_agent.geocode_address(address)
        
        categories = {
            "school": ["school", "college", "university"],
            "hospital": ["hospital", "clinic", "pharmacy"],
            "metro": ["metro station", "train station"],
            "hotel": ["hotel"],
            "supermarket": ["supermarket", "mall"]
        }
        
        all_markers = []
        for cat, terms in categories.items():
            pois = await chat_agent.fetch_nearby_places(lat, lng, terms, radius=2000)
            for poi in pois:
                poi["category"] = cat
                all_markers.append(poi)
                
        return {
            "status": "success",
            "data": {
                "center": {"lat": lat, "lng": lng, "address": address},
                "markers": all_markers
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch amenities: {str(e)}")

@router.get("/{locality}")
async def get_neighbourhood_report(
    locality: str,
    city: str = Query(default="Mumbai"),
    commute_destination: Optional[str] = Query(default=None),
    bhk: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
):
    """Fetch or generate a neighbourhood report for a locality."""
    # Normalize locality name
    clean_locality = locality.replace("-", " ").title()

    try:
        report = await neighbourhood_agent.get_or_generate_report(
            locality=clean_locality,
            city=city,
            commute_destination=commute_destination,
            bhk=bhk,
            user_id=user_id,
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to generate report: {str(e)}")

    return {
        "status": "success",
        "data": {
            "locality": report.locality,
            "city": report.city,
            "commute_data": report.commute_data,
            "amenities": report.amenities,
            "flood_risk": report.flood_risk,
            "aqi_score": report.aqi_score,
            "noise_level": report.noise_level,
            "price_trend": report.price_trend,
            "resident_sentiment": report.resident_sentiment,
            "livability_scores": report.livability_scores,
            "cached_at": report.cached_at.isoformat() if report.cached_at else None,
            "expires_at": report.expires_at.isoformat() if report.expires_at else None,
        },
    }
