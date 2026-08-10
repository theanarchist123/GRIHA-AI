from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from database.models.search_profile import SearchProfile
from database.models.user import User
import json
from google import genai
from config import settings

router = APIRouter(prefix="/api/search", tags=["Search"])

class ProfileCreateRequest(BaseModel):
    clerk_id: str
    user_status: str
    property_type: str
    budget_min: int
    budget_max: int
    locations: List[str]
    bhk: List[int]
    timeline: str
    purpose: str
    must_haves: List[str] = []
    deal_breakers: List[str] = []
    amenities: Dict[str, Any] = {}
    ai_summary: Optional[str] = None

@router.post("/profile")
async def save_search_profile(req: ProfileCreateRequest):
    user = await User.find_one(User.clerk_id == req.clerk_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not synced yet. Please sync first.")

    # Deactivate existing active profile
    active_profile = await SearchProfile.find_one(SearchProfile.user_id == user.id, SearchProfile.is_active == True)
    if active_profile:
        active_profile.is_active = False
        await active_profile.save()

    new_profile = SearchProfile(
        user_id=user.id,
        user_status=req.user_status,
        property_type=req.property_type,
        budget={"min": req.budget_min, "max": req.budget_max},
        locations=req.locations,
        bhk=req.bhk,
        timeline=req.timeline,
        purpose=req.purpose,
        must_haves=req.must_haves,
        deal_breakers=req.deal_breakers,
        amenities=req.amenities,
        ai_summary=req.ai_summary,
        is_active=True
    )
    
    await new_profile.insert()
    
    user.onboarding_completed = True
    await user.save()

    return {"status": "success", "message": "Search profile saved", "profile_id": str(new_profile.id)}

class NaturalSearchRequest(BaseModel):
    query: str

@router.post("/natural")
async def natural_language_search(req: NaturalSearchRequest):
    """Parses a natural language query into structured search filters."""
    prompt = f"""
You are an AI assistant for a real estate app (Griha AI) in India.
Extract search filters from the following natural language query: "{req.query}"

Return a JSON object with the following keys (use null/empty if not specified):
- locations: list of strings (e.g. ["Bandra West", "Powai"])
- min_budget: integer (e.g. 50000)
- max_budget: integer (e.g. 150000). (Translate phrases like "under 1.5L" to 150000, "1.5 lakhs" to 150000)
- bhk: string (e.g. "1 BHK", "2 BHK", "3 BHK", "4 BHK")
- property_type: string (e.g. "apartment", "villa", "independent house")
- amenities: list of strings (e.g. ["Gymnasium", "Swimming Pool", "Security"])

Respond ONLY with valid JSON. Do not include markdown formatting or backticks.
"""
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        # Clean up possible markdown
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        parsed_filters = json.loads(text.strip())
        return {"status": "success", "data": parsed_filters}
    except Exception as e:
        print(f"[Search API] Failed to parse natural query: {e}")
        # Fallback to empty if AI fails
        return {"status": "success", "data": {
            "locations": [],
            "min_budget": None,
            "max_budget": None,
            "bhk": None,
            "property_type": None,
            "amenities": []
        }}