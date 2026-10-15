"""Точка входа. Запускает FastAPI-сервер."""
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from app.translators.genapi_client import translate_text
from app.parsers.epub_parser import parse_epub
from app.api.routes_preview import router as preview_router
from app.api.routes_feedback import router as feedback_router
from app.core.session import job_store


@asynccontextmanager
async def lifespan(app):
    """Инициализация при старте приложения."""
    await job_store.init()
    yield


app = FastAPI(
    title="Book Translator",
    description="Перевод книг с сохранением вёрстки",
    version="0.1.0",
    lifespan=lifespan,
)

# Подключаем роутеры
app.include_router(preview_router)
app.include_router(feedback_router)

# Подключаем статику (UI)
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")

from fastapi.responses import FileResponse

@app.get("/offer")
async def offer_page():
    return FileResponse("static/offer.html")

@app.get("/privacy")
async def privacy_page():
    return FileResponse("static/privacy.html")


@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy"})


@app.get("/translate-test")
async def translate_test(
    text: str = Query(...),
    source: str = Query("en"),
    target: str = Query("ru"),
):
    try:
        result = translate_text(text, source_lang=source, target_lang=target)
        return {"status": "ok", "original": text, "translation": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/parse-test")
async def parse_test(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".epub"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Только .epub"})

    upload_path = settings.STORAGE_UPLOADS / file.filename
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        book = parse_epub(str(upload_path))
        return {
            "status": "ok",
            "title": book.title,
            "author": book.author,
            "language": book.language,
            "total_segments": len(book.segments),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
