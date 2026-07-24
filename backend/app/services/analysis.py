from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models import (
    AnalysisRun,
    AnalysisScore,
    JobDescription,
    Recommendation,
    Resume,
    RewriteRequest,
)
from app.services.llm import get_llm_client, safe_complete_json
from app.services.resume_extractor import detect_ats_issues
from app.services.scoring import compute_scores

SENSITIVE_KEYS = {"age", "gender", "race", "nationality", "religion", "photo", "marital_status", "disability"}
RESUME_TEXT_LIMIT = 8000
JD_TEXT_LIMIT = 8000

PARSE_RESUME_SYSTEM = """You extract structured resume data for a career tool.
Return JSON only. Never include or infer age, gender, race, nationality, religion,
photo, marital status, or disability. If such fields appear in the text, omit them.
Extract: name, contact, summary, skills, experience, education, certifications, projects.
"""

PARSE_JD_SYSTEM = """You extract structured job requirements from a job description.
Return JSON only with: required_skills, preferred_skills, experience_requirements,
education_requirements, responsibilities, industry_keywords, seniority_level.
Do not evaluate candidates. Do not consider protected personal attributes.
"""

COMPARE_SYSTEM = """You compare a resume to a job description and produce category scores plus recommendations.
Return JSON only. Score categories (integers, at or below max):
content_quality (0-25), job_relevance (0-25), achievements (0-15), skills_match (0-15),
readability (0-10), ats_compatibility (0-10).
Also include skill_match_pct, experience_match_pct, keyword_match_pct, responsibility_match_pct (0-100),
strengths (array), weaknesses (array), missing_keywords (array), matched_skills (array),
recommendations (array of {priority: critical|important|optional, section, message}) with at least 5 items.
Never score based on age, gender, race, nationality, religion, photo, marital status, or disability.
"""

REWRITE_SYSTEM = """You rewrite one resume section to be stronger and more measurable.
Return JSON only: {"rewritten_text": "..."}.
Keep facts plausible; do not invent employers. Prefer action verbs and quantified impact when reasonable.
Do not rewrite based on protected personal attributes.
"""


def _strip_sensitive(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _strip_sensitive(v) for k, v in data.items() if k.lower() not in SENSITIVE_KEYS}
    if isinstance(data, list):
        return [_strip_sensitive(v) for v in data]
    return data


async def parse_resume_text(text: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    client = get_llm_client(settings)
    raw = await safe_complete_json(
        client,
        PARSE_RESUME_SYSTEM,
        f"Extract structured resume data.\n\nResume text:\n{text[:RESUME_TEXT_LIMIT]}",
    )
    return _strip_sensitive(raw)


async def parse_job_description(text: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    client = get_llm_client(settings)
    return await safe_complete_json(
        client,
        PARSE_JD_SYSTEM,
        f"Extract job requirements.\n\nJob description:\n{text[:JD_TEXT_LIMIT]}",
    )


def create_analysis_run(
    db: Session,
    *,
    user_id: UUID,
    resume_id: UUID,
    job_description_id: UUID | None,
    target_role: str | None,
    experience_level: str | None,
    settings: Settings | None = None,
) -> AnalysisRun:
    """Create a running analysis row quickly; LLM work happens in the background."""
    settings = settings or get_settings()
    resume = db.get(Resume, resume_id)
    if not resume or resume.user_id != user_id:
        raise ValueError("Resume not found")
    if not resume.extracted_text:
        raise ValueError("Resume has no extracted text")

    if job_description_id:
        jd = db.get(JobDescription, job_description_id)
        if not jd or jd.user_id != user_id:
            raise ValueError("Job description not found")

    client = get_llm_client(settings)
    run = AnalysisRun(
        user_id=user_id,
        resume_id=resume_id,
        job_description_id=job_description_id,
        status="running",
        target_role=target_role,
        experience_level=experience_level,
        model_name=getattr(client, "model_name", settings.llm_provider),
        prompt_version=settings.prompt_version,
        input_tokens=0,
        output_tokens=0,
        estimated_cost=0.0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


async def execute_analysis_job(analysis_id: UUID, user_id: UUID) -> None:
    """Background worker: parse + score using a fresh DB session."""
    settings = get_settings()
    db = SessionLocal()
    try:
        run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.id == analysis_id, AnalysisRun.user_id == user_id)
            .one_or_none()
        )
        if not run:
            return

        resume = db.get(Resume, run.resume_id)
        if not resume or not resume.extracted_text:
            run.status = "failed"
            run.error_message = "Resume not found or empty"
            db.commit()
            return

        jd: JobDescription | None = None
        if run.job_description_id:
            jd = db.get(JobDescription, run.job_description_id)

        client = get_llm_client(settings)
        try:
            structured = resume.structured_data or await parse_resume_text(resume.extracted_text, settings)
            resume.structured_data = structured

            jd_parsed: dict[str, Any] = {}
            if jd:
                jd_parsed = jd.parsed_requirements or await parse_job_description(jd.raw_text, settings)
                jd.parsed_requirements = jd_parsed

            compare_user = (
                f"Target role: {run.target_role}\nExperience level: {run.experience_level}\n\n"
                f"Structured resume JSON:\n{structured}\n\n"
                f"Job requirements JSON:\n{jd_parsed or 'No job description provided; score general resume quality.'}\n\n"
                f"Raw resume excerpt:\n{resume.extracted_text[:6000]}\n"
            )
            comparison = await safe_complete_json(client, COMPARE_SYSTEM, compare_user)
            comparison = _strip_sensitive(comparison)

            ats_heuristic = detect_ats_issues(resume.extracted_text)
            scores = compute_scores(comparison, ats_heuristic)

            run.strengths = list(comparison.get("strengths") or [])
            run.weaknesses = list(comparison.get("weaknesses") or [])
            run.missing_keywords = list(comparison.get("missing_keywords") or [])
            run.matched_skills = list(comparison.get("matched_skills") or [])

            db.add(AnalysisScore(analysis_run_id=run.id, **scores))

            for rec in comparison.get("recommendations") or []:
                priority = str(rec.get("priority", "important")).lower()
                if priority not in {"critical", "important", "optional"}:
                    priority = "important"
                db.add(
                    Recommendation(
                        analysis_run_id=run.id,
                        priority=priority,
                        section=str(rec.get("section", "general")),
                        message=str(rec.get("message", "")),
                    )
                )

            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            run = db.get(AnalysisRun, analysis_id)
            if run:
                run.status = "failed"
                run.error_message = str(exc)
                db.commit()
    finally:
        db.close()


async def run_analysis(
    db: Session,
    *,
    user_id: UUID,
    resume_id: UUID,
    job_description_id: UUID | None,
    target_role: str | None,
    experience_level: str | None,
    settings: Settings | None = None,
) -> AnalysisRun:
    """Synchronous helper used by tests: create + execute in the same request."""
    run = create_analysis_run(
        db,
        user_id=user_id,
        resume_id=resume_id,
        job_description_id=job_description_id,
        target_role=target_role,
        experience_level=experience_level,
        settings=settings,
    )
    await execute_analysis_job(run.id, user_id)
    return get_analysis(db, run.id, user_id)


def get_analysis(db: Session, analysis_id: UUID, user_id: UUID) -> AnalysisRun:
    run = (
        db.query(AnalysisRun)
        .options(joinedload(AnalysisRun.scores), joinedload(AnalysisRun.recommendations))
        .filter(AnalysisRun.id == analysis_id, AnalysisRun.user_id == user_id)
        .one_or_none()
    )
    if not run:
        raise ValueError("Analysis not found")
    return run


def list_analyses(db: Session, user_id: UUID) -> list[AnalysisRun]:
    return (
        db.query(AnalysisRun)
        .options(joinedload(AnalysisRun.scores))
        .filter(AnalysisRun.user_id == user_id)
        .order_by(AnalysisRun.created_at.desc())
        .all()
    )


async def rewrite_section(
    db: Session,
    *,
    user_id: UUID,
    analysis_id: UUID,
    section_type: str,
    original_text: str,
    instruction: str | None,
    settings: Settings | None = None,
) -> RewriteRequest:
    settings = settings or get_settings()
    run = get_analysis(db, analysis_id, user_id)
    client = get_llm_client(settings)
    payload = await safe_complete_json(
        client,
        REWRITE_SYSTEM,
        (
            f"Section type: {section_type}\n"
            f"Instruction: {instruction or 'Improve clarity and impact'}\n"
            f"Target role: {run.target_role or 'the target role'}\n\n"
            f"Original text:\n{original_text}\n"
        ),
    )
    rewritten = str(payload.get("rewritten_text") or "").strip()
    if not rewritten:
        raise ValueError("Rewrite produced empty text")

    row = RewriteRequest(
        analysis_run_id=run.id,
        section_type=section_type,
        original_text=original_text,
        rewritten_text=rewritten,
        instruction=instruction,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def build_markdown_report(run: AnalysisRun, disclaimer: str) -> str:
    scores = run.scores
    lines = [
        "# AI Resume Reviewer — Analysis Report",
        "",
        f"**Status:** {run.status}",
        f"**Target role:** {run.target_role or 'N/A'}",
        f"**Experience level:** {run.experience_level or 'N/A'}",
        f"**Model:** {run.model_name or 'N/A'} (prompt {run.prompt_version or 'n/a'})",
        "",
    ]
    if scores:
        lines += [
            "## Scores",
            "",
            f"- Overall: **{scores.overall_score}/100**",
            f"- Job match: **{scores.job_match_score}%**",
            f"- ATS compatibility: **{scores.ats_score}/100**",
            "",
            "### Category breakdown",
            f"- Content quality: {scores.content_quality}/25",
            f"- Job relevance: {scores.job_relevance}/25",
            f"- Achievements: {scores.achievements}/15",
            f"- Skills match: {scores.skills_match}/15",
            f"- Readability: {scores.readability}/10",
            f"- ATS compatibility: {scores.ats_compatibility}/10",
            "",
        ]
    lines += ["## Strengths", ""]
    for s in run.strengths or []:
        lines.append(f"- {s}")
    lines += ["", "## Weaknesses", ""]
    for w in run.weaknesses or []:
        lines.append(f"- {w}")
    lines += ["", "## Matched skills", ""]
    for s in run.matched_skills or []:
        lines.append(f"- {s}")
    lines += ["", "## Missing keywords", ""]
    for k in run.missing_keywords or []:
        lines.append(f"- {k}")
    lines += ["", "## Recommendations", ""]
    for rec in run.recommendations or []:
        lines.append(f"- **[{rec.priority.upper()}]** ({rec.section}) {rec.message}")
    lines += ["", "---", "", f"_{disclaimer}_", ""]
    return "\n".join(lines)
