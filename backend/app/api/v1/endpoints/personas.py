from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.exceptions.api_exceptions import NotFoundError
from app.schemas.request.persona import PersonaGenerateRequest, PersonaImportRequest
from app.schemas.response.persona import PersonaListResponse, PersonaResponse
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("/import", response_model=PersonaListResponse, status_code=status.HTTP_201_CREATED)
async def import_personas(
    payload: PersonaImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Stores personas exactly as given (e.g. already generated and shown by a
    client) instead of having the backend generate its own. Useful when a
    frontend wants its displayed personas mirrored 1:1 into the database.
    """
    service = PersonaService(db)
    try:
        personas = await service.import_personas(
            payload.experiment_id, payload.personas, replace=payload.replace
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return PersonaListResponse(
        total=len(personas), experiment_id=payload.experiment_id, items=personas
    )


@router.post("/generate", response_model=PersonaListResponse, status_code=status.HTTP_201_CREATED)
async def generate_personas(
    payload: PersonaGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Runs the Persona Generation Agent for the given experiment and persists
    the resulting persona cards. Falls back to synthetic (Faker) generation
    automatically if no LLM provider (Groq/Gemini/Ollama) is reachable.
    """
    service = PersonaService(db)
    try:
        personas = await service.generate_for_experiment(
            payload.experiment_id,
            persona_count=payload.persona_count,
            regenerate=payload.regenerate,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return PersonaListResponse(
        total=len(personas), experiment_id=payload.experiment_id, items=personas
    )


@router.get("/experiment/{experiment_id}", response_model=PersonaListResponse)
async def list_personas_for_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    service = PersonaService(db)
    try:
        personas = await service.list_for_experiment(experiment_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return PersonaListResponse(total=len(personas), experiment_id=experiment_id, items=personas)


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str, db: AsyncSession = Depends(get_db)):
    service = PersonaService(db)
    try:
        return await service.get(persona_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

