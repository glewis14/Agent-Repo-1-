"""
SnapTrade connection test — run this on your Windows machine.

Usage:
  set SNAPTRADE_CLIENT_ID=PERS-OA1P9AG1BZOU7SBQ5F57
  set SNAPTRADE_CONSUMER_KEY=VazVIEZECcSDM7S4T9PnphWrFW81CRd3bzOoAgLPCm71BLIcYu
  set SNAPTRADE_USER_ID=<your user id>
  set SNAPTRADE_USER_SECRET=87bba2a9-6f30-4f6b-a6a1-54266422b0f8
  python test_snaptrade.py

Or just paste your credentials directly into the variables below.
"""

import os, json
from snaptrade_client import SnapTrade

CLIENT_ID    = os.getenv("SNAPTRADE_CLIENT_ID",    "PERS-OA1P9AG1BZOU7SBQ5F57")
CONSUMER_KEY = os.getenv("SNAPTRADE_CONSUMER_KEY", "VazVIEZECcSDM7S4T9PnphWrFW81CRd3bzOoAgLPCm71BLIcYu")
USER_ID      = os.getenv("SNAPTRADE_USER_ID",      "graham-hermes-1")
USER_SECRET  = os.getenv("SNAPTRADE_USER_SECRET",  "87bba2a9-6f30-4f6b-a6a1-54266422b0f8")

api = SnapTrade(consumer_key=CONSUMER_KEY, client_id=CLIENT_ID)

print("\n── 1. API Status ─────────────────────────────────────────────")
try:
    r = api.api_status.check()
    print(" ", r.body)
except Exception as e:
    print(f"  FAILED: {e}")

print("\n── 2. Registered Users (find your USER_ID here) ──────────────")
try:
    r = api.authentication.list_snap_trade_users()
    print(" ", r.body)
except Exception as e:
    print(f"  FAILED: {e}")

if not USER_ID:
    print("\nSet USER_ID above from the list, then re-run for full holdings.")
    exit(0)

print("\n── 3. Accounts ───────────────────────────────────────────────")
try:
    r = api.account_information.list_user_accounts(user_id=USER_ID, user_secret=USER_SECRET)
    for acct in (r.body or []):
        print(f"  {acct}")
except Exception as e:
    print(f"  FAILED: {e}")

print("\n── 4. Full Holdings (raw JSON) ───────────────────────────────")
try:
    r = api.account_information.get_all_user_holdings(user_id=USER_ID, user_secret=USER_SECRET)
    print(json.dumps(r.body, indent=2, default=str))
except Exception as e:
    print(f"  FAILED: {e}")
