"""SQLite-хранилище задач. Сохраняется на диск, переживает перезапуск сервера."""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import aiosqlite

from config import settings
from app.parsers.base import ParsedBook, TextSegment


DB_PATH = settings.STORAGE_UPLOADS.parent / "jobs.db"


def _serialize_book(book: ParsedBook) -> str:
    """Сериализует ParsedBook в JSON."""
    segments = []
    for seg in book.segments:
        segments.append({
            "id": seg.id,
            "text": seg.text,
            "chapter": seg.chapter,
            "order": seg.order,
            "mapping": seg.mapping or {},
        })

    return json.dumps({
        "title": book.title,
        "author": book.author,
        "language": book.language,
        "segments": segments,
        "metadata": book.metadata,
    }, ensure_ascii=False)


def _deserialize_book(data: str) -> ParsedBook:
    """Обратно: JSON → ParsedBook."""
    obj = json.loads(data)
    segments = []
    for s in obj["segments"]:
        segments.append(TextSegment(
            id=s["id"],
            text=s["text"],
            chapter=s["chapter"],
            order=s["order"],
            mapping=s.get("mapping", {}),
        ))
    return ParsedBook(
        title=obj["title"],
        author=obj["author"],
        language=obj["language"],
        segments=segments,
        metadata=obj.get("metadata", {}),
    )


class JobStore:
    """SQLite-хранилище задач."""

    def __init__(self) -> None:
        self.db_path = str(DB_PATH)

    async def init(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    book_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'created',
                    progress INTEGER NOT NULL DEFAULT 0,
                    total_segments INTEGER NOT NULL DEFAULT 0,
                    email TEXT NOT NULL DEFAULT '',
                    payment_id TEXT NOT NULL DEFAULT '',
                    receipt_email TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT ''
                )
            """)
            
            # 🛡️ Добавляем колонки, если их нет (для старых баз)
            try:
                await db.execute("ALTER TABLE jobs ADD COLUMN payment_id TEXT NOT NULL DEFAULT ''")
            except Exception:
                pass
            
            try:
                await db.execute("ALTER TABLE jobs ADD COLUMN receipt_email TEXT NOT NULL DEFAULT ''")
            except Exception:
                pass

            await db.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    job_id TEXT NOT NULL,
                    chapter_index INTEGER NOT NULL,
                    translations_json TEXT NOT NULL,
                    PRIMARY KEY (job_id, chapter_index),
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            """)
            await db.commit()

    async def create(self, filename: str, book: ParsedBook) -> str:
        """Создаёт новую задачу."""
        job_id = uuid.uuid4().hex[:12]
        created_at = datetime.now().isoformat(timespec="seconds")
        book_json = _serialize_book(book)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO jobs (id, filename, book_json, created_at, total_segments)
                   VALUES (?, ?, ?, ?, ?)""",
                (job_id, filename, book_json, created_at, len(book.segments)),
            )
            await db.commit()

        return job_id

    async def get(self, job_id: str) -> Optional[dict]:
        """Возвращает dict с полями job."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()

        if row is None:
            return None

        # 🛡️ Безопасное чтение (защита от старых баз)
        keys = row.keys()
        
        return {
            "id": row["id"],
            "filename": row["filename"],
            "book": _deserialize_book(row["book_json"]),
            "created_at": row["created_at"],
            "status": row["status"],
            "progress": row["progress"],
            "total_segments": row["total_segments"],
            "email": row["email"],
            "error": row["error"],
            "payment_id": row["payment_id"] if "payment_id" in keys else "",
            "receipt_email": row["receipt_email"] if "receipt_email" in keys else "",
        }

    async def update_status(self, job_id: str, status: str, error: str = "") -> None:
        """Обновляет статус задачи."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET status = ?, error = ? WHERE id = ?",
                (status, error, job_id),
            )
            await db.commit()

    async def update_progress(self, job_id: str, progress: int) -> None:
        """Обновляет прогресс (число переведённых сегментов)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET progress = ? WHERE id = ?",
                (progress, job_id),
            )
            await db.commit()

    async def set_email(self, job_id: str, email: str) -> None:
        """Сохраняет email для уведомления."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET email = ? WHERE id = ?",
                (email, job_id),
            )
            await db.commit()

    async def set_receipt_email(self, job_id: str, email: str) -> None:
        """Сохраняет email для отправки чека."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET receipt_email = ? WHERE id = ?",
                (email, job_id),
            )
            await db.commit()

    async def save_translation(
        self,
        job_id: str,
        chapter_index: int,
        translations: dict,
    ) -> None:
        """Сохраняет переводы для главы/страницы."""
        data = json.dumps(translations, ensure_ascii=False)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO translations (job_id, chapter_index, translations_json)
                   VALUES (?, ?, ?)""",
                (job_id, chapter_index, data),
            )
            await db.commit()

    async def get_translation(self, job_id: str, chapter_index: int) -> Optional[dict]:
        """Возвращает переводы для главы/страницы."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT translations_json FROM translations WHERE job_id = ? AND chapter_index = ?",
                (job_id, chapter_index),
            )
            row = await cursor.fetchone()

        if row is None:
            return None
        return json.loads(row[0])

    async def set_payment_id(self, job_id: str, payment_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET payment_id = ? WHERE id = ?",
                (payment_id, job_id),
            )
            await db.commit()    

    async def cleanup_old(self, ttl_hours: int = 24) -> int:
        """Удаляет задачи старше N часов."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=ttl_hours)).isoformat(timespec="seconds")

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM jobs WHERE created_at < ?", (cutoff,))
            count = (await cursor.fetchone())[0]
            await db.execute("DELETE FROM jobs WHERE created_at < ?", (cutoff,))
            await db.commit()

        return count


job_store = JobStore()
