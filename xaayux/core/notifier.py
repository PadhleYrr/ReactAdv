"""
notifier.py — Send DM notifications to users via the bot client
"""

import logging
from xaayux.config import SUPPORT_LINK

log = logging.getLogger(__name__)

_bot = None  # set after bot starts

def set_bot(bot_client):
    global _bot
    _bot = bot_client

async def _send(user_id: int, text: str):
    if not _bot:
        return
    try:
        await _bot.send_message(user_id, text, parse_mode="html")
    except Exception as e:
        log.warning(f"Could not DM user {user_id}: {e}")

async def notify_session_dead(owner_id: int, session_id: str):
    await _send(owner_id, (
        "⚠️ <b>Session Expired / Invalid</b>\n\n"
        f"One of your donated sessions <code>{session_id[:12]}...</code> is no longer working.\n\n"
        "• Your associated channel has been <b>removed</b> from the reaction pool.\n"
        "• All sessions (including yours) will <b>no longer react</b> to that channel.\n\n"
        "➕ To re-enroll your channel, donate a fresh valid session using /addchannel.\n\n"
        f"💬 Need help? <a href='{SUPPORT_LINK}'>Support</a>"
    ))

async def notify_channel_removed(owner_id: int, channel_username: str):
    await _send(owner_id, (
        f"📢 <b>Channel Removed: @{channel_username}</b>\n\n"
        "The session you donated to activate this channel has expired or become invalid.\n\n"
        "As a result:\n"
        "• Reactions to your channel have been <b>stopped</b>.\n"
        "• Your channel is <b>removed</b> from the network.\n\n"
        "To get back in, use /addchannel and donate a new working session.\n\n"
        f"💬 <a href='{SUPPORT_LINK}'>Support</a>"
    ))

async def notify_channel_added(owner_id: int, channel_username: str, session_info: dict):
    await _send(owner_id, (
        f"✅ <b>Channel Activated: @{channel_username}</b>\n\n"
        "Your channel is now live in the reaction network!\n\n"
        f"• Donated session: <b>{session_info.get('name', 'Unknown')}</b> "
        f"({session_info.get('username', '')})\n"
        "• All active sessions in the pool will now react to every new post.\n"
        "• Your session will react to all other channels too.\n\n"
        "🔁 The loop grows with every new member. Welcome aboard!"
    ))

async def notify_session_warning(owner_id: int, fail_count: int, max_fails: int):
    await _send(owner_id, (
        "⚠️ <b>Session Health Warning</b>\n\n"
        f"One of your sessions has failed <b>{fail_count}/{max_fails}</b> health checks.\n\n"
        "If it fails once more, it will be automatically removed and your channel "
        "will stop receiving reactions.\n\n"
        "Please check that the Telegram account is still active and not banned.\n\n"
        f"💬 <a href='{SUPPORT_LINK}'>Support</a>"
    ))

async def broadcast(user_ids: list[int], text: str):
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await _send(uid, text)
            sent += 1
        except Exception:
            failed += 1
    return sent, failed
