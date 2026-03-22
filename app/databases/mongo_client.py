from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel

from app.common.config import MONGO_DB_NAME, MONGO_URI

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_indexes_ready: bool = False


async def get_db() -> AsyncIOMotorDatabase:
    global _client, _db, _indexes_ready
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not set in .env")

    if _client is None:
        logger.info("Initializing Mongo client...")
        _client = AsyncIOMotorClient(MONGO_URI)

    if _db is None:
        if _client is not None:
            _db = _client[MONGO_DB_NAME]
        
    if _db is not None and not _indexes_ready:
        await _ensure_indexes(_db)
        _indexes_ready = True
        
    if _db is None:
        raise RuntimeError("Failed to initialize Mongo database")

    return _db


async def close_client():
    global _client, _db, _indexes_ready
    if _client is not None:
        _client.close()
    _client = None
    _db = None
    _indexes_ready = False


async def _ensure_indexes(db: AsyncIOMotorDatabase):
    ttl_6_months = 60 * 60 * 24 * 180

    try:
        await db.users.create_index([("user_id", ASCENDING)], unique=True)
        await db.users.create_index([("username_lc", ASCENDING)])
        await db.users.create_index([("phone_digits", ASCENDING)])

        await db.admins.create_index([("user_id", ASCENDING)], unique=True)
        await db.admins.create_index([("role", ASCENDING)])
        await db.admins.create_index([("is_on_shift", ASCENDING)])

        await db.menu.create_index([("category", ASCENDING)])
        await db.menu.create_index([("name", ASCENDING)])

        await db.sales.create_index([("record_type", ASCENDING)])
        await db.sales.create_index([("user_id", ASCENDING)])

        await _ensure_ttl_index(db.bookings, "created_at", ttl_6_months)
        await _ensure_ttl_index(db.sales, "timestamp", ttl_6_months)
        await _ensure_ttl_index(db.activity_logs, "timestamp", ttl_6_months)
        await _ensure_ttl_index(db.errors, "timestamp", ttl_6_months)
    except Exception as e:
        logger.error(f"Error ensuring indexes: {e}")


async def _ensure_ttl_index(collection, field: str, expire_seconds: int):
    try:
        info = await collection.index_information()
        for name, spec in (info or {}).items():
            key = spec.get("key")
            if key == [(field, 1)]:
                if spec.get("expireAfterSeconds") != expire_seconds:
                    try:
                        await collection.drop_index(name)
                    except Exception:
                        pass
        
        await collection.create_index(
            [(field, ASCENDING)],
            expireAfterSeconds=int(expire_seconds),
            name=f"{field}_ttl",
        )
    except Exception as e:
        logger.error(f"Error ensuring TTL index on {collection.name}: {e}")


def projection_without_mongo_id() -> dict[str, Any]:
    return {"_id": 0}
