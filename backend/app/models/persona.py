"""
Persona = one synthetic user generated for an Experiment.
Schema mirrors the PersonaProfile shape produced by the Persona Generation
Agent (app/agents/persona_agent.py) so agent output maps 1:1 onto storage.
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class Persona(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "personas"

    experiment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # --- Demographic profile ---
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(40), nullable=False)
    occupation: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    income_bracket: Mapped[str] = mapped_column(String(60), nullable=False)
    education_level: Mapped[str] = mapped_column(String(100), nullable=False)

    # --- Behavioral profile ---
    personality_traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    behavioral_patterns: Mapped[list[str]] = mapped_column(JSON, default=list)
    tech_savviness: Mapped[str] = mapped_column(String(30), nullable=False)  # low/medium/high
    daily_habits: Mapped[list[str]] = mapped_column(JSON, default=list)

    # --- Psychological profile ---
    core_values: Mapped[list[str]] = mapped_column(JSON, default=list)
    motivations: Mapped[list[str]] = mapped_column(JSON, default=list)
    pain_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_tolerance: Mapped[str] = mapped_column(String(30), nullable=False)  # low/medium/high

    # --- Narrative / display ---
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_seed: Mapped[str] = mapped_column(String(80), nullable=False)  # deterministic avatar key
    quote: Mapped[str] = mapped_column(Text, nullable=True)  # signature persona quote for cards

    # --- Consistency / memory anchor (used by Memory module in Milestone 2) ---
    persona_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    consistency_seed: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Generation provenance ---
    generation_source: Mapped[str] = mapped_column(String(30), default="llm")  # llm|ollama|synthetic_fallback
    product_fit_score: Mapped[float] = mapped_column(Float, nullable=True)  # populated in Milestone 3

    experiment: Mapped["Experiment"] = relationship(back_populates="personas")  # noqa: F821
    responses: Mapped[list["Response"]] = relationship(back_populates="persona", cascade="all, delete-orphan")  # noqa: F821
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(  # noqa: F821
        back_populates="persona", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Persona id={self.id} name={self.name!r} occupation={self.occupation!r}>"
