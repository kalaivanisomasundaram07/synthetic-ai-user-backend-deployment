from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.api_exceptions import NotFoundError
from app.models.experiment import ExperimentStatus
from app.models.persona import Persona
from app.models.response import Response
from app.models.survey import Survey, SurveyStatus
from app.repositories.experiment_repo import ExperimentRepository
from app.repositories.persona_repo import PersonaRepository
from app.repositories.response_repo import ResponseRepository
from app.repositories.survey_repo import SurveyRepository


class SurveyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.survey_repo = SurveyRepository(session)
        self.experiment_repo = ExperimentRepository(session)
        self.persona_repo = PersonaRepository(session)
        self.response_repo = ResponseRepository(session)

    async def create(
        self,
        experiment_id: str,
        title: str,
        questions: list[str],
        description: str | None = None
    ) -> Survey:
        """Create a new survey for an experiment."""
        experiment = await self.experiment_repo.get(experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found")

        if experiment.status != ExperimentStatus.PERSONAS_READY:
            raise ValueError(f"Experiment must have personas ready to create a survey")

        personas = await self.persona_repo.list_for_experiment(experiment_id)
        if not personas:
            raise ValueError(f"No personas found for experiment {experiment_id}")

        survey = Survey(
            experiment_id=experiment_id,
            title=title,
            description=description,
            questions=questions,
            status=SurveyStatus.DRAFT,
            total_personas=len(personas),
            completed_responses=0
        )
        await self.survey_repo.create(survey)
        await self.survey_repo.commit()
        return survey

    async def get(self, survey_id: str) -> Survey:
        survey = await self.survey_repo.get(survey_id)
        if survey is None:
            raise NotFoundError(f"Survey {survey_id} not found")
        return survey

    async def list_for_experiment(self, experiment_id: str) -> list[Survey]:
        experiment = await self.experiment_repo.get(experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found")
        return await self.survey_repo.list_for_experiment(experiment_id)

    async def update_status(self, survey_id: str, status: SurveyStatus) -> Survey:
        survey = await self.get(survey_id)
        survey.status = status
        await self.survey_repo.commit()
        return survey

    async def delete(self, survey_id: str) -> None:
        survey = await self.get(survey_id)
        await self.response_repo.delete_for_survey(survey_id)
        await self.survey_repo.delete(survey)
        await self.survey_repo.commit()

    async def add_response(
        self,
        survey_id: str,
        persona_id: str,
        question_text: str,
        answer_text: str,
        turn_number: int = 1,
        conversation_context: dict | None = None,
        consistency_score: float | None = None,
        consistency_issues: dict | None = None,
        rating: int | None = None,
        reasoning: str | None = None,
        response_metadata: dict | None = None
    ) -> Response:
        """Add a response to a survey."""
        survey = await self.get(survey_id)
        
        response = Response(
            persona_id=persona_id,
            survey_id=survey_id,
            question_text=question_text,
            answer_text=answer_text,
            turn_number=turn_number,
            conversation_context=conversation_context or [],
            consistency_score=consistency_score,
            consistency_issues=consistency_issues or [],
            rating=rating,
            reasoning=reasoning,
            response_metadata=response_metadata or {}
        )
        await self.response_repo.create(response)
        
        # Don't increment completed_responses here - it's handled at the persona level
        await self.survey_repo.commit()
        return response

    async def get_responses(self, survey_id: str) -> list[Response]:
        """Get all responses for a survey."""
        survey = await self.get(survey_id)
        return await self.response_repo.list_for_survey(survey_id)

    async def get_persona_responses(self, survey_id: str, persona_id: str) -> list[Response]:
        """Get all responses from a specific persona for a survey."""
        survey = await self.get(survey_id)
        return await self.response_repo.list(persona_id=persona_id, survey_id=survey_id)

    async def generate_responses_for_survey(self, survey_id: str) -> list[Response]:
        """Seed a survey with simple persona responses for demo and testing."""
        survey = await self.get(survey_id)
        personas = await self.persona_repo.list_for_experiment(survey.experiment_id)

        responses: list[Response] = []
        for persona in personas:
            for question in survey.questions:
                response = await self.add_response(
                    survey_id=survey.id,
                    persona_id=str(persona.id),
                    question_text=question,
                    answer_text=(
                        f"{persona.name} sees value in the product and would likely try it if onboarding stays simple."
                        if "product" in question.lower() or "use" in question.lower()
                        else f"{persona.name} is interested in the concept and wants clear guidance."
                    ),
                )
                responses.append(response)

        return responses
