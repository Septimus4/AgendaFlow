"""API configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Keys
    mistral_api_key: str
    openagenda_api_key: str
    hf_token: str = None

    # Service Configuration
    rag_model_name: str = "mistral-small-latest"
    index_path: str = "data/index/faiss"
    city: str = "Paris"

    # OpenAgenda Mode
    openagenda_mode: str = "agenda"  # agenda | transverse | fallback_odsd

    # Security
    rebuild_token: str = "change_me_in_production"

    # Optional: Model overrides
    embedding_model: str = "mistral-embed"
    embedding_cache_dir: str = "data/embeddings_cache"

    # Optional: API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # Optional: Retrieval Configuration
    k_initial: int = 60
    k_final: int = 10
    mmr_diversity: float = 0.3

    # Optional: Rate Limiting
    max_requests_per_minute: int = 30

    # Timeouts
    retrieval_timeout: float = 5.0
    generation_timeout: float = 30.0
    total_timeout: float = 40.0

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
