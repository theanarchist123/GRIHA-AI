"""
BrokerCall — tracks outbound AI voice calls to property brokers.
"""
from beanie import Document
from pydantic import Field, BaseModel
from datetime import datetime
from typing import List, Optional


class CallTranscriptLine(BaseModel):
    role: str = Field(..., description="'ai' or 'broker'")
    text: str
    timestamp: float = 0  # seconds into call


class BrokerCall(Document):
    property_id: str
    clerk_id: Optional[str] = None
    broker_phone: str
    status: str = Field(default="queued", description="queued, ringing, active, completed, failed, no_answer")
    vapi_call_id: Optional[str] = None

    # Call config
    objective: str = Field(default="general_inquiry", description="general_inquiry, negotiate_rent, check_availability, schedule_visit")
    property_context: Optional[dict] = None  # bhk, locality, city, price, etc.

    # Results (populated after call)
    duration_seconds: int = 0
    transcript: List[CallTranscriptLine] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    extracted_info: Optional[dict] = None  # actual_rent, deposit, available_from, broker_name, flexibility, etc.

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Settings:
        name = "broker_calls"
        indexes = [
            "property_id",
            "clerk_id",
            "status",
        ]
