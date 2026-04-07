from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from ..database import get_session
from ..schemas import (
    CreateActivityRequest,
    CreateActivityResponse,
    GetActivityProblemsResponse,
    ProblemModel,
)
from ..services import activity_service

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.post("", response_model=CreateActivityResponse)
async def create_activity(
    body: CreateActivityRequest, session: Session = Depends(get_session)
):
    if not body.content.strip():
        raise HTTPException(400, "content required")
    activity, problems = await activity_service.create_activity_with_problems(
        session, body.content
    )
    return CreateActivityResponse(
        activity_id=activity.id,
        problems=[
            ProblemModel(
                id=p.id, sequence_number=p.sequence_number, problem_text=p.problem_text
            )
            for p in problems
        ],
    )


@router.get("/{activity_id}/problems", response_model=GetActivityProblemsResponse)
def get_problems(activity_id: int, session: Session = Depends(get_session)):
    problems = activity_service.list_problems(session, activity_id)
    return GetActivityProblemsResponse(
        activity_id=activity_id,
        problems=[
            ProblemModel(id=p.id, sequence_number=p.sequence_number, problem_text=p.problem_text)
            for p in problems
        ],
    )
