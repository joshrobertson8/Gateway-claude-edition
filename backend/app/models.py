from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Activity(SQLModel, table=True):
    __tablename__ = "activity"
    id: Optional[int] = Field(default=None, primary_key=True)
    docs: str
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
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProblemResponse(SQLModel, table=True):
    __tablename__ = "problem_response"
    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id")
    problem_id: int = Field(foreign_key="problem.id")
    submitted_code: str
    ai_feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
