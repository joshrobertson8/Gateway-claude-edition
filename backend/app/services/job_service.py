"""Job orchestration: persists job state and runs work in background tasks."""
import json
import asyncio
from datetime import datetime
from typing import Optional, Callable, Awaitable
from sqlmodel import Session
from ..database import engine
from ..models import AsyncJob

JOB_GENERATE_PROBLEMS = "generate_problems"
JOB_GRADE_RESPONSE = "grade_response"
JOB_GENERATE_REPORT = "generate_report"


def create_job(session: Session, job_type: str, payload: Optional[dict] = None) -> AsyncJob:
    job = AsyncJob(
        job_type=job_type,
        status="pending",
        payload=json.dumps(payload) if payload else None,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_job(session: Session, job_id: int) -> Optional[AsyncJob]:
    return session.get(AsyncJob, job_id)


def _update_job(job_id: int, **fields) -> None:
    with Session(engine) as s:
        job = s.get(AsyncJob, job_id)
        if not job:
            return
        for k, v in fields.items():
            setattr(job, k, v)
        job.updated_at = datetime.utcnow()
        s.add(job)
        s.commit()


async def run_job(job_id: int, work: Callable[[], Awaitable[None]]) -> None:
    """Generic runner: marks processing, runs `work`, marks done/failed."""
    _update_job(job_id, status="processing")
    try:
        await work()
        _update_job(job_id, status="completed")
    except Exception as e:  # noqa: BLE001
        _update_job(job_id, status="failed", error_message=str(e))


def schedule(coro):
    """Fire-and-forget an asyncio coroutine."""
    asyncio.create_task(coro)
