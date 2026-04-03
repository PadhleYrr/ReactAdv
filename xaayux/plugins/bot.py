"""
bot.py — Public bot with phone+OTP login flow for session generation
State machine handles: channel enrollment, phone login, OTP, 2FA, admin panel
"""

import asyncio
import logging
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
    FloodWaitError,
    ChannelInvalidError,
    ChannelPrivateError,
    UsernameInvalidError,
    ApiIdInvalidError,
)

from xaayux.config import ADMIN_ID, BOT_TOKEN, API_ID, API_HASH
from xaayux.core import db
from xaayux.core import ui
from xaayux.core.notifier import set_bot, notify_channel_added
from xaayux.core.session_manager import add_to_pool
from xaayux.core.db import add_session, add_channel, channel_exists

log = logging.getLogger(__name__)

# ── State steps ────────────────────────────────────────────────
STEP_IDLE           = "idle"
STEP_AWAIT_CHANNEL  = "await_channel"
STEP_AWAIT_PHONE    = "await_phone"
STEP_AWAIT_OTP      = "await_otp"
STEP_AWAIT_2FA      = "await_2fa"
STEP_AWAIT_BCAST    = "await_broadcast"
STEP_AWAIT_BAN      = "await_ban_id"
STEP_AWAIT_UNBAN    = "await_unban_id"

# user_id → state dict
_states: dict[int, dict] = {}

# user_id → temp TelegramClient used during login flow
_login_clients: dict[int, TelegramClient] = {}

bot_client: TelegramClient = None


# ── Boot ───────────────────────────────────────────────────────

async def start_bot(userbot_clients: list):
    global bot_client
    bot_client = TelegramClient(StringSession(), api_id=API_ID, api_hash=API_HASH)
    await bot_client.start(bot_token=BOT_TOKEN)
    set_bot(bot_client)
    log.info("✅ Bot started")

    from xaayux.plugins.reaction import register_listener
    register_listener(bot_client)

    _register_handlers(bot_client)
    await bot_client.run_until_disconnected()


# ── State helpers ──────────────────────────────────────────────

def _state(user_id: int) -> dict:
    return _states.setdefault(user_id, {"step": STEP_IDLE})

def _clear(user_id: int):
    _states.pop(user_id, None)
    # Clean up any dangling login client
    client = _login_clients.pop(user_id, None)
    if client:
        asyncio.create_task(_safe_disconnect(client))

async def _safe_disconnect(client: TelegramClient):
    try:
        await client.disconnect()
    except Exception:
        pass

async def _resolve_channel(client: TelegramClient, text: str):
    username = (
        text.strip()
        .lstrip("@")
        .replace("https://t.me/", "")
        .replace("http://t.me/", "")
        .strip("/")
    )
    entity = await client.get_entity(f"@{username}")
    return entity.id, username

async def _go_home(event):
    _clear(event.sender_id)
    sender = await event.get_sender()
    name = getattr(sender, "first_name", "there") or "there"
    await event.edit(
        ui.welcome_text(name),
        buttons=ui.welcome_buttons(),
        parse_mode="html",
    )


# ── Register all handlers ──────────────────────────────────────

def _register_handlers(client: TelegramClient):

    # ── /start ────────────────────────────────────────────────

    @client.on(events.NewMessage(pattern="/start"))
    async def cmd_start(event):
        user = await event.get_sender()
        user_data = await db.get_user(user.id)
        if user_data and user_data.get("is_banned"):
            await event.respond(ui.BANNED)
            return
        await db.upsert_user(user.id, getattr(user, "username", None), user.first_name)
        _clear(user.id)
        await event.respond(
            ui.welcome_text(user.first_name or "there"),
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

    # ── Callback buttons ───────────────────────────────────────

    @client.on(events.CallbackQuery())
    async def on_callback(event):
        data = event.data.decode()
        user_id = event.sender_id

        user_data = await db.get_user(user_id)
        if user_data and user_data.get("is_banned"):
            await event.answer(ui.BANNED, alert=True)
            return

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

        elif data.startswith("remove_channel:"):
            channel_id = int(data.split(":")[1])
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

        # ── Admin ──────────────────────────────────────────────

        elif data == "admin_broadcast" and user_id == ADMIN_ID:
            _state(user_id)["step"] = STEP_AWAIT_BCAST
            await event.edit(
                "📢 <b>Broadcast</b>\n\nSend the message you want to broadcast to all users.",
                parse_mode="html",
            )

        elif data == "admin_stats" and user_id == ADMIN_ID:
            stats    = await db.get_stats()
            sessions = await db.get_active_sessions()
            channels = await db.get_active_channels()
            lines = [ui.admin_panel_text(stats), "\n<b>Active Sessions (latest 20):</b>"]
            for s in sessions[:20]:
                lines.append(f"• <code>{str(s['_id'])[:12]}…</code>  owner: <code>{s['owner_id']}</code>  fails: {s['fail_count']}")
            lines.append("\n<b>Active Channels (latest 20):</b>")
            for c in channels[:20]:
                lines.append(f"• @{c['username']}  owner: <code>{c['owner_id']}</code>")
            await event.edit(
                "\n".join(lines),
                buttons=[[Button.inline("⬅️ Back", b"back_home")]],
                parse_mode="html",
            )

        elif data == "admin_ban" and user_id == ADMIN_ID:
            _state(user_id)["step"] = STEP_AWAIT_BAN
            await event.edit("🚫 <b>Ban User</b>\n\nSend the Telegram user ID to ban.", parse_mode="html")

        elif data == "admin_unban" and user_id == ADMIN_ID:
            _state(user_id)["step"] = STEP_AWAIT_UNBAN
            await event.edit("✅ <b>Unban User</b>\n\nSend the Telegram user ID to unban.", parse_mode="html")

        await event.answer()

    # ── Message handler (state machine) ───────────────────────

    @client.on(events.NewMessage(func=lambda e: e.is_private and not e.message.text.startswith("/")))
    async def on_message(event):
        user_id = event.sender_id
        text    = (event.message.text or "").strip()
        state   = _state(user_id)
        step    = state.get("step", STEP_IDLE)

        if step == STEP_IDLE:
            return

        # ── 1. Awaiting channel username ───────────────────────

        elif step == STEP_AWAIT_CHANNEL:
            msg = await event.respond("🔍 Looking up your channel...")
            try:
                channel_id, username = await _resolve_channel(client, text)
            except (ChannelInvalidError, ChannelPrivateError, UsernameInvalidError, ValueError):
                await msg.edit(
                    "❌ <b>Channel not found.</b>\n\nMake sure it's public and the username is correct.\nTry again or /cancel.",
                    parse_mode="html",
                )
                return
            except Exception as e:
                await msg.edit(f"❌ Error: {e}\n\nTry again or /cancel.", parse_mode="html")
                return

            if await channel_exists(channel_id):
                await msg.edit(
                    f"⚠️ <b>@{username} is already enrolled</b>\n\nThis channel is already active in the network.",
                    parse_mode="html",
                )
                return

            state["step"]         = STEP_AWAIT_PHONE
            state["channel_id"]   = channel_id
            state["channel_user"] = username
            await msg.edit(ui.ask_phone_text(username), parse_mode="html")

        # ── 2. Awaiting phone number ───────────────────────────

        elif step == STEP_AWAIT_PHONE:
            phone = text.strip()
            if not phone.startswith("+"):
                await event.respond(
                    "❌ Please include the country code.\nExample: <code>+91XXXXXXXXXX</code>",
                    parse_mode="html",
                )
                return

            msg = await event.respond(ui.SENDING_OTP, parse_mode="html")

            # Create a fresh client for this user's login session
            login_client = TelegramClient(StringSession(), api_id=API_ID, api_hash=API_HASH)
            try:
                await login_client.connect()
                send_result = await login_client.send_code_request(phone)
                _login_clients[user_id] = login_client
                state["step"]        = STEP_AWAIT_OTP
                state["phone"]       = phone
                state["phone_hash"]  = send_result.phone_code_hash
                await msg.edit(ui.ask_otp_text(phone), parse_mode="html")

            except PhoneNumberInvalidError:
                await _safe_disconnect(login_client)
                await msg.edit(ui.login_error_text("Phone number is invalid. Check the format and try again."), parse_mode="html")
                state["step"] = STEP_AWAIT_PHONE

            except FloodWaitError as e:
                await _safe_disconnect(login_client)
                await msg.edit(
                    ui.login_error_text(f"Too many attempts. Please wait {e.seconds} seconds and try again."),
                    parse_mode="html",
                )
                state["step"] = STEP_AWAIT_PHONE

            except ApiIdInvalidError:
                await _safe_disconnect(login_client)
                await msg.edit(ui.login_error_text("API credentials error. Please contact support."), parse_mode="html")
                _clear(user_id)

            except Exception as e:
                await _safe_disconnect(login_client)
                await msg.edit(ui.login_error_text(str(e)), parse_mode="html")
                state["step"] = STEP_AWAIT_PHONE

        # ── 3. Awaiting OTP ────────────────────────────────────

        elif step == STEP_AWAIT_OTP:
            code         = text.replace(" ", "").replace("-", "")
            login_client = _login_clients.get(user_id)

            if not login_client:
                await event.respond("❌ Session expired. Please start over.", parse_mode="html")
                _clear(user_id)
                return

            msg = await event.respond(ui.LOGGING_IN, parse_mode="html")
            try:
                await login_client.sign_in(
                    phone=state["phone"],
                    code=code,
                    phone_code_hash=state["phone_hash"],
                )
                # Success — save session
                await _finalize_login(event, user_id, login_client, msg)

            except SessionPasswordNeededError:
                # 2FA required
                state["step"] = STEP_AWAIT_2FA
                await msg.edit(ui.ask_2fa_text(), parse_mode="html")

            except PhoneCodeInvalidError:
                await msg.edit(ui.otp_error_text("Incorrect code. Please check and try again."), parse_mode="html")

            except PhoneCodeExpiredError:
                await msg.edit(ui.otp_error_text("Code has expired. Type /cancel and start over."), parse_mode="html")

            except FloodWaitError as e:
                await msg.edit(
                    ui.otp_error_text(f"Too many attempts. Wait {e.seconds}s then try again."),
                    parse_mode="html",
                )

            except Exception as e:
                await msg.edit(ui.otp_error_text(str(e)), parse_mode="html")

        # ── 4. Awaiting 2FA password ───────────────────────────

        elif step == STEP_AWAIT_2FA:
            password     = text
            login_client = _login_clients.get(user_id)

            if not login_client:
                await event.respond("❌ Session expired. Please start over.", parse_mode="html")
                _clear(user_id)
                return

            msg = await event.respond(ui.LOGGING_IN, parse_mode="html")
            try:
                await login_client.sign_in(password=password)
                await _finalize_login(event, user_id, login_client, msg)

            except PasswordHashInvalidError:
                await msg.edit(
                    "❌ <b>Wrong 2FA password.</b>\n\nPlease try again or type /cancel.",
                    parse_mode="html",
                )

            except FloodWaitError as e:
                await msg.edit(
                    f"❌ Too many attempts. Wait {e.seconds}s then try again.",
                    parse_mode="html",
                )

            except Exception as e:
                await msg.edit(f"❌ Error: {e}", parse_mode="html")

        # ── Admin: broadcast ───────────────────────────────────

        elif step == STEP_AWAIT_BCAST and user_id == ADMIN_ID:
            from xaayux.core.notifier import broadcast
            users = await db.get_all_users()
            ids   = [u["user_id"] for u in users]
            sent, failed = await broadcast(ids, text)
            _clear(user_id)
            await event.respond(
                f"📢 <b>Broadcast complete.</b>\n✅ Sent: {sent}\n❌ Failed: {failed}",
                parse_mode="html",
            )

        # ── Admin: ban/unban ───────────────────────────────────

        elif step == STEP_AWAIT_BAN and user_id == ADMIN_ID:
            try:
                target = int(text)
                await db.set_banned(target, True)
                _clear(user_id)
                await event.respond(f"🚫 User <code>{target}</code> has been banned.", parse_mode="html")
            except ValueError:
                await event.respond("❌ Invalid user ID. Send numbers only.")

        elif step == STEP_AWAIT_UNBAN and user_id == ADMIN_ID:
            try:
                target = int(text)
                await db.set_banned(target, False)
                _clear(user_id)
                await event.respond(f"✅ User <code>{target}</code> has been unbanned.", parse_mode="html")
            except ValueError:
                await event.respond("❌ Invalid user ID. Send numbers only.")


# ── Finalize login — shared by OTP and 2FA paths ──────────────

async def _finalize_login(event, user_id: int, login_client: TelegramClient, msg):
    """Called once sign_in() succeeds. Saves session, adds to pool, enrolls channel."""
    try:
        me = await login_client.get_me()
        session_string = login_client.session.save()

        # Save to DB
        session_id = await add_session(owner_id=user_id, string=session_string)

        # Move client into live pool (reuse existing connection)
        from xaayux.core.session_manager import _pool
        _pool[session_id] = login_client
        _login_clients.pop(user_id, None)  # remove from temp map (don't disconnect)

        # Enroll channel
        state        = _state(user_id)
        channel_id   = state["channel_id"]
        channel_user = state["channel_user"]
        await add_channel(
            channel_id=channel_id,
            username=channel_user,
            owner_id=user_id,
            session_id=session_id,
        )

        _clear(user_id)

        stats     = await db.get_stats()
        pool_size = stats["sessions"]
        name      = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Unknown"
        uname     = f"@{me.username}" if me.username else "no username"

        await msg.edit(
            ui.login_success_text(channel_user, name, uname, pool_size),
            buttons=[[Button.inline("🏠 Home", b"back_home")]],
            parse_mode="html",
        )
        await notify_channel_added(user_id, channel_user, {"name": name, "username": uname})
        log.info(f"User {user_id} enrolled channel @{channel_user} via phone login ({name})")

    except Exception as e:
        log.error(f"_finalize_login error for user {user_id}: {e}")
        await msg.edit(
            f"❌ <b>Something went wrong while saving your session.</b>\n\nError: {e}\n\nPlease try again or contact support.",
            parse_mode="html",
        )
        _clear(user_id)
