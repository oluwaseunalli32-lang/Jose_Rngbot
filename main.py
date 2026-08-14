import logging
import os
import asyncio
from random import randint

from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN set in environment variables")

PORT = int(os.environ.get("PORT", 8080))

# --------------------- Bot Handlers ---------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message."""
    await update.message.reply_text(
        "🎲 Hi! I'm your random number generator.\n"
        "Use /random <min> <max> to get a random integer.\n"
        "Example: /random 1 100\n"
        "If you omit numbers, I'll use 1–100 by default."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    await update.message.reply_text(
        "📖 *Help*\n"
        "/start – Show welcome\n"
        "/help  – Show this help\n"
        "/random [min] [max] – Generate a random number\n"
        "   * min* – lower bound (default 1)\n"
        "   * max* – upper bound (default 100)",
        parse_mode="Markdown"
    )

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a random integer between min and max."""
    args = context.args
    min_val, max_val = 1, 100

    if len(args) >= 2:
        try:
            min_val = int(args[0])
            max_val = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ Please provide valid integers.")
            return
    elif len(args) == 1:
        await update.message.reply_text(
            "❌ You gave only one number. Use two: /random <min> <max>"
        )
        return
    # else use defaults

    if min_val > max_val:
        await update.message.reply_text("❌ Minimum must be less than or equal to maximum.")
        return

    result = randint(min_val, max_val)
    await update.message.reply_text(
        f"🎲 Your random number between {min_val} and {max_val} is:\n"
        f"**{result}**",
        parse_mode="Markdown"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Something went wrong. Please try again later."
        )

# --------------------- Health Check Server ---------------------

async def health_check(request: web.Request) -> web.Response:
    """Respond to health checks."""
    return web.Response(text="OK")

async def start_web_server() -> None:
    """Start the aiohttp health check server."""
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info(f"Health check server running on port {PORT}")

# --------------------- Main ---------------------

async def main() -> None:
    """Start the bot and the health check server concurrently."""
    # Build the bot application
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_error_handler(error_handler)

    # Start polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Bot started polling.")

    # Start web server for health checks
    await start_web_server()

    # Keep the process alive
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    asyncio.run(main())
