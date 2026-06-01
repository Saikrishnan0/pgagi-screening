from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # AI
    groq_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./pgagi.db"

    # Vector Store
    chroma_persist_dir: str = "../vector_store"
    chroma_collection_name: str = "pgagi_knowledge"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # RAG
    chunk_size: int = 600
    chunk_overlap: int = 80
    top_k_retrieval: int = 5

    # Interview
    num_questions: int = 8
    max_follow_ups: int = 2

    # CORS
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
