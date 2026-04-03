"""
db.py — All MongoDB operations for ReactionNet
Collections:
  users    — everyone who has interacted with the bot
  sessions — donated string sessions (1 per channel slot)
  channels — channels enrolled for reactions
"""

import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from xaayux.config import MONGO_URI, DB_NAME

log = logging.getLogger(__name__)

_client: AsyncIOMotorClient = None

def get_db():
    return _client[DB_NAME]

async def connect():
    global _client
    _client = AsyncIOMotorClient(MONGO_URI)
    await _client.admin.command("ping")
    log.info("✅ MongoDB connected")
    # indexes
    db = get_db()
    await db.users.create_index("user_id", unique=True)
    await db.sessions.create_index("owner_id")
    await db.sessions.create_index("status")
    await db.channels.create_index("channel_id", unique=True)
    await db.channels.create_index("owner_id")
    await db.channels.create_index("session_id")

async def disconnect():
    if _client:
        _client.close()

# ── Users ──────────────────────────────────────────────────────

async def get_user(user_id: int):
    return await get_db().users.find_one({"user_id": user_id})

async def upsert_user(user_id: int, username: str = None, full_name: str = None):
    await get_db().users.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "joined_at": datetime.utcnow(),
            "is_banned": False,
        }},
        upsert=True,
    )

async def get_all_users():
    return await get_db().users.find({"is_banned": False}).to_list(None)

async def set_banned(user_id: int, banned: bool):
    await get_db().users.update_one({"user_id": user_id}, {"$set": {"is_banned": banned}})

async def get_stats():
    db = get_db()
    users    = await db.users.count_documents({})
    sessions = await db.sessions.count_documents({"status": "active"})
    channels = await db.channels.count_documents({"status": "active"})
    return {"users": users, "sessions": sessions, "channels": channels}

# ── Sessions ───────────────────────────────────────────────────

async def add_session(owner_id: int, string: str) -> str:
    """Insert a new session, return its _id as string."""
    from bson import ObjectId
    doc = {
        "owner_id":     owner_id,
        "string":       string,
        "status":       "active",      # active | dead
        "fail_count":   0,
        "added_at":     datetime.utcnow(),
        "last_checked": datetime.utcnow(),
    }
    result = await get_db().sessions.insert_one(doc)
    return str(result.inserted_id)

async def get_active_sessions():
    return await get_db().sessions.find({"status": "active"}).to_list(None)

async def get_sessions_by_owner(owner_id: int):
    return await get_db().sessions.find({"owner_id": owner_id}).to_list(None)

async def mark_session_dead(session_id: str):
    from bson import ObjectId
    await get_db().sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"status": "dead", "last_checked": datetime.utcnow()}},
    )

async def increment_session_fail(session_id: str) -> int:
    """Increment fail counter, return new count."""
    from bson import ObjectId
    result = await get_db().sessions.find_one_and_update(
        {"_id": ObjectId(session_id)},
        {
            "$inc": {"fail_count": 1},
            "$set": {"last_checked": datetime.utcnow()},
        },
        return_document=True,
    )
    return result["fail_count"] if result else 999

async def reset_session_fail(session_id: str):
    from bson import ObjectId
    await get_db().sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"fail_count": 0, "last_checked": datetime.utcnow()}},
    )

async def delete_session(session_id: str):
    from bson import ObjectId
    await get_db().sessions.delete_one({"_id": ObjectId(session_id)})

# ── Channels ───────────────────────────────────────────────────

async def channel_exists(channel_id: int) -> bool:
    return bool(await get_db().channels.find_one({"channel_id": channel_id}))

async def add_channel(channel_id: int, username: str, owner_id: int, session_id: str):
    await get_db().channels.insert_one({
        "channel_id":  channel_id,
        "username":    username,
        "owner_id":    owner_id,
        "session_id":  session_id,   # the session donated to unlock this slot
        "status":      "active",
        "added_at":    datetime.utcnow(),
    })

async def get_active_channels():
    return await get_db().channels.find({"status": "active"}).to_list(None)

async def get_channels_by_owner(owner_id: int):
    return await get_db().channels.find({"owner_id": owner_id}).to_list(None)

async def get_channel_by_session(session_id: str):
    return await get_db().channels.find_one({"session_id": session_id})

async def remove_channel_by_session(session_id: str):
    """Remove the channel whose unlock-session died. Returns the doc before deletion."""
    doc = await get_db().channels.find_one_and_delete({"session_id": session_id})
    return doc

async def remove_channel(channel_id: int):
    await get_db().channels.delete_one({"channel_id": channel_id})

async def get_channel_by_session_or_id(channel_id: int):
    return await get_db().channels.find_one({"channel_id": channel_id})
