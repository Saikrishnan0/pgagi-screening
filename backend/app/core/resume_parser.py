"""
Resume Parser (Groq API)
"""

import json
import logging
import re
from typing import Dict
import fitz  # PyMuPDF
from groq import Groq

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_client():
    return Groq(api_key=settings.groq_api_key)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text("text")
        text = re.sub(r"\n{3,}", "\n\n", text)
        pages.append(text.strip())
    doc.close()
    return "\n\n".join(pages)


def parse_resume(resume_text: str) -> Dict:
    client = _get_client()

    prompt = f"""Extract structured information from this resume.
Return ONLY valid JSON, no markdown, no explanation.

Resume:
{resume_text[:2000]}

Return exactly this JSON structure:
{{
  "name": "candidate full name",
  "email": "email or null",
  "phone": "phone or null",
  "skills": ["list of ML/AI technical skills"],
  "technologies": ["programming languages, frameworks, tools"],
  "domains": ["application domains like NLP, Computer Vision etc"],
  "experience_years": 0,
  "education": ["degree and institution"],
  "projects": ["brief project titles, max 5"],
  "summary": "2-sentence professional summary",
  "difficulty_hint": "beginner or intermediate or advanced"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        profile = json.loads(raw)
        logger.info(f"Parsed resume for: {profile.get('name', 'Unknown')}")
        return profile
    except Exception as e:
        logger.error(f"Resume parsing error: {e}")
        return _fallback_parse(resume_text)


def _fallback_parse(resume_text: str) -> Dict:
    skill_keywords = [
        "machine learning", "deep learning", "neural network", "nlp",
        "computer vision", "supervised learning", "unsupervised learning",
        "reinforcement learning", "data science", "statistics",
        "feature engineering", "model evaluation", "clustering",
        "classification", "regression", "random forest", "gradient boosting",
    ]
    tech_keywords = [
        "python", "r", "tensorflow", "pytorch", "keras", "scikit-learn",
        "pandas", "numpy", "sql", "spark", "docker", "flask", "fastapi",
        "aws", "gcp", "azure", "git",
    ]
    text_lower = resume_text.lower()
    return {
        "name": "Candidate",
        "email": None,
        "phone": None,
        "skills": [s for s in skill_keywords if s in text_lower][:10],
        "technologies": [t for t in tech_keywords if t in text_lower][:10],
        "domains": [],
        "experience_years": 0,
        "education": [],
        "projects": [],
        "summary": "Resume parsed with fallback method.",
        "difficulty_hint": "intermediate",
    }
