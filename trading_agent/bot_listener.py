"""
Long-running Telegram bot for on-demand briefs.
Run this as a background process/startup program on Windows:
  pythonw bot_listener.py

Commands:
  /brief   — generate and send the full daily brief immediately
  /status  — confirm the bot is alive
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import config
import main as agent

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Generating brief — this takes ~30 seconds...")
    try:
        brief = agent.run_brief()
        # run_brief() already sends to Telegram; reply confirms in the same chat
        await update.message.reply_text("Brief sent.")
    except Exception as exc:
        await update.message.reply_text(f"Error generating brief:\n{exc}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Trading agent is online. Use /brief to generate a brief.")


def main() -> None:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("brief",  cmd_brief))
    app.add_handler(CommandHandler("status", cmd_status))
    logging.info("Bot polling started. Send /brief in Telegram to trigger a brief.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
