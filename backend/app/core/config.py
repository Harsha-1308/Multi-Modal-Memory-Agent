import os
from typing import List
from dotenv import load_dotenv


load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Project Memory Agent")

    HINDSIGHT_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "")

    HINDSIGHT_BASE_URL: str = os.getenv(
        "HINDSIGHT_BASE_URL",
        "https://api.hindsight.vectorize.io",
    )

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    GROQ_MODEL: str = os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-120b",
    )

    GROQ_VISION_MODEL: str = os.getenv(
        "GROQ_VISION_MODEL",
        "qwen/qwen3.8-27b",
    )

    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./data/project_memory.db",
    )

    STORAGE_ROOT: str = os.getenv("STORAGE_ROOT", "./data/storage")

    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))

    @property
    def cors_origins_list(self) -> List[str]:
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def sqlite_db_path(self) -> str:
        if self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL.replace("sqlite:///", "", 1)
        elif self.DATABASE_URL.startswith("sqlite://"):
            return self.DATABASE_URL.replace("sqlite://", "", 1)
        return self.DATABASE_URL


settings = Settings()