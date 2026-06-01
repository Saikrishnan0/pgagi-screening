from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import InterviewSession
from app.schemas.schemas import ResumeParseResponse
from app.core.resume_parser import extract_text_from_pdf_bytes, parse_resume

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload/{session_id}", response_model=ResumeParseResponse)
async def upload_resume(
    session_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a resume PDF for an existing session.
    Parses the resume and stores the extracted profile.
    """
    # Validate session
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate file type
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")

    # Read file
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Extract text
    if file.filename.lower().endswith(".pdf"):
        resume_text = extract_text_from_pdf_bytes(content)
    else:
        resume_text = content.decode("utf-8", errors="ignore")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the uploaded file")

    # Parse with AI
    profile = parse_resume(resume_text)

    # Persist to session
    session.resume_text = resume_text
    session.extracted_profile = profile
    await db.commit()

    return ResumeParseResponse(
        session_id=session_id,
        extracted_profile=profile,
        message=f"Resume parsed successfully for {profile.get('name', 'Candidate')}",
    )
