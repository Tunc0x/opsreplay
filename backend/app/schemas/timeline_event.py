from datetime import datetime

from pydantic import BaseModel


class TimelineEvidenceRead(BaseModel):
    webhook_delivery_id: int
    github_delivery_id: str


class TimelineEventRead(BaseModel):
    id: int
    repository_id: int
    source: str
    event_type: str
    summary: str
    observed_at: datetime
    created_at: datetime
    evidence: TimelineEvidenceRead
