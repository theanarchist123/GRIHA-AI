from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from database.models.notification import Notification

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

def _serialize_notification(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "priority": n.priority,
        "read": n.read,
        "action_url": n.action_url,
        "created_at": n.created_at.isoformat()
    }

@router.get("/")
async def get_notifications(clerk_id: str, unread_only: bool = False, limit: int = 50):
    query = {"clerk_id": clerk_id}
    if unread_only:
        query["read"] = False
        
    notifications = await Notification.find(query).sort("-created_at").limit(limit).to_list()
    return {"status": "success", "data": [_serialize_notification(n) for n in notifications]}

@router.get("/unread-count")
async def get_unread_count(clerk_id: str):
    count = await Notification.find({"clerk_id": clerk_id, "read": False}).count()
    return {"status": "success", "data": {"count": count}}

@router.patch("/{notif_id}/read")
async def mark_read(notif_id: str):
    from beanie import PydanticObjectId
    notif = await Notification.get(PydanticObjectId(notif_id))
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notif.read = True
    await notif.save()
    return {"status": "success", "data": _serialize_notification(notif)}

@router.post("/read-all")
async def mark_all_read(clerk_id: str):
    await Notification.find({"clerk_id": clerk_id, "read": False}).update({"$set": {"read": True}})
    return {"status": "success"}

@router.delete("/clear-all")
async def clear_all(clerk_id: str):
    await Notification.find({"clerk_id": clerk_id}).delete()
    return {"status": "success"}
