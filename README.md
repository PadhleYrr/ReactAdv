# 🔁 ReactionNet — Telegram Reaction Exchange Network

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)
![Telethon](https://img.shields.io/badge/Telethon-1.34%2B-green?style=for-the-badge)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-brightgreen?style=for-the-badge&logo=mongodb)
![License](https://img.shields.io/badge/License-Open%20Source-orange?style=for-the-badge)
![Deploy](https://img.shields.io/badge/Deploy-Heroku%20%7C%20VPS-purple?style=for-the-badge)

> A self-growing Telegram reaction network. Every member donates a session, every session reacts to every channel. The loop never ends — it only grows.

---

## 📌 How It Works

```
User A donates Session-A  →  unlocks Channel-A for reactions
User B donates Session-B  →  unlocks Channel-B for reactions
User C donates Session-C  →  unlocks Channel-C for reactions

New post in Channel-A?  →  Session-A + B + C all react to it
New post in Channel-B?  →  Session-A + B + C all react to it
New post in Channel-C?  →  Session-A + B + C all react to it
```

**1 session = 1 channel slot.**
Want to enroll 2 channels? Donate 2 sessions.
Your session reacts to everyone. Everyone's sessions react to you. 🔁

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔁 Reaction exchange loop | All sessions react to all channels automatically |
| 🔑 1-to-1 session→channel | Each channel slot costs exactly one donated session |
| 🛡️ Live session validation | Sessions are tested on submission before being accepted |
| 💀 Auto dead-session cleanup | Expired/banned sessions are detected and removed automatically |
| 📢 Owner notifications | DM alerts when your session dies or your channel is removed |
| 🤖 Professional bot UI | Inline buttons, guided onboarding, help sections |
| 🗄️ MongoDB persistence | All state stored in MongoDB Atlas — survives restarts |
| 🔧 Admin panel | Broadcast, ban/unban, view all sessions & channels |
| ♻️ Health checker | Background task checks all sessions every 30 minutes |
| 🚀 Heroku ready | Procfile + runtime.txt included |

---

## 🏗️ Project Structure

```
ReactionNet/
├── xaayux/
│   ├── __init__.py              # Boot sequence (DB → pool → bot → health checker)
│   ├── __main__.py              # Entry point
│   ├── config.py                # All settings (reads from env vars)
│   ├── core/
│   │   ├── db.py                # All MongoDB operations
│   │   ├── session_manager.py   # Live pool, validation, health checks
│   │   ├── notifier.py          # DM notifications to users
│   │   └── ui.py                # All message text and button layouts
│   └── plugins/
│       ├── bot.py               # Public bot — /start, add channel flow, admin panel
│       └── reaction.py          # Reaction engine — listens & fires all sessions
├── .env.example                 # Environment variable template
├── .gitignore
├── Procfile                     # Heroku: worker: python3 -m xaayux
├── requirements.txt
├── runtime.txt                  # python-3.11.3
└── README.md
```

---

## ⚙️ Setup

### 1. Clone & install

```bash
git clone https://github.com/yourrepo/ReactionNet.git
cd ReactionNet
pip install -r requirements.txt
```

### 2. Create a MongoDB Atlas database

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) → free tier is enough
2. Create a cluster → get your connection string
3. It looks like: `mongodb+srv://user:pass@cluster.mongodb.net/reactionnet`

### 3. Get Telegram API credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in → API Development Tools → Create App
3. Copy `API_ID` and `API_HASH`

### 4. Configure environment

Copy `.env.example` to `.env` and fill in:

```env
BOT_TOKEN=your_bot_token        # From @BotFather
ADMIN_ID=your_telegram_user_id  # Your personal Telegram ID
API_ID=your_api_id              # From my.telegram.org
API_HASH=your_api_hash          # From my.telegram.org
MONGO_URI=mongodb+srv://...     # Your Atlas connection string
```

### 5. Run

```bash
python3 -m xaayux
```

---

## 🚀 Deploy to Heroku

```bash
heroku create your-app-name
heroku config:set BOT_TOKEN=xxx ADMIN_ID=xxx API_ID=xxx API_HASH=xxx MONGO_URI=xxx
git push heroku main
heroku ps:scale worker=1
```

---

## 🤖 Bot User Flow

```
/start
  │
  ├── ➕ Add Channel
  │     ├── Step 1: Send channel username (@mychannel)
  │     │           Bot verifies channel exists & not already enrolled
  │     ├── Step 2: Send a string session from a spare account
  │     │           Bot validates session live (connects to Telegram)
  │     └── ✅ Channel activated — reactions start immediately
  │
  ├── 📋 My Channels  →  list all your enrolled channels + status
  ├── 📊 Network Stats →  total users, sessions, channels live
  ├── ℹ️ How It Works  →  full explanation
  └── 💬 Support       →  support channel link
```

---

## 🛠️ Admin Commands

Message the bot from your admin account:

| Action | How |
|---|---|
| Open admin panel | `/admin` |
| Broadcast to all users | Admin Panel → 📢 Broadcast → send message |
| Ban a user | Admin Panel → 🚫 Ban → send user ID |
| Unban a user | Admin Panel → ✅ Unban → send user ID |
| View all sessions | Admin Panel → 🔑 List Sessions |
| View all channels | Admin Panel → 📋 List Channels |

---

## 🔑 Generating a String Session

Users need to generate a session string from a **spare Telegram account**. Here's how:

```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID   = 123456        # your api_id
API_HASH = "your_hash"   # your api_hash

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())
```

Run it, log in with the spare account's phone number, and copy the printed string.

---

## 🛡️ Session Health System

Every **30 minutes**, the system checks all active sessions:

```
For each session:
  → Try to call get_me() with a 15s timeout
  → If alive: reset fail counter ✅
  → If dead:  increment fail counter
    → fail == 2: send warning DM to owner ⚠️
    → fail == 3: mark session dead, remove from pool,
                 remove associated channel,
                 send DM to session owner,
                 send DM to channel owner ❌
```

This keeps the pool clean without manual intervention.

---

## 📦 Dependencies

```
telethon>=1.34.0      # Telegram client
motor>=3.3.0          # Async MongoDB driver
pymongo>=4.6.0        # MongoDB
python-decouple>=3.8  # Env var management
cryptg>=0.4.0         # Faster encryption (optional but recommended)
```

---

## 🔐 Security Notes

- **Never share session strings** — they give full account access
- **Never commit `.env`** — it's in `.gitignore` already
- Sessions are used **only to send reactions** — the bot never reads messages or posts content
- Use only **spare accounts** for sessions, never your main account

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `FloodWaitError` on reactions | Normal — Telethon handles this automatically with retries |
| Session rejected on submission | Regenerate the session string; account may be restricted |
| Channel not found | Use public username only (`@channel`), not private invite links |
| Bot not responding | Check `BOT_TOKEN` and that the bot isn't stopped |
| MongoDB connection failed | Verify `MONGO_URI` and whitelist your server IP in Atlas |
| Reactions stopped on my channel | Your donated session may have died — check DMs from bot |

---

## 📣 Credits

- Built with [Telethon](https://github.com/LonamiWebs/Telethon) + [Motor](https://motor.readthedocs.io/)
- Original concept by [@xAaYuX](https://t.me/xAaYuX) and [@LegendxTricks](https://t.me/LegendxTricks)
- Support: [t.me/LegendxTricks](https://t.me/LegendxTricks)

---

## 📄 License

Open source — free to use, modify, and distribute.
