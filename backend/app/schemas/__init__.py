from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    llm_provider: str
    storage_backend: str
    disclaimer: str


class ResumeUploadResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    file_size: int
    extracted_text_preview: str
    created_at: datetime


class ResumeDetail(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    file_size: int
    extracted_text: Optional[str] = None
    structured_data: Optional[dict[str, Any]] = None
    created_at: datetime


class JobDescriptionCreate(BaseModel):
    raw_text: str = Field(min_length=20)
    title: Optional[str] = None


class JobDescriptionResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    raw_text: str
    parsed_requirements: Optional[dict[str, Any]] = None
    created_at: datetime


class AnalysisCreate(BaseModel):
    resume_id: UUID
    job_description_id: Optional[UUID] = None
    target_role: Optional[str] = "Senior Full-Stack Developer"
    experience_level: Optional[str] = "senior"


class CategoryScores(BaseModel):
    content_quality: int
    job_relevance: int
    achievements: int
    skills_match: int
    readability: int
    ats_compatibility: int
    overall_score: int
    job_match_score: int
    ats_score: int
    skill_match_pct: int = 0
    experience_match_pct: int = 0
    keyword_match_pct: int = 0
    responsibility_match_pct: int = 0


class RecommendationOut(BaseModel):
    id: UUID
    priority: Literal["critical", "important", "optional"]
    section: str
    message: str


class AnalysisResponse(BaseModel):
    id: UUID
    status: str
    resume_id: UUID
    job_description_id: Optional[UUID] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    scores: Optional[CategoryScores] = None
    strengths: list[str] = []
    weaknesses: list[str] = []
    missing_keywords: list[str] = []
    matched_skills: list[str] = []
    recommendations: list[RecommendationOut] = []
    error_message: Optional[str] = None
    disclaimer: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class AnalysisSummary(BaseModel):
    id: UUID
    status: str
    target_role: Optional[str] = None
    overall_score: Optional[int] = None
    job_match_score: Optional[int] = None
    ats_score: Optional[int] = None
    created_at: datetime


class RewriteCreate(BaseModel):
    analysis_id: UUID
    section_type: str = Field(description="summary | experience_bullet | project | skills")
    original_text: str = Field(min_length=5)
    instruction: Optional[str] = "Add measurable impact and stronger action verbs"


class RewriteResponse(BaseModel):
    id: UUID
    analysis_run_id: UUID
    section_type: str
    original_text: str
    rewritten_text: str
    instruction: Optional[str] = None
    created_at: datetime


class ExportResponse(BaseModel):
    analysis_id: UUID
    markdown: str
    disclaimer: str


class MessageResponse(BaseModel):
    message: str
