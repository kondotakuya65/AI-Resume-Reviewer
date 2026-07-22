from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import resolve_user
from app.db.session import get_db
from app.models import JobDescription, User
from app.schemas import JobDescriptionCreate, JobDescriptionResponse

router = APIRouter(prefix="/job-descriptions", tags=["job-descriptions"])


@router.post("", response_model=JobDescriptionResponse)
async def create_job_description(
    payload: JobDescriptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(resolve_user),
) -> JobDescriptionResponse:
    jd = JobDescription(user_id=user.id, title=payload.title, raw_text=payload.raw_text)
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return JobDescriptionResponse(
        id=jd.id,
        title=jd.title,
        raw_text=jd.raw_text,
        parsed_requirements=jd.parsed_requirements,
        created_at=jd.created_at,
    )
