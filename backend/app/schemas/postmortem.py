from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.timeline_event import TimelineEventRead


class GroundedStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    evidence_event_ids: list[Annotated[int, Field(gt=0)]] = Field(
        min_length=1
    )

# summary tells what the incident was about overall
# timeline tells what happend, in order
class PostmortemDraftContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: list[GroundedStatement] = Field(min_length=1)
    timeline: list[GroundedStatement] = Field(min_length=1)
    impact: GroundedStatement | None
    root_cause: GroundedStatement | None
    resolution: GroundedStatement | None
    unknowns: list[Annotated[str, Field(min_length=1)]]


class PostmortemDraftRead(BaseModel):
    incident_id: int
    model: str
    draft: PostmortemDraftContent
    evidence: list[TimelineEventRead]
