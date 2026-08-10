from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from database.models.visit import Visit
from database.models.property import Property

router = APIRouter(prefix="/api/visits", tags=["Visits"])

class VisitCreate(BaseModel):
    property_id: str
    user_email: str
    date: datetime
    time_slot: str
    notes: Optional[str] = None

class VisitUpdate(BaseModel):
    status: Optional[str] = None
    date: Optional[datetime] = None
    time_slot: Optional[str] = None
    notes: Optional[str] = None

@router.post("/")
async def schedule_visit(req: VisitCreate):
    if not ObjectId.is_valid(req.property_id):
        raise HTTPException(status_code=400, detail="Invalid property ID")
        
    prop = await Property.get(ObjectId(req.property_id))
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
        
    visit = Visit(
        property=prop,
        user_email=req.user_email,
        date=req.date,
        time_slot=req.time_slot,
        notes=req.notes
    )
    await visit.insert()
    
    return {"status": "success", "message": "Visit scheduled successfully", "data": {"id": str(visit.id)}}

@router.get("/")
async def list_visits(user_email: str):
    visits = await Visit.find(Visit.user_email == user_email).sort("-date").to_list()
    
    result = []
    for v in visits:
        await v.fetch_link(Visit.property)
        prop = v.property
        result.append({
            "id": str(v.id),
            "property_id": str(prop.id) if prop else None,
            "property_title": prop.title if prop else "Unknown Property",
            "property_image": prop.images[0] if prop and prop.images else None,
            "property_price": prop.price if prop else None,
            "property_location": prop.locality if prop else None,
            "date": v.date.isoformat(),
            "time_slot": v.time_slot,
            "status": v.status,
            "notes": v.notes,
        })
        
    return {"status": "success", "data": result}

@router.patch("/{visit_id}")
async def update_visit(visit_id: str, req: VisitUpdate):
    if not ObjectId.is_valid(visit_id):
        raise HTTPException(status_code=400, detail="Invalid visit ID")
        
    visit = await Visit.get(ObjectId(visit_id))
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
        
    if req.status:
        visit.status = req.status
    if req.date:
        visit.date = req.date
    if req.time_slot:
        visit.time_slot = req.time_slot
    if req.notes:
        visit.notes = req.notes
        
    visit.updated_at = datetime.now()
    await visit.save()
    
    return {"status": "success", "message": "Visit updated successfully"}

@router.delete("/{visit_id}")
async def cancel_visit(visit_id: str):
    if not ObjectId.is_valid(visit_id):
        raise HTTPException(status_code=400, detail="Invalid visit ID")
        
    visit = await Visit.get(ObjectId(visit_id))
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
        
    visit.status = "cancelled"
    visit.updated_at = datetime.now()
    await visit.save()
    
    return {"status": "success", "message": "Visit cancelled successfully"}
