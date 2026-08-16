from pydantic import BaseModel, ConfigDict
from typing import Any
from datetime import datetime


class SurveyResponse(BaseModel):
    """Survey response for API clients."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    experiment_id: str
    title: str
    description: str | None
    questions: list[str]
    status: str
    total_personas: int
    completed_responses: int
    avg_rating: float | None = None
    created_at: datetime
    updated_at: datetime
    
    
class RatingResponse(BaseModel):
    rating: int | None
    reasoning: str | None
    elaboration: str


class SurveyListResponse(BaseModel):
    total: int
    experiment_id: str
    items: list[SurveyResponse]


class PersonaSurveyResponse(BaseModel):
    """Response from a single persona to survey questions."""
    persona_id: str
    persona_name: str
    responses: list[dict[str, Any]]


class SurveyExecutionResponse(BaseModel):
    """Result of executing a survey across all personas."""
    survey_id: str
    total_personas: int
    completed_responses: int
    avg_rating: float | None = None
    persona_responses: list[PersonaSurveyResponse]
