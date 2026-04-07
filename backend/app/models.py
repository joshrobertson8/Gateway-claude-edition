from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AsyncJob(SQLModel, table=True):
    __tablename__ = "async_job"
    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: str
    status: str = "pending"  # pending | processing | completed | failed
    payload: Optional[str] = None  # JSON string
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Activity(SQLModel, table=True):
    __tablename__ = "activity"
    id: Optional[int] = Field(default=None, primary_key=True)
    docs: str
    generation_job_id: Optional[int] = Field(default=None, foreign_key="async_job.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Problem(SQLModel, table=True):
    __tablename__ = "problem"
    id: Optional[int] = Field(default=None, primary_key=True)
    activity_id: int = Field(foreign_key="activity.id")
    problem_text: str
    sequence_number: int


class Submission(SQLModel, table=True):
    __tablename__ = "submission"
    id: Optional[int] = Field(default=None, primary_key=True)
    activity_id: int = Field(foreign_key="activity.id")
    feedback_report: Optional[str] = None
    report_job_id: Optional[int] = Field(default=None, foreign_key="async_job.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProblemResponse(SQLModel, table=True):
    __tablename__ = "problem_response"
    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id")
    problem_id: int = Field(foreign_key="problem.id")
    submitted_code: str
    ai_feedback: Optional[str] = None
    grading_job_id: Optional[int] = Field(default=None, foreign_key="async_job.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
