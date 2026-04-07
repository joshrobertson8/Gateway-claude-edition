from sqlmodel import Session, select
from ..database import engine
from ..models import Activity, Problem, AsyncJob
from ..config import PROBLEMS_PER_ACTIVITY
from . import ai_service, job_service


def create_activity(session: Session, content: str) -> tuple[Activity, AsyncJob]:
    activity = Activity(docs=content)
    session.add(activity)
    session.commit()
    session.refresh(activity)

    job = job_service.create_job(
        session,
        job_service.JOB_GENERATE_PROBLEMS,
        {"activity_id": activity.id},
    )
    activity.generation_job_id = job.id
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return activity, job


async def generate_problems_work(activity_id: int, job_id: int) -> None:
    """Background work: call AI, save problems, write result on job."""

    async def work():
        with Session(engine) as s:
            activity = s.get(Activity, activity_id)
            if not activity:
                raise RuntimeError("activity missing")
            content = activity.docs

        problems = await ai_service.generate_problems(content, PROBLEMS_PER_ACTIVITY)

        with Session(engine) as s:
            for i, text in enumerate(problems):
                s.add(Problem(activity_id=activity_id, problem_text=text, sequence_number=i + 1))
            s.commit()
            job = s.get(AsyncJob, job_id)
            if job:
                job.result = f"generated {len(problems)} problems"
                s.add(job)
                s.commit()

    await job_service.run_job(job_id, work)


def list_problems(session: Session, activity_id: int) -> list[Problem]:
    return list(
        session.exec(
            select(Problem).where(Problem.activity_id == activity_id).order_by(Problem.sequence_number)
        )
    )
