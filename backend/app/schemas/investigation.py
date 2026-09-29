from datetime import datetime

from pydantic import BaseModel

from app.schemas.timeline_event import TimelineEventRead


class InvestigationContextRead(BaseModel):
    repository_id: int
    trigger_event_id: int
    window_start: datetime
    window_end: datetime
    events: list[TimelineEventRead]
