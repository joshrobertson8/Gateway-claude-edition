from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- Activities ----
class CreateActivityRequest(CamelModel):
    content: str


class CreateActivityResponse(CamelModel):
    activity_id: int
    problems: List["ProblemModel"]


class ProblemModel(CamelModel):
    id: int
    sequence_number: int
    problem_text: str


class GetActivityProblemsResponse(CamelModel):
    activity_id: int
    problems: List[ProblemModel]


# ---- Submissions ----
class CreateSubmissionResponse(CamelModel):
    submission_id: int
    activity_id: int
    feedback_report: Optional[str] = None


class SubmitProblemResponseRequest(CamelModel):
    submitted_code: str


class SubmitProblemResponseResponse(CamelModel):
    problem_response_id: int
    ai_feedback: str


class GetProblemResponseResponse(CamelModel):
    id: int
    submission_id: int
    problem_id: int
    submitted_code: str
    ai_feedback: Optional[str] = None


class GenerateReportResponse(CamelModel):
    submission_id: int
    feedback_report: str


class GetReportResponse(CamelModel):
    submission_id: int
    feedback_report: Optional[str] = None


