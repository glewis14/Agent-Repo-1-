"""Send messages to Telegram, splitting on 4096-char limit."""

import asyncio
import telegram
import config

MAX_LEN = 4096


def _split(text: str, limit: int = MAX_LEN) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, buf = [], []
    for line in text.splitlines(keepends=True):
        if sum(len(l) for l in buf) + len(line) > limit:
            chunks.append("".join(buf))
            buf = []
        buf.append(line)
    if buf:
        chunks.append("".join(buf))
    return chunks


async def _send_async(text: str) -> None:
    bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
    for chunk in _split(text):
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=chunk,
            parse_mode=None,
        )


def send(text: str) -> None:
    """Synchronous wrapper — safe to call from main or cron context."""
    asyncio.run(_send_async(text))
