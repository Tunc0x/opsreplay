from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.github_installation import GitHubInstallation
    from app.models.repository import Repository


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    repositories: Mapped[list[Repository]] = relationship(
        back_populates="organization"
    )
    github_installation: Mapped[GitHubInstallation | None] = relationship(
        back_populates="organization",
        uselist=False,
    )
