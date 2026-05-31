"""Quick Telegram test — run this first to verify bot delivery."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

import config, telegram_sender

print(f"Bot token: {config.TELEGRAM_BOT_TOKEN[:20]}...")
print(f"Chat ID:   {config.TELEGRAM_CHAT_ID}")
print("Sending test message...")

try:
    telegram_sender.send("GL21ClaudeBot online. Trading agent connected successfully.")
    print("SUCCESS — check your Telegram.")
except Exception as e:
    print(f"FAILED: {e}")
