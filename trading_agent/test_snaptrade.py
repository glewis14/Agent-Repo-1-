"""
Quick SnapTrade connection test.
Usage: python test_snaptrade.py
Set env vars or paste credentials directly below for testing.
"""

import os
import json
from snaptrade_client import SnapTrade

CLIENT_ID    = os.getenv("SNAPTRADE_CLIENT_ID",    "")
CONSUMER_KEY = os.getenv("SNAPTRADE_CONSUMER_KEY", "")
USER_ID      = os.getenv("SNAPTRADE_USER_ID",      "")
USER_SECRET  = os.getenv("SNAPTRADE_USER_SECRET",  "")

if not all([CLIENT_ID, CONSUMER_KEY, USER_ID, USER_SECRET]):
    print("ERROR: Set these env vars before running:")
    print("  SNAPTRADE_CLIENT_ID")
    print("  SNAPTRADE_CONSUMER_KEY")
    print("  SNAPTRADE_USER_ID")
    print("  SNAPTRADE_USER_SECRET")
    exit(1)

api = SnapTrade(consumer_key=CONSUMER_KEY, client_id=CLIENT_ID)

print("\n── 1. Verifying API credentials ──────────────────────────────")
try:
    api_status = api.api_status.check()
    print(f"  API status: {api_status.body}")
except Exception as e:
    print(f"  FAILED: {e}")

print("\n── 2. Listing registered users ───────────────────────────────")
try:
    users = api.authentication.list_snap_trade_users()
    print(f"  Users: {users.body}")
except Exception as e:
    print(f"  FAILED: {e}")

print("\n── 3. Fetching accounts ──────────────────────────────────────")
try:
    accounts = api.account_information.list_user_accounts(
        user_id=USER_ID, user_secret=USER_SECRET
    )
    for acct in (accounts.body or []):
        print(f"  Account: {acct}")
except Exception as e:
    print(f"  FAILED: {e}")

print("\n── 4. Fetching all holdings ──────────────────────────────────")
try:
    holdings = api.account_information.get_all_user_holdings(
        user_id=USER_ID, user_secret=USER_SECRET
    )
    print(json.dumps(holdings.body, indent=2, default=str))
except Exception as e:
    print(f"  FAILED: {e}")
