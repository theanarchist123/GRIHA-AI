from beanie import Document
from pydantic import Field
from datetime import datetime, timezone
from typing import Optional

class Notification(Document):
    clerk_id: str
    type: str = Field(description="price_drop, visit_reminder, match_found, legal_complete, negotiation_update")
    title: str
    message: str
    priority: str = Field(default="normal", description="low, normal, high")
    read: bool = Field(default=False)
    action_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "notifications"
