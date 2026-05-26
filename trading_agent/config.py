import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val

ANTHROPIC_API_KEY     = os.getenv("ANTHROPIC_API_KEY", "")  # optional — using Claude Code CLI
TELEGRAM_BOT_TOKEN    = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID      = _require("TELEGRAM_CHAT_ID")
SNAPTRADE_CLIENT_ID   = _require("SNAPTRADE_CLIENT_ID")
SNAPTRADE_CONSUMER_KEY = _require("SNAPTRADE_CONSUMER_KEY")
SNAPTRADE_USER_ID     = _require("SNAPTRADE_USER_ID")
SNAPTRADE_USER_SECRET = _require("SNAPTRADE_USER_SECRET")
CLAUDE_MODEL          = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
