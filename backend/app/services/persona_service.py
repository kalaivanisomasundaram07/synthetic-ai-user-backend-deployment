import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.persona_agent import PersonaProfile, generate_personas
from app.exceptions.api_exceptions import NotFoundError
from app.models.experiment import ExperimentStatus
from app.models.persona import Persona
from app.repositories.experiment_repo import ExperimentRepository
from app.repositories.persona_repo import PersonaRepository
from app.schemas.request.persona import PersonaImportItem


class PersonaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.persona_repo = PersonaRepository(session)
        self.experiment_repo = ExperimentRepository(session)

    @staticmethod
    def _to_orm(profile: PersonaProfile, experiment_id: str) -> Persona:
        return Persona(
            experiment_id=experiment_id,
            name=profile.name,
            age=profile.age,
            gender=profile.gender,
            occupation=profile.occupation,
            location=profile.location,
            income_bracket=profile.income_bracket,
            education_level=profile.education_level,
            personality_traits=profile.personality_traits,
            behavioral_patterns=profile.behavioral_patterns,
            tech_savviness=profile.tech_savviness,
            daily_habits=profile.daily_habits,
            core_values=profile.core_values,
            motivations=profile.motivations,
            pain_points=profile.pain_points,
            risk_tolerance=profile.risk_tolerance,
            bio=profile.bio,
            avatar_seed=profile.avatar_seed,
            quote=profile.quote,
            persona_hash=profile.persona_hash,
            consistency_seed=profile.consistency_seed,
            generation_source=profile.generation_source,
        )

    async def generate_for_experiment(
        self, experiment_id: str, *, persona_count: int | None = None, regenerate: bool = False
    ) -> list[Persona]:
        experiment = await self.experiment_repo.get(experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found")

        if regenerate:
            await self.persona_repo.delete_for_experiment(experiment_id)

        count = persona_count or experiment.persona_count

        profiles = await generate_personas(
            product_description=experiment.product_description,
            target_audience=experiment.target_audience,
            research_objectives=experiment.research_objectives,
            persona_count=count,
        )

        personas = [self._to_orm(p, experiment_id) for p in profiles]
        for persona in personas:
            await self.persona_repo.create(persona)

        experiment.status = ExperimentStatus.PERSONAS_READY
        await self.persona_repo.commit()

        return personas

    @staticmethod
    def _from_import_item(item: PersonaImportItem, experiment_id: str) -> Persona:
        """Builds a Persona row directly from a client-supplied payload,
        filling every NOT NULL column with a sensible default so a partial
        payload (e.g. a lightweight frontend that only tracks name/age/
        occupation/location/bio/tags) still stores cleanly."""
        name = item.name.strip()
        age = item.age if item.age is not None else 30
        traits = item.personality_traits or item.tags or []
        behaviors = item.behavioral_patterns or ([item.behavioral_pattern] if item.behavioral_pattern else [])
        fit_score = item.product_fit_score if item.product_fit_score is not None else item.adoption_score

        fingerprint = f"{name}|{age}|{item.occupation or ''}|{item.location or ''}"
        persona_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
        consistency_seed = int(hashlib.sha256(persona_hash.encode()).hexdigest(), 16) % (2**31)
        avatar_seed = item.avatar_seed or hashlib.md5(name.encode()).hexdigest()[:12]

        return Persona(
            experiment_id=experiment_id,
            name=name,
            age=age,
            gender=item.gender or "Not specified",
            occupation=item.occupation or "Not specified",
            location=item.location or "Not specified",
            income_bracket=item.income_bracket or "Not specified",
            education_level=item.education_level or "Not specified",
            personality_traits=traits,
            behavioral_patterns=behaviors,
            tech_savviness=item.tech_savviness or "medium",
            daily_habits=item.daily_habits or [],
            core_values=item.core_values or [],
            motivations=item.motivations or [],
            pain_points=item.pain_points or [],
            risk_tolerance=item.risk_tolerance or "medium",
            bio=item.bio or "",
            avatar_seed=avatar_seed,
            quote=item.quote,
            persona_hash=persona_hash,
            consistency_seed=consistency_seed,
            generation_source="client_import",
            product_fit_score=fit_score,
        )

    async def import_personas(
        self, experiment_id: str, items: list[PersonaImportItem], *, replace: bool = False
    ) -> list[Persona]:
        """Stores personas exactly as supplied by the caller (e.g. already
        generated/displayed client-side) instead of generating new ones."""
        experiment = await self.experiment_repo.get(experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found")

        if replace:
            await self.persona_repo.delete_for_experiment(experiment_id)

        personas = [self._from_import_item(item, experiment_id) for item in items]
        for persona in personas:
            await self.persona_repo.create(persona)

        experiment.status = ExperimentStatus.PERSONAS_READY
        await self.persona_repo.commit()

        return personas

    async def list_for_experiment(self, experiment_id: str) -> list[Persona]:
        experiment = await self.experiment_repo.get(experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found")
        return await self.persona_repo.list_for_experiment(experiment_id)

    async def get(self, persona_id: str) -> Persona:
        persona = await self.persona_repo.get(persona_id)
        if persona is None:
            raise NotFoundError(f"Persona {persona_id} not found")
        return persona
