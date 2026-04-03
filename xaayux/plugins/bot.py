"""
bot.py — Public-facing bot: /start, add channel flow, my channels, stats, support
Uses conversation-style state machine per user.
"""

import asyncio
import logging
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors import ChannelInvalidError, ChannelPrivateError, UsernameInvalidError

from xaayux.config import ADMIN_ID, BOT_TOKEN, API_ID, API_HASH
from xaayux.core import db
from xaayux.core import ui
from xaayux.core.notifier import set_bot, notify_channel_added
from xaayux.core.session_manager import validate_session, add_to_pool
from xaayux.core.db import add_session, add_channel, channel_exists

log = logging.getLogger(__name__)

# ── State machine ──────────────────────────────────────────────
# user_id → {"step": str, "channel": str, ...}
_states: dict[int, dict] = {}

STEP_IDLE          = "idle"
STEP_AWAIT_CHANNEL = "await_channel"
STEP_AWAIT_SESSION = "await_session"
STEP_AWAIT_BCAST   = "await_broadcast"

bot_client: TelegramClient = None

async def start_bot(userbot_clients: list):
    global bot_client
    from telethon.sessions import StringSession
    bot_client = TelegramClient(StringSession(), api_id=API_ID, api_hash=API_HASH)
    await bot_client.start(bot_token=BOT_TOKEN)
    set_bot(bot_client)
    log.info("✅ Bot started")

    # Register reaction listener on the bot client
    from xaayux.plugins.reaction import register_listener
    register_listener(bot_client)

    _register_handlers(bot_client)
    await bot_client.run_until_disconnected()

# ── Helpers ────────────────────────────────────────────────────

async def _resolve_channel(client: TelegramClient, text: str):
    """Try to resolve a channel from username or t.me link. Returns (channel_id, username) or raises."""
    username = text.strip().lstrip("@").replace("https://t.me/", "").replace("http://t.me/", "").strip("/")
    entity = await client.get_entity(f"@{username}")
    return entity.id, username

def _state(user_id: int) -> dict:
    return _states.setdefault(user_id, {"step": STEP_IDLE})

def _clear(user_id: int):
    _states.pop(user_id, None)

async def _go_home(event):
    user_id = event.sender_id
    _clear(user_id)
    user = await db.get_user(user_id)
    name = event.sender.first_name if hasattr(event, "sender") and event.sender else "there"
    await event.edit(
        ui.welcome_text(name),
        buttons=ui.welcome_buttons(),
        parse_mode="html",
    )

# ── Handler registration ───────────────────────────────────────

def _register_handlers(client: TelegramClient):

    # ── /start ────────────────────────────────────────────────

    @client.on(events.NewMessage(pattern="/start"))
    async def cmd_start(event):
        user = event.sender
        user_data = await db.get_user(user.id)
        if user_data and user_data.get("is_banned"):
            await event.respond(ui.BANNED)
            return
        await db.upsert_user(user.id, getattr(user, "username", None), user.first_name)
        _clear(user.id)
        await event.respond(
            ui.welcome_text(user.first_name),
            buttons=ui.welcome_buttons(),
            parse_mode="html",
        )

    # ── /cancel ───────────────────────────────────────────────

    @client.on(events.NewMessage(pattern="/cancel"))
    async def cmd_cancel(event):
        _clear(event.sender_id)
        await event.respond(ui.CANCELLED, parse_mode="html")

    # ── /admin ────────────────────────────────────────────────

    @client.on(events.NewMessage(pattern="/admin"))
    async def cmd_admin(event):
        if event.sender_id != ADMIN_ID:
            return
        stats = await db.get_stats()
        await event.respond(
            ui.admin_panel_text(stats),
            buttons=ui.admin_buttons(),
            parse_mode="html",
        )

    # ── Inline button callbacks ────────────────────────────────

    @client.on(events.CallbackQuery())
    async def on_callback(event):
        data = event.data.decode()
        user_id = event.sender_id

        user_data = await db.get_user(user_id)
        if user_data and user_data.get("is_banned"):
            await event.answer(ui.BANNED, alert=True)
            return

        # ── Navigation ─────────────────────────────────────

        if data == "back_home":
            await _go_home(event)

        elif data == "how_it_works":
            await event.edit(ui.HOW_IT_WORKS, buttons=ui.how_it_works_buttons(), parse_mode="html")

        elif data == "support":
            await event.edit(ui.support_text(), buttons=ui.support_buttons(), parse_mode="html")

        elif data == "stats":
            stats = await db.get_stats()
            await event.edit(ui.stats_text(stats), buttons=ui.stats_buttons(), parse_mode="html")

        elif data == "my_channels":
            channels = await db.get_channels_by_owner(user_id)
            await event.edit(
                ui.my_channels_text(channels),
                buttons=ui.my_channels_buttons(channels),
                parse_mode="html",
            )

        elif data == "add_channel":
            _state(user_id)["step"] = STEP_AWAIT_CHANNEL
            await event.edit(ui.ASK_CHANNEL, parse_mode="html")

        # ── Remove channel ──────────────────────────────────

        elif data.startswith("remove_channel:"):
            channel_id = int(data.split(":")[1])
            # Find the session linked to this channel
            ch = await db.get_channel_by_session_or_id(channel_id)
            if ch:
                await db.mark_session_dead(ch["session_id"])
                from xaayux.core.session_manager import remove_from_pool
                await remove_from_pool(ch["session_id"])
                await db.remove_channel(channel_id)
                await event.answer("✅ Channel and its session removed.", alert=True)
                channels = await db.get_channels_by_owner(user_id)
                await event.edit(
                    ui.my_channels_text(channels),
                    buttons=ui.my_channels_buttons(channels),
                    parse_mode="html",
                )
            else:
                await event.answer("Channel not found.", alert=True)

        # ── Admin actions ───────────────────────────────────

        elif data == "admin_broadcast" and user_id == ADMIN_ID:
            _state(user_id)["step"] = STEP_AWAIT_BCAST
            await event.edit("📢 <b>Broadcast</b>\n\nSend the message to broadcast to all users.", parse_mode="html")

        elif data == "admin_stats" and user_id == ADMIN_ID:
            stats = await db.get_stats()
            sessions = await db.get_active_sessions()
            channels = await db.get_active_channels()
            lines = [ui.admin_panel_text(stats), "\n<b>Active Sessions:</b>"]
            for s in sessions[:20]:
                lines.append(f"• <code>{str(s['_id'])[:12]}...</code> owner: <code>{s['owner_id']}</code> fails: {s['fail_count']}")
            lines.append("\n<b>Active Channels:</b>")
            for c in channels[:20]:
                lines.append(f"• @{c['username']} owner: <code>{c['owner_id']}</code>")
            await event.edit("\n".join(lines), buttons=[[Button.inline("⬅️ Back", b"back_home")]], parse_mode="html")

        elif data == "admin_ban" and user_id == ADMIN_ID:
            await event.edit("🚫 <b>Ban User</b>\n\nSend the user ID to ban.", parse_mode="html")
            _state(user_id)["step"] = "await_ban_id"

        elif data == "admin_unban" and user_id == ADMIN_ID:
            await event.edit("✅ <b>Unban User</b>\n\nSend the user ID to unban.", parse_mode="html")
            _state(user_id)["step"] = "await_unban_id"

        await event.answer()

    # ── Message handler (state machine) ───────────────────────

    @client.on(events.NewMessage(func=lambda e: e.is_private and not e.message.text.startswith("/")))
    async def on_message(event):
        user_id = event.sender_id
        text = event.message.text.strip()
        state = _state(user_id)
        step = state.get("step", STEP_IDLE)

        if step == STEP_IDLE:
            return

        # ── Step: awaiting channel username ─────────────────

        elif step == STEP_AWAIT_CHANNEL:
            await event.respond("🔍 Looking up your channel...")
            try:
                channel_id, username = await _resolve_channel(client, text)
            except (ChannelInvalidError, ChannelPrivateError, UsernameInvalidError, ValueError):
                await event.respond(
                    "❌ <b>Channel not found.</b>\n\nMake sure it's a public channel and the username is correct.\nTry again or /cancel.",
                    parse_mode="html",
                )
                return
            except Exception as e:
                await event.respond(f"❌ Error: {e}\n\nTry again or /cancel.", parse_mode="html")
                return

            if await channel_exists(channel_id):
                await event.respond(ui.channel_exists_text(username), parse_mode="html")
                return

            state["step"]      = STEP_AWAIT_SESSION
            state["channel_id"]   = channel_id
            state["channel_user"] = username
            await event.respond(ui.ASK_SESSION, parse_mode="html")

        # ── Step: awaiting session string ────────────────────

        elif step == STEP_AWAIT_SESSION:
            session_str = text.strip()
            validating_msg = await event.respond(ui.validating_text(), parse_mode="html")

            is_valid, reason, info = await validate_session(session_str)

            if not is_valid:
                await validating_msg.edit(ui.session_invalid_text(reason), parse_mode="html")
                return

            # Save session to DB
            session_id = await add_session(owner_id=user_id, string=session_str)

            # Add to live pool
            await add_to_pool(session_id, session_str)

            # Save channel
            channel_id   = state["channel_id"]
            channel_user = state["channel_user"]
            await add_channel(
                channel_id=channel_id,
                username=channel_user,
                owner_id=user_id,
                session_id=session_id,
            )

            _clear(user_id)

            from xaayux.core import db as _db
            stats = await _db.get_stats()
            pool_size = stats["sessions"]

            await validating_msg.edit(
                ui.channel_added_text(channel_user, info["name"], info["username"], pool_size),
                buttons=[[Button.inline("⬅️ Home", b"back_home")]],
                parse_mode="html",
            )
            await notify_channel_added(user_id, channel_user, info)

        # ── Admin: broadcast ─────────────────────────────────

        elif step == STEP_AWAIT_BCAST and user_id == ADMIN_ID:
            from xaayux.core.notifier import broadcast
            users = await db.get_all_users()
            ids = [u["user_id"] for u in users]
            sent, failed = await broadcast(ids, text)
            _clear(user_id)
            await event.respond(
                f"📢 Broadcast done.\n✅ Sent: {sent}\n❌ Failed: {failed}",
                parse_mode="html",
            )

        # ── Admin: ban/unban ─────────────────────────────────

        elif step == "await_ban_id" and user_id == ADMIN_ID:
            try:
                target = int(text)
                await db.set_banned(target, True)
                _clear(user_id)
                await event.respond(f"🚫 User <code>{target}</code> banned.", parse_mode="html")
            except ValueError:
                await event.respond("❌ Invalid user ID.")

        elif step == "await_unban_id" and user_id == ADMIN_ID:
            try:
                target = int(text)
                await db.set_banned(target, False)
                _clear(user_id)
                await event.respond(f"✅ User <code>{target}</code> unbanned.", parse_mode="html")
            except ValueError:
                await event.respond("❌ Invalid user ID.")
