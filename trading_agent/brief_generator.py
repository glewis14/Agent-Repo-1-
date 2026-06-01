"""
Generates the daily trading brief via two sequential Claude calls:
  Call 1 -- holdings analysis (PORTFOLIO_PULSE, OPTION_PULSE, ALLOCATIONS, ADJUSTMENTS)
  Call 2 -- new opportunities (OPPORTUNITIES)
Smaller prompts = faster response, no timeouts.
"""

import re
import subprocess
import json
import os
from datetime import datetime
import pytz
from market_data import fmt_technicals

# ---------------------------------------------------------------------------
# Doctrine blocks -- one per call to keep prompts small
# ---------------------------------------------------------------------------

DOCTRINE_HOLDINGS = """Trading analyst for Graham Lewis. Use ONLY the provided portfolio data. No web search. No tools.

ACCOUNT: Robinhood | Targets: Stocks 60% / Options 25% / Crypto 10% / Cash 5%
Priority: Close allocation gaps first. Weekly cap: $2,000-$3,000.

EXIT RULES
Stocks: mainstream media covers thesis OR RSI>60.
  EXCEPTION: Index ETFs and leveraged ETFs (SPY, VOO, QQQ, TQQQ, BRK.B) are permanent core holds. RSI exit rule NEVER applies to them.
Options: full exit +200%, half exit +100% past halfway to expiry. T3 stop -80%.
Drawdown: 2 losses -> -30% size. 3 losses -> pause. 20% drawdown -> halve all.

RULES: Tag estimates [EST]. Options<60 DTE: [EXPIRY WARNING]. Always be explicit if no action is needed.

OUTPUT: Produce exactly 4 sections using these delimiters. No text outside sections.

[SECTION: PORTFOLIO_PULSE]
Equity holdings. Skip pure HOLDs -- do not list them. Only show positions needing action (BUY_MORE / SELL / TRIM).
Format per line: TICKER | $price | $value | ACTION | one-sentence reason.
If no equity actions: "No equity actions needed."

[SECTION: OPTION_PULSE]
Options at exit criteria only: gain >+100%, or DTE<60, or T3 loss >-80%.
Format per line: symbol | $value | P&L% | DTE | ACTION | reason.
If no option actions: "No option actions needed."

[SECTION: ALLOCATIONS]
Each asset class on its own line: class | current $ | current % | target % | status.
Flag classes more than 5% off target with [REBALANCE]. End with one-line dollar suggestion.

[SECTION: ADJUSTMENTS]
Sells on current holdings with specific reasoning. Buys on watchlist tickers meeting signal criteria.
Signal Format for buys: TICKER | ACTION | TIER / Signal / Entry $X / Target $X / Size $X / Source / Exit trigger.
If nothing qualifies: "No adjustments recommended." """


DOCTRINE_OPPORTUNITIES = """Trading analyst for Graham Lewis. Use ONLY the watchlist data provided. No web search. No tools.
Use the portfolio total shown for position sizing.

SIGNAL TIERS
T1 (COMBINED): Social Arb + RSI<35. Size 15%. No stop.
T2 (SOCIAL ARB): Info imbalance only. Size 10%. No stop.
T3 (RSI ONLY): RSI<35 turning up, above 150MA, vol>1.2x. Size 10%. Stop -15%.
NO TRADE if neither signal. Small cap: 50% size.
Options: ATM or 1-strike OTM, 6-9mo expiry.

SIGNAL FORMAT:
TICKER | ACTION | TIER
Signal: [type] | Entry: $X | Strike: $X (opt) | Expiry: Mo YYYY (opt)
Target: $X (+X%) | Stop: $X (T3 only) | Size: $X,XXX (X%)
Source: [catalyst] | Not priced in: [reason] | Data: [RSI/vol/MA] | Exit: [trigger] | Risk: X%

OUTPUT: Produce exactly 1 section. No text outside.

[SECTION: OPPORTUNITIES]
3-5 new proposals using Signal Format, T1 first.
If no qualifying signals, briefly explain why and note relevant market context.
Always provide useful analysis even with no trades."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_targets():
    path = os.path.join(os.path.dirname(__file__), "data", "targets.json")
    defaults = {"stocks": 60, "options": 25, "crypto": 10, "cash": 5}
    if os.path.exists(path):
        with open(path) as f:
            defaults.update(json.load(f))
    return defaults


def _load_positions_context():
    path = os.path.join(os.path.dirname(__file__), "data", "positions_context.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _parse_sections(text):
    parts = re.split(r'\[SECTION:\s*(\w+)\]', text)
    sections = {}
    for i in range(1, len(parts), 2):
        key = parts[i].lower()
        sections[key] = parts[i + 1].strip() if i + 1 < len(parts) else ""
    if not sections:
        sections["_raw"] = text.strip()
    return sections


def _build_holdings_block(portfolio, technicals, positions_context, last_log, cst_now, targets):
    lines = [f"TODAY: {cst_now}", ""]
    total = portfolio["total"]
    stocks_v = sum(s["value"] for s in portfolio["stocks"])
    opts_v   = sum(o["market_value"] for o in portfolio["options"])
    crypto_v = sum(c["value"] for c in portfolio["crypto"])
    cash_v   = portfolio["cash"]

    lines.append("=== ACCOUNT TARGETS ===")
    lines.append(
        f"Stocks: {targets['stocks']}% | Options: {targets['options']}% | "
        f"Crypto: {targets['crypto']}% | Cash: {targets['cash']}%"
    )
    lines.append("")
    lines.append("=== LIVE PORTFOLIO ===")
    lines.append(f"Total: ${total:,.2f} | Cash: ${cash_v:,.2f} ({cash_v/total*100:.1f}%)")
    lines.append(f"Stocks:  ${stocks_v:,.0f} ({stocks_v/total*100:.1f}% / target {targets['stocks']}%)")
    lines.append(f"Options: ${opts_v:,.0f} ({opts_v/total*100:.1f}% / target {targets['options']}%)")
    lines.append(f"Crypto:  ${crypto_v:,.0f} ({crypto_v/total*100:.1f}% / target {targets['crypto']}%)")
    lines.append("")

    lines.append("STOCKS:")
    for s in portfolio["stocks"]:
        t = technicals.get(s["ticker"], {})
        ctx = positions_context.get(s["ticker"])
        ctx_str = f" | Thesis: {ctx['thesis']}" if ctx else ""
        lines.append(
            f"  {s['ticker']:6s} {s['shares']:.4f} sh @ ${s['price']:.2f} = ${s['value']:,.0f}"
            f"  |  {fmt_technicals(t)}{ctx_str}"
        )

    lines.append("\nOPTIONS:")
    for o in portfolio["options"]:
        pct = (o["market_value"] - o["cost_basis"]) / o["cost_basis"] * 100 if o["cost_basis"] else 0
        flag = " [EXPIRY WARNING]" if 0 <= o["dte"] <= 60 else ""
        t = technicals.get(o["underlying"], {})
        itm = ""
        if t.get("price"):
            itm = "ITM" if (o["opt_type"] == "CALL" and t["price"] > o["strike"]) else "OTM"
        lines.append(
            f"  {o['symbol']} | {o['contracts']} contracts | ${o['market_value']:,.0f} ({pct:+.1f}%)"
            f" | DTE {o['dte']}{flag} | {itm} | underlying: {fmt_technicals(t)}"
        )

    lines.append("\nCRYPTO:")
    for c in portfolio["crypto"]:
        pnl = (c["price"] - c["avg_cost"]) / c["avg_cost"] * 100 if c.get("avg_cost") else 0
        lines.append(
            f"  {c['symbol']:6s} {c['quantity']:.6f} @ ${c['price']:.4f}"
            f" = ${c['value']:,.2f} ({pnl:+.1f}% vs avg)"
        )

    if last_log:
        lines.append("\n=== LAST BRIEF ===")
        lines.append(f"Date: {last_log.get('date', 'unknown')}")
        for p in last_log.get("proposals", []):
            lines.append(f"  * {p}")

    return "\n".join(lines)


def _build_watchlist_block(watchlist, technicals, total):
    lines = [f"PORTFOLIO TOTAL: ${total:,.2f} (use for position sizing)", ""]
    lines.append("=== WATCHLIST TECHNICALS ===")
    for w in watchlist:
        t = technicals.get(w["ticker"], {})
        lines.append(
            f"  {w['ticker']:6s} [{w['status']:7s}] {w['signal_type']:18s}"
            f" trigger:{w['trigger']:10s} | {fmt_technicals(t)}"
        )
        if w.get("notes"):
            lines.append(f"    Notes: {w['notes']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Claude invocation
# ---------------------------------------------------------------------------

def _invoke(full_prompt: str) -> str:
    import config
    if config.ANTHROPIC_API_KEY:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            messages=[{"role": "user", "content": full_prompt}],
        )
        return response.content[0].text
    else:
        import shutil
        if not (shutil.which("claude") or shutil.which("claude.cmd")):
            raise RuntimeError("claude CLI not found in PATH")
        result = subprocess.run(
            "claude --print --dangerously-skip-permissions --model claude-haiku-4-5-20251001",
            shell=True,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(f"Claude CLI error:\n{result.stderr}")
        return result.stdout.strip()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_brief(portfolio, technicals, watchlist, last_log) -> dict:
    """Returns dict with keys: portfolio_pulse, option_pulse, allocations, adjustments, opportunities."""
    cst = pytz.timezone("America/Chicago")
    cst_now = datetime.now(cst).strftime("%Y-%m-%d %H:%M CST")
    targets = _load_targets()
    positions_context = _load_positions_context()

    # Call 1: Holdings analysis
    holdings_block = _build_holdings_block(
        portfolio, technicals, positions_context, last_log, cst_now, targets
    )
    raw1 = _invoke(f"{DOCTRINE_HOLDINGS}\n\n=== PORTFOLIO DATA ===\n{holdings_block}\n\nProduce the analysis now.")
    sections = _parse_sections(raw1)

    # Call 2: New opportunities (separate prompt, watchlist only)
    watchlist_block = _build_watchlist_block(watchlist, technicals, portfolio["total"])
    raw2 = _invoke(f"{DOCTRINE_OPPORTUNITIES}\n\n=== WATCHLIST DATA ===\n{watchlist_block}\n\nProduce opportunities now.")
    sections.update(_parse_sections(raw2))

    return sections
