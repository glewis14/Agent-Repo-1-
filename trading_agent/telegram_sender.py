"""Sends messages to Telegram, splitting on the 4096-char limit."""

import requests
import config

MAX_LEN = 4096


def _split(text, limit=MAX_LEN):
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


def send(text: str) -> None:
    """Send message to Telegram using plain requests — no async needed."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    for chunk in _split(text):
        resp = requests.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": chunk,
        }, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Telegram error {resp.status_code}: {resp.text}")


def send_test() -> None:
    send("GL21ClaudeBot online. Trading agent connected.")
