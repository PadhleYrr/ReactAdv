"""
xaayux/__init__.py — Boot sequence for ReactionNet
"""

import asyncio
import logging
from xaayux.core import db
from xaayux.core.session_manager import boot_pool, health_check_all
from xaayux.plugins.bot import start_bot

logging.basicConfig(
    format="[%(levelname)5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

async def main():
    log.info("🚀 ReactionNet starting...")

    # 1. Connect to MongoDB
    await db.connect()

    # 2. Load all saved sessions into live pool
    await boot_pool()

    # 3. Run bot + health checker concurrently
    from xaayux.plugins.bot import bot_client as _bc
    await asyncio.gather(
        start_bot([]),                    # starts bot, registers reaction listener
        _run_health_check(),
    )

async def _run_health_check():
    # Wait for bot to start before running health checks
    await asyncio.sleep(10)
    from xaayux.plugins.bot import bot_client
    await health_check_all(bot_client)
