"""Эндпоинт для отзывов и предложений."""
import json
from datetime import datetime
from pathlib import Path
from threading import Lock

import httpx
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from config import settings

router = APIRouter(prefix="/feedback", tags=["feedback"])

FEEDBACK_FILE = settings.STORAGE_UPLOADS.parent / "feedback.json"
_lock = Lock()


def _load_feedback() -> list:
    if not FEEDBACK_FILE.exists():
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_feedback(items: list) -> None:
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _send_telegram(item: dict) -> None:
    """Отправляет отзыв в Telegram. Тихо игнорирует ошибки."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return

    type_label = "⭐ Отзыв" if item["type"] == "review" else "💡 Предложение"
    rating_str = ""
    if item.get("rating"):
        stars = "★" * item["rating"] + "☆" * (5 - item["rating"])
        rating_str = f"\n{stars} ({item['rating']}/5)"

    email_str = f"\n📧 {item['email']}" if item.get("email") else ""

    text = (
        f"{type_label}{rating_str}{email_str}\n"
        f"🕐 {item['created_at']}\n\n"
        f"{item['text']}"
    )

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(url, json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": True,
            })
    except Exception:
        # Не ломаем запрос пользователя, если телега недоступна
        pass


@router.post("/submit")
async def submit_feedback(
    type: str = Form(...),
    text: str = Form(...),
    rating: int = Form(0),
    email: str = Form(""),
):
    """Сохраняет отзыв и отправляет в Telegram."""
    if type not in ("review", "suggestion"):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "type должен быть review или suggestion"},
        )

    text = text.strip()
    if len(text) < 3:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Слишком короткий текст"},
        )
    if len(text) > 3000:
        text = text[:3000]

    if type == "review" and not (1 <= rating <= 5):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Оценка должна быть от 1 до 5"},
        )

    item = {
        "type": type,
        "rating": rating if type == "review" else None,
        "text": text,
        "email": email.strip()[:100] if email else "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    # 1) Сохраняем в файл (для локальной разработки)
    with _lock:
        items = _load_feedback()
        items.append(item)
        _save_feedback(items)

    # 2) Отправляем в Telegram (работает везде, включая Render)
    _send_telegram(item)

    return {"status": "ok", "message": "Спасибо! Мы получили ваш отзыв."}
