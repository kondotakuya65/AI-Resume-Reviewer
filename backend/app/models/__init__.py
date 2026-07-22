import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base

# Use JSON for SQLite test compatibility; Postgres still works with JSON
JSONType = JSON().with_variant(JSONB(), "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    guest_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resumes: Mapped[list["Resume"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    job_descriptions: Mapped[list["JobDescription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    original_filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(128))
    storage_key: Mapped[str] = mapped_column(String(1024))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="resumes")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_requirements: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="job_descriptions")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="job_description")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    resume_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("resumes.id", ondelete="CASCADE"))
    job_description_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="pending")
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    strengths: Mapped[Optional[list[Any]]] = mapped_column(JSONType, nullable=True)
    weaknesses: Mapped[Optional[list[Any]]] = mapped_column(JSONType, nullable=True)
    missing_keywords: Mapped[Optional[list[Any]]] = mapped_column(JSONType, nullable=True)
    matched_skills: Mapped[Optional[list[Any]]] = mapped_column(JSONType, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="analysis_runs")
    resume: Mapped["Resume"] = relationship(back_populates="analysis_runs")
    job_description: Mapped[Optional["JobDescription"]] = relationship(back_populates="analysis_runs")
    scores: Mapped[Optional["AnalysisScore"]] = relationship(
        back_populates="analysis_run", uselist=False, cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    rewrite_requests: Mapped[list["RewriteRequest"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )


class AnalysisScore(Base):
    __tablename__ = "analysis_scores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id", ondelete="CASCADE"), unique=True
    )
    content_quality: Mapped[int] = mapped_column(Integer, default=0)
    job_relevance: Mapped[int] = mapped_column(Integer, default=0)
    achievements: Mapped[int] = mapped_column(Integer, default=0)
    skills_match: Mapped[int] = mapped_column(Integer, default=0)
    readability: Mapped[int] = mapped_column(Integer, default=0)
    ats_compatibility: Mapped[int] = mapped_column(Integer, default=0)
    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    job_match_score: Mapped[int] = mapped_column(Integer, default=0)
    ats_score: Mapped[int] = mapped_column(Integer, default=0)
    skill_match_pct: Mapped[int] = mapped_column(Integer, default=0)
    experience_match_pct: Mapped[int] = mapped_column(Integer, default=0)
    keyword_match_pct: Mapped[int] = mapped_column(Integer, default=0)
    responsibility_match_pct: Mapped[int] = mapped_column(Integer, default=0)

    analysis_run: Mapped["AnalysisRun"] = relationship(back_populates="scores")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    priority: Mapped[str] = mapped_column(String(32))
    section: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)

    analysis_run: Mapped["AnalysisRun"] = relationship(back_populates="recommendations")


class RewriteRequest(Base):
    __tablename__ = "rewrite_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id", ondelete="CASCADE")
    )
    section_type: Mapped[str] = mapped_column(String(64))
    original_text: Mapped[str] = mapped_column(Text)
    rewritten_text: Mapped[str] = mapped_column(Text)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analysis_run: Mapped["AnalysisRun"] = relationship(back_populates="rewrite_requests")
