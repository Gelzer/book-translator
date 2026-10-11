"""Отправка email через Resend HTTP API (работает на Render)."""
import httpx

from config import settings


RESEND_API_URL = "https://api.resend.com/emails"


def send_translation_ready(
    to_email: str,
    job_id: str,
    book_title: str,
) -> tuple[bool, str]:
    """
    Отправляет письмо «перевод готов» через Resend.
    Возвращает (успех, текст_ошибки_или_пустая_строка).
    """
    if not settings.RESEND_API_KEY:
        return False, "RESEND_API_KEY не задан в .env"

    if not to_email or "@" not in to_email:
        return False, f"Некорректный email: {to_email}"

    download_url = f"{settings.PUBLIC_URL.rstrip('/')}/preview/job/{job_id}"
    subject = f"Ваш перевод готов: {book_title}"

    html_body = f"""
    <html>
      <body style="font-family: -apple-system, sans-serif; color: #1a1a1a; line-height: 1.6;">
        <h2 style="color: #7a1f4a;">Перевод готов ✅</h2>
        <p>Мы закончили перевод книги:</p>
        <p style="font-size: 18px; font-weight: 600;">{book_title}</p>
        <p style="margin-top: 24px;">
          <a href="{download_url}"
             style="display:inline-block; padding:14px 28px; background:#15803d;
                    color:white; text-decoration:none; border-radius:10px;">
            ⬇ Скачать EPUB
          </a>
        </p>
        <p style="color: #6b7280; font-size: 13px; margin-top: 32px;">
          Если кнопка не работает, скопируйте ссылку:<br>
          <a href="{download_url}">{download_url}</a>
        </p>
        <p style="color: #6b7280; font-size: 13px; margin-top: 24px;">
          С уважением,<br>Book Translator
        </p>
      </body>
    </html>
    """

    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }

    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(RESEND_API_URL, json=payload, headers=headers)
            if resp.status_code >= 400:
                err = f"HTTP {resp.status_code}: {resp.text[:300]}"
                print(f"=== EMAIL ERROR ===")
                print(err)
                print("===================")
                return False, err
        return True, ""
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        print(f"=== EMAIL EXCEPTION ===")
        print(err)
        print("=======================")
        return False, err
