"""
Long-running Telegram bot for on-demand briefs.
Run at Windows startup via setup_bot_startup.bat.

Commands:
  /brief              -- generate and send the full daily brief (5 messages)
  /status             -- confirm the bot is alive
  /alloc stocks 65    -- update an allocation target percentage
"""

import json
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import config

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Generating brief -- ~60 seconds...")
    try:
        import main as agent
        agent.run_brief()
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Trading agent online.\n"
        "/brief -- generate daily brief\n"
        "/alloc stocks 65 -- update allocation target"
    )


async def cmd_alloc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update an allocation target. Usage: /alloc stocks 65"""
    args = context.args
    valid = {"stocks", "options", "crypto", "cash"}

    if len(args) != 2 or args[0].lower() not in valid:
        await update.message.reply_text(
            "Usage: /alloc <stocks|options|crypto|cash> <percent>\n"
            "Example: /alloc stocks 65"
        )
        return

    asset = args[0].lower()
    try:
        pct = float(args[1])
    except ValueError:
        await update.message.reply_text("Percent must be a number. Example: /alloc stocks 65")
        return

    path = os.path.join(os.path.dirname(__file__), "data", "targets.json")
    targets = {"stocks": 70, "options": 20, "crypto": 0, "cash": 10}
    if os.path.exists(path):
        with open(path) as f:
            targets.update(json.load(f))

    targets[asset] = pct
    with open(path, "w") as f:
        json.dump(targets, f, indent=2)

    total = sum(targets.values())
    await update.message.reply_text(
        f"Targets updated.\n"
        f"Stocks: {targets['stocks']}% | Options: {targets['options']}% | "
        f"Crypto: {targets['crypto']}% | Cash: {targets['cash']}%\n"
        f"Total: {total:.0f}%"
    )


def main() -> None:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("brief",  cmd_brief))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("alloc",  cmd_alloc))
    logging.info("Bot polling. Send /brief, /status, or /alloc in Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
