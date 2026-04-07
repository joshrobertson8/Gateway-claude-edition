from sqlmodel import Session, select
from ..models import Activity, Problem
from ..config import PROBLEMS_PER_ACTIVITY
from . import ai_service


async def create_activity_with_problems(
    session: Session, content: str
) -> tuple[Activity, list[Problem]]:
    activity = Activity(docs=content)
    session.add(activity)
    session.commit()
    session.refresh(activity)

    problem_texts = await ai_service.generate_problems(content, PROBLEMS_PER_ACTIVITY)

    problems: list[Problem] = []
    for i, text in enumerate(problem_texts):
        p = Problem(activity_id=activity.id, problem_text=text, sequence_number=i + 1)
        session.add(p)
        problems.append(p)
    session.commit()
    for p in problems:
        session.refresh(p)
    return activity, problems


def list_problems(session: Session, activity_id: int) -> list[Problem]:
    return list(
        session.exec(
            select(Problem)
            .where(Problem.activity_id == activity_id)
            .order_by(Problem.sequence_number)
        )
    )
