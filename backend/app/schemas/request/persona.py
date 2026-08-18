from pydantic import BaseModel, Field


class PersonaImportItem(BaseModel):
    """One already-generated persona (e.g. produced client-side) to store
    as-is, instead of asking the backend to generate a new one. Only `name`
    is required — every other field has a sensible default so partial
    payloads from lighter-weight clients still store cleanly."""

    id: str | None = None  # client-side id, kept only for the caller's own bookkeeping; ignored for storage
    name: str
    age: int | None = None
    gender: str | None = None
    occupation: str | None = None
    location: str | None = None
    income_bracket: str | None = None
    education_level: str | None = None
    personality_traits: list[str] | None = None
    tags: list[str] | None = None  # accepted as an alias for personality_traits
    behavioral_patterns: list[str] | None = None
    behavioral_pattern: str | None = None  # accepted as a singular-string alias
    tech_savviness: str | None = None
    daily_habits: list[str] | None = None
    core_values: list[str] | None = None
    motivations: list[str] | None = None
    pain_points: list[str] | None = None
    risk_tolerance: str | None = None
    bio: str | None = None
    avatar_seed: str | None = None
    quote: str | None = None
    adoption_score: float | None = None  # accepted as an alias for product_fit_score
    product_fit_score: float | None = None


class PersonaImportRequest(BaseModel):
    """Payload for POST /api/v1/personas/import — stores personas exactly as
    given (e.g. already generated/displayed by a client) rather than having
    the backend generate its own."""

    experiment_id: str = Field(..., description="Experiment these personas belong to.")
    personas: list[PersonaImportItem] = Field(..., min_length=1)
    replace: bool = Field(
        default=False,
        description="If true, deletes existing personas for this experiment before importing.",
    )


class PersonaGenerateRequest(BaseModel):
    """
    Payload for POST /api/personas/generate.
    experiment_id lives in the body (not the path) to match the frontend's
    api_client.py contract.
    """

    experiment_id: str = Field(..., description="Experiment to generate personas for.")
    persona_count: int | None = Field(
        default=None, ge=3, le=12, description="Override experiment's default persona_count."
    )
    regenerate: bool = Field(
        default=False,
        description="If true, deletes existing personas for this experiment before generating new ones.",
    )
