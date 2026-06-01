"""
Question Generator (Groq API)
"""

import json
import logging
import re
from typing import List, Dict, Optional
from groq import Groq

from app.config import get_settings
from app.core.rag.retrieval import retrieve_for_profile, retrieve_chunks

logger = logging.getLogger(__name__)
settings = get_settings()

ROLE_LABELS = {
    "ai_ml": "AI/ML Engineer",
    "data_science": "Data Scientist / Applied ML",
    "advanced_ml": "Senior ML / Research Engineer",
}


def _get_client():
    return Groq(api_key=settings.groq_api_key)


def generate_interview_questions(
    profile: Dict,
    role: str,
    num_questions: int = None,
) -> List[Dict]:
    num_questions = num_questions or settings.num_questions
    client = _get_client()
    role_label = ROLE_LABELS.get(role, role.replace("_", " ").title())
    difficulty = profile.get("difficulty_hint", "intermediate")

    context_chunks = retrieve_for_profile(profile, role, num_queries=3)
    context_text = "\n---\n".join([c["text"][:300] for c in context_chunks[:4]])
    source_books = list({c["display_name"] for c in context_chunks})
    full_context_str = "\n---\n".join([c["text"][:200] for c in context_chunks[:3]])

    skills = ", ".join(profile.get("skills", [])[:5]) or "machine learning"
    tech = ", ".join(profile.get("technologies", [])[:4]) or "Python"
    experience = profile.get("experience_years", 0)

    prompt = f"""You are a senior technical interviewer for a {role_label} position.

Candidate: {experience} years experience. Skills: {skills}. Technologies: {tech}. Level: {difficulty}.

Knowledge base context (from ML textbooks):
{context_text}

Generate exactly {num_questions} interview questions grounded in this context.
Mix of conceptual, applied, and behavioral questions. Progress easy to hard.
No yes/no questions.

Return ONLY a JSON array of exactly {num_questions} objects:
[{{"question_text":"...","question_type":"conceptual|applied|behavioral","difficulty":"easy|medium|hard","topic_tags":["tag1","tag2"]}}]
No markdown, no explanation, only the JSON array."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        questions_raw = json.loads(raw)

        while len(questions_raw) < num_questions:
            questions_raw.extend(_fallback_questions(role_label, num_questions))

        questions = []
        for q in questions_raw[:num_questions]:
            questions.append({
                "question_text": q.get("question_text", ""),
                "question_type": q.get("question_type", "conceptual"),
                "difficulty": q.get("difficulty", difficulty),
                "topic_tags": q.get("topic_tags", []),
                "retrieved_context": full_context_str,
                "source_books": source_books,
            })

        logger.info(f"Generated {len(questions)} questions for role={role}")
        return questions

    except Exception as e:
        logger.error(f"Question generation error: {e}")
        return _fallback_questions(role_label, num_questions)


def generate_followup_question(
    previous_question: str,
    candidate_answer: str,
    profile: Dict,
    role: str,
) -> Optional[Dict]:
    client = _get_client()
    role_label = ROLE_LABELS.get(role, role)

    context_chunks = retrieve_chunks(candidate_answer[:200], role, top_k=2)
    context_text = "\n".join([c["text"][:150] for c in context_chunks]) if context_chunks else ""

    prompt = f"""Technical interviewer for {role_label}.
Previous Q: {previous_question[:200]}
Candidate answer: {candidate_answer[:300]}
Context: {context_text}

Generate ONE follow-up question that probes deeper.
Return ONLY JSON (no markdown):
{{"question_text":"...","question_type":"conceptual","difficulty":"hard","topic_tags":["..."],"retrieved_context":"","source_books":[]}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        raw = re.sub(r"```json\s*|\s*```", "", response.choices[0].message.content.strip()).strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Follow-up generation error: {e}")
        return None


def _fallback_questions(role_label: str, num: int) -> List[Dict]:
    base = [
        {
            "question_text": "Explain the bias-variance tradeoff and how it affects model selection.",
            "question_type": "conceptual",
            "difficulty": "medium",
            "topic_tags": ["bias-variance", "model selection"],
            "retrieved_context": "",
            "source_books": [],
        },
        {
            "question_text": "Describe a machine learning project you have worked on. What was your approach to feature engineering?",
            "question_type": "behavioral",
            "difficulty": "medium",
            "topic_tags": ["feature engineering", "project experience"],
            "retrieved_context": "",
            "source_books": [],
        },
        {
            "question_text": "What is overfitting and what techniques do you use to prevent it?",
            "question_type": "conceptual",
            "difficulty": "easy",
            "topic_tags": ["overfitting", "regularization"],
            "retrieved_context": "",
            "source_books": [],
        },
        {
            "question_text": "Explain the difference between supervised and unsupervised learning with examples.",
            "question_type": "conceptual",
            "difficulty": "easy",
            "topic_tags": ["supervised learning", "unsupervised learning"],
            "retrieved_context": "",
            "source_books": [],
        },
        {
            "question_text": "How do you handle missing data in a dataset before training a model?",
            "question_type": "applied",
            "difficulty": "medium",
            "topic_tags": ["data preprocessing", "missing values"],
            "retrieved_context": "",
            "source_books": [],
        },
        {
            "question_text": "What is cross-validation and why is it important in model evaluation?",
            "question_type": "conceptual",
            "difficulty": "medium",
            "topic_tags": ["cross-validation", "model evaluation"],
            "retrieved_context": "",
            "source_books": [],
        },
        {
            "question_text": "Explain gradient descent and its variants (SGD, Adam). When would you use each?",
            "question_type": "conceptual",
            "difficulty": "hard",
            "topic_tags": ["gradient descent", "optimization"],
            "retrieved_context": "",
            "source_books": [],
        },
        {
            "question_text": "How would you evaluate a classification model on an imbalanced dataset?",
            "question_type": "applied",
            "difficulty": "hard",
            "topic_tags": ["imbalanced data", "model evaluation", "metrics"],
            "retrieved_context": "",
            "source_books": [],
        },
    ]
    result = []
    while len(result) < num:
        result.extend(base)
    return result[:num]
