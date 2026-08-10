from beanie import Document, Link
from pydantic import Field
from datetime import datetime, timezone
from typing import Optional
from database.models.property import Property

class Visit(Document):
    property_id: str
    property_title: str
    property_image: Optional[str] = None
    property_price: Optional[float] = None
    property_location: Optional[str] = None
    
    user_email: str
    date: datetime
    time_slot: str
    status: str = Field(default="scheduled", description="scheduled, completed, cancelled")
    notes: Optional[str] = None
    reminder_sent: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "visits"
        indexes = [
            "user_email",
            "property",
            "date"
        ]
