"""
Generates the daily trading brief by calling the Claude Code CLI.
Requires `claude` to be installed and available in PATH.
No Anthropic API key needed -- uses your existing Claude Code subscription.
"""

import re
import subprocess
import json
import os
from datetime import datetime
import pytz
from market_data import fmt_technicals

DOCTRINE = """Trading analyst for Graham Lewis. Use ONLY the data provided below. Do NOT search the web, read files, or use any tools. Generate the brief entirely from the provided data.

ACCOUNT: Robinhood | Weekly cap: $2,000-$3,000. No crypto positions.

SIGNAL TIERS
T1 (COMBINED): Social Arb + RSI<35. Size 15%. No stop.
T2 (SOCIAL ARB): Info imbalance only. Size 10%. No stop.
T3 (RSI ONLY): RSI<35 turning up, above 150MA, vol>1.2x. Size 10%. Stop -15%.
NO TRADE if neither signal. Small cap: 50% size, OI>500, avg vol>500k/day.

TRADE CONSTRUCTION
Options: ATM or 1-strike OTM, 6-9mo expiry. High conviction: 12mo ATM.
Event-driven: 60-90 days only, exit before earnings.
Stocks exit: mainstream media covers thesis OR RSI>60.
Options exit: full +200%, half +100% past halfway to expiry. T3 stop -80%.
Drawdown: 2 losses -> -30% size. 3 losses -> pause. 20% drawdown -> halve all.

SECTORS: Defense/drones, HVAC/thermal/ECS, Mfg/robotics/onshoring, Consumer/social trends.

RULES: Tag estimates [EST]. Options<60 DTE: [EXPIRY WARNING]. Repeat ticker needs new info: [UNACTIONED].

SIGNAL FORMAT (use for every new proposal):
TICKER | ACTION | TIER
Signal: [SOCIAL ARB / RSI REVERSION / COMBINED]
Entry: $X | Strike: $X (opt) | Expiry: Mo YYYY (opt) | Target: $X (+X%) | Stop: $X (T3 only)
Size: $X,XXX (X%) | Source: [catalyst] | Not priced in: [reason] | Data: [RSI/vol/MA] | Exit: [trigger] | Risk: X%

OUTPUT: Produce exactly 5 labeled sections using these delimiters. No text outside the sections.

[SECTION: PORTFOLIO_PULSE]
Equity holdings summary only. Skip any HOLD position entirely -- do not list it. Show only positions needing action (BUY_MORE / SELL / TRIM): ticker, price, value, action, one-sentence reason. If no equity actions needed: "No equity actions needed."

[SECTION: OPTION_PULSE]
Options needing action only. Show positions at exit criteria (>+100% gain, DTE<60, or -80% loss on T3): symbol, value, P&L%, DTE, action, one-sentence reason. If no option actions: "No option actions needed."

[SECTION: ALLOCATIONS]
Compare current vs targets (from ACCOUNT TARGETS in data). One line per class: current $ / current % / target %. Flag classes >5% off target with [REBALANCE]. End with one-line dollar suggestion to rebalance.

[SECTION: ADJUSTMENTS]
Specific sell or buy recommendations only. Sells on current holdings with reason. Buys on watchlist tickers meeting a signal tier (use Signal Format). If nothing qualifies: "No adjustments recommended."

[SECTION: OPPORTUNITIES]
3-5 new trade proposals using Signal Format, T1 first. If no qualifying signals exist, briefly explain why and note relevant market context. Always include useful analysis even with no trades."""


def _load_targets():
    path = os.path.join(os.path.dirname(__file__), "data", "targets.json")
    defaults = {"stocks": 70, "options": 20, "crypto": 0, "cash": 10}
    if os.path.exists(path):
        with open(path) as f:
            defaults.update(json.load(f))
    return defaults


def _parse_sections(text):
    parts = re.split(r'\[SECTION:\s*(\w+)\]', text)
    sections = {}
    for i in range(1, len(parts), 2):
        key = parts[i].lower()
        sections[key] = parts[i + 1].strip() if i + 1 < len(parts) else ""
    return sections


def _build_data_block(portfolio, technicals, watchlist, last_log, cst_now, targets):
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
        lines.append(
            f"  {s['ticker']:6s} {s['shares']:.4f} sh @ ${s['price']:.2f} = ${s['value']:,.0f}"
            f"  |  {fmt_technicals(t)}"
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

    lines.append("\n=== WATCHLIST TECHNICALS ===")
    for w in watchlist:
        t = technicals.get(w["ticker"], {})
        lines.append(
            f"  {w['ticker']:6s} [{w['status']:7s}] {w['signal_type']:18s}"
            f" trigger:{w['trigger']:10s} | {fmt_technicals(t)}"
        )

    lines.append("\n=== LAST BRIEF ===")
    if last_log:
        lines.append(f"Date: {last_log.get('date', 'unknown')}")
        lines.append("Prior proposals (check UNACTIONED):")
        for p in last_log.get("proposals", []):
            lines.append(f"  * {p}")
        lines.append(f"Feedback: {last_log.get('feedback', '[none]')}")
    else:
        lines.append("No prior log entry.")

    return "\n".join(lines)


def _via_sdk(full_prompt: str) -> str:
    import anthropic
    import config
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("No ANTHROPIC_API_KEY set")
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        messages=[{"role": "user", "content": full_prompt}],
    )
    return response.content[0].text


def _via_cli(full_prompt: str) -> str:
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


def generate_brief(portfolio, technicals, watchlist, last_log) -> dict:
    """Returns dict with keys: portfolio_pulse, option_pulse, allocations, adjustments, opportunities."""
    cst = pytz.timezone("America/Chicago")
    cst_now = datetime.now(cst).strftime("%Y-%m-%d %H:%M CST")
    targets = _load_targets()

    data_block = _build_data_block(portfolio, technicals, watchlist, last_log, cst_now, targets)
    full_prompt = (
        f"{DOCTRINE}\n\n"
        f"=== LIVE DATA FOR TODAY'S BRIEF ===\n{data_block}\n\n"
        f"Produce the brief now."
    )

    import config
    raw = _via_sdk(full_prompt) if config.ANTHROPIC_API_KEY else _via_cli(full_prompt)
    return _parse_sections(raw)
