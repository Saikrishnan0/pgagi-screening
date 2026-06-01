"""
Session Evaluator (Groq API)
"""

import json
import logging
import re
from typing import Dict, List
from groq import Groq

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ROLE_LABELS = {
    "ai_ml": "AI/ML Engineer",
    "data_science": "Data Scientist / Applied ML",
    "advanced_ml": "Senior ML / Research Engineer",
}


def _get_client():
    return Groq(api_key=settings.groq_api_key)


def evaluate_session(
    profile: Dict,
    role: str,
    qa_pairs: List[Dict],
) -> Dict:
    client = _get_client()
    role_label = ROLE_LABELS.get(role, role)

    if not qa_pairs:
        return _empty_summary()

    qa_text = ""
    for i, pair in enumerate(qa_pairs, 1):
        qa_text += f"\nQ{i} [{pair.get('difficulty','medium').upper()}]: {pair['question']}\nA{i}: {(pair.get('answer','') or '')[:400]}\n---"

    profile_summary = f"Name: {profile.get('name','Candidate')}, Experience: {profile.get('experience_years',0)} years, Skills: {', '.join(profile.get('skills',[])[:5])}"

    prompt = f"""You are a hiring manager evaluating a {role_label} interview.

Candidate: {profile_summary}

Interview transcript:
{qa_text}

Evaluate performance. Return ONLY valid JSON (no markdown):
{{
  "overall_score": <0-100>,
  "recommendation": "<Strong Hire|Hire|Maybe|No Hire>",
  "strengths": ["strength1", "strength2", "strength3"],
  "weaknesses": ["weakness1", "weakness2"],
  "topic_scores": [
    {{"topic": "topic name", "score": <0-100>, "comment": "brief comment"}}
  ],
  "detailed_feedback": "3-4 paragraph assessment of technical depth, communication, practical knowledge, and areas to improve."
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )
        raw = re.sub(r"```json\s*|\s*```", "", response.choices[0].message.content.strip()).strip()
        result = json.loads(raw)
        logger.info(f"Evaluation complete. Score: {result.get('overall_score')}, Rec: {result.get('recommendation')}")
        return result
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        return _empty_summary()


def _empty_summary() -> Dict:
    return {
        "overall_score": None,
        "recommendation": "Insufficient data",
        "strengths": [],
        "weaknesses": ["Interview not completed"],
        "topic_scores": [],
        "detailed_feedback": "The interview session did not have enough responses to generate a full evaluation.",
    }
