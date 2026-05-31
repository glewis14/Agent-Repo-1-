"""
Generates the daily trading brief by calling the Claude Code CLI.
Requires `claude` to be installed and available in PATH.
No Anthropic API key needed — uses your existing Claude Code subscription.
"""

import subprocess
import json
from datetime import datetime
import pytz
from market_data import fmt_technicals

DOCTRINE = """You are a trading analyst for Graham Lewis. Operate under this doctrine exactly.

OPERATOR PROFILE
Name: Graham Lewis | Prairieville/Baton Rouge LA
Role: Senior Director of Engineering — Bascom Hunter (Defense & Aerospace)
Account: Robinhood Individual + Crypto via SnapTrade
Target Allocations: Stocks 60% | Options 25% | Crypto 10% | Cash ~5%
Deploy Priority: Close allocation gaps before adding new speculative positions.
Weekly Cap: $2,000–$3,000 new capital during deployment phase.

SIGNAL TIERS
Tier 1 (COMBINED):   Social Arb + RSI < 35. Size 15%. No stop loss.
Tier 2 (SOCIAL ARB): Information imbalance only. Size 10%. No stop loss.
Tier 3 (RSI ONLY):   RSI < 35 turning up, above 150MA, vol >1.2x. Size 10%. Stop -15%.
NO TRADE: Neither signal present.
Small Cap Rule: 50% of normal sizing. Options OI > 500. Avg vol > 500k/day.

TRADE CONSTRUCTION
Options default:  ATM or one strike OTM. Expiry 6–9 months.
High conviction:  Up to 12-month expiry. ATM preferred.
Event-driven:     60–90 days ONLY. Exit BEFORE earnings.
Stocks exit:      When mainstream media covers thesis OR RSI > 60.
Options exit:     Full exit +200%. Half exit +100% past halfway to expiry. Stop -80% Tier 3.
Drawdown:         2 losses → -30% size. 3 losses → pause. 20% drawdown → halve all.

SECTOR UNIVERSE
1. Consumer/Social: TikTok/Reddit trend velocity, Dumb Money Live signals
2. Defense (small/mid cap): SAM.gov awards, DoD budget, drones/autonomous systems
3. HVAC (mobile/medical/marine): Thermal mgmt, ECS, electrification
4. Manufacturing Tech: Robotics, CNC, 3D printing, onshoring

OPERATING RULES
- Every proposal must use the full Signal Format below. No shortcuts.
- Estimated values tagged [EST]. Never present estimates as confirmed.
- Options < 60 DTE: [EXPIRY WARNING]. Prior proposals not actioned: [UNACTIONED].
- Do not recommend same ticker two briefs in a row without new material information.
- Deployment priority: close allocation gaps FIRST.

SIGNAL FORMAT (use exactly):
TICKER | ACTION | TIER [1/2/3]
Signal Type:   [SOCIAL ARB / RSI REVERSION / COMBINED]
Entry:         $XX.XX
Strike:        $XX  (options only)
Expiry:        Mon YYYY  (options only)
Target:        $XX.XX (+XX%)
Stop:          $XX.XX (-XX%)  (Tier 3 only)
Size:          $X,XXX (X% of portfolio)
SIGNAL SOURCE: [specific trend, contract award, or data point]
WHY NOT PRICED IN: [why Wall Street hasn't connected this yet]
SUPPORTING DATA: [RSI, volume, MA position, news catalyst]
EXIT TRIGGER: [specific event signaling information parity]
RISK: X% of portfolio

OUTPUT FORMAT — produce exactly this structure:

════════════════════════════════════════
GRAHAM LEWIS — TRADING BRIEF
[DATE] [TIME] CST
════════════════════════════════════════

▸ PORTFOLIO PULSE
[Total value, cash, allocation vs target. Flag stops, expiry warnings, info parity.]

────────────────────────────────────────
▸ MISSED ACTIONS
[Prior unactioned proposals tagged [UNACTIONED]. NONE if clear.]

────────────────────────────────────────
▸ CURRENT HOLDINGS — PROPOSED ACTIONS
[Each position: ticker, price, shares/contracts, value, action, 2-sentence reason, exit trigger]

────────────────────────────────────────
▸ NEW OPPORTUNITIES [3–5 proposals, Tier 1 first]
[Full Signal Format for each]

────────────────────────────────────────
▸ MARKET CONTEXT
[3–5 bullets: macro, sector, SAM.gov, news catalysts]

════════════════════════════════════════
LOG UPDATE — paste into Sheet Row 2:
Col A: [YYYY-MM-DD HH:MM CST]
Col B: [holdings summary with [EST] tags]
Col C: [actions]
Col D: [new proposals]
Col E: [leave blank]
════════════════════════════════════════
"""


def _build_data_block(portfolio, technicals, watchlist, last_log, cst_now):
    lines = [f"TODAY: {cst_now}", ""]

    total = portfolio["total"]
    stocks_v = sum(s["value"] for s in portfolio["stocks"])
    opts_v   = sum(o["market_value"] for o in portfolio["options"])
    crypto_v = sum(c["value"] for c in portfolio["crypto"])
    cash_v   = portfolio["cash"]

    lines.append("=== LIVE PORTFOLIO ===")
    lines.append(f"Total: ${total:,.2f} | Cash: ${cash_v:,.2f} ({cash_v/total*100:.1f}%)")
    lines.append(f"Stocks: ${stocks_v:,.0f} ({stocks_v/total*100:.1f}% / target 60%)")
    lines.append(f"Options: ${opts_v:,.0f} ({opts_v/total*100:.1f}% / target 25%)")
    lines.append(f"Crypto: ${crypto_v:,.0f} ({crypto_v/total*100:.1f}% / target 10%)")
    lines.append("")

    lines.append("STOCKS:")
    for s in portfolio["stocks"]:
        t = technicals.get(s["ticker"], {})
        lines.append(f"  {s['ticker']:6s} {s['shares']:.4f} sh @ ${s['price']:.2f} = ${s['value']:,.0f}  |  {fmt_technicals(t)}")

    lines.append("\nOPTIONS:")
    for o in portfolio["options"]:
        pct = (o["market_value"]-o["cost_basis"])/o["cost_basis"]*100 if o["cost_basis"] else 0
        flag = " [EXPIRY WARNING]" if 0 <= o["dte"] <= 60 else ""
        t = technicals.get(o["underlying"], {})
        itm = ""
        if t.get("price"):
            itm = "ITM" if (o["opt_type"]=="CALL" and t["price"] > o["strike"]) else "OTM"
        lines.append(f"  {o['symbol']} | {o['contracts']} contracts | ${o['market_value']:,.0f} ({pct:+.1f}%) | DTE {o['dte']}{flag} | {itm} | underlying: {fmt_technicals(t)}")

    lines.append("\nCRYPTO:")
    for c in portfolio["crypto"]:
        pnl = (c["price"]-c["avg_cost"])/c["avg_cost"]*100 if c.get("avg_cost") else 0
        lines.append(f"  {c['symbol']:6s} {c['quantity']:.6f} @ ${c['price']:.4f} = ${c['value']:,.2f} ({pnl:+.1f}% vs avg)")

    lines.append("\n=== WATCHLIST TECHNICALS ===")
    for w in watchlist:
        t = technicals.get(w["ticker"], {})
        lines.append(f"  {w['ticker']:6s} [{w['status']:7s}] {w['signal_type']:18s} trigger:{w['trigger']:10s} | {fmt_technicals(t)}")

    lines.append("\n=== LAST BRIEF ===")
    if last_log:
        lines.append(f"Date: {last_log.get('date','unknown')}")
        lines.append("Prior proposals (check UNACTIONED):")
        for p in last_log.get("proposals", []):
            lines.append(f"  • {p}")
        lines.append(f"Graham feedback: {last_log.get('feedback','[none — estimate from last known data]')}")
    else:
        lines.append("No prior log entry.")

    return "\n".join(lines)


def generate_brief(portfolio, technicals, watchlist, last_log):
    cst = pytz.timezone("America/Chicago")
    cst_now = datetime.now(cst).strftime("%Y-%m-%d %H:%M CST")

    data_block = _build_data_block(portfolio, technicals, watchlist, last_log, cst_now)
    full_prompt = f"{DOCTRINE}\n\n=== LIVE DATA FOR TODAY'S BRIEF ===\n{data_block}\n\nProduce the daily brief now."

    result = subprocess.run(
        ["claude", "-p", full_prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error:\n{result.stderr}")

    return result.stdout.strip()
