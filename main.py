import asyncio
import logging
import os
import sys
from pathlib import Path
from aiohttp import web

# ---------------------------------------------------------------------------
# Load .env manually (no python-dotenv dependency required)
# ---------------------------------------------------------------------------
def _load_dotenv(path: str = ".env"):
    env_file = Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

_load_dotenv()

from app.config import BOT_TOKEN, HOST, PORT, APP_URL, DEBUG
from app.database import init_db
from app.web.app import create_web_app
from app.bot.bot_instance import get_bot, get_dispatcher
from app.bot.handlers import start_router, items_router

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("plancart")


async def setup_webhook(bot, dp, web_app: web.Application):
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    
    webhook_path = f"/tg/webhook"
    webhook_url = f"{APP_URL}{webhook_path}"
    
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True
    )
    logger.info(f"Webhook set: {webhook_url}")
    
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(web_app.router, path=webhook_path)
    setup_application(web_app, dp, bot=bot)


async def main():
    logger.info("🚀 Initializing PlanCart...")
    
    # Init DB
    await init_db()
    logger.info("✅ Database initialized")
    
    # Create web app
    web_app = create_web_app()
    logger.info("✅ Web app created")
    
    if not BOT_TOKEN:
        logger.warning("⚠️  BOT_TOKEN not set — Telegram bot disabled. Running web server only.")
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        logger.info(f"🌐 Server running at http://{HOST}:{PORT}")
        await asyncio.Event().wait()
        return
    
    bot = get_bot()
    dp = get_dispatcher()
    
    # Register routers
    dp.include_router(start_router)
    dp.include_router(items_router)
    
    if APP_URL and not APP_URL.startswith("http://localhost"):
        # Webhook mode (production)
        await setup_webhook(bot, dp, web_app)
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        logger.info(f"🌐 PlanCart running at {APP_URL} (webhook mode)")
        await asyncio.Event().wait()
    else:
        # Long polling mode (development)
        logger.info("🔄 Starting in long-polling mode (dev)...")
        
        # Delete existing webhook to avoid conflicts
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Start web server in background
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        logger.info(f"🌐 Web server: http://{HOST}:{PORT}")
        
        try:
            await dp.start_polling(bot, polling_timeout=30)
        finally:
            await runner.cleanup()
            await bot.session.close()
            logger.info("👋 Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
