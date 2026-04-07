from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from ..database import get_session
from ..schemas import (
    CreateSubmissionResponse,
    SubmitProblemResponseRequest,
    SubmitProblemResponseResponse,
    GetProblemResponseResponse,
    GenerateReportResponse,
    GetReportResponse,
    RunCodeRequest,
    RunCodeResponse,
)
from ..services import submission_service, job_service, runner_service, ai_service

router = APIRouter(tags=["submissions"])


@router.post("/api/activities/{activity_id}/submissions", response_model=CreateSubmissionResponse)
def create_submission(activity_id: int, session: Session = Depends(get_session)):
    sub = submission_service.create_submission(session, activity_id)
    return CreateSubmissionResponse(
        submission_id=sub.id, activity_id=sub.activity_id, feedback_report=sub.feedback_report
    )


@router.post(
    "/api/submissions/{submission_id}/problems/{problem_id}/responses",
    response_model=SubmitProblemResponseResponse,
)
async def submit_response(
    submission_id: int,
    problem_id: int,
    body: SubmitProblemResponseRequest,
    session: Session = Depends(get_session),
):
    pr, job = submission_service.submit_response(
        session, submission_id, problem_id, body.submitted_code
    )
    job_service.schedule(submission_service.grade_response_work(pr.id, job.id))
    return SubmitProblemResponseResponse(
        problem_response_id=pr.id, job_id=job.id, status=job.status
    )


@router.get(
    "/api/submissions/{submission_id}/problems/{problem_id}/responses",
    response_model=GetProblemResponseResponse,
)
def get_response(submission_id: int, problem_id: int, session: Session = Depends(get_session)):
    pr = submission_service.get_response(session, submission_id, problem_id)
    if not pr:
        raise HTTPException(404, "no response yet")
    return GetProblemResponseResponse(
        id=pr.id,
        submission_id=pr.submission_id,
        problem_id=pr.problem_id,
        submitted_code=pr.submitted_code,
        ai_feedback=pr.ai_feedback,
        grading_job_id=pr.grading_job_id,
    )


@router.post("/api/submissions/{submission_id}/report", response_model=GenerateReportResponse)
async def start_report(submission_id: int, session: Session = Depends(get_session)):
    job = submission_service.start_report(session, submission_id)
    job_service.schedule(submission_service.generate_report_work(submission_id, job.id))
    return GenerateReportResponse(submission_id=submission_id, job_id=job.id, status=job.status)


@router.get("/api/submissions/{submission_id}/report", response_model=GetReportResponse)
def get_report(submission_id: int, session: Session = Depends(get_session)):
    sub = submission_service.get_submission(session, submission_id)
    if not sub:
        raise HTTPException(404, "submission not found")
    return GetReportResponse(submission_id=sub.id, feedback_report=sub.feedback_report)


# ---- Helpers ----
@router.post("/api/run", response_model=RunCodeResponse)
async def run_code(body: RunCodeRequest):
    out, err, code = await runner_service.run_python(body.code)
    return RunCodeResponse(stdout=out, stderr=err, exit_code=code)


@router.post("/api/hint")
async def hint(body: dict):
    problem_text = body.get("problemText", "")
    code = body.get("code", "")
    text = await ai_service.generate_hint(problem_text, code)
    return {"hint": text}
