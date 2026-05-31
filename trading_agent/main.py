"""
Entry point for the daily trading brief.
Called by Windows Task Scheduler at 7:00 AM CST every weekday.
Also called by bot_listener.py on /brief command.
"""

import sys
import traceback
from datetime import datetime
import pytz

import robinhood_client
import market_data
import brief_generator
import telegram_sender
import store

SECTION_LABELS = {
    "portfolio_pulse": "-- PORTFOLIO PULSE --",
    "option_pulse":    "-- OPTION PULSE --",
    "allocations":     "-- ALLOCATIONS --",
    "adjustments":     "-- ADJUSTMENT SUMMARY --",
    "opportunities":   "-- NEW OPPORTUNITIES --",
}


def run_brief() -> None:
    cst = pytz.timezone("America/Chicago")
    now = datetime.now(cst).strftime("%Y-%m-%d %H:%M CST")

    print(f"[{now}] Fetching portfolio from SnapTrade...")
    try:
        portfolio = robinhood_client.get_portfolio()
    except Exception as exc:
        msg = f"SnapTrade error: {exc}\nUsing empty portfolio -- check credentials."
        print(msg)
        telegram_sender.send(f"[TRADING AGENT ERROR]\n{msg}")
        return

    stock_tickers  = [s["ticker"] for s in portfolio["stocks"]]
    option_tickers = list({o["underlying"] for o in portfolio["options"]})
    watchlist      = store.load_watchlist()
    watch_tickers  = [w["ticker"] for w in watchlist]
    all_tickers    = list(dict.fromkeys(stock_tickers + option_tickers + watch_tickers))

    print(f"[{now}] Fetching technicals for {len(all_tickers)} tickers...")
    technicals = market_data.get_bulk_technicals(all_tickers)

    last_log = store.load_last_log()

    print(f"[{now}] Generating brief via Claude...")
    sections = brief_generator.generate_brief(portfolio, technicals, watchlist, last_log)

    store.save_log_entry(date=now, proposals=["[see brief above]"])

    print(f"[{now}] Sending to Telegram...")
    telegram_sender.send(f"TRADING BRIEF -- {now}")
    for key in ["portfolio_pulse", "option_pulse", "allocations", "adjustments", "opportunities"]:
        content = sections.get(key, "").strip()
        if content:
            telegram_sender.send(f"{SECTION_LABELS[key]}\n\n{content}")

    print(f"[{now}] Done.")


if __name__ == "__main__":
    try:
        run_brief()
    except Exception:
        msg = f"[TRADING AGENT UNHANDLED ERROR]\n{traceback.format_exc()}"
        print(msg, file=sys.stderr)
        try:
            telegram_sender.send(msg)
        except Exception:
            pass
        sys.exit(1)
