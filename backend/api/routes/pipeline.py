from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from database.mongo import get_db

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])

class PipelineItemCreate(BaseModel):
    property_id: str
    title: str
    location: str
    price: str
    image: str
    status: str = "shortlisted"
    user_email: str = "guest@example.com"

class PipelineItemUpdate(BaseModel):
    status: str

@router.post("/")
async def add_to_pipeline(item: PipelineItemCreate, db = Depends(get_db)):
    try:
        pipeline_collection = db["pipeline"]
        
        # Check if already exists for this user
        existing = await pipeline_collection.find_one({"property_id": item.property_id, "user_email": item.user_email})
        if existing:
            return {"status": "success", "message": "Already in pipeline", "data": {"id": str(existing["_id"])}}
            
        doc = item.dict()
        doc["aiAction"] = "Added to pipeline"
        
        result = await pipeline_collection.insert_one(doc)
        return {"status": "success", "message": "Added to pipeline", "data": {"id": str(result.inserted_id)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_pipeline(user_email: Optional[str] = None, db = Depends(get_db)):
    try:
        pipeline_collection = db["pipeline"]
        query = {"user_email": user_email} if user_email else {}
        cursor = pipeline_collection.find(query)
        items = await cursor.to_list(length=100)
        
        # Group by status
        result = {
            "shortlisted": [],
            "underReview": [],
            "negotiating": [],
            "offerMade": []
        }
        
        for item in items:
            status = item.get("status", "shortlisted")
            # Map back to camelCase columns
            if status == "under_review": status = "underReview"
            if status == "offer_made": status = "offerMade"
            
            # Default to shortlisted if unknown
            if status not in result:
                status = "shortlisted"
                
            result[status].append({
                "id": str(item["_id"]),
                "property_id": item["property_id"],
                "title": item["title"],
                "location": item["location"],
                "price": item["price"],
                "image": item["image"],
                "aiAction": item.get("aiAction", "")
            })
            
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{item_id}")
async def update_pipeline_status(item_id: str, update: PipelineItemUpdate, db = Depends(get_db)):
    try:
        from bson import ObjectId
        pipeline_collection = db["pipeline"]
        
        status = update.status
        # Handle camelCase from frontend
        if status == "underReview": status = "under_review"
        if status == "offerMade": status = "offer_made"
        
        result = await pipeline_collection.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"status": status}}
        )
        
        if result.modified_count == 0:
            # Maybe it wasn't modified or didn't exist
            pass
            
        return {"status": "success", "message": "Status updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
