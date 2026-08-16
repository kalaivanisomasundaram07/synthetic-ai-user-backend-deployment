"""
Report Service — generates research reports with PDF export for experiments.
"""
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.api_exceptions import NotFoundError
from app.models.experiment import Experiment
from app.models.insight import Insight
from app.models.persona import Persona
from app.models.report import Report
from app.models.response import Response
from app.models.survey import Survey
from app.repositories.experiment_repo import ExperimentRepository
from app.repositories.insight_repo import InsightRepository
from app.repositories.persona_repo import PersonaRepository
from app.repositories.report_repo import ReportRepository
from app.repositories.response_repo import ResponseRepository
from app.repositories.survey_repo import SurveyRepository
from app.services.pdf_generator import PDFGenerator


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.report_repo = ReportRepository(session)
        self.experiment_repo = ExperimentRepository(session)
        self.persona_repo = PersonaRepository(session)
        self.insight_repo = InsightRepository(session)
        self.response_repo = ResponseRepository(session)
        self.survey_repo = SurveyRepository(session)
        self.pdf_generator = PDFGenerator()

    async def generate(self, experiment_id: str) -> Report:
        """Generate a research report for an experiment."""
        experiment = await self.experiment_repo.get(experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found")

        # Get personas
        personas = await self.persona_repo.list_for_experiment(experiment_id)
        
        # Get insights
        insight = await self.insight_repo.get_latest_for_experiment(experiment_id)
        
        # Get survey responses for highlights
        surveys = await self.survey_repo.list_for_experiment(experiment_id)
        response_highlights = []
        for survey in surveys:
            responses = await self.response_repo.list_for_survey(survey.id)
            for response in responses[:3]:  # Top 3 responses per survey
                persona = next((p for p in personas if str(p.id) == response.persona_id), None)
                if persona:
                    response_highlights.append({
                        "persona_name": persona.name,
                        "question": response.question_text,
                        "answer": response.answer_text,
                        "sentiment": response.sentiment or "neutral",
                    })

        # Build persona profiles
        persona_profiles = []
        for persona in personas:
            persona_profiles.append({
                "name": persona.name,
                "age": persona.age,
                "occupation": persona.occupation,
                "location": persona.location,
                "personality_traits": persona.personality_traits,
                "core_values": persona.core_values,
                "bio": persona.bio,
                "product_fit_score": persona.product_fit_score,
            })

        # Build insight summary
        insight_summary = {}
        if insight:
            insight_summary = {
                "would_use_pct": insight.would_use_pct,
                "would_pay_pct": insight.would_pay_pct,
                "themes": insight.themes,
                "sentiment": insight.sentiment,
                "key_quotes": insight.key_quotes,
                "suggestions": insight.suggestions,
                "user_wants_summary": insight.user_wants_summary,
                "persona_scores": insight.persona_scores,
            }

        # Build validation scoring
        validation_scoring = {
            "overall_product_fit_score": (
                sum(
                    p["product_fit_score"]
                    for p in persona_profiles
                    if p["product_fit_score"] is not None
                )
                / sum(
                    1
                    for p in persona_profiles
                    if p["product_fit_score"] is not None
                )
                if any(p["product_fit_score"] is not None for p in persona_profiles)
                else 0
            ),
            "would_use_percentage": insight_summary.get("would_use_pct", 0),
            "would_pay_percentage": insight_summary.get("would_pay_pct", 0),
        }

        # Generate recommendations based on insights
        recommendations = []
        if insight and insight.suggestions:
            for suggestion in insight.suggestions[:5]:
                recommendations.append({
                    "suggestion": suggestion.get("suggestion", ""),
                    "category": suggestion.get("category", ""),
                    "priority": suggestion.get("priority", "medium"),
                })

        # Create report
        report = Report(
            experiment_id=experiment_id,
            title=f"Research Report: {experiment.title}",
            summary=self._generate_summary(experiment, insight_summary, validation_scoring),
            persona_profiles=persona_profiles,
            response_highlights=response_highlights,
            insight_summary=insight_summary,
            validation_scoring=validation_scoring,
            recommendations=recommendations,
            status="generating",
        )
        
        await self.report_repo.create(report)
        await self.report_repo.commit()
        
        # Generate PDF
        try:
            experiment_dict = {
                "id": experiment.id,
                "title": experiment.title,
                "product_description": experiment.product_description,
                "target_audience": experiment.target_audience,
                "research_objectives": experiment.research_objectives,
            }
            
            pdf_path = self.pdf_generator.generate_report(
                experiment=experiment_dict,
                personas=persona_profiles,
                insights=insight_summary,
                validation_scoring=validation_scoring,
                recommendations=recommendations,
                response_highlights=response_highlights,
            )
            
            report.file_path = pdf_path
            report.status = "ready"
        except Exception as e:
            report.status = "failed"
            report.error_message = str(e)
        
        await self.report_repo.update(report)
        await self.report_repo.commit()
        
        # Update experiment status
        experiment.status = "completed"
        await self.experiment_repo.update(experiment)
        await self.report_repo.commit()
        
        return report

    def _generate_summary(self, experiment: Experiment, insight_summary: dict, validation_scoring: dict) -> str:
        """Generate a narrative summary of the research findings."""
        summary_parts = [
            f"This report summarizes research findings for '{experiment.title}'. ",
            f"The product targets {experiment.target_audience}. ",
        ]
        
        if validation_scoring:
            summary_parts.append(
                f"Product fit score: {validation_scoring.get('overall_product_fit_score', 0):.1f}/10. "
            )
            summary_parts.append(
                f"{validation_scoring.get('would_use_percentage', 0)}% of personas would use this product, "
                f"and {validation_scoring.get('would_pay_percentage', 0)}% would pay for it. "
            )
        
        if insight_summary.get("user_wants_summary"):
            summary_parts.append(f"\n\nKey user needs: {insight_summary['user_wants_summary']}")
        
        return "".join(summary_parts)

    async def get(self, report_id: str) -> Report:
        report = await self.report_repo.get(report_id)
        if report is None:
            raise NotFoundError(f"Report {report_id} not found")
        return report

    async def get_by_experiment(self, experiment_id: str) -> Report:
        report = await self.report_repo.get_by_experiment(experiment_id)
        if report is None:
            raise NotFoundError(f"No report found for experiment {experiment_id}")
        return report

    async def delete(self, report_id: str) -> None:
        report = await self.get(report_id)
        await self.report_repo.delete(report)
        await self.report_repo.commit()
