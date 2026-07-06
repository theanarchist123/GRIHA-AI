from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database.models.autopilot import AutopilotHunt
from datetime import datetime, timezone

router = APIRouter(prefix="/api/autopilot", tags=["Autopilot"])

class CreateHuntRequest(BaseModel):
    clerk_id: str
    locations: List[str]
    bhk: str = "2 BHK"
    max_budget: int = 50000
    min_budget: int = 0
    must_have: List[str] = []
    preferred_furnishing: Optional[str] = None
    auto_legal_check: bool = True
    auto_broker_call: bool = False
    digest_email: Optional[str] = None

def _serialize_hunt(hunt: AutopilotHunt) -> dict:
    return {
        "id": str(hunt.id),
        "status": hunt.status,
        "locations": hunt.locations,
        "bhk": hunt.bhk,
        "max_budget": hunt.max_budget,
        "min_budget": hunt.min_budget,
        "total_properties_found": hunt.total_properties_found,
        "matches": [m.dict() for m in hunt.matches]
    }

@router.post("/create")
async def create_autopilot_hunt(req: CreateHuntRequest):
    existing = await AutopilotHunt.find_one(
        AutopilotHunt.clerk_id == req.clerk_id,
        AutopilotHunt.status == "active"
    )
    if existing:
        return {"status": "success", "message": "Active hunt already exists", "data": _serialize_hunt(existing)}

    hunt = AutopilotHunt(
        clerk_id=req.clerk_id,
        locations=req.locations,
        bhk=req.bhk,
        max_budget=req.max_budget,
        min_budget=req.min_budget,
        must_have=req.must_have,
        preferred_furnishing=req.preferred_furnishing,
        auto_legal_check=req.auto_legal_check,
        auto_broker_call=req.auto_broker_call,
        digest_email=req.digest_email,
        next_run_at=datetime.now(timezone.utc)
    )
    await hunt.insert()
    return {"status": "success", "data": _serialize_hunt(hunt)}

@router.get("/{clerk_id}")
async def get_autopilot_hunt(clerk_id: str):
    hunt = await AutopilotHunt.find_one(
        AutopilotHunt.clerk_id == clerk_id,
        AutopilotHunt.status.in_(["active", "paused"])
    )
    if not hunt:
        return {"status": "not_found", "data": None}
    return {"status": "success", "data": _serialize_hunt(hunt)}

@router.delete("/{hunt_id}")
async def cancel_hunt(hunt_id: str):
    from beanie import PydanticObjectId
    hunt = await AutopilotHunt.get(PydanticObjectId(hunt_id))
    if hunt:
        hunt.status = "completed"
        await hunt.save()
    return {"status": "success"}