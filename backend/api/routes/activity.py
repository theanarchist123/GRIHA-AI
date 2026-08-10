"""
Activity Feed API Routes — Real activity log from MongoDB.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from database.mongo import get_db
from database.models.activity_log import ActivityLog

router = APIRouter(prefix="/api/activity", tags=["Activity"])


@router.get("/")
async def get_activity_feed(
    clerk_id: Optional[str] = Query(default=None),
    type_filter: Optional[str] = Query(default=None),
    limit: int = Query(default=30, le=100),
    skip: int = Query(default=0),
    db = Depends(get_db)
):
    """Fetch the activity feed, optionally filtered by user and type."""
    query_filters = []

    if clerk_id:
        # Include user-specific and system activities
        query_filters.append(
            {"$or": [{"user_id": clerk_id}, {"user_id": None}]}
        )
    
    if type_filter and type_filter != "all":
        query_filters.append({"type": type_filter})

    if query_filters:
        raw_query = {"$and": query_filters}
    else:
        raw_query = {}

    activity_logs = db["activity_logs"]
    total = await activity_logs.count_documents(raw_query)
    cursor = activity_logs.find(raw_query).sort("created_at", -1).skip(skip).limit(limit)
    activities = await cursor.to_list(length=limit)

    result = []
    for act in activities:
        result.append({
            "id": str(act["_id"]),
            "type": act.get("type"),
            "text": act.get("text"),
            "property_name": act.get("property_name"),
            "property_id": act.get("property_id"),
            "action_label": act.get("action_label"),
            "action_href": act.get("action_href"),
            "timestamp": _relative_time(act.get("created_at")),
            "created_at": act.get("created_at").isoformat() if act.get("created_at") else None,
        })

    return {"status": "success", "data": result, "total": total, "skip": skip, "limit": limit}


def _relative_time(dt) -> str:
    """Convert datetime to relative time string."""
    from datetime import datetime, timezone
    if not dt:
        return "Just now"
    
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} min{'s' if mins > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hr{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return dt.strftime("%b %d, %Y")
