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
    type: str = "Price Drop"

@router.post("/")
async def add_to_alerts(item: AlertItemCreate, db = Depends(get_db)):
    try:
        alerts_collection = db["alerts"]
        
        # Check if already exists
        existing = await alerts_collection.find_one({"property_id": item.property_id})
        if existing:
            return {"status": "success", "message": "Already watching", "data": {"id": str(existing["_id"])}}
            
        doc = item.dict()
        doc["status"] = "watching"
        # Dummy math for alert target and drop amount
        import re
        price_val = 0
        match = re.search(r'([\d.]+)', item.price)
        if match:
            price_val = float(match.group(1))
            
        doc["alertTarget"] = f"₹{price_val * 0.9:.1f} L" if "L" in item.price else f"₹{price_val * 0.9:.1f} Cr"
        doc["saveAmount"] = f"₹{price_val * 0.1:.1f} L (10%)" if "L" in item.price else f"₹{price_val * 0.1:.1f} Cr (10%)"
        
        result = await alerts_collection.insert_one(doc)
        return {"status": "success", "message": "Watching property", "data": {"id": str(result.inserted_id)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_alerts(db = Depends(get_db)):
    try:
        alerts_collection = db["alerts"]
        cursor = alerts_collection.find({})
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
async def delete_alert(property_id: str, db = Depends(get_db)):
    try:
        alerts_collection = db["alerts"]
        await alerts_collection.delete_one({"property_id": property_id})
        return {"status": "success", "message": "Alert removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
