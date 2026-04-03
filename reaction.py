"""
reaction.py — Listens for new posts in enrolled channels, fires all pool sessions
"""

import asyncio
import random
import logging
from telethon import events, functions, types
from xaayux.config import EMOJIS, REACTION_DELAY
from xaayux.core import db
from xaayux.core.session_manager import get_pool, increment_session_fail_safe

log = logging.getLogger(__name__)

# We use one "listener" client — the bot itself or the first userbot.
# It watches for new channel posts, then dispatches all pool clients to react.

_listener_client = None

def set_listener(client):
    global _listener_client
    _listener_client = client

async def increment_session_fail_safe(session_id: str, owner_id: int):
    from xaayux.core.session_manager import _handle_dead_session
    from xaayux.config import MAX_FAIL_COUNT
    from xaayux.core.notifier import notify_session_warning
    fail = await db.increment_session_fail(session_id)
    if fail == MAX_FAIL_COUNT - 1:
        await notify_session_warning(owner_id, fail, MAX_FAIL_COUNT)
    if fail >= MAX_FAIL_COUNT:
        await _handle_dead_session(session_id, owner_id)

async def react_with_all_sessions(chat_id: int, msg_id: int):
    """Fire all active pool sessions to react to a given message."""
    pool = get_pool()
    if not pool:
        return

    sessions_db = await db.get_active_sessions()
    session_map = {str(s["_id"]): s for s in sessions_db}

    for session_id, client in list(pool.items()):
        try:
            emoji = random.choice(EMOJIS)
            await client(functions.messages.SendReactionRequest(
                peer=chat_id,
                msg_id=msg_id,
                big=False,
                add_to_recent=True,
                reaction=[types.ReactionEmoji(emoticon=emoji)],
            ))
            await db.reset_session_fail(session_id)
            log.debug(f"Session {session_id[:8]}... reacted with {emoji}")
        except Exception as e:
            err = str(e).lower()
            log.warning(f"Session {session_id[:8]}... reaction failed: {e}")
            s = session_map.get(session_id)
            if s:
                await increment_session_fail_safe(session_id, s["owner_id"])

        await asyncio.sleep(REACTION_DELAY)

def register_listener(client):
    """Register the new-message handler on a Telethon client."""
    set_listener(client)

    @client.on(events.NewMessage())
    async def on_new_message(event):
        if not event.is_channel:
            return
        try:
            chat_id = event.chat_id
            # Check if this channel is enrolled
            active_channels = await db.get_active_channels()
            enrolled_ids = {c["channel_id"] for c in active_channels}
            if chat_id not in enrolled_ids:
                return
            log.info(f"New post in {chat_id} (msg {event.id}) — dispatching reactions")
            asyncio.create_task(react_with_all_sessions(chat_id, event.id))
        except Exception as e:
            log.error(f"on_new_message error: {e}")
