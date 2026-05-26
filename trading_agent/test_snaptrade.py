"""
SnapTrade connection test — uses per-account endpoints (get_all_user_holdings is gone).
"""

import json
from snaptrade_client import SnapTrade
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID    = os.getenv("SNAPTRADE_CLIENT_ID",    "PERS-OA1P9AG1BZOU7SBQ5F57")
CONSUMER_KEY = os.getenv("SNAPTRADE_CONSUMER_KEY", "VazVIEZECcSDM7S4T9PnphWrFW81CRd3bzOoAgLPCm71BLIcYu")
USER_ID      = os.getenv("SNAPTRADE_USER_ID",      "graham-hermes-1")
USER_SECRET  = os.getenv("SNAPTRADE_USER_SECRET",  "87bba2a9-6f30-4f6b-a6a1-54266422b0f8")

api = SnapTrade(consumer_key=CONSUMER_KEY, client_id=CLIENT_ID)

# ── Get accounts ──────────────────────────────────────────────────────────────
print("\n── Accounts ──────────────────────────────────────────────────")
accounts = api.account_information.list_user_accounts(
    user_id=USER_ID, user_secret=USER_SECRET
).body
for acct in accounts:
    print(f"  {acct['name']} | id: {acct['id']} | balance: ${acct['balance']['total']['amount']:,.2f}")

# ── Per-account positions and balances ────────────────────────────────────────
for acct in accounts:
    acct_id   = acct["id"]
    acct_name = acct["name"]

    print(f"\n── {acct_name} — Positions ────────────────────────────────")
    try:
        positions = api.account_information.get_user_account_positions(
            user_id=USER_ID, user_secret=USER_SECRET, account_id=acct_id
        ).body
        print(json.dumps(positions, indent=2, default=str))
    except Exception as e:
        print(f"  FAILED: {e}")

    print(f"\n── {acct_name} — Balance ──────────────────────────────────")
    try:
        balance = api.account_information.get_user_account_balance(
            user_id=USER_ID, user_secret=USER_SECRET, account_id=acct_id
        ).body
        print(json.dumps(balance, indent=2, default=str))
    except Exception as e:
        print(f"  FAILED: {e}")

    print(f"\n── {acct_name} — Options ──────────────────────────────────")
    try:
        options = api.options.list_option_holdings(
            user_id=USER_ID, user_secret=USER_SECRET, account_id=acct_id
        ).body
        print(json.dumps(options, indent=2, default=str))
    except Exception as e:
        print(f"  FAILED: {e}")

# ── Parsed portfolio via robinhood_client ─────────────────────────────────────
print("\n\n══ PARSED PORTFOLIO (robinhood_client.py) ═══════════════════")
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import robinhood_client
portfolio = robinhood_client.get_portfolio()
print(f"\nTotal:  ${portfolio['total']:>10,.2f}")
print(f"Cash:   ${portfolio['cash']:>10,.2f}")
print("\nSTOCKS:")
for s in portfolio["stocks"]:
    print(f"  {s['ticker']:6s}  {s['shares']:>10.4f} sh  @  ${s['price']:>10.2f}  =  ${s['value']:>10,.2f}")
print("\nOPTIONS:")
for o in portfolio["options"]:
    pct = (o['market_value'] - o['cost_basis']) / o['cost_basis'] * 100 if o['cost_basis'] else 0
    print(f"  {o['symbol']}  |  {o['contracts']} contracts  |  ${o['market_value']:,.0f}  ({pct:+.1f}%)  |  DTE {o['dte']}")
print("\nCRYPTO:")
for c in portfolio["crypto"]:
    print(f"  {c['symbol']:6s}  {c['quantity']:>12.6f}  @  ${c['price']:>12.4f}  =  ${c['value']:>10,.2f}")
