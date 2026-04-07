from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from ..database import get_session
from ..schemas import GetJobResponse
from ..services import job_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=GetJobResponse)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = job_service.get_job(session, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return GetJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        result=job.result,
        error_message=job.error_message,
    )
