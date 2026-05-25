"""Persists watchlist and last log entry to JSON files in data/."""

import json
import os
import config

WATCHLIST_FILE  = os.path.join(config.DATA_DIR, "watchlist.json")
LAST_LOG_FILE   = os.path.join(config.DATA_DIR, "last_log.json")


def load_watchlist() -> list[dict]:
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE) as f:
        return json.load(f)


def save_watchlist(watchlist: list[dict]) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)


def load_last_log() -> dict:
    if not os.path.exists(LAST_LOG_FILE):
        return {}
    with open(LAST_LOG_FILE) as f:
        return json.load(f)


def save_log_entry(date: str, proposals: list[str], feedback: str = "") -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    entry = {"date": date, "proposals": proposals, "feedback": feedback}
    with open(LAST_LOG_FILE, "w") as f:
        json.dump(entry, f, indent=2)
