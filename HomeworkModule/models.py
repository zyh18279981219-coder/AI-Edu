from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


AssignmentType = Literal["subjective", "objective", "choice", "code", "code_practice"]
AssignmentStatus = Literal["draft", "published", "closed"]
SubmissionStatus = Literal["submitted", "graded"]


class QuestionDraft(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=1)
    options: List[str] = Field(default_factory=list)
    correct_answer: str = ""
    reference_answer: str = ""
    rubric: str = ""
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)


class AssignmentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    assignment_type: AssignmentType
    class_name: str = ""
    due_at: Optional[str] = None
    allow_late: bool = False
    total_score: float = Field(default=100, ge=0)
    rubric: str = ""
    questions: List[QuestionDraft] = Field(default_factory=list)
    publish_now: bool = False


class AssignmentUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    assignment_type: AssignmentType
    class_name: str = ""
    due_at: Optional[str] = None
    allow_late: bool = False
    total_score: float = Field(default=100, ge=0)
    rubric: str = ""
    questions: List[QuestionDraft] = Field(default_factory=list)


class AssignmentQuestionGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    assignment_type: AssignmentType
    count: int = Field(default=3, ge=1, le=10)
    difficulty: str = Field(default="medium", max_length=32)
    language: str = Field(default="zh")
    extra_requirements: str = ""


class AIAssignmentDraftRequest(BaseModel):
    assignment_type: AssignmentType = "subjective"
    topic: str = Field(..., min_length=1, max_length=200)
    difficulty: str = Field(default="中等", max_length=32)
    class_name: str = ""


class AssignmentDetailRequest(BaseModel):
    assignment_id: str = Field(..., min_length=1)


class AssignmentSubmitRequest(BaseModel):
    answers: List[Dict[str, Any]] = Field(default_factory=list)


class AIGradeRequest(BaseModel):
    force_regenerate: bool = False


class FinalGradeRequest(BaseModel):
    teacher_score: float = Field(..., ge=0)
    teacher_comment: str = ""


class AssignmentRecord(BaseModel):
    id: str
    title: str
    description: str
    assignment_type: AssignmentType
    class_name: str = ""
    due_at: Optional[str] = None
    allow_late: bool = False
    total_score: float = 100.0
    rubric: str = ""
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    created_by: str
    created_at: str
    status: AssignmentStatus = "draft"


class SubmissionRecord(BaseModel):
    id: str
    assignment_id: str
    student_username: str
    answers: List[Dict[str, Any]] = Field(default_factory=list)
    submitted_at: str
    status: SubmissionStatus = "submitted"
    ai_score: Optional[float] = None
    ai_feedback: str = ""
    ai_rationale: str = ""
    teacher_score: Optional[float] = None
    teacher_comment: str = ""
    graded_at: Optional[str] = None
    grader_username: str = ""
