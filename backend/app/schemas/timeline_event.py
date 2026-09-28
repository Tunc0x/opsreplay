from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GitHubWebhookEvidenceRead(BaseModel):
    kind: Literal["github_webhook"]
    webhook_delivery_id: int
    github_delivery_id: str


class AlertWebhookEvidenceRead(BaseModel):
    kind: Literal["alert_webhook"]
    alert_delivery_id: int
    external_event_id: str


class TimelineEventRead(BaseModel):
    id: int
    repository_id: int
    source: str
    event_type: str
    summary: str
    observed_at: datetime
    created_at: datetime
    evidence: GitHubWebhookEvidenceRead | AlertWebhookEvidenceRead
