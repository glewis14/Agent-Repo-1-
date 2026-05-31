"""
Run this on your Windows machine to get a full portfolio assessment.
Usage: python run_assessment.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import robinhood_client
import market_data
import store
from datetime import datetime
import pytz

cst = pytz.timezone("America/Chicago")
now = datetime.now(cst).strftime("%Y-%m-%d %H:%M CST")

print(f"\n{'='*56}")
print(f"  GRAHAM LEWIS — PORTFOLIO ASSESSMENT")
print(f"  {now}")
print(f"{'='*56}")

# ── Pull live portfolio ───────────────────────────────────────
print("\nPulling live data from SnapTrade...")
try:
    portfolio = robinhood_client.get_portfolio()
except Exception as e:
    print(f"SnapTrade error: {e}")
    sys.exit(1)

# ── Collect tickers for technicals ───────────────────────────
stock_tickers  = [s["ticker"] for s in portfolio["stocks"]]
option_tickers = list({o["underlying"] for o in portfolio["options"]})
watchlist      = store.load_watchlist()
watch_tickers  = [w["ticker"] for w in watchlist]
all_tickers    = list(dict.fromkeys(stock_tickers + option_tickers + watch_tickers))

print(f"Fetching technicals for {len(all_tickers)} tickers...")
techs = market_data.get_bulk_technicals(all_tickers)

# ── Allocation breakdown ──────────────────────────────────────
total    = portfolio["total"]
stocks_v = sum(s["value"] for s in portfolio["stocks"])
opts_v   = sum(o["market_value"] for o in portfolio["options"])
crypto_v = sum(c["value"] for c in portfolio["crypto"])
cash_v   = portfolio["cash"]

def pct(v): return v / total * 100 if total else 0
def gap(actual, target): return f"{'▲' if actual > target else '▼'} {abs(actual-target):.1f}%"

print(f"\n{'─'*56}")
print(f"  PORTFOLIO PULSE")
print(f"{'─'*56}")
print(f"  Total Value:  ${total:>10,.2f}")
print(f"  Cash:         ${cash_v:>10,.2f}  ({pct(cash_v):.1f}%)")
print()
print(f"  {'Category':<10} {'Value':>10}  {'Actual':>7}  {'Target':>7}  {'Gap':>10}")
print(f"  {'─'*54}")
print(f"  {'Stocks':<10} ${stocks_v:>9,.0f}  {pct(stocks_v):>6.1f}%  {'60.0%':>7}  {gap(pct(stocks_v),60):>10}")
print(f"  {'Options':<10} ${opts_v:>9,.0f}  {pct(opts_v):>6.1f}%  {'25.0%':>7}  {gap(pct(opts_v),25):>10}")
print(f"  {'Crypto':<10} ${crypto_v:>9,.0f}  {pct(crypto_v):>6.1f}%  {'10.0%':>7}  {gap(pct(crypto_v),10):>10}")
print(f"  {'Cash':<10} ${cash_v:>9,.0f}  {pct(cash_v):>6.1f}%  {' 5.0%':>7}  {gap(pct(cash_v),5):>10}")

# ── Stock positions ───────────────────────────────────────────
print(f"\n{'─'*56}")
print(f"  STOCK POSITIONS")
print(f"{'─'*56}")
print(f"  {'Ticker':<6}  {'Shares':>8}  {'Price':>9}  {'Value':>9}  {'RSI':>5}  {'vs MA150':>9}")
print(f"  {'─'*60}")
for s in sorted(portfolio["stocks"], key=lambda x: -x["value"]):
    t = techs.get(s["ticker"], {})
    rsi = f"{t['rsi']:.0f}" if t.get("rsi") else "  n/a"
    ma  = t.get("ma150")
    if ma and t.get("price"):
        ma_str = f"{'ABOVE' if t['price'] > ma else 'BELOW'} ${ma:,.0f}"
    else:
        ma_str = "n/a"
    flag = ""
    if t.get("rsi") and t["rsi"] < 35:
        flag = " ◀ RSI OVERSOLD"
    print(f"  {s['ticker']:<6}  {s['shares']:>8.4f}  ${s['price']:>8,.2f}  ${s['value']:>8,.0f}  {rsi:>5}  {ma_str:<14}{flag}")

# ── Options positions ─────────────────────────────────────────
print(f"\n{'─'*56}")
print(f"  OPTIONS POSITIONS")
print(f"{'─'*56}")
for o in portfolio["options"]:
    pnl = (o["market_value"] - o["cost_basis"]) / o["cost_basis"] * 100 if o["cost_basis"] else 0
    flag = " [EXPIRY WARNING]" if 0 <= o["dte"] <= 60 else ""
    print(f"  {o['symbol']}")
    print(f"    Contracts: {o['contracts']}  |  Value: ${o['market_value']:,.0f}  |  Cost: ${o['cost_basis']:,.0f}  |  P&L: {pnl:+.1f}%")
    print(f"    DTE: {o['dte']} days{flag}")
    t = techs.get(o["underlying"], {})
    if t.get("price"):
        itm = "ITM" if (o["opt_type"]=="CALL" and t["price"] > o["strike"]) or (o["opt_type"]=="PUT" and t["price"] < o["strike"]) else "OTM"
        print(f"    Underlying: ${t['price']:,.2f}  RSI: {t.get('rsi','n/a')}  [{itm}]")
    print()

# ── Crypto positions ──────────────────────────────────────────
print(f"{'─'*56}")
print(f"  CRYPTO POSITIONS")
print(f"{'─'*56}")
for c in portfolio["crypto"]:
    pnl = (c["price"] - c["avg_cost"]) / c["avg_cost"] * 100 if c.get("avg_cost") else 0
    print(f"  {c['symbol']:<6}  {c['quantity']:>12.6f}  @  ${c['price']:>12.4f}  =  ${c['value']:>9,.2f}  ({pnl:+.1f}% vs avg cost)")

# ── Watchlist technicals ──────────────────────────────────────
print(f"\n{'─'*56}")
print(f"  WATCHLIST — SIGNAL SCAN")
print(f"{'─'*56}")
print(f"  {'Ticker':<6}  {'Status':<7}  {'Price':>9}  {'RSI':>5}  {'vs MA150':>12}  Signal")
print(f"  {'─'*65}")
for w in watchlist:
    t = techs.get(w["ticker"], {})
    price = f"${t['price']:,.2f}" if t.get("price") else "  n/a"
    rsi   = f"{t['rsi']:.0f}" if t.get("rsi") else " n/a"
    ma    = t.get("ma150")
    if ma and t.get("price"):
        ma_str = f"{'ABOVE' if t['price'] > ma else 'BELOW'} ${ma:,.0f}"
    else:
        ma_str = "n/a"
    signal = ""
    if t.get("rsi") and t["rsi"] < 35:
        signal = "◀ RSI TRIGGER"
    print(f"  {w['ticker']:<6}  {w['status']:<7}  {price:>9}  {rsi:>5}  {ma_str:<16}  {signal}")

print(f"\n{'='*56}")
print("  Paste this output to Claude for full brief analysis.")
print(f"{'='*56}\n")
