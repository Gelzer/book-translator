"""Отправка email через SMTP (Яндекс.Почта и др.)."""
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from config import settings


def send_translation_ready(
    to_email: str,
    job_id: str,
    book_title: str,
) -> tuple[bool, str]:
    """
    Отправляет письмо «перевод готов».
    Возвращает (успех, текст_ошибки_или_пустая_строка).
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return False, "SMTP не настроен (нет SMTP_USER или SMTP_PASSWORD)"

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

    plain_body = f"Перевод книги «{book_title}» готов.\n\nСкачать: {download_url}\n\n— Book Translator"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True, ""
    except Exception as e:
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        print("=== EMAIL ERROR ===")
        print(err)
        print("===================")
        return False, str(e)