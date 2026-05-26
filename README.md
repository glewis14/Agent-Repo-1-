# Trading Brief Agent

Automated daily trading brief for Graham Lewis's Robinhood portfolio.

Pulls live position data via SnapTrade, fetches market technicals, generates a structured brief using Claude AI following the Social Arbitrage + RSI Reversion doctrine, and delivers it to Telegram every weekday at 7:00 AM CST — or on demand via `/brief`.

---

## How It Works

```
Windows Task Scheduler (7am CST)
        ↓
  robinhood_client.py  →  SnapTrade API  →  live positions, options, crypto, cash
  market_data.py       →  yfinance       →  price, RSI, MA150/200, volume ratio
        ↓
  brief_generator.py   →  Claude CLI     →  structured daily brief
        ↓
  telegram_sender.py   →  Telegram bot   →  delivered to your phone
```

On-demand: send `/brief` to your Telegram bot anytime → `bot_listener.py` triggers the same pipeline.

---

## Project Structure

```
trading_agent/
├── main.py                  # Orchestrator — runs the full pipeline
├── bot_listener.py          # Telegram bot — /brief and /status commands
├── robinhood_client.py      # SnapTrade API → portfolio data
├── market_data.py           # yfinance → price, RSI, MA, volume
├── brief_generator.py       # Prompt builder + Claude API call
├── telegram_sender.py       # Telegram delivery (handles 4096-char splits)
├── store.py                 # Persists watchlist and last log entry
├── config.py                # Loads and validates env vars
├── data/
│   ├── watchlist.json       # Your watchlist (edit directly to add/remove tickers)
│   └── last_log.json        # Last brief's proposals (used for UNACTIONED check)
├── setup_windows_task.bat   # One-click Task Scheduler setup (run as Admin)
├── setup_bot_startup.bat    # Starts bot_listener.py silently at Windows login
├── requirements.txt
└── .env.example             # Credential template
```

---

## Setup

### 1. Clone and install

```bat
git clone https://github.com/glewis14/agent-repo-1-
cd agent-repo-1-\trading_agent
pip install -r requirements.txt
```

### 2. Configure credentials

```bat
copy .env.example .env
```

Edit `.env` with your values:

| Variable | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/botfather) on Telegram |
| `TELEGRAM_CHAT_ID` | Message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` |
| `SNAPTRADE_CLIENT_ID` | [snaptrade.com](https://snaptrade.com) developer portal |
| `SNAPTRADE_CONSUMER_KEY` | SnapTrade developer portal |
| `SNAPTRADE_USER_ID` | Run `python test_snaptrade.py` (Step 3 below) |
| `SNAPTRADE_USER_SECRET` | Returned when you connected Robinhood via SnapTrade |

### 3. Find your SnapTrade USER_ID

```bat
python test_snaptrade.py
```

This lists all registered users on your SnapTrade account. Copy your user ID into `.env`.

### 4. Test the connection

Re-run `test_snaptrade.py` with `USER_ID` set — it dumps your full raw portfolio JSON so you can verify positions are pulling correctly.

### 5. Schedule the daily brief (run as Administrator)

```bat
setup_windows_task.bat      # Daily brief — Mon–Fri 7:00 AM
setup_bot_startup.bat       # Bot listener — starts at Windows login
```

### 6. Test end-to-end

```bat
python main.py
```

You should receive the brief in Telegram within ~30 seconds.

---

## Telegram Commands

| Command | Action |
|---|---|
| `/brief` | Generate and send the full brief immediately |
| `/status` | Confirm the bot is online |

---

## Updating the Watchlist

Edit `data/watchlist.json` directly. Fields:

```json
{
  "ticker": "KTOS",
  "name": "Kratos Defense",
  "sector": "Defense / Drones",
  "signal_type": "Social Arb T2",
  "trigger": "$28-30",
  "status": "ACTIVE",
  "notes": "Your thesis here.",
  "added": "2026-05-17"
}
```

Status values: `ACTIVE` | `WATCH` | `CLOSED` | `EXITED` | `REMOVED`

---

## Trading Doctrine Summary

| Tier | Signal | Size | Stop |
|---|---|---|---|
| 1 — Combined | Social Arb + RSI < 35 | 15% | None |
| 2 — Social Arb | Information imbalance | 10% | None |
| 3 — RSI Only | RSI < 35, above 150MA, vol confirmed | 10% | −15% |

Options default: ATM or one strike OTM, 6–9 month expiry.
Exit rule: full exit at +200%, half exit at +100% past halfway to expiry.

Full doctrine is embedded in `brief_generator.py` as the Claude system prompt.

---

## Requirements

- Python 3.11+
- Windows machine (for Task Scheduler + Claude Code CLI)
- Claude Code installed (`claude` available in PATH)
- Robinhood account connected to SnapTrade
- Telegram bot created via @BotFather
