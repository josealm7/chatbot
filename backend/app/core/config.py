from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Anthropic (opcional)
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")

    # Groq (gratuito)
    groq_api_key: str = Field("", env="GROQ_API_KEY")

    # Vector store
    vector_store: str = Field("chroma", env="VECTOR_STORE")
    pinecone_api_key: str = Field("", env="PINECONE_API_KEY")
    pinecone_index_name: str = Field("smartchat-docs", env="PINECONE_INDEX_NAME")
    chroma_persist_dir: str = Field("./data/chroma_db", env="CHROMA_PERSIST_DIR")

    # App
    app_env: str = Field("development", env="APP_ENV")
    secret_key: str = Field("dev-secret-key", env="SECRET_KEY")
    allowed_origins: str = Field("http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:5173", env="ALLOWED_ORIGINS")

    # Default bot config
    default_company_name: str = Field("Mi Empresa S.L.", env="DEFAULT_COMPANY_NAME")
    default_bot_name: str = Field("Asistente Virtual", env="DEFAULT_BOT_NAME")
    default_industry: str = Field("seguros", env="DEFAULT_INDUSTRY")

    # LLM config
    model_name: str = "llama-3.1-8b-instant"
    max_tokens: int = 1024
    temperature: float = 0.3
    retrieval_k: int = 4
    similarity_threshold: float = 0.35

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()