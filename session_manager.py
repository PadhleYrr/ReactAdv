"""
session_manager.py — Live session validation, health checks, pool management
"""

import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    AuthKeyUnregisteredError,
    UserDeactivatedError,
    UserDeactivatedBanError,
    SessionRevokedError,
    SessionExpiredError,
    RPCError,
)
from xaayux.config import API_ID, API_HASH, SESSION_VALIDATE_TIMEOUT, MAX_FAIL_COUNT, HEALTH_CHECK_INTERVAL
from xaayux.core import db

log = logging.getLogger(__name__)

# ── Live client pool ──────────────────────────────────────────
# session_id (str) → TelegramClient
_pool: dict[str, TelegramClient] = {}

def get_pool() -> dict:
    return _pool

async def _make_client(string: str) -> TelegramClient:
    client = TelegramClient(
        StringSession(string),
        api_id=API_ID,
        api_hash=API_HASH,
        connection_retries=2,
    )
    return client

# ── Validate a brand-new session string ───────────────────────

async def validate_session(string: str) -> tuple[bool, str, dict]:
    """
    Try to connect with the given session string.
    Returns (is_valid, error_reason, account_info)
    account_info has keys: name, phone, username
    """
    client = await _make_client(string)
    try:
        await asyncio.wait_for(client.connect(), timeout=SESSION_VALIDATE_TIMEOUT)
        if not await client.is_user_authorized():
            return False, "Session is not authorized (expired or revoked).", {}
        me = await client.get_me()
        info = {
            "name":     f"{me.first_name or ''} {me.last_name or ''}".strip(),
            "phone":    me.phone or "hidden",
            "username": f"@{me.username}" if me.username else "no username",
        }
        return True, "", info
    except AuthKeyUnregisteredError:
        return False, "Auth key is unregistered — session was terminated.", {}
    except (SessionRevokedError, SessionExpiredError):
        return False, "Session was revoked or expired.", {}
    except (UserDeactivatedError, UserDeactivatedBanError):
        return False, "This Telegram account is deactivated or banned.", {}
    except asyncio.TimeoutError:
        return False, "Connection timed out. Check your session string.", {}
    except Exception as e:
        return False, f"Unexpected error: {e}", {}
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

# ── Boot: load all active sessions into pool ──────────────────

async def boot_pool():
    sessions = await db.get_active_sessions()
    log.info(f"Booting pool with {len(sessions)} active sessions...")
    for s in sessions:
        sid = str(s["_id"])
        try:
            client = await _make_client(s["string"])
            await client.connect()
            if await client.is_user_authorized():
                _pool[sid] = client
                log.info(f"  ✅ Session {sid[:8]}... loaded")
            else:
                log.warning(f"  ❌ Session {sid[:8]}... unauthorized on boot")
                await _handle_dead_session(sid, s["owner_id"])
        except Exception as e:
            log.error(f"  ❌ Session {sid[:8]}... failed on boot: {e}")
            await _handle_dead_session(sid, s["owner_id"])

async def add_to_pool(session_id: str, string: str) -> bool:
    """Add a freshly validated session into the live pool."""
    try:
        client = await _make_client(string)
        await client.connect()
        _pool[session_id] = client
        log.info(f"Session {session_id[:8]}... added to pool")
        return True
    except Exception as e:
        log.error(f"Failed to add session {session_id[:8]}... to pool: {e}")
        return False

async def remove_from_pool(session_id: str):
    client = _pool.pop(session_id, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass

# ── Health checker ────────────────────────────────────────────

async def _handle_dead_session(session_id: str, owner_id: int):
    """Mark DB dead, remove from pool, remove associated channel, notify owner."""
    from xaayux.core.notifier import notify_session_dead, notify_channel_removed
    await db.mark_session_dead(session_id)
    await remove_from_pool(session_id)

    # Remove the channel this session unlocked
    channel_doc = await db.remove_channel_by_session(session_id)

    # Notify session owner
    await notify_session_dead(owner_id, session_id)

    # If a channel was removed, notify its owner too (may be same person)
    if channel_doc:
        await notify_channel_removed(channel_doc["owner_id"], channel_doc["username"])
        log.info(f"Channel @{channel_doc['username']} removed because session died.")

async def health_check_all(bot_client):
    """Periodic background task — runs every HEALTH_CHECK_INTERVAL seconds."""
    from xaayux.core.notifier import notify_session_dead, notify_channel_removed
    while True:
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)
        log.info("🔍 Running session health check...")
        sessions = await db.get_active_sessions()
        for s in sessions:
            sid = str(s["_id"])
            client = _pool.get(sid)
            alive = False
            if client:
                try:
                    me = await asyncio.wait_for(client.get_me(), timeout=15)
                    alive = me is not None
                except Exception:
                    alive = False

            if alive:
                await db.reset_session_fail(sid)
            else:
                fail_count = await db.increment_session_fail(sid)
                log.warning(f"Session {sid[:8]}... failed health check ({fail_count}/{MAX_FAIL_COUNT})")
                if fail_count >= MAX_FAIL_COUNT:
                    log.error(f"Session {sid[:8]}... exceeded max fails — killing")
                    await _handle_dead_session(sid, s["owner_id"])
