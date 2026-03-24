"""
Redis-кэш для голосований: быстрая отдача списка опросов и отдельного опроса с актуальными результатами.
Ключи: poll:{poll_id}, trip_polls:{trip_id}. При создании/изменении опроса или голосе — инвалидация.
"""
import json
import logging
import os
from typing import Optional

from redis.asyncio import Redis
from schemas.poll import PollResponse

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POLL_CACHE_TTL = 300  # 5 минут
TRIP_POLLS_CACHE_TTL = 120  # 2 минуты для списка по поездке

_redis: Optional[Redis] = None


def _poll_to_json(p: PollResponse) -> str:
    """Сериализация PollResponse в JSON (UUID и datetime уже в json-совместимом виде)."""
    return p.model_dump_json(mode="json")


def _poll_from_json(s: str) -> PollResponse:
    return PollResponse.model_validate_json(s)


async def get_redis() -> Optional[Redis]:
    global _redis
    return _redis


async def init_redis() -> None:
    global _redis
    try:
        _redis = Redis.from_url(REDIS_URL, decode_responses=True)
        await _redis.ping()
        logger.info("Redis connected: %s", REDIS_URL)
    except Exception as e:
        logger.warning("Redis unavailable, cache disabled: %s", e)
        _redis = None


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


# ——— Ключи ——— 
def _key_poll(poll_id: str) -> str:
    return f"poll:{poll_id}"


def _key_trip_polls(trip_id: str) -> str:
    return f"trip_polls:{trip_id}"


# ——— Чтение ———
async def cache_get_poll(poll_id: str) -> Optional[PollResponse]:
    r = await get_redis()
    if not r:
        return None
    try:
        data = await r.get(_key_poll(poll_id))
        if data:
            logger.info("Cache HIT poll:%s", poll_id)
            return _poll_from_json(data)
        logger.info("Cache MISS poll:%s", poll_id)
    except Exception as e:
        logger.warning("Redis get_poll error: %s", e)
    return None


async def cache_get_trip_polls(trip_id: str) -> Optional[list[PollResponse]]:
    r = await get_redis()
    if not r:
        return None
    try:
        data = await r.get(_key_trip_polls(trip_id))
        if data:
            items = json.loads(data)
            result = [PollResponse.model_validate(obj) for obj in items]
            logger.info("Cache HIT trip_polls:%s (polls=%d)", trip_id, len(result))
            return result
        logger.info("Cache MISS trip_polls:%s", trip_id)
    except Exception as e:
        logger.warning("Redis get_trip_polls error: %s", e)
    return None


# ——— Запись ———
async def cache_set_poll(poll: PollResponse) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        key = _key_poll(str(poll.id))
        await r.set(key, _poll_to_json(poll), ex=POLL_CACHE_TTL)
        logger.info("Cache SET poll:%s", poll.id)
    except Exception as e:
        logger.warning("Redis set_poll error: %s", e)


async def cache_set_trip_polls(trip_id: str, polls: list[PollResponse]) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        key = _key_trip_polls(trip_id)
        data = json.dumps([p.model_dump(mode="json") for p in polls])
        await r.set(key, data, ex=TRIP_POLLS_CACHE_TTL)
        logger.info("Cache SET trip_polls:%s (polls=%d)", trip_id, len(polls))
    except Exception as e:
        logger.warning("Redis set_trip_polls error: %s", e)


# ——— Инвалидация (после создания опроса, добавления варианта, голоса) ———
async def cache_invalidate_poll(poll_id: str, trip_id: str) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        await r.delete(_key_poll(poll_id))
        await r.delete(_key_trip_polls(trip_id))
        logger.info("Cache INVALIDATE poll:%s, trip_polls:%s", poll_id, trip_id)
    except Exception as e:
        logger.warning("Redis invalidate error: %s", e)
