from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "external_event_id",
            name="uq_alert_deliveries_external_event_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    repository_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "repositories.id",
            name="fk_alert_deliveries_repository_id_repositories",
        ),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    payload_body: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
