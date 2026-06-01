"""Pulls live portfolio data from Robinhood via SnapTrade API."""

from datetime import date
import json
import os
import config
from snaptrade_client import SnapTrade


def _init():
    return SnapTrade(
        consumer_key=config.SNAPTRADE_CONSUMER_KEY,
        client_id=config.SNAPTRADE_CLIENT_ID,
    )


def _get_accounts(api, uid, usec):
    return api.account_information.list_user_accounts(
        user_id=uid, user_secret=usec
    ).body or []


def get_portfolio() -> dict:
    """
    Returns:
        {
            "stocks":  [{"ticker", "shares", "price", "value", "avg_cost"}],
            "options": [{"symbol", "underlying", "strike", "expiry", "opt_type",
                         "contracts", "cost_basis", "market_value", "dte"}],
            "crypto":  [{"symbol", "quantity", "price", "value", "avg_cost"}],
            "cash":    float,
            "total":   float,
            "accounts": [{"name", "id", "total"}],
        }
    """
    api   = _init()
    uid   = config.SNAPTRADE_USER_ID
    usec  = config.SNAPTRADE_USER_SECRET

    accounts = _get_accounts(api, uid, usec)
    stocks, options, crypto = [], [], []
    cash_total = 0.0
    account_summaries = []

    for acct in accounts:
        acct_id   = acct["id"]
        acct_name = acct["name"]
        acct_total = float((acct.get("balance") or {}).get("total", {}).get("amount", 0) or 0)
        account_summaries.append({"name": acct_name, "id": acct_id, "total": acct_total})

        # ── Cash balance ──────────────────────────────────────────────────────
        try:
            balances = api.account_information.get_user_account_balance(
                user_id=uid, user_secret=usec, account_id=acct_id
            ).body or []
            for bal in balances:
                if (bal.get("currency") or {}).get("code") == "USD":
                    cash_total += float(bal.get("cash", 0) or 0)
        except Exception:
            pass

        # ── Stock / crypto positions ──────────────────────────────────────────
        try:
            positions = api.account_information.get_user_account_positions(
                user_id=uid, user_secret=usec, account_id=acct_id
            ).body or []

            for pos in positions:
                # Field path confirmed from live API: pos["symbol"]["symbol"]
                sym_info   = (pos.get("symbol") or {}).get("symbol") or {}
                ticker     = sym_info.get("symbol", "?")
                asset_code = (sym_info.get("type") or {}).get("code", "")
                units      = float(pos.get("units") or 0)
                price      = float(pos.get("price") or 0)
                avg_cost   = float(pos.get("average_purchase_price") or 0)
                value      = units * price

                if asset_code == "crypto":
                    crypto.append({
                        "symbol":   ticker,
                        "quantity": units,
                        "price":    price,
                        "value":    value,
                        "avg_cost": avg_cost,
                    })
                else:
                    stocks.append({
                        "ticker":   ticker,
                        "shares":   units,
                        "price":    price,
                        "value":    value,
                        "avg_cost": avg_cost,
                    })
        except Exception:
            pass

        # ── Options positions ─────────────────────────────────────────────────
        try:
            opts = api.options.list_option_holdings(
                user_id=uid, user_secret=usec, account_id=acct_id
            ).body or []

            for opt in opts:
                opt_sym    = (opt.get("symbol") or {}).get("option_symbol") or {}
                underlying = (opt_sym.get("underlying_symbol") or {}).get("symbol", "?")
                strike     = float(opt_sym.get("strike_price") or 0)
                expiry     = opt_sym.get("expiration_date", "?")
                opt_type   = opt_sym.get("option_type", "?")
                contracts  = int(float(opt.get("units") or 0))
                # price from API is per-contract value in dollars
                mkt_val    = float(opt.get("price") or 0) * contracts
                avg_price  = opt.get("average_purchase_price")
                cost       = float(avg_price) * contracts if avg_price else 0.0

                try:
                    dte = (date.fromisoformat(expiry) - date.today()).days
                except Exception:
                    dte = -1

                label = f"{underlying} ${int(strike)}{opt_type[0].upper()} exp {expiry}"
                options.append({
                    "symbol":       label,
                    "underlying":   underlying,
                    "strike":       strike,
                    "expiry":       expiry,
                    "opt_type":     opt_type,
                    "contracts":    contracts,
                    "cost_basis":   cost,
                    "market_value": mkt_val,
                    "dte":          dte,
                })
        except Exception:
            pass

    # Merge manually tracked options (positions SnapTrade may not return)
    manual_path = os.path.join(os.path.dirname(__file__), "data", "manual_options.json")
    if os.path.exists(manual_path):
        with open(manual_path) as f:
            manual_opts = json.load(f)
        existing_symbols = {o["symbol"] for o in options}
        for m in manual_opts:
            if m["symbol"] not in existing_symbols:
                try:
                    m["dte"] = (date.fromisoformat(m["expiry"]) - date.today()).days
                except Exception:
                    m["dte"] = -1
                options.append(m)

    total = (sum(s["value"] for s in stocks)
             + sum(o["market_value"] for o in options)
             + sum(c["value"] for c in crypto)
             + cash_total)

    return {
        "stocks":   stocks,
        "options":  options,
        "crypto":   crypto,
        "cash":     cash_total,
        "total":    total,
        "accounts": account_summaries,
    }
