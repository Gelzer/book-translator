"""Эндпоинты превью и полного перевода книги."""
import asyncio
import httpx
import shutil
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Request, Body
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse

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

async def _require_paid(job: dict) -> tuple[bool, str, str]:
    """
    Проверяет оплату задачи.
    Возвращает (ok, message, status):
      - ok=True,  message="",    status="succeeded" — оплачено, можно работать
      - ok=False, message="...", status="pending"   — обрабатывается, ждём
      - ok=False, message="...", status="canceled"|"refunded"|"error" — не пускаем
    """
    from app.payments.yookassa_client import client as yookassa_client

    payment_id = job.get("payment_id") or ""
    if not payment_id:
        return False, "Требуется оплата", "no_payment"

    try:
        payment = yookassa_client.get_payment(payment_id)
    except Exception:
        return False, "Сервис оплаты временно недоступен. Попробуйте через минуту.", "error"

    status = payment.get("status", "unknown")

    # Проверяем, что платёж относится именно к этой задаче
    metadata = payment.get("metadata") or {}
    if metadata.get("job_id") != job["id"]:
        return False, "Платёж не относится к этой задаче", "error"

    if status == "succeeded":
        return True, "", "succeeded"

    if status in ("pending", "waiting_for_capture"):
        return False, "Оплата обрабатывается, подождите пару минут и обновите страницу", "pending"

    if status == "canceled":
        return False, "Платёж отменён. Попробуйте оплатить заново.", "canceled"

    if status == "refunded":
        return False, "Платёж возвращён. Для доступа к переводу требуется новая оплата.", "refunded"

    return False, f"Платёж в неизвестном статусе: {status}", "error"

@router.post("/upload")
async def preview_upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".epub"):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Только .epub"},
        )

    # 🔒 БЕЗОПАСНОСТЬ: берем только имя файла (без путей), добавляем UUID для уникальности
    original_name = Path(file.filename).name
    safe_filename = f"{uuid.uuid4().hex[:8]}_{original_name}"

    upload_path = settings.STORAGE_UPLOADS / safe_filename
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        book = parse_epub(str(upload_path))
        # Сохраняем в БД оригинальное имя (чтобы при скачивании файл назывался красиво)
        job_id = await job_store.create(original_name, book)
        
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

    # 🔒 ПРОВЕРКА: Если превью уже переводили — отдаем из базы, не тратя деньги на GenAPI
    existing_preview = await job_store.get_translation(job_id, KEY_PREVIEW)
    if existing_preview:
        results = []
        for seg in segments_to_translate:
            if seg.id in existing_preview:
                translated_html = restore_placeholders(existing_preview[seg.id], seg.mapping or {})
                results.append({
                    "id": seg.id,
                    "original_html": seg.text,
                    "translated_html": translated_html,
                })
        return {
            "status": "ok",
            "translated_count": len(existing_preview),
            "results": results,
            "cached": True  # Пометка, что это из кэша
        }

    # Если превью еще нет — переводим
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
        translations_map = {}

        await job_store.update_status(job_id, "translating")
        await job_store.update_progress(job_id, 0)

        for i in range(0, total, BATCH_SIZE):
            batch_segs = segments[i:i + BATCH_SIZE]
            batch_input = [(s.id, s.text) for s in batch_segs]

            if settings.MOCK_TRANSLATION:
                await asyncio.sleep(0.3)
            else:
                # 🛑 ПАУЗА: Чтобы не получить ошибку 429 Too Many Requests
                await asyncio.sleep(1.5)

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
                            text, source_lang=book.language, target_lang="ru",
                        )
                        translations_map[seg_id] = translated
                    except Exception as e:
                        print(f"[TRANSLATION ERROR] Сегмент {seg_id} упал: {e}")
            except Exception as e:
                print(f"[TRANSLATION ERROR] Батч упал: {e}")
                for seg_id, text in batch_input:
                    try:
                        translated = translate_text(
                            text, source_lang=book.language, target_lang="ru",
                        )
                        translations_map[seg_id] = translated
                    except Exception as e2:
                        print(f"[TRANSLATION ERROR] Одиночный сегмент {seg_id} упал: {e2}")

            await job_store.update_progress(job_id, min(i + BATCH_SIZE, total))

        if not translations_map:
            await job_store.update_status(job_id, "error", "GenAPI не вернул ни одного перевода. Проверьте логи.")
            return

        await job_store.save_translation(job_id, KEY_FULL_BOOK, translations_map)
        await job_store.update_status(job_id, "done")
        
        # ... (блок с email оставляем как есть) ...

        try:
            job = await job_store.get(job_id)
            if job and job.get("email"):
                ok, err = send_translation_ready(
                    to_email=job["email"],
                    job_id=job_id,
                    book_title=job["book"].title or "Ваша книга",
                )
                if not ok:
                    print(f"EMAIL SEND FAILED для {job['email']}: {err}")
        except Exception as e:
            print(f"EMAIL EXCEPTION: {e}")

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

    # 🔒 Проверка оплаты — без неё нельзя запустить полный перевод
    paid, err_msg, pay_status = await _require_paid(job)
    if not paid:
        return JSONResponse(
            status_code=402,
            content={
                "status": "error",
                "message": err_msg,
                "payment_status": pay_status,
            },
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


@router.post("/set-receipt-email")
async def preview_set_receipt_email(
    job_id: str = Form(...),
    email: str = Form(...),
):
    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"status": "error", "message": "job_id не найден"})

    email = email.strip()[:200]
    if "@" not in email or "." not in email:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Некорректный email"})

    await job_store.set_receipt_email(job_id, email)

    # 🚨 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ БРАТУ В TELEGRAM
    try:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if bot_token and chat_id:
            book_title = job["book"].title or "Без названия"
            text = (
                f"🧾 **Новый запрос на чек!**\n\n"
                f"📖 Книга: {book_title}\n"
                f"📧 Почта клиента: `{email}`\n"
                f"🆔 ID задачи: `{job_id}`\n\n"
                f"Не забудьте сформировать чек в 'Мой налог' и отправить его на этот адрес!"
            )
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Отправляем асинхронно, чтобы не задерживать ответ клиенту
            async with httpx.AsyncClient() as client:
                await client.post(url, json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }, timeout=10.0)
    except Exception as e:
        print(f"Ошибка при отправке уведомления в Telegram: {e}")

    return {"status": "ok", "message": "Email для чека сохранён"}


@router.post("/download")
async def preview_download(job_id: str = Form(...)):
    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "job_id не найден"},
        )

    # Сначала пытаемся получить полный перевод
    full_translations = await job_store.get_translation(job_id, KEY_FULL_BOOK)

    if full_translations:
        # 🔒 Полный перевод — только после оплаты
        paid, err_msg, pay_status = await _require_paid(job)
        if not paid:
            return JSONResponse(
                status_code=402,
                content={
                    "status": "error",
                    "message": err_msg,
                    "payment_status": pay_status,
                },
            )
        translations = full_translations
    else:
        # Превью — бесплатно, оплата не нужна
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


@router.post("/create-payment")
async def create_payment(job_id: str = Form(...)):
    from app.payments.yookassa_client import client as yookassa_client

    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "job_id не найден"},
        )

    return_url = f"{settings.YOOKASSA_RETURN_URL}?job_id={job_id}&payment=1"
    description = f"Перевод книги: {job['book'].title}"

    try:
        payment = yookassa_client.create_payment(
            amount_rub=settings.BOOK_PRICE_RUB,
            description=description,
            return_url=return_url,
            metadata={"job_id": job_id},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Ошибка ЮKassa: {e}"},
        )

    await job_store.set_payment_id(job_id, payment["id"])

    return {
        "status": "ok",
        "payment_id": payment["id"],
        "confirmation_url": payment["confirmation"]["confirmation_url"],
    }


@router.post("/verify-payment")
async def verify_payment(job_id: str = Form(...)):
    from app.payments.yookassa_client import client as yookassa_client

    job = await job_store.get(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "job_id не найден"},
        )

    payment_id = job.get("payment_id", "")
    if not payment_id:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Платёж не создан"},
        )

    try:
        payment = yookassa_client.get_payment(payment_id)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Ошибка ЮKassa: {e}"},
        )

    pay_status = payment.get("status", "unknown")
    paid = pay_status == "succeeded"

    return {
        "status": "ok",
        "paid": paid,
        "payment_status": pay_status,
        "processing": pay_status in ("pending", "waiting_for_capture"),
    }


@router.get("/job/{job_id}", response_class=HTMLResponse)
async def job_page(job_id: str):
    job = await job_store.get(job_id)
    if not job:
        return HTMLResponse(
            content="""
            <html><body style="font-family:sans-serif;max-width:600px;margin:80px auto;padding:20px;text-align:center;">
            <h1 style="color:#7a1f4a;">Задача не найдена</h1>
            <p>Ссылка устарела или задача удалена (через 24 часа).</p>
            <a href="/ui/" style="color:#7a1f4a;">← Вернуться на главную</a>
            </body></html>
            """,
            status_code=404,
        )

    status = job["status"]
    progress = job["progress"]
    total = job["total_segments"]

    if status == "done":
        # Проверяем, сохранена ли уже почта для чека
        receipt_email = job.get("receipt_email", "")
        
        if not receipt_email:
            receipt_form = f"""
            <div style="margin-top: 30px; padding: 20px; background: #fafaf7; border: 1px solid #e5e7eb; border-radius: 12px; text-align: left;">
                <h3 style="margin-top: 0; margin-bottom: 8px; font-size: 16px;">🧾 Получить официальный чек</h3>
                <p style="font-size: 13px; color: #6b7280; margin-bottom: 12px;">Пожалуйста, укажите email для получения чека (требование законодательства РФ). Мы отправим его в течение 24 часов.</p>
                <form onsubmit="event.preventDefault(); saveReceipt('{job_id}');" style="display: flex; gap: 10px;">
                    <input type="email" id="receipt-email-input" placeholder="your@email.com" required style="flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                    <button type="submit" style="padding: 10px 20px; background: #7a1f4a; color: white; border: none; border-radius: 5px; cursor: pointer;">Отправить</button>
                </form>
                <p id="receipt-msg" style="font-size: 13px; color: #15803d; margin-top: 10px; display: none;">✅ Почта сохранена! Чек придет на указанный адрес.</p>
            </div>
            <script>
                async function saveReceipt(jobId) {{
                    const email = document.getElementById('receipt-email-input').value;
                    const fd = new FormData();
                    fd.append('job_id', jobId);
                    fd.append('email', email);
                    const res = await fetch('/preview/set-receipt-email', {{ method: 'POST', body: fd }});
                    if (res.ok) {{
                        document.getElementById('receipt-email-input').disabled = true;
                        document.querySelector('#receipt-email-input + button').disabled = true;
                        document.getElementById('receipt-msg').style.display = 'block';
                    }} else {{
                        alert('Ошибка при сохранении.');
                    }}
                }}
            </script>
            """
        else:
            receipt_form = f"""
            <div style="margin-top: 30px; padding: 20px; background: #fafaf7; border: 1px solid #e5e7eb; border-radius: 12px;">
                <h3 style="margin-top: 0; font-size: 16px;">🧾 Чек об оплате</h3>
                <p style="font-size: 14px; color: #15803d;">✅ Чек будет отправлен на почту: <strong>{receipt_email}</strong></p>
            </div>
            """

        body = f"""
        <h1 style="color:#15803d;">✅ Перевод готов</h1>
        <p><strong>{job['book'].title}</strong></p>
        <p>{job['book'].author}</p>
        <form method="post" action="/preview/download" style="margin-top:30px;">
            <input type="hidden" name="job_id" value="{job_id}">
            <button type="submit" style="padding:14px 28px;background:#15803d;color:white;border:none;border-radius:10px;font-size:15px;cursor:pointer; width: 100%;">
                ⬇ Скачать EPUB
            </button>
        </form>
        {receipt_form}
        """
    elif status == "error":
        body = f"""
        <h1 style="color:#b91c1c;">❌ Ошибка перевода</h1>
        <p>{job.get('error', 'Неизвестная ошибка')}</p>
        """
    else:
        pct = int((progress / total * 100) if total > 0 else 0)
        body = f"""
        <h1 style="color:#7a1f4a;">⏳ Перевод книги…</h1>
        <p>{progress} / {total} ({pct}%)</p>
        <div style="height:10px;background:#f0f0f0;border-radius:100px;overflow:hidden;margin:20px 0;">
            <div style="height:100%;background:#7a1f4a;width:{pct}%;"></div>
        </div>
        <p style="color:#666;font-size:13px;">Обновляйте страницу, чтобы увидеть прогресс</p>
        """

    html = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>Перевод книги</title></head>
    <body style="font-family:-apple-system,sans-serif;max-width:600px;margin:80px auto;padding:20px;color:#1a1a1a;">
      {body}
      <p style="margin-top:40px;color:#999;font-size:12px;">Book Translator · Job ID: {job_id}</p>
    </body></html>
    """
    return HTMLResponse(content=html)


async def _translate_segments(segments, source_lang: str):
    batch_input = [(seg.id, seg.text) for seg in segments]
    # Создаем словарь для быстрого поиска mapping по id
    mapping_by_id = {seg.id: (seg.mapping or {}) for seg in segments}
    
    batches = [
        batch_input[i:i + BATCH_SIZE]
        for i in range(0, len(batch_input), BATCH_SIZE)
    ]

    translations_map = {}
    errors = []

    from app.utils.validator import validate_translation # Импортируем валидатор

    for batch in batches:
        expected_ids = {seg_id for seg_id, _ in batch}
        try:
            result = translate_batch(
                batch, source_lang=source_lang, target_lang="ru",
            )
            
            # Проверяем КАЖДЫЙ переведенный сегмент
            for seg_id, translated_text in result.items():
                original_text = next((t for sid, t in batch if sid == seg_id), "")
                mapping = mapping_by_id.get(seg_id, {})
                
                is_valid, val_errors = validate_translation(original_text, translated_text, mapping)
                
                if is_valid:
                    translations_map[seg_id] = translated_text
                else:
                    # Если QA не прошел — логируем и будем переводить по одному
                    print(f"[QA WARNING] Сегмент {seg_id} не прошел проверку: {val_errors}")
                    # Нам нужно добавить его в список "пропущенных", чтобы перевести заново
                    
            # Ищем те, что потерялись или не прошли QA
            missing_or_failed_ids = expected_ids - set(translations_map.keys())
            
            for seg_id in missing_or_failed_ids:
                text = next((t for i, t in batch if i == seg_id), None)
                if not text:
                    continue
                try:
                    # Переводим по одному куску (точнее, но дороже)
                    translated = translate_text(
                        text, source_lang=source_lang, target_lang="ru",
                    )
                    # Проверяем еще раз
                    is_valid, val_errors = validate_translation(text, translated, mapping_by_id.get(seg_id, {}))
                    if is_valid:
                        translations_map[seg_id] = translated
                    else:
                        errors.append({"id": seg_id, "error": f"QA failed: {val_errors}"})
                except Exception as e2:
                    errors.append({"id": seg_id, "error": str(e2)})
                    
        except Exception:
            # Если батч упал полностью — переводим по одному
            for seg_id, text in batch:
                try:
                    translated = translate_text(
                        text, source_lang=source_lang, target_lang="ru",
                    )
                    translations_map[seg_id] = translated
                except Exception as e2:
                    errors.append({"id": seg_id, "error": str(e2)})

    return translations_map, errors

@router.post("/webhook/yookassa")
async def yookassa_webhook(background_tasks: BackgroundTasks, data: dict = Body(...)):
    """
    Вебхук от ЮKassa. Сюда приходят уведомления об оплате.
    """
    event = data.get("event")
    
    # Нас интересует только успешная оплата
    if event == "payment.succeeded":
        payment = data.get("object", {})
        metadata = payment.get("metadata", {})
        job_id = metadata.get("job_id")
        
        if job_id:
            job = await job_store.get(job_id)
            # Если задача есть и она еще не переведена — запускаем!
            if job and job["status"] not in ("translating", "done"):
                await job_store.update_status(job_id, "translating")
                background_tasks.add_task(_translate_book_background, job_id)
                print(f"[WEBHOOK] Оплата получена, запущен перевод для job_id={job_id}")

    # ЮKassa требует всегда возвращать 200, иначе она будет спамить запросами
    return {"status": "ok"}

try:
    from app.utils.mailer import send_translation_ready
except ImportError:
    def send_translation_ready(*args, **kwargs):
        return False, "mailer не настроен"
