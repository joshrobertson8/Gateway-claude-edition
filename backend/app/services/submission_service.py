from sqlmodel import Session, select
from ..models import Submission, ProblemResponse, Problem
from . import ai_service


def create_submission(session: Session, activity_id: int) -> Submission:
    sub = Submission(activity_id=activity_id)
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


def get_submission(session: Session, submission_id: int) -> Submission | None:
    return session.get(Submission, submission_id)


async def submit_and_grade_response(
    session: Session, submission_id: int, problem_id: int, code: str
) -> ProblemResponse:
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

    problem = session.get(Problem, problem_id)
    if not problem:
        raise RuntimeError("problem missing")

    feedback = await ai_service.grade_submission(problem.problem_text, code)
    pr.ai_feedback = feedback
    session.add(pr)
    session.commit()
    session.refresh(pr)
    return pr


def get_response(
    session: Session, submission_id: int, problem_id: int
) -> ProblemResponse | None:
    return session.exec(
        select(ProblemResponse).where(
            ProblemResponse.submission_id == submission_id,
            ProblemResponse.problem_id == problem_id,
        )
    ).first()


async def generate_and_save_report(session: Session, submission_id: int) -> Submission:
    sub = session.get(Submission, submission_id)
    if not sub:
        raise RuntimeError("submission missing")

    responses = list(
        session.exec(
            select(ProblemResponse)
            .where(ProblemResponse.submission_id == submission_id)
            .order_by(ProblemResponse.id)
        )
    )
    items = []
    for pr in responses:
        problem = session.get(Problem, pr.problem_id)
        items.append(
            {
                "problem": problem.problem_text if problem else "",
                "code": pr.submitted_code,
                "feedback": pr.ai_feedback,
            }
        )

    report = await ai_service.generate_report(items)
    sub.feedback_report = report
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub
