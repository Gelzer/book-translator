"""Эндпоинты превью и полного перевода книги."""
import asyncio
import shutil
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse

from config import settings
from app.parsers.epub_parser import parse_epub
from app.translators.genapi_client import translate_text, translate_batch
from app.placeholders.restorer import restore_placeholders
from app.builders.epub_builder import build_translated_epub
from app.core.session import job_store

router = APIRouter(prefix="/preview", tags=["preview"])

PREVIEW_SEGMENTS = 40
BATCH_SIZE = 5

KEY_PREVIEW = 0
KEY_FULL_BOOK = 1


# ============================================================
# ЗАГРУЗКА
# ============================================================

@router.post("/upload")
async def preview_upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".epub"):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Только .epub"},
        )

    upload_path = settings.STORAGE_UPLOADS / file.filename
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        book = parse_epub(str(upload_path))
        job_id = await job_store.create(file.filename, book)

        preview_segments = [s for s in book.segments if len(s.text.strip()) > 3][:PREVIEW_SEGMENTS]
        total_segments = len(book.segments)
        estimated_minutes = max(1, total_segments // 40)

        return {
            "status": "ok",
            "job_id": job_id,
            "title": book.title,
            "author": book.author,
            "language": book.language,
            "total_segments": total_segments,
            "preview_count": len(preview_segments),
            "estimated_minutes": estimated_minutes,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# ============================================================
# ПРЕВЬЮ
# ============================================================

@router.post("/translate")
async def preview_translate(job_id: str = Form(...)):
    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "job_id не найден или истёк"},
        )

    book = job["book"]
    segments_to_translate = [s for s in book.segments if len(s.text.strip()) > 3][:PREVIEW_SEGMENTS]

    if not segments_to_translate:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "В книге нет текста для перевода"},
        )

    translations_map, errors = await _translate_segments(
        segments_to_translate, book.language
    )

    results = []
    translations_for_save = {}

    for seg in segments_to_translate:
        if seg.id in translations_map:
            translated = translations_map[seg.id]
            translated_html = restore_placeholders(translated, seg.mapping or {})
            results.append({
                "id": seg.id,
                "original_html": seg.text,
                "translated_html": translated_html,
            })
            translations_for_save[seg.id] = translated
        else:
            err_msg = next(
                (e["error"] for e in errors if e["id"] == seg.id),
                "не получен перевод от API",
            )
            results.append({"id": seg.id, "error": err_msg})

    await job_store.save_translation(job_id, KEY_PREVIEW, translations_for_save)

    return {
        "status": "ok",
        "translated_count": len(translations_for_save),
        "results": results,
    }


# ============================================================
# ПОЛНЫЙ ПЕРЕВОД (фоновая задача)
# ============================================================

async def _translate_book_background(job_id: str) -> None:
    try:
        job = await job_store.get(job_id)
        if not job:
            return

        book = job["book"]
        segments = [s for s in book.segments if len(s.text.strip()) > 3]

        if not segments:
            await job_store.update_status(job_id, "error", "Нет текста для перевода")
            return

        total = len(segments)
        await job_store.update_status(job_id, "translating")

        translations_map = {}

        for i in range(0, total, BATCH_SIZE):
            batch_segs = segments[i:i + BATCH_SIZE]
            batch_input = [(s.id, s.text) for s in batch_segs]

            if settings.MOCK_TRANSLATION:
                await asyncio.sleep(0.3)

            try:
                result = translate_batch(
                    batch_input,
                    source_lang=book.language,
                    target_lang="ru",
                )
                translations_map.update(result)

                missing_ids = {s.id for s in batch_segs} - set(result.keys())
                for seg_id in missing_ids:
                    text = next((t for sid, t in batch_input if sid == seg_id), None)
                    if not text:
                        continue
                    try:
                        translated = translate_text(
                            text,
                            source_lang=book.language,
                            target_lang="ru",
                        )
                        translations_map[seg_id] = translated
                    except Exception:
                        pass
            except Exception:
                for seg_id, text in batch_input:
                    try:
                        translated = translate_text(
                            text,
                            source_lang=book.language,
                            target_lang="ru",
                        )
                        translations_map[seg_id] = translated
                    except Exception:
                        pass

            await job_store.update_progress(job_id, min(i + BATCH_SIZE, total))

        await job_store.save_translation(job_id, KEY_FULL_BOOK, translations_map)
        await job_store.update_status(job_id, "done")

    except Exception as e:
        try:
            await job_store.update_status(job_id, "error", str(e))
        except Exception:
            pass


@router.post("/translate-full")
async def preview_translate_full(
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
):
    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "job_id не найден"},
        )

    if job["status"] == "translating":
        return {
            "status": "ok",
            "message": "Перевод уже идёт",
            "job_id": job_id,
            "already_running": True,
        }

    if job["status"] == "done":
        return {
            "status": "ok",
            "message": "Перевод уже готов",
            "job_id": job_id,
            "already_done": True,
        }

    await job_store.update_status(job_id, "translating")
    background_tasks.add_task(_translate_book_background, job_id)

    return {
        "status": "ok",
        "job_id": job_id,
        "total_segments": job["total_segments"],
        "estimated_minutes": max(1, job["total_segments"] // 40),
    }


@router.get("/status/{job_id}")
async def preview_status(job_id: str):
    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "job_id не найден"},
        )

    return {
        "status": "ok",
        "job_status": job["status"],
        "progress": job["progress"],
        "total": job["total_segments"],
        "error": job["error"],
    }


@router.post("/set-email")
async def preview_set_email(
    job_id: str = Form(...),
    email: str = Form(...),
):
    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "job_id не найден"},
        )

    email = email.strip()[:200]
    if "@" not in email or "." not in email:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Некорректный email"},
        )

    await job_store.set_email(job_id, email)
    return {"status": "ok", "message": "Email сохранён"}


# ============================================================
# СКАЧИВАНИЕ
# ============================================================

@router.post("/download")
async def preview_download(job_id: str = Form(...)):
    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "job_id не найден"},
        )

    translations = await job_store.get_translation(job_id, KEY_FULL_BOOK)
    if not translations:
        translations = await job_store.get_translation(job_id, KEY_PREVIEW)

    if not translations:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Сначала переведите книгу"},
        )

    book = job["book"]
    source_path = book.metadata.get("file_path")
    if not source_path:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Не найден исходный файл"},
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"{timestamp}_{job['filename']}"
    output_path = settings.STORAGE_OUTPUTS / output_name

    try:
        build_translated_epub(
            source_path=source_path,
            output_path=str(output_path),
            translations=translations,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )

    return FileResponse(
        path=str(output_path),
        media_type="application/epub+zip",
        filename=f"translated_{job['filename']}",
    )


# ============================================================
# ВСПОМОГАТЕЛЬНОЕ
# ============================================================

async def _translate_segments(segments, source_lang: str):
    batch_input = [(seg.id, seg.text) for seg in segments]
    batches = [
        batch_input[i:i + BATCH_SIZE]
        for i in range(0, len(batch_input), BATCH_SIZE)
    ]

    translations_map = {}
    errors = []

    for batch in batches:
        expected_ids = {seg_id for seg_id, _ in batch}
        try:
            result = translate_batch(batch, source_lang=source_lang, target_lang="ru")
            translations_map.update(result)

            missing_ids = expected_ids - set(result.keys())
            for seg_id in missing_ids:
                text = next((t for i, t in batch if i == seg_id), None)
                if not text:
                    continue
                try:
                    translated = translate_text(text, source_lang=source_lang, target_lang="ru")
                    translations_map[seg_id] = translated
                except Exception as e2:
                    errors.append({"id": seg_id, "error": str(e2)})
        except Exception:
            for seg_id, text in batch:
                try:
                    translated = translate_text(text, source_lang=source_lang, target_lang="ru")
                    translations_map[seg_id] = translated
                except Exception as e2:
                    errors.append({"id": seg_id, "error": str(e2)})

    return translations_map, errors