"""
Long-running Telegram bot for on-demand briefs.
Run at Windows startup via setup_bot_startup.bat.

Commands:
  /brief   — generate and send the full daily brief
  /status  — confirm the bot is alive
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import config
import telegram_sender

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Generating brief — ~30 seconds...")
    try:
        import main as agent
        agent.run_brief()
        await update.message.reply_text("Brief sent.")
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Trading agent is online. Use /brief to generate a brief.")


def main() -> None:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("brief",  cmd_brief))
    app.add_handler(CommandHandler("status", cmd_status))
    logging.info("Bot polling. Send /brief or /status in Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
