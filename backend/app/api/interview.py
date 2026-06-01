from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.database import get_db
from app.models.models import InterviewSession, InterviewQuestion, SessionSummary, SessionStatus
from app.schemas.schemas import (
    StartInterviewResponse, QuestionResponse,
    SubmitAnswerRequest, AnswerResponse, SummaryResponse
)
from app.core.rag.generator import generate_interview_questions, generate_followup_question
from app.core.evaluator import evaluate_session
from app.config import get_settings

router = APIRouter(prefix="/interview", tags=["Interview"])
settings = get_settings()

# How many words in an answer trigger a follow-up
FOLLOWUP_WORD_THRESHOLD = 30
# Max follow-ups per session
MAX_FOLLOWUPS_PER_SESSION = 2


def _should_generate_followup(answer: str, followup_count: int) -> bool:
    """Decide whether this answer deserves a follow-up question."""
    if followup_count >= MAX_FOLLOWUPS_PER_SESSION:
        return False
    word_count = len(answer.strip().split())
    # Only follow up on substantial answers (candidate clearly knows something)
    return word_count >= FOLLOWUP_WORD_THRESHOLD


@router.post("/start/{session_id}", response_model=StartInterviewResponse)
async def start_interview(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate all questions for the session and return the first one.
    Requires resume to have been uploaded first.
    """
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.resume_text:
        raise HTTPException(status_code=400, detail="Please upload a resume before starting the interview")

    if session.status == SessionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Interview already completed")

    # Delete any existing questions (allow restart)
    existing = await db.execute(
        select(InterviewQuestion).where(InterviewQuestion.session_id == session_id)
    )
    for q in existing.scalars().all():
        await db.delete(q)
    await db.commit()

    # Generate questions via RAG pipeline
    profile = session.extracted_profile or {}
    questions_data = generate_interview_questions(
        profile=profile,
        role=session.target_role,
        num_questions=8,
    )

    # Persist questions to DB
    db_questions = []
    for i, q in enumerate(questions_data, 1):
        question = InterviewQuestion(
            session_id=session_id,
            sequence_number=i,
            question_text=q["question_text"],
            question_type=q.get("question_type", "conceptual"),
            difficulty=q.get("difficulty", "medium"),
            topic_tags=q.get("topic_tags", []),
            retrieved_context=q.get("retrieved_context", ""),
            source_books=q.get("source_books", []),
        )
        db.add(question)
        db_questions.append(question)

    session.status = SessionStatus.IN_PROGRESS
    session.total_questions = len(db_questions)
    await db.commit()
    for q in db_questions:
        await db.refresh(q)

    first_question = db_questions[0]
    return StartInterviewResponse(
        session_id=session_id,
        first_question=QuestionResponse.model_validate(first_question),
        total_questions=len(db_questions),
        message=f"Interview started! {len(db_questions)} questions generated.",
    )


@router.post("/answer/{question_id}", response_model=AnswerResponse)
async def submit_answer(
    question_id: str,
    payload: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit an answer for a question.
    If the answer is substantial, may inject a follow-up question.
    Returns the next question or signals completion.
    """
    result = await db.execute(
        select(InterviewQuestion).where(InterviewQuestion.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Save answer
    question.candidate_answer = payload.answer
    question.answered_at = datetime.utcnow()
    await db.commit()

    # Get session
    sess_result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == question.session_id)
    )
    session = sess_result.scalar_one_or_none()
    profile = session.extracted_profile or {}

    # Count existing follow-ups in this session
    all_q_result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.session_id == question.session_id)
        .order_by(InterviewQuestion.sequence_number)
    )
    all_questions = all_q_result.scalars().all()
    followup_count = sum(1 for q in all_questions if q.question_type == "followup")

    # Get next planned question
    next_q_result = await db.execute(
        select(InterviewQuestion).where(
            InterviewQuestion.session_id == question.session_id,
            InterviewQuestion.sequence_number == question.sequence_number + 1,
        ).limit(1)
    )
    next_question = next_q_result.scalars().first()

    # Decide whether to inject a follow-up BEFORE the next question
    if (
        next_question is not None
        and _should_generate_followup(payload.answer, followup_count)
        and question.question_type != "followup"  # don't follow up on follow-ups
    ):
        followup_data = generate_followup_question(
            previous_question=question.question_text,
            candidate_answer=payload.answer,
            profile=profile,
            role=session.target_role,
        )

        if followup_data and followup_data.get("question_text"):
            # Shift all subsequent questions up by 1 to make room
            for q in all_questions:
                if q.sequence_number > question.sequence_number:
                    q.sequence_number += 1

            # Insert follow-up right after current question
            followup_q = InterviewQuestion(
                session_id=question.session_id,
                sequence_number=question.sequence_number + 1,
                question_text=followup_data["question_text"],
                question_type="followup",
                difficulty=followup_data.get("difficulty", "hard"),
                topic_tags=followup_data.get("topic_tags", []),
                retrieved_context=followup_data.get("retrieved_context", ""),
                source_books=followup_data.get("source_books", []),
            )
            db.add(followup_q)
            session.total_questions = len(all_questions) + 1
            await db.commit()
            await db.refresh(followup_q)

            return AnswerResponse(
                question_id=question_id,
                next_question=QuestionResponse.model_validate(followup_q),
                is_complete=False,
                message="Interesting answer! Here's a follow-up question.",
            )

    # No follow-up — return next planned question or complete
    if next_question:
        return AnswerResponse(
            question_id=question_id,
            next_question=QuestionResponse.model_validate(next_question),
            is_complete=False,
            message="Answer recorded. Here's your next question.",
        )
    else:
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        await db.commit()
        return AnswerResponse(
            question_id=question_id,
            next_question=None,
            is_complete=True,
            message="Interview complete! Generating your evaluation...",
        )


@router.get("/questions/{session_id}", response_model=list[QuestionResponse])
async def get_all_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all questions for a session (useful for review)."""
    result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.session_id == session_id)
        .order_by(InterviewQuestion.sequence_number)
    )
    return result.scalars().all()


@router.post("/complete/{session_id}", response_model=SummaryResponse)
async def complete_and_evaluate(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger final evaluation and generate session summary.
    """
    sess_result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch all Q&A pairs
    q_result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.session_id == session_id)
        .order_by(InterviewQuestion.sequence_number)
    )
    questions = q_result.scalars().all()

    qa_pairs = [
        {
            "question": q.question_text,
            "answer": q.candidate_answer,
            "topic_tags": q.topic_tags or [],
            "difficulty": q.difficulty,
        }
        for q in questions
    ]

    answered_count = sum(1 for q in questions if q.candidate_answer)

    # Generate evaluation
    profile = session.extracted_profile or {}
    evaluation = evaluate_session(profile, session.target_role, qa_pairs)

    # Save or update summary
    existing_summary = await db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    )
    summary = existing_summary.scalar_one_or_none()

    if not summary:
        summary = SessionSummary(session_id=session_id)
        db.add(summary)

    summary.overall_score = evaluation.get("overall_score")
    summary.recommendation = evaluation.get("recommendation")
    summary.strengths = evaluation.get("strengths", [])
    summary.weaknesses = evaluation.get("weaknesses", [])
    summary.topic_scores = evaluation.get("topic_scores", [])
    summary.detailed_feedback = evaluation.get("detailed_feedback", "")
    summary.generated_at = datetime.utcnow()

    session.status = SessionStatus.COMPLETED
    session.completed_at = datetime.utcnow()
    await db.commit()

    return SummaryResponse(
        session_id=session_id,
        candidate_name=session.candidate_name,
        target_role=session.target_role,
        overall_score=summary.overall_score,
        recommendation=summary.recommendation,
        strengths=summary.strengths,
        weaknesses=summary.weaknesses,
        topic_scores=summary.topic_scores,
        detailed_feedback=summary.detailed_feedback,
        total_questions=session.total_questions,
        questions_answered=answered_count,
        generated_at=summary.generated_at,
    )


@router.get("/summary/{session_id}", response_model=SummaryResponse)
async def get_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the evaluation summary for a completed session."""
    sess_result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sum_result = await db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    )
    summary = sum_result.scalar_one_or_none()

    q_result = await db.execute(
        select(InterviewQuestion).where(InterviewQuestion.session_id == session_id)
    )
    questions = q_result.scalars().all()
    answered_count = sum(1 for q in questions if q.candidate_answer)

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not yet generated. Call POST /complete first.")

    return SummaryResponse(
        session_id=session_id,
        candidate_name=session.candidate_name,
        target_role=session.target_role,
        overall_score=summary.overall_score,
        recommendation=summary.recommendation,
        strengths=summary.strengths,
        weaknesses=summary.weaknesses,
        topic_scores=summary.topic_scores,
        detailed_feedback=summary.detailed_feedback,
        total_questions=session.total_questions,
        questions_answered=answered_count,
        generated_at=summary.generated_at,
    )
