from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import ensure_owner, resolve_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Resume, User
from app.schemas import MessageResponse, ResumeDetail, ResumeUploadResponse
from app.services.resume_extractor import (
    SUPPORTED_CONTENT_TYPES,
    SUPPORTED_EXTENSIONS,
    extract_text_from_bytes,
)
from app.services.storage import get_storage

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> ResumeUploadResponse:
    settings = get_settings()
    filename = file.filename or "resume.txt"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content_type = file.content_type or "application/octet-stream"
    if ext not in SUPPORTED_EXTENSIONS and content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Supported formats: PDF, DOCX, TXT")

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    try:
        text = extract_text_from_bytes(data, filename, content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {exc}") from exc

    storage = get_storage(settings)
    key = await storage.save(data, filename, content_type)
    resume = Resume(
        user_id=user.id,
        original_filename=filename,
        content_type=content_type,
        storage_key=key,
        file_size=len(data),
        extracted_text=text,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    preview = text[:400] + ("..." if len(text) > 400 else "")
    return ResumeUploadResponse(
        id=resume.id,
        original_filename=resume.original_filename,
        content_type=resume.content_type,
        file_size=resume.file_size,
        extracted_text_preview=preview,
        created_at=resume.created_at,
    )


@router.get("/{resume_id}", response_model=ResumeDetail)
async def get_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> ResumeDetail:
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    ensure_owner(resume.user_id, user)
    return ResumeDetail(
        id=resume.id,
        original_filename=resume.original_filename,
        content_type=resume.content_type,
        file_size=resume.file_size,
        extracted_text=resume.extracted_text,
        structured_data=resume.structured_data,
        created_at=resume.created_at,
    )


@router.delete("/{resume_id}", response_model=MessageResponse)
async def delete_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> MessageResponse:
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    ensure_owner(resume.user_id, user)
    storage = get_storage()
    try:
        await storage.delete(resume.storage_key)
    except Exception:  # noqa: BLE001
        pass
    db.delete(resume)
    db.commit()
    return MessageResponse(message="Resume deleted")
