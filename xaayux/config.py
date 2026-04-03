import os

# ── Telegram Bot ──────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN",  "5449793938:AAFe6U4iNY_QXF2gaCdeO258c2_cFvjjOx4")
ADMIN_ID   = int(os.getenv("ADMIN_ID", "5488677608"))
API_ID     = int(os.getenv("API_ID",   "7630000"))
API_HASH   = os.getenv("API_HASH",     "f70361ddf4ec755395b4b6f1ab2d4fae")

# ── MongoDB ───────────────────────────────────────────────────
MONGO_URI  = os.getenv("MONGO_URI", "mongodb+srv://xaayux:xaayux@cluster0.mojpz.mongodb.net/reactionnet?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME    = "reactionnet"

# ── Behaviour ─────────────────────────────────────────────────
HEALTH_CHECK_INTERVAL = 1800        # seconds between session health checks
REACTION_DELAY        = 2           # seconds between each reaction call
MAX_FAIL_COUNT        = 3           # consecutive failures before session killed
SESSION_VALIDATE_TIMEOUT = 30       # seconds to wait when validating a new session

EMOJIS = ["❤️", "👍", "😂", "🔥", "🎉", "😎", "🤖", "💯", "✨", "🙌"]

# ── Text / UI ─────────────────────────────────────────────────
SUPPORT_LINK  = "https://t.me/LegendxTricks"
BOT_USERNAME  = "YourBotUsername"   # update after deploying
