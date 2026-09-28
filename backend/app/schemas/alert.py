from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AlertPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_id: int = Field(gt=0)
    severity: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=500)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value
