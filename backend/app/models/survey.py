"""
Survey = a collection of questions posed to personas for response comparison.
Part of Milestone 2 Survey Mode feature.
"""
from __future__ import annotations

import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class SurveyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Survey(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "surveys"

    experiment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Survey metadata
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Questions for the survey
    questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    # Survey state
    status: Mapped[SurveyStatus] = mapped_column(
    Enum(
        SurveyStatus,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    ),
    default=SurveyStatus.DRAFT,
    nullable=False,
    )
    
    # Response tracking
    total_personas: Mapped[int] = mapped_column(Integer, default=0)
    completed_responses: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    experiment: Mapped["Experiment"] = relationship(back_populates="surveys")  # noqa: F821
    responses: Mapped[list["Response"]] = relationship(back_populates="survey", cascade="all, delete-orphan")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Survey id={self.id} title={self.title!r} status={self.status}>"
