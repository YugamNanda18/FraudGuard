"""Application configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """FraudAI Agent configuration.

    Reads from environment variables and .env file.
    """

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b-instruct-q4_K_M"
    ollama_keep_alive: str = "5m"

    # LLM Provider
    llm_provider: str = "groq"  # "anthropic" | "groq" | "openai"
    llm_model: str = "groq/compound"  # default Groq model
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # Auth / JWT
    jwt_secret: str = "fraudai-dev-secret-change-in-production"

    # App
    log_level: str = "INFO"
    environment: str = "development"
    cors_allowed_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
