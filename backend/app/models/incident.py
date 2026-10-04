from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint(
            "trigger_timeline_event_id",
            name="uq_incidents_trigger_timeline_event_id",
        ),
        CheckConstraint(
            "lookback_minutes >= 0 AND lookback_minutes <= 1440",
            name="ck_incidents_lookback_minutes_range",
        ),
        CheckConstraint(
            "lookahead_minutes >= 0 AND lookahead_minutes <= 1440",
            name="ck_incidents_lookahead_minutes_range",
        ),
        CheckConstraint(
            "status IN ('open', 'resolved')",
            name="ck_incidents_status",
        ),
        CheckConstraint(
            "(status = 'open' AND resolved_at IS NULL) OR "
            "(status = 'resolved' AND resolved_at IS NOT NULL)",
            name="ck_incidents_resolution_state",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "repositories.id",
            name="fk_incidents_repository_id_repositories",
        ),
        nullable=False,
    )
    trigger_timeline_event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "timeline_events.id",
            name=(
                "fk_incidents_trigger_timeline_event_id_"
                "timeline_events"
            ),
        ),
        nullable=False,
    )
    lookback_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    lookahead_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="open",
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
