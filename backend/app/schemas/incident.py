from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.investigation import InvestigationContextRead


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_timeline_event_id: int = Field(gt=0)
    lookback_minutes: int = Field(default=30, ge=0, le=1440)
    lookahead_minutes: int = Field(default=30, ge=0, le=1440)


class IncidentRead(BaseModel):
    id: int
    repository_id: int
    trigger_timeline_event_id: int
    lookback_minutes: int
    lookahead_minutes: int
    status: str
    resolved_at: datetime | None
    created_at: datetime
    context: InvestigationContextRead
