from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PostmortemDraftEvidence(Base):
    __tablename__ = "postmortem_draft_evidence"
    __table_args__ = (
        UniqueConstraint(
            "postmortem_draft_id",
            "position",
            name="uq_postmortem_draft_evidence_draft_position",
        ),
    )

    postmortem_draft_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "postmortem_drafts.id",
            name=(
                "fk_postmortem_draft_evidence_draft_id_"
                "postmortem_drafts"
            ),
        ),
        primary_key=True,
        nullable=False,
    )
    timeline_event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "timeline_events.id",
            name=(
                "fk_postmortem_draft_evidence_event_id_"
                "timeline_events"
            ),
        ),
        primary_key=True,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
