from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    AI_ML = "ai_ml"
    DATA_SCIENCE = "data_science"
    ADVANCED_ML = "advanced_ml"


# ── Session ──────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    candidate_name: str = Field(..., min_length=2, max_length=255)
    target_role: RoleEnum


class SessionResponse(BaseModel):
    id: str
    candidate_name: str
    target_role: str
    status: str
    total_questions: int
    created_at: datetime
    extracted_profile: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ── Resume ───────────────────────────────────────────────────────────────────

class ResumeParseResponse(BaseModel):
    session_id: str
    extracted_profile: Dict[str, Any]
    message: str


# ── Questions ────────────────────────────────────────────────────────────────

class QuestionResponse(BaseModel):
    id: str
    session_id: str
    sequence_number: int
    question_text: str
    question_type: str
    difficulty: str
    topic_tags: Optional[List[str]] = None
    source_books: Optional[List[str]] = None

    class Config:
        from_attributes = True


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=5000)


class AnswerResponse(BaseModel):
    question_id: str
    next_question: Optional[QuestionResponse] = None
    is_complete: bool
    message: str


# ── Summary ──────────────────────────────────────────────────────────────────

class TopicScore(BaseModel):
    topic: str
    score: int
    comment: str


class SummaryResponse(BaseModel):
    session_id: str
    candidate_name: str
    target_role: str
    overall_score: Optional[int]
    recommendation: Optional[str]
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    topic_scores: Optional[List[Dict[str, Any]]]
    detailed_feedback: Optional[str]
    total_questions: int
    questions_answered: int
    generated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Interview Start ───────────────────────────────────────────────────────────

class StartInterviewResponse(BaseModel):
    session_id: str
    first_question: QuestionResponse
    total_questions: int
    message: str
