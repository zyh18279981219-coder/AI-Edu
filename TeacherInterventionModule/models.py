from __future__ import annotations

from typing import Literal, List

from pydantic import BaseModel, Field


class DiagnoseStudentsRequest(BaseModel):
    student_usernames: List[str] = Field(default_factory=list)


class GenerateInterventionDraftRequest(BaseModel):
    student_username: str = Field(..., min_length=1)
    question_count: int = Field(default=3, ge=1, le=8)
    difficulty: str = Field(default="中等", min_length=1, max_length=32)


class InterventionQuestionDraft(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=1)
    question_type: Literal["fill_blank", "single_choice", "multiple_choice", "code", "subjective"] = "subjective"
    options: List[str] = Field(default_factory=list)
    correct_answer: str = ""
    reference_answer: str = ""
    rubric: str = ""
    test_cases: List[dict] = Field(default_factory=list)
    difficulty: str = "中等"


class UpdateInterventionDraftRequest(BaseModel):
    strategy_summary: str = ""
    recommended_concepts: List[str] = Field(default_factory=list)
    recommended_videos: List[str] = Field(default_factory=list)
    questions: List[InterventionQuestionDraft] = Field(default_factory=list)


class StudentDecisionRequest(BaseModel):
    decision: Literal["accepted", "declined"]
    note: str = ""


class StudentProgressUpdateRequest(BaseModel):
    status: Literal["in_progress", "completed"]
    completion_rate: float = Field(default=0, ge=0, le=1)
    note: str = ""


class StudentAnswerUpdateRequest(BaseModel):
    question_id: str = Field(..., min_length=1)
    answer: str = ""
    note: str = ""


class TeacherQuestionGradeRequest(BaseModel):
    question_id: str = Field(..., min_length=1)
    teacher_score: float = Field(..., ge=0, le=100)
    teacher_comment: str = ""

