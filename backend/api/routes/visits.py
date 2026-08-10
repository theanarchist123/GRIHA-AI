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
    property_title: str
    property_image: Optional[str] = None
    property_price: Optional[float] = None
    property_location: Optional[str] = None
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
    visit = Visit(
        property_id=req.property_id,
        property_title=req.property_title,
        property_image=req.property_image,
        property_price=req.property_price,
        property_location=req.property_location,
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
        result.append({
            "id": str(v.id),
            "property_id": v.property_id,
            "property_title": v.property_title,
            "property_image": v.property_image,
            "property_price": v.property_price,
            "property_location": v.property_location,
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
