from beanie import Document
from pydantic import Field, BaseModel
from datetime import datetime
from typing import List, Optional

class AutopilotMatch(BaseModel):
    property_id: str
    match_score: float
    found_at: datetime = Field(default_factory=datetime.utcnow)
    legal_checked: bool = False
    legal_status: Optional[str] = None
    broker_called: bool = False
    broker_call_id: Optional[str] = None
    visit_scheduled: bool = False

class AutopilotRun(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    properties_scraped: int = 0
    new_matches: int = 0
    legal_checks_run: int = 0
    broker_calls_made: int = 0
    status: str = "running"
    error: Optional[str] = None

class AutopilotHunt(Document):
    clerk_id: str
    status: str = Field(default="active", description="active, paused, completed, exhausted")

    locations: List[str] = Field(default_factory=list)
    bhk: str = "2 BHK"
    max_budget: int = 50000
    min_budget: int = 0
    must_have: List[str] = Field(default_factory=list)
    preferred_furnishing: Optional[str] = None
    auto_legal_check: bool = True
    auto_broker_call: bool = False
    auto_schedule_visit: bool = False

    matches: List[AutopilotMatch] = Field(default_factory=list)
    runs: List[AutopilotRun] = Field(default_factory=list)
    total_properties_found: int = 0
    total_runs: int = 0

    interval_hours: int = Field(default=2)
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None

    digest_email: Optional[str] = None