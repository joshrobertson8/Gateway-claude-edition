from sqlmodel import Session, select
from ..database import engine
from ..models import Submission, ProblemResponse, Problem, AsyncJob
from . import ai_service, job_service


def create_submission(session: Session, activity_id: int) -> Submission:
    sub = Submission(activity_id=activity_id)
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


def get_submission(session: Session, submission_id: int) -> Submission | None:
    return session.get(Submission, submission_id)


def submit_response(
    session: Session, submission_id: int, problem_id: int, code: str
) -> tuple[ProblemResponse, AsyncJob]:
    # upsert problem_response
    existing = session.exec(
        select(ProblemResponse).where(
            ProblemResponse.submission_id == submission_id,
            ProblemResponse.problem_id == problem_id,
        )
    ).first()
    if existing:
        existing.submitted_code = code
        existing.ai_feedback = None
        pr = existing
    else:
        pr = ProblemResponse(
            submission_id=submission_id, problem_id=problem_id, submitted_code=code
        )
    session.add(pr)
    session.commit()
    session.refresh(pr)

    job = job_service.create_job(
        session,
        job_service.JOB_GRADE_RESPONSE,
        {"problem_response_id": pr.id},
    )
    pr.grading_job_id = job.id
    session.add(pr)
    session.commit()
    session.refresh(pr)
    return pr, job


def get_response(
    session: Session, submission_id: int, problem_id: int
) -> ProblemResponse | None:
    return session.exec(
        select(ProblemResponse).where(
            ProblemResponse.submission_id == submission_id,
            ProblemResponse.problem_id == problem_id,
        )
    ).first()


async def grade_response_work(problem_response_id: int, job_id: int) -> None:
    async def work():
        with Session(engine) as s:
            pr = s.get(ProblemResponse, problem_response_id)
            if not pr:
                raise RuntimeError("response missing")
            problem = s.get(Problem, pr.problem_id)
            if not problem:
                raise RuntimeError("problem missing")
            problem_text = problem.problem_text
            code = pr.submitted_code

        feedback = await ai_service.grade_submission(problem_text, code)

        with Session(engine) as s:
            pr = s.get(ProblemResponse, problem_response_id)
            pr.ai_feedback = feedback
            s.add(pr)
            job = s.get(AsyncJob, job_id)
            if job:
                job.result = feedback
                s.add(job)
            s.commit()

    await job_service.run_job(job_id, work)


def start_report(session: Session, submission_id: int) -> AsyncJob:
    job = job_service.create_job(
        session, job_service.JOB_GENERATE_REPORT, {"submission_id": submission_id}
    )
    sub = session.get(Submission, submission_id)
    if sub:
        sub.report_job_id = job.id
        session.add(sub)
        session.commit()
    return job


async def generate_report_work(submission_id: int, job_id: int) -> None:
    async def work():
        with Session(engine) as s:
            responses = list(
                s.exec(
                    select(ProblemResponse)
                    .where(ProblemResponse.submission_id == submission_id)
                    .order_by(ProblemResponse.id)
                )
            )
            items = []
            for pr in responses:
                problem = s.get(Problem, pr.problem_id)
                items.append(
                    {
                        "problem": problem.problem_text if problem else "",
                        "code": pr.submitted_code,
                        "feedback": pr.ai_feedback,
                    }
                )

        report = await ai_service.generate_report(items)

        with Session(engine) as s:
            sub = s.get(Submission, submission_id)
            if sub:
                sub.feedback_report = report
                s.add(sub)
            job = s.get(AsyncJob, job_id)
            if job:
                job.result = report
                s.add(job)
            s.commit()

    await job_service.run_job(job_id, work)
