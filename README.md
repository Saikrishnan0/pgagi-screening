# PGAGI AI Screening System

An AI-powered, role-based candidate screening system that conducts **dynamic technical interviews** grounded in real ML textbooks via a **RAG (Retrieval-Augmented Generation)** pipeline.

---

## 📽️ Demo Video

> [Add your demo video link here]

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Onboard  │  │  Interview   │  │   Results / Summary   │ │
│  │  Page    │→ │    Page      │→ │       Page            │ │
│  └──────────┘  └──────────────┘  └───────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (Axios)
┌────────────────────────▼────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                │
│                                                             │
│  /api/sessions/   →  Session lifecycle                      │
│  /api/resume/     →  PDF parse + profile extraction         │
│  /api/interview/  →  Start, answer, complete, summarise     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  AI/ML Pipeline                      │   │
│  │                                                     │   │
│  │  Resume Text                                        │   │
│  │      │                                              │   │
│  │      ▼                                              │   │
│  │  [Gemini] → Structured Profile                      │   │
│  │      │       (skills, tech, domains, difficulty)   │   │
│  │      │                                              │   │
│  │      ▼                                              │   │
│  │  Query Construction                                 │   │
│  │  (multi-query from profile fields)                  │   │
│  │      │                                              │   │
│  │      ▼                                              │   │
│  │  [ChromaDB] ← sentence-transformers embeddings      │   │
│  │  (role-scoped retrieval, cosine similarity)         │   │
│  │      │                                              │   │
│  │      ▼                                              │   │
│  │  Top-K Chunks → Context Window                      │   │
│  │      │                                              │   │
│  │      ▼                                              │   │
│  │  [Gemini] → 8 Interview Questions                   │   │
│  │  (role-aware, difficulty-matched, context-grounded) │   │
│  │      │                                              │   │
│  │      ▼                                              │   │
│  │  Q&A Loop → SQLite Storage                          │   │
│  │      │                                              │   │
│  │      ▼                                              │   │
│  │  [Gemini] → Structured Evaluation + Score           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      DATA LAYER                             │
│                                                             │
│  SQLite (SQLAlchemy async)     ChromaDB (persistent)        │
│  ┌──────────────────────┐     ┌──────────────────────────┐ │
│  │ interview_sessions   │     │ pgagi_knowledge          │ │
│  │ interview_questions  │     │ (vector embeddings from  │ │
│  │ session_summaries    │     │  7 ML textbooks)         │ │
│  └──────────────────────┘     └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Setup & Running

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### 1. Clone & Setup Backend

```bash
cd backend

# Create virtualenv
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 2. Prepare Knowledge Base

Download the 7 PDFs from the assignment resources and place them in `knowledge_base/` with these exact filenames:

```
knowledge_base/
├── mitchell_ml.pdf                  (Machine Learning — Tom Mitchell)
├── hundred_page_ml.pdf              (The Hundred-Page ML Book — Burkov)
├── ml_absolute_beginners.pdf        (ML for Absolute Beginners)
├── intro_ml_python.pdf              (Introduction to ML with Python)
├── master_ml_algorithms.pdf         (Master ML Algorithms — Brownlee)
├── bishop_pattern_recognition.pdf   (Pattern Recognition & ML — Bishop)
└── ai_ml_deep_learning.pdf          (AI, ML & Deep Learning)
```

### 3. Ingest Knowledge Base (Run Once)

```bash
cd backend
python scripts/ingest.py
```

This chunks all PDFs, generates embeddings using `sentence-transformers`, and stores them in ChromaDB. This takes ~5–15 minutes depending on your machine.

### 4. Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:3000

---

## 🧠 Key Design Decisions

### RAG Pipeline

**Chunking strategy**: Sentence-boundary sliding window with 600-character chunks and 80-character overlap. This preserves conceptual context while keeping chunks within embedding model limits. Pure character splitting would break mid-sentence, losing semantic coherence.

**Embedding model**: `all-MiniLM-L6-v2` — lightweight (80MB), fast inference, strong semantic quality for technical text. No API cost, fully local.

**Vector database**: ChromaDB with cosine similarity and HNSW indexing. Persisted locally, no infrastructure required, and supports metadata filtering for role-scoped retrieval.

**Multi-query retrieval**: Rather than a single query, we construct 4–5 diverse queries from different aspects of the candidate's profile (skills, technologies, domains) and deduplicate results. This produces a richer context pool that better covers the candidate's background.

**Role scoping**: Each chunk is tagged with role labels at ingestion time. Retrieval filters by role, ensuring questions are sourced from relevant books (e.g., Bishop's Pattern Recognition only for `advanced_ml` candidates).

### Question Generation

Questions are generated with the retrieved context injected directly into the prompt, making it structurally impossible to produce generic questions. The difficulty level and phrasing are guided by the candidate's `difficulty_hint` derived from their experience level.

### Resume Parsing

Gemini extracts a structured JSON profile including skills, technologies, domains, experience years, and a `difficulty_hint`. This profile then drives both query construction and question difficulty calibration — creating a closed feedback loop between the resume and the interview.

### Database Design

Three tables with clear separation of concerns:
- `interview_sessions` — core session state
- `interview_questions` — full traceability (what context was retrieved, which books were used)
- `session_summaries` — evaluation outputs, decoupled from Q&A

### API Design

RESTful, stateless API with clear lifecycle: `POST /sessions` → `POST /resume/upload` → `POST /interview/start` → `POST /interview/answer` (N times) → `POST /interview/complete`.

All business logic is in `app/core/`, keeping routes thin and testable.

---

## 📁 Project Structure

```
pgagi-screening/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + CORS + lifespan
│   │   ├── config.py                # Pydantic settings (env vars)
│   │   ├── api/
│   │   │   ├── sessions.py          # Session CRUD
│   │   │   ├── resume.py            # Resume upload & parsing
│   │   │   └── interview.py         # Full interview lifecycle
│   │   ├── core/
│   │   │   ├── resume_parser.py     # PDF text extraction + Gemini parsing
│   │   │   ├── evaluator.py         # Session scoring + feedback
│   │   │   └── rag/
│   │   │       ├── ingestion.py     # PDF → chunks → embeddings → ChromaDB
│   │   │       ├── retrieval.py     # Semantic search + role filtering
│   │   │       └── generator.py     # RAG-grounded question generation
│   │   ├── models/models.py         # SQLAlchemy ORM models
│   │   ├── schemas/schemas.py       # Pydantic request/response schemas
│   │   └── db/database.py           # Async DB engine + session
│   ├── scripts/ingest.py            # One-time KB ingestion script
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx             # Onboarding (name + role + resume)
│       │   ├── interview/page.tsx   # Live interview with progress
│       │   └── results/page.tsx     # Evaluation summary
│       └── lib/api.ts               # Typed API client
│
├── knowledge_base/                  # Place PDF books here
├── vector_store/                    # Auto-generated ChromaDB data
└── README.md
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sessions/` | Create interview session |
| GET | `/api/sessions/{id}` | Get session details |
| POST | `/api/resume/upload/{session_id}` | Upload & parse resume |
| POST | `/api/interview/start/{session_id}` | Generate questions, return first |
| POST | `/api/interview/answer/{question_id}` | Submit answer, get next question |
| GET | `/api/interview/questions/{session_id}` | All questions for session |
| POST | `/api/interview/complete/{session_id}` | Trigger evaluation |
| GET | `/api/interview/summary/{session_id}` | Get evaluation summary |

Full interactive docs: http://localhost:8000/docs

---

## 🎨 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Framer Motion |
| Backend | Python, FastAPI, SQLAlchemy (async) |
| Database | SQLite (via aiosqlite) |
| Vector Store | ChromaDB (persistent, local) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| LLM | Google Gemini 1.5 Flash |
| PDF Parsing | PyMuPDF (fitz) |
