"""
Сервис уведомлений: отправка email (приглашение, новое голосование, новое сообщение в чате).
Внутренний API: POST /internal/send — вызывают trip-, voting-, chat-service.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "noreply@tripplanner.local")


def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _send_email(to_emails: list[str], subject: str, body_text: str) -> None:
    if not _smtp_configured():
        logger.warning("SMTP not configured, skip sending email to %s: %s", to_emails, subject)
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(to_emails)
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            for to in to_emails:
                server.sendmail(FROM_EMAIL, to, msg.as_string())
        logger.info("Email sent to %s: %s", to_emails, subject)
    except Exception as e:
        logger.exception("Failed to send email to %s: %s", to_emails, e)


class NotifyPayload(BaseModel):
    """Тело запроса на отправку уведомления."""
    event: str = Field(..., description="invite | new_poll | new_chat_message | password_reset")
    to_emails: list[str] = Field(..., min_length=1)
    data: dict = Field(default_factory=dict)


def _render_invite(data: dict) -> tuple[str, str]:
    trip_title = data.get("trip_title", "Поездка")
    inviter_name = data.get("inviter_name", "Участник")
    subject = f"Приглашение в поездку: {trip_title}"
    body = (
        f"Здравствуйте.\n\n{inviter_name} приглашает вас в поездку «{trip_title}».\n\n"
        "Войдите в TripPlanner, откройте эту поездку и в блоке «Участники» нажмите «Принять приглашение»."
    )
    return subject, body


def _render_new_poll(data: dict) -> tuple[str, str]:
    trip_title = data.get("trip_title", "Поездка")
    question = data.get("question", "Новый опрос")
    subject = f"Новое голосование: {trip_title}"
    body = f"В поездке «{trip_title}» создано голосование:\n\n{question}\n\nЗайдите в приложение, чтобы проголосовать."
    return subject, body


def _render_password_reset(data: dict) -> tuple[str, str]:
    reset_url = data.get("reset_url", "")
    subject = "Сброс пароля TripPlanner"
    body = (
        "Здравствуйте.\n\n"
        "Вы запросили сброс пароля. Перейдите по ссылке (она действует ограниченное время):\n\n"
        f"{reset_url}\n\n"
        "Если вы не запрашивали сброс, проигнорируйте это письмо."
    )
    return subject, body


def _render_new_chat_message(data: dict) -> tuple[str, str]:
    trip_title = data.get("trip_title", "Поездка")
    author_name = data.get("author_name", "Участник")
    preview = (data.get("message_preview") or "")[:200]
    subject = f"Новое сообщение в чате: {trip_title}"
    body = f"В чате поездки «{trip_title}» {author_name} написал:\n\n{preview}\n\n..."
    return subject, body


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Notification Service (SMTP configured: %s)", _smtp_configured())
    yield
    logger.info("Notification Service stopped")


app = FastAPI(title="TripPlanner Notification Service", lifespan=lifespan)


@app.get("/")
async def root():
    return {
        "service": "Notification Service",
        "status": "running",
        "smtp_configured": _smtp_configured(),
        "endpoints": {"send": "POST /internal/send"},
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "notification-service"}


@app.post("/internal/send")
async def send_notification(payload: NotifyPayload):
    """
    Внутренний эндпоинт. Отправка email по событию.
    event: invite | new_poll | new_chat_message | password_reset
    to_emails: список адресов
    data: параметры для шаблона (trip_title, inviter_name, question, author_name, message_preview и т.д.)
    """
    event = payload.event
    to_emails = [e.strip().lower() for e in payload.to_emails if e and "@" in e]
    if not to_emails:
        raise HTTPException(status_code=400, detail="to_emails required")
    data = payload.data or {}

    if event == "invite":
        subject, body = _render_invite(data)
    elif event == "new_poll":
        subject, body = _render_new_poll(data)
    elif event == "new_chat_message":
        subject, body = _render_new_chat_message(data)
    elif event == "password_reset":
        subject, body = _render_password_reset(data)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown event: {event}")

    _send_email(to_emails, subject, body)
    return {"sent": True, "to": to_emails, "event": event}
