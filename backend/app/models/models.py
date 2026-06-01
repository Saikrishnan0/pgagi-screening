from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime
import uuid
import enum


class Base(DeclarativeBase):
    pass


class SessionStatus(str, enum.Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_name = Column(String(255), nullable=False)
    target_role = Column(String(100), nullable=False)
    resume_text = Column(Text, nullable=False)
    extracted_profile = Column(JSON, nullable=True)   # skills, tech, experience
    status = Column(Enum(SessionStatus), default=SessionStatus.CREATED)
    total_questions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    summary = relationship("SessionSummary", back_populates="session", uselist=False, cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), default="conceptual")   # conceptual | applied | behavioral
    difficulty = Column(String(20), default="medium")          # easy | medium | hard
    topic_tags = Column(JSON, nullable=True)                   # e.g. ["supervised learning", "overfitting"]
    retrieved_context = Column(Text, nullable=True)            # which book chunks were used
    source_books = Column(JSON, nullable=True)                 # traceability
    candidate_answer = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="questions")


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False, unique=True)
    overall_score = Column(Integer, nullable=True)              # 0-100
    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)
    topic_scores = Column(JSON, nullable=True)                  # per-topic breakdown
    recommendation = Column(String(50), nullable=True)          # Strong Yes / Yes / No
    detailed_feedback = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="summary")
