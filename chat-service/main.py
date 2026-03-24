"""
Сервис чата поездки.
- Отправка сообщений в чат поездки (REST и WebSocket).
- Список сообщений (с пагинацией).
- WebSocket: подключение к чату поездки, сообщения приходят в реальном времени.
"""
import json
import logging
import os
import uuid

import httpx
from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from db.db import engine, Base, get_db, SessionLocal
from models.message import Message
from schemas.message import MessageCreate, MessageResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
TRIP_SERVICE_URL = os.getenv("TRIP_SERVICE_URL", "http://trip-service:8000")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000")


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Верификация токена через Auth Service."""
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/auth/verify",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=5.0,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


async def check_trip_access(
    trip_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Проверка доступа к поездке через Trip Service."""
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TRIP_SERVICE_URL}/trips/{trip_id}/internal/check-access",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Trip not found")
            if response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to access this trip",
                )
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Trip service error")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Trip service unavailable")


class ConnectionManager:
    """Подключённые WebSocket-клиенты по trip_id. Рассылка новых сообщений в реальном времени."""

    def __init__(self):
        self._rooms: dict[str, set[WebSocket]] = {}

    def connect(self, trip_id: str, websocket: WebSocket) -> None:
        if trip_id not in self._rooms:
            self._rooms[trip_id] = set()
        self._rooms[trip_id].add(websocket)

    def disconnect(self, trip_id: str, websocket: WebSocket) -> None:
        if trip_id in self._rooms:
            self._rooms[trip_id].discard(websocket)
            if not self._rooms[trip_id]:
                del self._rooms[trip_id]

    async def broadcast_message(self, trip_id: str, message: Message) -> None:
        """Разослать сообщение всем подключённым к чату поездки."""
        if trip_id not in self._rooms:
            return
        payload = json.dumps(
            MessageResponse.model_validate(message).model_dump(mode="json"),
            ensure_ascii=False,
        )
        dead = set()
        for ws in self._rooms[trip_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._rooms[trip_id].discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Chat Service")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    app.state.ws_manager = ConnectionManager()
    yield
    logger.info("Chat Service stopped")
    engine.dispose()


app = FastAPI(
    title="TripPlanner Chat Service",
    lifespan=lifespan,
)


def _get_user_uuid(user_data: dict) -> uuid.UUID:
    raw = user_data.get("user_id") or user_data.get("sub")
    return uuid.UUID(raw)


async def _notify_new_message(trip_id: str, author_id: uuid.UUID, message_preview: str) -> None:
    """Отправить участникам поездки (кроме автора) уведомление о новом сообщении в чате."""
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{TRIP_SERVICE_URL}/trips/{trip_id}/internal/participant-ids", timeout=5.0)
            if r.status_code != 200:
                return
            ids = [uid for uid in r.json().get("user_ids", []) if uid != str(author_id)]
            r2 = await client.get(f"{TRIP_SERVICE_URL}/trips/{trip_id}/internal/info", timeout=5.0)
            trip_title = (r2.json().get("title") or "Поездка") if r2.status_code == 200 else "Поездка"
            ra = await client.get(f"{AUTH_SERVICE_URL}/auth/internal/user/{author_id}", timeout=5.0)
            author_name = "Участник"
            if ra.status_code == 200:
                author_name = ra.json().get("full_name") or ra.json().get("username") or author_name
            to_emails = []
            for uid in ids:
                ru = await client.get(f"{AUTH_SERVICE_URL}/auth/internal/user/{uid}", timeout=5.0)
                if ru.status_code == 200 and ru.json().get("email"):
                    to_emails.append(ru.json()["email"])
            if to_emails:
                await client.post(
                    f"{NOTIFICATION_SERVICE_URL}/internal/send",
                    json={
                        "event": "new_chat_message",
                        "to_emails": to_emails,
                        "data": {
                            "trip_title": trip_title,
                            "author_name": author_name,
                            "message_preview": message_preview[:200],
                        },
                    },
                    timeout=5.0,
                )
        except httpx.RequestError as e:
            logger.warning("Failed to send new_chat_message notification: %s", e)


@app.get("/")
async def root():
    return {
        "service": "Chat Service",
        "status": "running",
        "endpoints": {
            "send_message": "POST /trips/{trip_id}/messages",
            "list_messages": "GET /trips/{trip_id}/messages",
            "websocket": "WS /trips/{trip_id}/messages/ws?token=JWT",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chat-service"}


@app.post(
    "/trips/{trip_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def send_message(
    trip_id: str,
    body: MessageCreate,
    user_data: dict = Depends(verify_token),
    _access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Отправить сообщение в чат поездки. Доступно только участникам поездки."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip_id")
    author_id = _get_user_uuid(user_data)
    message = Message(
        trip_id=trip_uuid,
        author_user_id=author_id,
        content=body.content.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    logger.info(
        "Message %s added to trip %s by %s",
        message.id,
        trip_id,
        author_id,
    )
    manager: ConnectionManager = app.state.ws_manager
    await manager.broadcast_message(trip_id, message)
    await _notify_new_message(trip_id, author_id, (body.content or "").strip()[:200])
    return message


@app.get(
    "/trips/{trip_id}/messages",
    response_model=list[MessageResponse],
)
async def list_messages(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    _access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Список сообщений чата поездки (новые сверху). Доступно только участникам."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip_id")
    messages = (
        db.query(Message)
        .filter(Message.trip_id == trip_uuid)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return list(reversed(messages))  # в ответе — от старых к новым


@app.websocket("/trips/{trip_id}/messages/ws")
async def websocket_chat(
    websocket: WebSocket,
    trip_id: str,
):
    """
    WebSocket чата поездки. В query передать token=JWT.
    После подключения можно отправлять JSON: {"content": "текст"} — сообщение сохранится и разошлётся всем.
    Все новые сообщения (в т.ч. от POST /messages) приходят в реальном времени.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{AUTH_SERVICE_URL}/auth/verify",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=5.0,
            )
            if r.status_code != 200:
                await websocket.close(code=4001)
                return
            user_data = r.json()
        except httpx.RequestError:
            await websocket.close(code=4001)
            return
    async with httpx.AsyncClient() as trip_client:
        try:
            r = await trip_client.get(
                f"{TRIP_SERVICE_URL}/trips/{trip_id}/internal/check-access",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            if r.status_code != 200:
                await websocket.close(code=4003)
                return
        except httpx.RequestError:
            await websocket.close(code=4003)
            return

    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        await websocket.close(code=4000)
        return

    await websocket.accept()
    manager: ConnectionManager = app.state.ws_manager
    manager.connect(trip_id, websocket)
    author_id = _get_user_uuid(user_data)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                obj = json.loads(data)
                content = (obj.get("content") or "").strip()
            except (json.JSONDecodeError, TypeError):
                await websocket.send_text(json.dumps({"error": "Invalid JSON, expected { \"content\": \"...\" }"}))
                continue
            if not content:
                continue
            if len(content) > 10_000:
                await websocket.send_text(json.dumps({"error": "Content too long"}))
                continue
            message = Message(trip_id=trip_uuid, author_user_id=author_id, content=content)
            db = SessionLocal()
            try:
                db.add(message)
                db.commit()
                db.refresh(message)
                await manager.broadcast_message(trip_id, message)
                await _notify_new_message(trip_id, author_id, content[:200])
            finally:
                db.close()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(trip_id, websocket)
