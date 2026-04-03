# 🔁 ReactionNet — Telegram Reaction Exchange Network

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)
![Telethon](https://img.shields.io/badge/Telethon-1.34%2B-green?style=for-the-badge)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-brightgreen?style=for-the-badge&logo=mongodb)
![Deploy](https://img.shields.io/badge/Deploy-Heroku%20%7C%20VPS-purple?style=for-the-badge)

> A self-growing Telegram reaction network. Every member logs in with a spare account. Every account reacts to every channel. The loop never ends — it only grows.

---

## 📌 How It Works

```
User A logs in with spare account A  →  unlocks Channel A
User B logs in with spare account B  →  unlocks Channel B
User C logs in with spare account C  →  unlocks Channel C

New post in Channel A?  →  Accounts A + B + C all react ✅
New post in Channel B?  →  Accounts A + B + C all react ✅
New post in Channel C?  →  Accounts A + B + C all react ✅
```

**1 login = 1 channel slot.**
Want 2 channels? Log in with 2 spare accounts.
Everyone reacts to you. You react to everyone. 🔁

---

## ✨ Features

| Feature | Details |
|---|---|
| 📱 Phone + OTP login | Users just enter phone number + OTP — no technical steps |
| 🔐 2FA support | Handles accounts with Two-Factor Authentication |
| 🔁 Reaction exchange loop | All sessions react to all channels automatically |
| 🛡️ Auto dead-session cleanup | Expired/banned sessions detected and removed every 30 min |
| 📢 Owner DM notifications | Alerts when your session dies or channel is removed |
| 🤖 Professional bot UI | Inline buttons, guided onboarding, help sections |
| 🗄️ MongoDB persistence | All state in MongoDB Atlas — survives restarts |
| 🔧 Admin panel | Broadcast, ban/unban, view all sessions & channels |
| 🚀 Heroku ready | Procfile + runtime.txt included |

---

## 🏗️ Project Structure

```
ReactionNet/
├── xaayux/
│   ├── __init__.py              # Boot: DB → session pool → bot → health checker
│   ├── __main__.py              # Entry point
│   ├── config.py                # All settings (reads from env vars)
│   ├── core/
│   │   ├── db.py                # All MongoDB operations
│   │   ├── session_manager.py   # Live pool, health checks, dead session handling
│   │   ├── notifier.py          # DM notifications to users
│   │   └── ui.py                # All message text and button layouts
│   └── plugins/
│       ├── bot.py               # Public bot — full login flow + admin panel
│       └── reaction.py          # Reaction engine — listens & fires all sessions
├── .env.example                 # Environment variable template
├── .gitignore
├── Procfile                     # Heroku: worker: python3 -m xaayux
├── requirements.txt
├── runtime.txt                  # python-3.11.3
└── README.md
```

---

## 🤖 User Flow

```
/start
  │
  └── ➕ Add Channel
        │
        ├── Step 1: Send your channel username (@mychannel)
        │          Bot verifies channel exists & not already enrolled
        │
        ├── Step 2: Send your spare account's phone number (+91XXXXXXXXXX)
        │          Bot requests OTP from Telegram on the backend
        │
        ├── Step 3: Send the OTP code Telegram sent you
        │          (If 2FA) Bot asks for your cloud password
        │
        └── ✅ Session generated silently, channel activated
               All pool accounts start reacting to your channel immediately
```

No API IDs. No session strings. Just **phone number + OTP**.

---

## ⚙️ Setup

### 1. Clone & install

```bash
git clone https://github.com/yourrepo/ReactionNet.git
cd ReactionNet
pip install -r requirements.txt
```

### 2. MongoDB Atlas (free)

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) → create free cluster
2. Get connection string: `mongodb+srv://user:pass@cluster.mongodb.net/reactionnet`

### 3. Telegram API credentials

1. Go to [my.telegram.org](https://my.telegram.org) → API Development Tools
2. Create app → copy `API_ID` and `API_HASH`

### 4. Configure environment

Copy `.env.example` → `.env` and fill in:

```env
BOT_TOKEN=your_bot_token         # From @BotFather
ADMIN_ID=your_telegram_user_id   # Your Telegram ID
API_ID=your_api_id               # From my.telegram.org
API_HASH=your_api_hash           # From my.telegram.org
MONGO_URI=mongodb+srv://...      # Your Atlas connection string
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

## 🛠️ Admin Commands

Message the bot from your `ADMIN_ID` account:

| Action | How |
|---|---|
| Open admin panel | `/admin` |
| Broadcast to all users | Admin Panel → 📢 Broadcast |
| Ban a user | Admin Panel → 🚫 Ban → send user ID |
| Unban a user | Admin Panel → ✅ Unban → send user ID |
| View all sessions | Admin Panel → 🔑 Sessions |
| View all channels | Admin Panel → 📋 Channels |

---

## 🛡️ Session Health System

Every **30 minutes**, the bot checks every active session:

```
→ Alive?      reset fail counter ✅
→ 1st fail?   log warning
→ 2nd fail?   send DM warning to owner ⚠️
→ 3rd fail?   kill session, remove channel, notify owner ❌
```

Self-cleaning. Zero manual intervention needed.

---

## 🔐 Security & Transparency

- Spare accounts are used **only to send emoji reactions** — nothing else
- We never read messages, post content, or access private data
- Sessions are stored encrypted in MongoDB
- Users are informed exactly what their account will be used for before login
- **Always use spare accounts**, never your main Telegram account

---

## 📦 Dependencies

```
telethon>=1.34.0      # Telegram client & OTP login
motor>=3.3.0          # Async MongoDB driver
pymongo>=4.6.0        # MongoDB
python-decouple>=3.8  # Env var management
cryptg>=0.4.0         # Faster encryption (recommended)
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| OTP not received | Wait 60s, try again. Check SMS too |
| 2FA password wrong | Recover via Telegram Settings → Privacy → Two-Step Verification |
| Phone number invalid | Include country code e.g. `+91XXXXXXXXXX` |
| Channel not found | Must be a public channel with a username |
| Bot not reacting | Ensure bot is admin in your channel |
| MongoDB error | Whitelist your server IP in Atlas Network Access |
| Reactions stopped | Your session expired — check DMs from bot and re-login |

---

## 📣 Credits

- Built with [Telethon](https://github.com/LonamiWebs/Telethon) + [Motor](https://motor.readthedocs.io/)
- Original concept by [@xAaYuX](https://t.me/xAaYuX) and [@LegendxTricks](https://t.me/LegendxTricks)
- Support: [t.me/LegendxTricks](https://t.me/LegendxTricks)

---

## 📄 License

Open source — free to use, modify, and distribute.
