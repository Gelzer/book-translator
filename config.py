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

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # --- ЮKassa ---
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")
    YOOKASSA_RETURN_URL: str = os.getenv("YOOKASSA_RETURN_URL", "http://localhost:8000/ui/")
    BOOK_PRICE_RUB: int = int(os.getenv("BOOK_PRICE_RUB", "990"))

    # --- Email (SMTP) ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.yandex.ru")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Book Translator")
    PUBLIC_URL: str = os.getenv("PUBLIC_URL", "http://localhost:8000")

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
