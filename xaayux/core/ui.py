"""
ui.py — All message text and inline keyboard layouts for the bot
"""

from telethon import Button
from xaayux.config import SUPPORT_LINK

# ── Welcome ────────────────────────────────────────────────────

def welcome_text(first_name: str) -> str:
    return (
        f"👋 <b>Hey {first_name}!</b> Welcome to <b>ReactionNet</b>\n\n"
        "🔁 <b>How it works:</b>\n"
        "Every member logs in with a spare Telegram account.\n"
        "In return, <b>all accounts</b> in the network react to <b>your channel</b> — automatically, forever.\n\n"
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
    "<b>Step 1 — Login with a spare account</b>\n"
    "You log in with a spare Telegram account via phone + OTP.\n"
    "That account joins the global reaction pool.\n\n"
    "<b>Step 2 — Your channel gets reactions</b>\n"
    "Every new post in your channel gets reacted to by ALL accounts in the pool.\n\n"
    "<b>Step 3 — You react to others too</b>\n"
    "Your spare account reacts to every other enrolled channel automatically.\n\n"
    "<b>1 login = 1 channel slot.</b>\n"
    "Want to enroll a 2nd channel? Log in with a 2nd spare account.\n\n"
    "🛡️ <b>What if my session expires?</b>\n"
    "We detect it automatically. You get a DM warning, the account is removed "
    "and your channel is unenrolled until you log in again.\n\n"
    "🔒 <b>Is it safe?</b>\n"
    "Accounts are <b>only used to send reactions</b> — nothing else.\n"
    "We never read your messages, send messages, or access any content."
)

def how_it_works_buttons():
    return [[Button.inline("⬅️ Back", b"back_home")]]

# ── Add Channel ─────────────────────────────────────────────────

ASK_CHANNEL = (
    "📢 <b>Step 1 of 2 — Your Channel</b>\n\n"
    "Send me your channel username or link.\n\n"
    "<b>Examples:</b>\n"
    "• <code>@mychannel</code>\n"
    "• <code>https://t.me/mychannel</code>\n\n"
    "⚠️ Make sure this bot is an <b>admin</b> in your channel so it can monitor posts.\n\n"
    "Type /cancel to abort."
)

def ask_phone_text(channel: str) -> str:
    return (
        f"✅ <b>Channel found: @{channel}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>Step 2 of 2 — Login with a spare account</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "To activate reactions for your channel, you need to log in with a <b>spare Telegram account</b>.\n\n"
        "That account will:\n"
        "• React to posts in <b>all enrolled channels</b> (including yours)\n"
        "• <b>Never</b> send messages, read chats, or do anything else\n"
        "• Be automatically removed if it gets banned or expires\n\n"
        "📱 Send me the phone number of your spare account.\n\n"
        "<b>Format:</b> <code>+91XXXXXXXXXX</code> (include country code)\n\n"
        "Type /cancel to abort."
    )

def ask_otp_text(phone: str) -> str:
    return (
        f"📲 <b>OTP Sent to {phone}</b>\n\n"
        "Telegram has sent a verification code to that account.\n\n"
        "Check the Telegram app on that phone (or SMS) and send the code here.\n\n"
        "<b>Format:</b> <code>12345</code> (5 digits, no spaces)\n\n"
        "⏳ Code expires in 2 minutes.\n\n"
        "Type /cancel to abort."
    )

def ask_2fa_text() -> str:
    return (
        "🔐 <b>Two-Factor Authentication</b>\n\n"
        "This account has 2FA (cloud password) enabled.\n\n"
        "Send your <b>2FA password</b> to continue.\n\n"
        "Type /cancel to abort."
    )

def login_success_text(channel: str, name: str, username: str, pool_size: int) -> str:
    return (
        "🎉 <b>Channel Activated!</b>\n\n"
        f"• Channel: <b>@{channel}</b>\n"
        f"• Logged in as: <b>{name}</b> ({username})\n"
        f"• Reactions from: <b>{pool_size} accounts</b> in the pool\n\n"
        "Every new post in your channel will now be reacted to automatically.\n"
        "Your account will also react to all other enrolled channels.\n\n"
        "🔁 Welcome to the loop!"
    )

def login_error_text(reason: str) -> str:
    return (
        f"❌ <b>Login Failed</b>\n\n"
        f"Reason: <i>{reason}</i>\n\n"
        "Please try again with a valid spare account.\n"
        "Type /cancel to abort or send a different phone number."
    )

def otp_error_text(reason: str) -> str:
    return (
        f"❌ <b>Invalid Code</b>\n\n"
        f"Reason: <i>{reason}</i>\n\n"
        "Please check the code and try again, or type /cancel."
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
    lines.append("\n<i>Each channel requires 1 spare account login.</i>")
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
        "Every new post gets reacted to by all active accounts.\n"
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
        "<b>Common issues:</b>\n"
        "• <b>OTP not received</b> — wait 60s and try again\n"
        "• <b>2FA forgotten</b> — recover via Telegram settings first\n"
        "• <b>Bot not reacting</b> — ensure bot is admin in your channel\n"
        "• <b>Channel removed</b> — your session may have expired, re-login"
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
        [Button.inline("📢 Broadcast",      b"admin_broadcast"),
         Button.inline("📊 Full Stats",     b"admin_stats")],
        [Button.inline("🔑 Sessions",       b"admin_sessions"),
         Button.inline("📋 Channels",       b"admin_channels")],
        [Button.inline("🚫 Ban User",       b"admin_ban"),
         Button.inline("✅ Unban User",     b"admin_unban")],
    ]

# ── Misc ───────────────────────────────────────────────────────

CANCELLED = "❌ <b>Cancelled.</b> Use /start to go back to the menu."
BANNED    = "🚫 You are banned from using this bot."
SENDING_OTP = "📲 <b>Sending OTP...</b>\n\nRequesting verification code from Telegram. Please wait."
LOGGING_IN  = "⏳ <b>Logging in...</b>\n\nVerifying your code with Telegram."
