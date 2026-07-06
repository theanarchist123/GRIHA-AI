import re
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
    type: str = "Price Drop"

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
        doc["target_price_float"] = original_val * 0.9  # Default 10% drop target
        
        # Keep formatted strings for UI
        doc["alertTarget"] = f"₹{doc['target_price_float']:.1f} L" if doc['target_price_float'] < 100 else f"₹{doc['target_price_float']/100:.2f} Cr"
        doc["saveAmount"] = f"₹{original_val * 0.1:.1f} L (10%)" if (original_val * 0.1) < 100 else f"₹{(original_val * 0.1)/100:.2f} Cr (10%)"
        
        result = await alerts_collection.insert_one(doc)
        return {"status": "success", "message": "Watching property", "data": {"id": str(result.inserted_id)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_alerts(user_email: str, db = Depends(get_db)):
    try:
        alerts_collection = db["alerts"]
        cursor = alerts_collection.find({"user_email": user_email})
        items = await cursor.to_list(length=100)
        
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
                "alertTarget": item.get("alertTarget", "N/A"),
                "saveAmount": item.get("saveAmount", "N/A"),
                "status": item.get("status", "watching")
            })
            
        return {"status": "success", "data": results}
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
