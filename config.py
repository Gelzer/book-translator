"""Читает переменные из .env и отдаёт их остальному коду."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # --- GenAPI ---
    GENAPI_API_KEY: str = os.getenv("GENAPI_API_KEY", "")
    GENAPI_BASE_URL: str = os.getenv("GENAPI_BASE_URL", "https://api.gen-api.ru/v1")
    GENAPI_MODEL: str = os.getenv("GENAPI_MODEL", "gpt-4o-mini")
    MOCK_TRANSLATION: bool = os.getenv("MOCK_TRANSLATION", "false").lower() == "true"

    # --- Сервер ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # --- Файлы ---
    STORAGE_UPLOADS: Path = BASE_DIR / os.getenv("STORAGE_UPLOADS", "storage/uploads")
    STORAGE_OUTPUTS: Path = BASE_DIR / os.getenv("STORAGE_OUTPUTS", "storage/outputs")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    FILE_TTL_HOURS: int = int(os.getenv("FILE_TTL_HOURS", "24"))

    def ensure_dirs(self) -> None:
        self.STORAGE_UPLOADS.mkdir(parents=True, exist_ok=True)
        self.STORAGE_OUTPUTS.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()