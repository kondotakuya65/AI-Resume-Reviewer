from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import resolve_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.schemas import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisSummary,
    CategoryScores,
    ExportResponse,
    RecommendationOut,
    RewriteCreate,
    RewriteResponse,
)
from app.services import analysis as analysis_service

router = APIRouter(tags=["analyses"])


def _to_response(run) -> AnalysisResponse:
    settings = get_settings()
    scores = None
    if run.scores:
        s = run.scores
        scores = CategoryScores(
            content_quality=s.content_quality,
            job_relevance=s.job_relevance,
            achievements=s.achievements,
            skills_match=s.skills_match,
            readability=s.readability,
            ats_compatibility=s.ats_compatibility,
            overall_score=s.overall_score,
            job_match_score=s.job_match_score,
            ats_score=s.ats_score,
            skill_match_pct=s.skill_match_pct,
            experience_match_pct=s.experience_match_pct,
            keyword_match_pct=s.keyword_match_pct,
            responsibility_match_pct=s.responsibility_match_pct,
        )
    return AnalysisResponse(
        id=run.id,
        status=run.status,
        resume_id=run.resume_id,
        job_description_id=run.job_description_id,
        target_role=run.target_role,
        experience_level=run.experience_level,
        model_name=run.model_name,
        prompt_version=run.prompt_version,
        scores=scores,
        strengths=list(run.strengths or []),
        weaknesses=list(run.weaknesses or []),
        missing_keywords=list(run.missing_keywords or []),
        matched_skills=list(run.matched_skills or []),
        recommendations=[
            RecommendationOut(
                id=r.id,
                priority=r.priority,  # type: ignore[arg-type]
                section=r.section,
                message=r.message,
            )
            for r in (run.recommendations or [])
        ],
        error_message=run.error_message,
        disclaimer=settings.disclaimer,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


@router.post("/analyses", response_model=AnalysisResponse)
async def create_analysis(
    payload: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> AnalysisResponse:
    try:
        run = analysis_service.create_analysis_run(
            db,
            user_id=user.id,
            resume_id=payload.resume_id,
            job_description_id=payload.job_description_id,
            target_role=payload.target_role,
            experience_level=payload.experience_level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Run LLM work in the background so Next.js proxy does not hang up on slow Ollama/PDF jobs
    background_tasks.add_task(analysis_service.execute_analysis_job, run.id, user.id)
    return _to_response(run)


@router.get("/analyses", response_model=list[AnalysisSummary])
async def list_analyses(
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> list[AnalysisSummary]:
    runs = analysis_service.list_analyses(db, user.id)
    return [
        AnalysisSummary(
            id=r.id,
            status=r.status,
            target_role=r.target_role,
            overall_score=r.scores.overall_score if r.scores else None,
            job_match_score=r.scores.job_match_score if r.scores else None,
            ats_score=r.scores.ats_score if r.scores else None,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> AnalysisResponse:
    try:
        run = analysis_service.get_analysis(db, analysis_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(run)


@router.get("/analyses/{analysis_id}/export", response_model=ExportResponse)
async def export_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> ExportResponse:
    settings = get_settings()
    try:
        run = analysis_service.get_analysis(db, analysis_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    md = analysis_service.build_markdown_report(run, settings.disclaimer)
    return ExportResponse(analysis_id=run.id, markdown=md, disclaimer=settings.disclaimer)


@router.post("/rewrites", response_model=RewriteResponse)
async def create_rewrite(
    payload: RewriteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> RewriteResponse:
    try:
        row = await analysis_service.rewrite_section(
            db,
            user_id=user.id,
            analysis_id=payload.analysis_id,
            section_type=payload.section_type,
            original_text=payload.original_text,
            instruction=payload.instruction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RewriteResponse(
        id=row.id,
        analysis_run_id=row.analysis_run_id,
        section_type=row.section_type,
        original_text=row.original_text,
        rewritten_text=row.rewritten_text,
        instruction=row.instruction,
        created_at=row.created_at,
    )
