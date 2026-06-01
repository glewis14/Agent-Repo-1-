"""
T1 Social Arb + RSI options scan. Run from your Windows machine.

Usage (from C:\\Users\\Graham\\Desktop\\TradingAgent):
    python trading_agent\\scan_t1.py

Outputs tickers with RSI<35 (T1 eligible) and RSI 35-50 (approaching).
Focus your Social Arb lens on the RSI<35 bucket for Monday entries.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from market_data import get_bulk_technicals

# ---------------------------------------------------------------------------
# Scan universe -- target sectors first, then broader Social Arb expansion
# ---------------------------------------------------------------------------

SECTORS = {
    "Defense / Drones": [
        "KTOS", "CDRE", "RCAT", "RDW", "AVAV", "DCO", "BYRN", "ATRO",
        "CACI", "SAIC", "PLTR", "RKLB", "SPIR", "HELO", "JOBY", "ACHR",
    ],
    "HVAC / Thermal / ECS": [
        "VRT", "CARR", "TT", "JCI", "LII", "AAON", "MODG", "ITRI",
    ],
    "Manufacturing / Robotics / Onshoring": [
        "ON", "RRX", "KMT", "ONTO", "FORM", "NOVT", "MKSI", "AMAT",
        "LRCX", "ENTG", "CCMP",
    ],
    "Consumer / Social Arb (Camillo-style)": [
        "HOOD", "SNAP", "PINS", "RDDT", "DUOL", "APP", "MELI",
        "CELH", "SFIX", "XPOF", "PTON", "FIGS", "SQSP", "HIMS",
        "MNST", "NFLX", "SPOT", "RBLX", "U",
    ],
    "Fintech / Retail Finance": [
        "SOFI", "UPST", "AFRM", "DAVE", "NU", "LC",
    ],
    "Small Cap Social Arb Expansion": [
        "ACMR", "VERX", "DOCN", "BRZE", "WEAV", "ALKT", "STEP",
        "ALCC", "PAYO", "LASR", "MIRM", "HIMS", "TNDM",
    ],
}

ALL_TICKERS = []
TICKER_SECTOR = {}
for sector, tickers in SECTORS.items():
    for t in tickers:
        if t not in TICKER_SECTOR:
            ALL_TICKERS.append(t)
            TICKER_SECTOR[t] = sector

# ---------------------------------------------------------------------------
# Run scan
# ---------------------------------------------------------------------------

print(f"\nScanning {len(ALL_TICKERS)} tickers across {len(SECTORS)} sectors...")
print("(This takes ~30 seconds)\n")

results = get_bulk_technicals(ALL_TICKERS)

t1_eligible = []   # RSI < 35 -- both signals required for T1
approaching = []   # RSI 35-50 -- monitor
errors = []

for ticker, d in results.items():
    if d.get("error") or d.get("rsi") is None or d.get("price") is None:
        errors.append(ticker)
        continue

    rsi       = d["rsi"]
    price     = d["price"]
    ma150     = d.get("ma150")
    vol_ratio = d.get("vol_ratio") or 0
    above_ma  = (price > ma150) if ma150 else None

    row = {
        "ticker":    ticker,
        "sector":    TICKER_SECTOR[ticker],
        "price":     price,
        "rsi":       rsi,
        "ma150":     ma150,
        "above_ma":  above_ma,
        "vol_ratio": vol_ratio,
        # T3 RSI component check (RSI<35, above MA150, vol>1.2x)
        "t3_check":  rsi < 35 and above_ma and vol_ratio >= 1.2,
    }

    if rsi < 35:
        t1_eligible.append(row)
    elif rsi <= 50:
        approaching.append(row)

t1_eligible.sort(key=lambda x: x["rsi"])
approaching.sort(key=lambda x: x["rsi"])

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

COLS = f"{'TICKER':7} {'PRICE':>8}  {'RSI':>5}  {'MA150':>8}  {'ABOVE':5}  {'VOL':>5}  SECTOR"
DIVIDER = "-" * 90

print("=" * 90)
print("  RSI < 35  --  T1 ELIGIBLE  (need Social Arb thesis to confirm T1)")
print("=" * 90)
if t1_eligible:
    print(COLS)
    print(DIVIDER)
    for r in t1_eligible:
        above_str = "YES  " if r["above_ma"] else ("NO   " if r["above_ma"] is not None else "n/a  ")
        t3_flag   = " [T3 RSI OK]" if r["t3_check"] else ""
        print(
            f"  {r['ticker']:7} ${r['price']:>7.2f}  {r['rsi']:>5.1f}  "
            f"${r['ma150']:>7.2f}  {above_str}  {r['vol_ratio']:>4.1f}x  "
            f"{r['sector']}{t3_flag}"
        )
else:
    print("  None found -- no tickers below RSI 35 in this universe today.")

print()
print("=" * 90)
print("  RSI 35-50  --  APPROACHING  (watch for entry next 1-5 sessions)")
print("=" * 90)
if approaching:
    print(COLS)
    print(DIVIDER)
    for r in approaching:
        above_str = "YES  " if r["above_ma"] else ("NO   " if r["above_ma"] is not None else "n/a  ")
        print(
            f"  {r['ticker']:7} ${r['price']:>7.2f}  {r['rsi']:>5.1f}  "
            f"${r['ma150']:>7.2f}  {above_str}  {r['vol_ratio']:>4.1f}x  "
            f"{r['sector']}"
        )
else:
    print("  None in this range.")

print()
print(f"Errors / no data: {', '.join(errors) if errors else 'none'}")
print()
print("NEXT STEP: For any RSI<35 name above, apply the Social Arb filter:")
print("  1. Is there a consumer/trend signal Wall Street hasn't priced in?")
print("  2. Is the pullback technical (not thesis-breaking)?")
print("  3. Does options OI > 500 at your target strike?")
print("  If YES to all three -> T1 confirmed -> size 15%, ATM or 1-OTM call, 6-9mo expiry.")
