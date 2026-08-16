"""
Dashboard API endpoints — aggregated analytics and visualization data.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user_id
from app.core.database import get_db
from app.exceptions.api_exceptions import NotFoundError
from app.repositories.experiment_repo import ExperimentRepository
from app.repositories.insight_repo import InsightRepository
from app.repositories.persona_repo import PersonaRepository
from app.repositories.report_repo import ReportRepository
from app.services.insight_service import InsightService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/experiment/{experiment_id}")
async def get_experiment_dashboard(experiment_id: str, db: AsyncSession = Depends(get_db)):
    """Get comprehensive dashboard data for an experiment."""
    experiment_repo = ExperimentRepository(db)
    persona_repo = PersonaRepository(db)
    insight_repo = InsightRepository(db)
    report_repo = ReportRepository(db)
    
    # Get experiment
    experiment = await experiment_repo.get(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    
    # Get personas
    personas = await persona_repo.list_for_experiment(experiment_id)
    
    # Get insights
    insight = await insight_repo.get_by_experiment(experiment_id)
    
    # Get report
    report = await report_repo.get_by_experiment(experiment_id)
    
    # Build dashboard data
    dashboard_data = {
        "experiment": {
            "id": experiment.id,
            "title": experiment.title,
            "status": experiment.status,
            "product_description": experiment.product_description,
            "target_audience": experiment.target_audience,
            "research_objectives": experiment.research_objectives,
            "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
        },
        "personas": {
            "count": len(personas),
            "items": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "age": p.age,
                    "occupation": p.occupation,
                    "adoption_score": p.product_fit_score,
                    "product_fit_score": p.product_fit_score,
                }
                for p in personas
            ],
        },
        "insights": None,
        "report": None,
    }
    
    if insight:
        dashboard_data["insights"] = {
            "id": insight.id,
            "would_use_pct": insight.would_use_pct,
            "would_pay_pct": insight.would_pay_pct,
            "themes": insight.themes,
            "sentiment": insight.sentiment,
            "key_quotes": insight.key_quotes,
            "suggestions": insight.suggestions,
            "user_wants_summary": insight.user_wants_summary,
            "persona_scores": insight.persona_scores,
            "created_at": insight.created_at.isoformat() if insight.created_at else None,
        }
    
    if report:
        dashboard_data["report"] = {
            "id": report.id,
            "title": report.title,
            "summary": report.summary,
            "validation_scoring": report.validation_scoring,
            "recommendations": report.recommendations,
            "status": report.status,
            "file_path": report.file_path,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
    
    return dashboard_data


@router.get("/overview")
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """Get overview statistics across all experiments."""
    experiment_repo = ExperimentRepository(db)
    persona_repo = PersonaRepository(db)
    insight_repo = InsightRepository(db)
    report_repo = ReportRepository(db)
    
    # Get all experiments
    experiments = await experiment_repo.list_all()
    
    total_personas = 0
    total_insights = 0
    total_reports = 0
    completed_experiments = 0
    
    for exp in experiments:
        personas = await persona_repo.list_for_experiment(exp.id)
        total_personas += len(personas)
        
        insight = await insight_repo.get_by_experiment(exp.id)
        if insight:
            total_insights += 1
        
        report = await report_repo.get_by_experiment(exp.id)
        if report:
            total_reports += 1
        
        if exp.status == "completed":
            completed_experiments += 1
    
    return {
        "total_experiments": len(experiments),
        "completed_experiments": completed_experiments,
        "total_personas": total_personas,
        "total_insights": total_insights,
        "total_reports": total_reports,
        "recent_experiments": [
            {
                "id": exp.id,
                "title": exp.title,
                "status": exp.status,
                "created_at": exp.created_at.isoformat() if exp.created_at else None,
            }
            for exp in sorted(experiments, key=lambda x: x.created_at or "", reverse=True)[:5]
        ],
    }
