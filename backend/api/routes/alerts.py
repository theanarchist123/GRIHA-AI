import re
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from database.mongo import get_db

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

class AlertItemCreate(BaseModel):
    property_id: str
    title: str
    location: str
    price: str
    image: str
    user_email: str
    whatsapp_number: Optional[str] = None
    type: str = "Price Drop"
    target_percentage: float = 10.0

class AlertUpdate(BaseModel):
    target_percentage: float

def parse_price(price_str: str) -> float:
    match = re.search(r'([\d.]+)', str(price_str))
    if match:
        val = float(match.group(1))
        # If it contains Cr, convert to L for standard comparison (1 Cr = 100 L)
        if "Cr" in str(price_str):
            val *= 100
        return val
    return 0.0

@router.post("/")
async def add_to_alerts(item: AlertItemCreate, db = Depends(get_db)):
    try:
        alerts_collection = db["alerts"]
        
        # Check if already exists for this user
        existing = await alerts_collection.find_one({"property_id": item.property_id, "user_email": item.user_email})
        if existing:
            return {"status": "success", "message": "Already watching", "data": {"id": str(existing["_id"])}}
            
        doc = item.dict()
        doc["status"] = "watching"
        
        # Store structured float prices for logic
        original_val = parse_price(item.price)
        doc["original_price_float"] = original_val
        doc["current_price_float"] = original_val
        doc["target_percentage"] = item.target_percentage
        doc["target_price_float"] = original_val * (1 - item.target_percentage / 100)
        doc["whatsapp_number"] = item.whatsapp_number
        
        # Keep formatted strings for UI
        doc["alertTarget"] = f"₹{doc['target_price_float']:.1f} L" if doc['target_price_float'] < 100 else f"₹{doc['target_price_float']/100:.2f} Cr"
        doc["saveAmount"] = f"₹{original_val * (item.target_percentage / 100):.1f} L ({item.target_percentage}%)" if (original_val * (item.target_percentage / 100)) < 100 else f"₹{(original_val * (item.target_percentage / 100))/100:.2f} Cr ({item.target_percentage}%)"
        
        result = await alerts_collection.insert_one(doc)
        return {"status": "success", "message": "Watching property", "data": {"id": str(result.inserted_id)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_alerts(user_email: str, skip: int = 0, limit: int = 100, db = Depends(get_db)):
    try:
        alerts_collection = db["alerts"]
        total = await alerts_collection.count_documents({"user_email": user_email})
        cursor = alerts_collection.find({"user_email": user_email}).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        
        results = []
        for item in items:
            results.append({
                "id": str(item["_id"]),
                "property_id": item["property_id"],
                "title": item["title"],
                "location": item["location"],
                "price": item["price"],
                "image": item["image"],
                "type": item.get("type", "3 BHK"),
                "target_percentage": item.get("target_percentage", 10.0),
                "alertTarget": item.get("alertTarget", "N/A"),
                "saveAmount": item.get("saveAmount", "N/A"),
                "status": item.get("status", "watching")
            })
            
        return {"status": "success", "data": results, "total": total, "skip": skip, "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{property_id}")
async def delete_alert(property_id: str, user_email: str, db = Depends(get_db)):
    try:
        alerts_collection = db["alerts"]
        await alerts_collection.delete_one({"property_id": property_id, "user_email": user_email})
        return {"status": "success", "message": "Alert removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{alert_id}")
async def update_alert(alert_id: str, update: AlertUpdate, user_email: str, db = Depends(get_db)):
    try:
        alerts_collection = db["alerts"]
        alert = await alerts_collection.find_one({"_id": ObjectId(alert_id), "user_email": user_email})
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        original_val = alert.get("original_price_float", parse_price(alert["price"]))
        target_price_float = original_val * (1 - update.target_percentage / 100)
        
        alertTarget = f"₹{target_price_float:.1f} L" if target_price_float < 100 else f"₹{target_price_float/100:.2f} Cr"
        saveAmount = f"₹{original_val * (update.target_percentage / 100):.1f} L ({update.target_percentage}%)" if (original_val * (update.target_percentage / 100)) < 100 else f"₹{(original_val * (update.target_percentage / 100))/100:.2f} Cr ({update.target_percentage}%)"
        
        await alerts_collection.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {
                "target_percentage": update.target_percentage,
                "target_price_float": target_price_float,
                "alertTarget": alertTarget,
                "saveAmount": saveAmount
            }}
        )
        return {"status": "success", "message": "Alert updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
