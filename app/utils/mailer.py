"""Отправка email через стандартный SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from threading import Thread
from config import settings


def _send_email_sync(to_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Синхронная отправка письма."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return False, "SMTP_USER или SMTP_PASSWORD не заданы в .env"

    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = settings.SMTP_USER
    msg['To'] = to_email

    try:
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10)
            server.starttls()

        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())
        server.quit()
        return True, ""
    except Exception as e:
        print(f"=== EMAIL ERROR ===\n{type(e).__name__}: {e}\n===================")
        return False, str(e)


def send_translation_ready(to_email: str, job_id: str, book_title: str) -> tuple[bool, str]:
    """Отправляет письмо клиенту о готовности перевода."""
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
    return _send_email_sync(to_email, subject, html_body)


def send_admin_notification(subject: str, text: str) -> None:
    """Отправляет уведомление (чек или отзыв) вам на почту в фоновом потоке."""
    if not settings.ADMIN_EMAIL:
        print("ADMIN_EMAIL не задан. Уведомление не отправлено.")
        return

    # Оборачиваем текст в простой HTML для красоты
    html_body = f"""
    <html>
      <body style="font-family: sans-serif; font-size: 15px; color: #333;">
        <div style="padding: 20px; background: #f9f9f9; border-radius: 10px; border: 1px solid #ddd;">
          {text.replace(chr(10), '<br>')}
        </div>
      </body>
    </html>
    """

    def _task():
        success, err = _send_email_sync(settings.ADMIN_EMAIL, subject, html_body)
        if not success:
            print(f"Не удалось отправить уведомление админу: {err}")

    # Запускаем в фоне, чтобы не задерживать ответ сервера
    Thread(target=_task).start()
