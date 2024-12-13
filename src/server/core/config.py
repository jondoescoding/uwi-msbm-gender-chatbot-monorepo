# Built-in imports
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from typing import Optional

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings using Pydantic"""
    # API Configuration
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    environment: Optional[str] = None
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    
    # MongoDB Settings
    MONGODB_CONNECTION_STRING: str = os.getenv("MONGODB_CONNECTION_STRING", "")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "")
    MONGODB_COLLECTION_NAME: str = os.getenv("MONGODB_COLLECTION_NAME", "articles")
    
    # AstraDB Settings
    ASTRA_DB_API_ENDPOINT: str = os.getenv("ASTRA_DB_API_ENDPOINT", "")
    ASTRA_DB_APPLICATION_TOKEN: str = os.getenv("ASTRA_DB_APPLICATION_TOKEN", "")
    ASTRA_DB_NAMESPACE: str = os.getenv("ASTRA_DB_NAMESPACE", "")
    
    # Application Settings
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "news_article_with_llm_summary_hypo_qs_v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "Alibaba-NLP/gte-large-en-v1.5")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt4o")
    MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "5"))
    
    # New fields with exact case matching
    huggingface_api_key: str = os.getenv("huggingface_api_key", "")
    openrouter_api_key: str = os.getenv("openrouter_api_key", "")
    langchain_tracing_v2: bool = os.getenv("langchain_tracing_v2", "False").lower() == "true"
    langchain_endpoint: str = os.getenv("langchain_endpoint", "")
    langchain_api_key: str = os.getenv("langchain_api_key", "")
    langchain_project: str = os.getenv("langchain_project", "")
    username: str = os.getenv("username", "")
    password: str = os.getenv("password", "")
    mongodb_atlas_cluster_uri: str = os.getenv("mongodb_atlas_cluster_uri", "")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow"
    }

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()