"""
ui.py — All message text and inline keyboard layouts for the bot
"""

from telethon import Button
from xaayux.config import SUPPORT_LINK, BOT_USERNAME

# ── Welcome ────────────────────────────────────────────────────

def welcome_text(first_name: str) -> str:
    return (
        f"👋 <b>Hey {first_name}!</b> Welcome to <b>ReactionNet</b>\n\n"
        "🔁 <b>How it works:</b>\n"
        "Every member donates a Telegram session (spare account).\n"
        "In return, <b>all sessions</b> in the network react to <b>your channel</b> — automatically, forever.\n\n"
        "🌱 The more people join, the more reactions everyone gets.\n\n"
        "<b>To get started, add your first channel below.</b>"
    )

def welcome_buttons():
    return [
        [Button.inline("➕ Add Channel", b"add_channel")],
        [Button.inline("📋 My Channels", b"my_channels"),
         Button.inline("📊 Network Stats", b"stats")],
        [Button.inline("ℹ️ How It Works", b"how_it_works"),
         Button.inline("💬 Support", b"support")],
    ]

# ── How It Works ───────────────────────────────────────────────

HOW_IT_WORKS = (
    "🔁 <b>ReactionNet — How It Works</b>\n\n"
    "<b>Step 1 — Donate a session</b>\n"
    "You give us a Telegram string session from a spare account.\n"
    "This account joins the global reaction pool.\n\n"
    "<b>Step 2 — Your channel gets reactions</b>\n"
    "You tell us your channel username.\n"
    "Every new post in your channel gets reacted to by ALL sessions in the pool.\n\n"
    "<b>Step 3 — You react to others too</b>\n"
    "Your donated session reacts to every other channel in the network.\n\n"
    "<b>1 session = 1 channel slot.</b>\n"
    "Want to enroll a second channel? Donate a second session.\n\n"
    "🛡️ <b>What happens if my session expires?</b>\n"
    "We detect it automatically. You get a DM warning, your session is removed "
    "from the pool, and your channel is unenrolled until you donate a fresh one.\n\n"
    "🔒 <b>Is it safe?</b>\n"
    "Sessions are only used to send reactions — nothing else.\n"
    "We never read your messages or post content."
)

def how_it_works_buttons():
    return [[Button.inline("⬅️ Back", b"back_home")]]

# ── Add Channel Flow ───────────────────────────────────────────

ASK_CHANNEL = (
    "📢 <b>Step 1 of 2 — Your Channel</b>\n\n"
    "Send me your channel username or invite link.\n\n"
    "<b>Examples:</b>\n"
    "• <code>@mychannel</code>\n"
    "• <code>https://t.me/mychannel</code>\n\n"
    "⚠️ Make sure the bot is an <b>admin</b> in your channel so it can monitor new posts.\n\n"
    "Type /cancel to abort."
)

ASK_SESSION = (
    "🔑 <b>Step 2 of 2 — Donate a Session</b>\n\n"
    "Send me a valid <b>Telegram String Session</b> from a spare account.\n\n"
    "This session will:\n"
    "• Be added to the global reaction pool\n"
    "• React to posts in <b>all enrolled channels</b> (including yours)\n"
    "• Unlock your channel for reactions from everyone\n\n"
    "📖 <b>How to generate a session string:</b>\n"
    "Run this on your machine:\n"
    "<pre>pip install telethon\npython3 -c \"\nfrom telethon.sync import TelegramClient\n"
    "from telethon.sessions import StringSession\nclient = TelegramClient(StringSession(), "
    "API_ID, API_HASH)\nclient.start()\nprint(client.session.save())\n\"</pre>\n\n"
    "⚠️ Use a <b>spare account</b>, not your main one.\n\n"
    "Type /cancel to abort."
)

def validating_text() -> str:
    return "⏳ <b>Validating your session...</b>\n\nConnecting to Telegram. This takes up to 30 seconds."

def session_invalid_text(reason: str) -> str:
    return (
        f"❌ <b>Invalid Session</b>\n\n"
        f"Reason: <i>{reason}</i>\n\n"
        "Please generate a fresh session string and try again.\n"
        "Type /cancel to abort or send a new session."
    )

def channel_added_text(channel: str, account_name: str, account_user: str, pool_size: int) -> str:
    return (
        f"🎉 <b>Channel Activated!</b>\n\n"
        f"• Channel: <b>@{channel}</b>\n"
        f"• Donated account: <b>{account_name}</b> ({account_user})\n"
        f"• Reactions from: <b>{pool_size} sessions</b> in the pool\n\n"
        "Every new post in your channel will now be reacted to automatically.\n"
        "Your session will also react to all other enrolled channels.\n\n"
        "🔁 Welcome to the loop!"
    )

def channel_exists_text(channel: str) -> str:
    return (
        f"⚠️ <b>@{channel} is already enrolled</b>\n\n"
        "This channel is already active in the network.\n"
        "Each channel can only be enrolled once."
    )

# ── My Channels ────────────────────────────────────────────────

def my_channels_text(channels: list) -> str:
    if not channels:
        return (
            "📋 <b>My Channels</b>\n\n"
            "You have no channels enrolled yet.\n\n"
            "Use ➕ Add Channel to get started."
        )
    lines = ["📋 <b>My Channels</b>\n"]
    for i, c in enumerate(channels, 1):
        status = "✅ Active" if c["status"] == "active" else "❌ Inactive"
        lines.append(f"{i}. @{c['username']} — {status}")
    lines.append("\n<i>Each channel requires 1 donated session.</i>")
    return "\n".join(lines)

def my_channels_buttons(channels: list):
    buttons = []
    for c in channels:
        buttons.append([Button.inline(
            f"🗑 Remove @{c['username']}",
            f"remove_channel:{c['channel_id']}".encode()
        )])
    buttons.append([Button.inline("➕ Add Another Channel", b"add_channel")])
    buttons.append([Button.inline("⬅️ Back", b"back_home")])
    return buttons

# ── Stats ──────────────────────────────────────────────────────

def stats_text(stats: dict) -> str:
    return (
        "📊 <b>ReactionNet — Live Stats</b>\n\n"
        f"👥 Total Users:       <b>{stats['users']}</b>\n"
        f"🔑 Active Sessions:   <b>{stats['sessions']}</b>\n"
        f"📢 Active Channels:   <b>{stats['channels']}</b>\n\n"
        "Every new post gets reacted to by all active sessions.\n"
        "Join and make the loop stronger! 🔁"
    )

def stats_buttons():
    return [
        [Button.inline("➕ Add My Channel", b"add_channel")],
        [Button.inline("⬅️ Back", b"back_home")],
    ]

# ── Support ────────────────────────────────────────────────────

def support_text() -> str:
    return (
        "💬 <b>Support</b>\n\n"
        f"Join our support channel for help, updates and announcements:\n{SUPPORT_LINK}\n\n"
        "Common issues:\n"
        "• <b>Session invalid</b> — generate a fresh one and re-add your channel\n"
        "• <b>Bot not reacting</b> — ensure bot is admin in your channel\n"
        "• <b>Channel not found</b> — use public username, not private links"
    )

def support_buttons():
    return [
        [Button.url("💬 Open Support Channel", SUPPORT_LINK)],
        [Button.inline("⬅️ Back", b"back_home")],
    ]

# ── Admin ──────────────────────────────────────────────────────

def admin_panel_text(stats: dict) -> str:
    return (
        "🛠 <b>Admin Panel</b>\n\n"
        f"👥 Users:    <b>{stats['users']}</b>\n"
        f"🔑 Sessions: <b>{stats['sessions']}</b>\n"
        f"📢 Channels: <b>{stats['channels']}</b>\n"
    )

def admin_buttons():
    return [
        [Button.inline("📢 Broadcast", b"admin_broadcast"),
         Button.inline("📊 Full Stats", b"admin_stats")],
        [Button.inline("🔑 List Sessions", b"admin_sessions"),
         Button.inline("📋 List Channels", b"admin_channels")],
        [Button.inline("🚫 Ban User", b"admin_ban"),
         Button.inline("✅ Unban User", b"admin_unban")],
    ]

# ── Misc ───────────────────────────────────────────────────────

CANCELLED = "❌ <b>Cancelled.</b> Use /start to go back to the menu."
BANNED    = "🚫 You are banned from using this bot."
