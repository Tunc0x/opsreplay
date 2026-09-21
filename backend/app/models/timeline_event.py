from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    __table_args__ = (
        UniqueConstraint(
            "webhook_delivery_id",
            name="uq_timeline_events_webhook_delivery_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "repositories.id",
            name="fk_timeline_events_repository_id_repositories",
        ),
        nullable=False,
    )
    webhook_delivery_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "webhook_deliveries.id",
            name=(
                "fk_timeline_events_webhook_delivery_id_"
                "webhook_deliveries"
            ),
        ),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
