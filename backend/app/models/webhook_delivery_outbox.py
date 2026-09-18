from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Outbox row contains reminders: deliveries that still need to go to SQS
# And published_at tells us whether that reminder has already been handled.
# published_at = timestamp
# → successfully sent to SQS
class WebhookDeliveryOutbox(Base):
    __tablename__ = "webhook_delivery_outbox"
    __table_args__ = (
        UniqueConstraint(
            "webhook_delivery_id",
            name="uq_webhook_delivery_outbox_webhook_delivery_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    webhook_delivery_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "webhook_deliveries.id",
            name="fk_webhook_delivery_outbox_delivery_id_webhook_deliveries",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
