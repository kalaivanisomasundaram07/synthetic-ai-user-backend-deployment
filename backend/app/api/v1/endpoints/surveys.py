from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user_id
from app.core.database import get_db
from app.agents.survey_agent import SurveyResponseAgent
from app.exceptions.api_exceptions import NotFoundError
from app.models.persona import Persona
from app.models.response import Response
from app.models.survey import SurveyStatus
from app.repositories.persona_repo import PersonaRepository
from app.repositories.response_repo import ResponseRepository
from app.schemas.request.survey import SurveyCreateRequest, SurveyExecuteRequest, SurveyUpdateRequest
from app.schemas.response.survey import (
    SurveyExecutionResponse,
    SurveyListResponse,
    SurveyResponse as SurveyResponseSchema,
    PersonaSurveyResponse
)
from app.services.survey_service import SurveyService

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.post("", response_model=SurveyResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_survey(
    payload: SurveyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new survey for an experiment."""
    service = SurveyService(db)
    try:
        survey = await service.create(
            experiment_id=payload.experiment_id,
            title=payload.title,
            questions=payload.questions,
            description=payload.description
        )
        return survey
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/experiment/{experiment_id}", response_model=SurveyListResponse)
async def list_surveys_for_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    """List all surveys for an experiment."""
    service = SurveyService(db)
    try:
        surveys = await service.list_for_experiment(experiment_id)
        return SurveyListResponse(total=len(surveys), experiment_id=experiment_id, items=surveys)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{survey_id}", response_model=SurveyResponseSchema)
async def get_survey(survey_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific survey by ID."""
    service = SurveyService(db)
    try:
        return await service.get(survey_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{survey_id}", response_model=SurveyResponseSchema)
async def update_survey(
    survey_id: str, payload: SurveyUpdateRequest, db: AsyncSession = Depends(get_db)
):
    """Update a survey."""
    service = SurveyService(db)
    try:
        survey = await service.get(survey_id)
        
        if payload.title is not None:
            survey.title = payload.title
        if payload.description is not None:
            survey.description = payload.description
        if payload.status is not None:
            try:
                survey.status = SurveyStatus(payload.status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")
        
        await service.survey_repo.commit()
        return survey
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey(survey_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a survey and all its responses."""
    service = SurveyService(db)
    try:
        await service.delete(survey_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/execute", response_model=SurveyExecutionResponse)
async def execute_survey(
    payload: SurveyExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a survey - generate responses from all personas simultaneously.
    This is the core Survey Mode feature for Milestone 2.
    """
    service = SurveyService(db)
    persona_repo = PersonaRepository(db)
    response_repo = ResponseRepository(db)
    
    try:
        survey = await service.get(payload.survey_id)
        
        # Get personas for the experiment
        personas = await persona_repo.list_for_experiment(survey.experiment_id)
        if not personas:
            raise HTTPException(status_code=400, detail="No personas found for this experiment")
        
        # Clear existing responses if regenerating
        if payload.regenerate:
            await response_repo.delete_for_survey(survey.id)
            survey.completed_responses = 0
        
        # Update survey status
        survey.status = SurveyStatus.ACTIVE
        await service.survey_repo.commit()
        
        # Generate responses using the survey agent
        agent = SurveyResponseAgent()
        
        # Convert personas to dict format for agent
        persona_dicts = []
        for persona in personas:
            persona_dict = {
                "id": str(persona.id),
                "name": persona.name,
                "age": persona.age,
                "gender": persona.gender,
                "occupation": persona.occupation,
                "location": persona.location,
                "income_bracket": persona.income_bracket,
                "education_level": persona.education_level,
                "personality_traits": persona.personality_traits,
                "behavioral_patterns": persona.behavioral_patterns,
                "tech_savviness": persona.tech_savviness,
                "daily_habits": persona.daily_habits,
                "core_values": persona.core_values,
                "motivations": persona.motivations,
                "pain_points": persona.pain_points,
                "risk_tolerance": persona.risk_tolerance,
                "bio": persona.bio,
                "persona_hash": persona.persona_hash,
                "consistency_seed": persona.consistency_seed
            }
            persona_dicts.append(persona_dict)
        
        # Generate batch responses
        batch_responses = await agent.generate_batch_responses(persona_dicts, survey.questions)
        
        # Store responses in database
        persona_responses = []
        total_rating = 0
        rating_count = 0
        completed_personas = 0
        
        for persona_id, responses in batch_responses.items():
            # Get persona name
            persona = next((p for p in personas if str(p.id) == persona_id), personas[0])
            
            response_list = []
            persona_has_responses = False
            
            for idx, response in enumerate(responses):
                # Store in database
                await service.add_response(
                    survey_id=survey.id,
                    persona_id=persona_id,
                    question_text=response.question,
                    answer_text=response.answer,
                    turn_number=idx + 1,
                    rating=response.rating,
                    reasoning=response.reasoning,
                    response_metadata={"confidence": response.confidence, "reasoning": response.reasoning}
                )
                
                if response.rating is not None:
                    total_rating += response.rating
                    rating_count += 1
                
                persona_has_responses = True
                
                response_list.append({
                    "question": response.question,
                    "answer": response.answer,
                    "rating": response.rating,
                    "reasoning": response.reasoning,
                    "confidence": response.confidence
                })
            
            if persona_has_responses:
                completed_personas += 1
            
            persona_responses.append(PersonaSurveyResponse(
                persona_id=persona_id,
                persona_name=persona.name,
                responses=response_list
            ))
        
        # Update survey status to completed
        survey.status = SurveyStatus.COMPLETED
        survey.completed_responses = completed_personas
        if rating_count > 0:
            survey.avg_rating = round(total_rating / rating_count, 2)
        await service.survey_repo.commit()
        
        return SurveyExecutionResponse(
            survey_id=survey.id,
            total_personas=survey.total_personas,
            completed_responses=survey.completed_responses,
            avg_rating=survey.avg_rating,
            persona_responses=persona_responses
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{survey_id}/responses")
async def get_survey_responses(survey_id: str, db: AsyncSession = Depends(get_db)):
    """Get all responses for a survey, organized by persona."""
    service = SurveyService(db)
    try:
        survey = await service.get(survey_id)
        responses = await service.get_responses(survey_id)
        
        # Group responses by persona
        persona_responses_map: dict[str, list[dict]] = {}
        for response in responses:
            persona_id = str(response.persona_id)
            if persona_id not in persona_responses_map:
                persona_responses_map[persona_id] = []
            
            persona_responses_map[persona_id].append({
                "question": response.question_text,
                "answer": response.answer_text,
                "rating": response.rating,
                "reasoning": response.reasoning,
                "turn_number": response.turn_number,
                "consistency_score": response.consistency_score,
                "consistency_issues": response.consistency_issues,
                "metadata": response.response_metadata
            })
        
        # Convert to response format
        persona_responses = []
        for persona_id, resp_list in persona_responses_map.items():
            # Get persona name
            persona = await service.persona_repo.get(persona_id)
            persona_responses.append(PersonaSurveyResponse(
                persona_id=persona_id,
                persona_name=persona.name if persona else "Unknown",
                responses=resp_list
            ))
        
        return {
            "survey_id": survey_id,
            "total_personas": survey.total_personas,
            "completed_responses": survey.completed_responses,
            "avg_rating": survey.avg_rating,
            "persona_responses": persona_responses
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
