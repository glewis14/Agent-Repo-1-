"""Pulls live portfolio data from Robinhood via SnapTrade API."""

import config
from snaptrade_client import SnapTrade


def _init():
    return SnapTrade(
        consumer_key=config.SNAPTRADE_CONSUMER_KEY,
        client_id=config.SNAPTRADE_CLIENT_ID,
    )


def get_portfolio() -> dict:
    """
    Returns:
        {
            "stocks": [{"ticker": str, "shares": float, "price": float, "value": float}],
            "options": [{"symbol": str, "strike": float, "expiry": str, "contracts": int,
                         "cost_basis": float, "market_value": float, "dte": int}],
            "crypto":  [{"symbol": str, "quantity": float, "price": float, "value": float}],
            "cash":    float,
            "total":   float,
        }
    """
    api = _init()
    uid = config.SNAPTRADE_USER_ID
    usec = config.SNAPTRADE_USER_SECRET

    raw = api.account_information.get_all_user_holdings(
        user_id=uid,
        user_secret=usec,
    ).body

    stocks, options, crypto = [], [], []
    cash_total = 0.0

    for account_data in raw:
        # ── Balances ──────────────────────────────────────────────
        for bal in (account_data.get("balances") or []):
            currency = (bal.get("currency") or {}).get("code", "")
            if currency == "USD":
                cash_total += float(bal.get("cash", 0) or 0)

        # ── Equity positions ──────────────────────────────────────
        for pos in (account_data.get("positions") or []):
            sym_obj  = pos.get("symbol") or {}
            symbol   = sym_obj.get("symbol", "") if isinstance(sym_obj, dict) else str(sym_obj)
            units    = float(pos.get("units", 0) or 0)
            price    = float(pos.get("price", 0) or 0)
            value    = units * price

            # SnapTrade marks crypto tickers with a type field or separate section
            asset_type = (sym_obj.get("type") or "") if isinstance(sym_obj, dict) else ""
            if asset_type.upper() in ("CRYPTO", "CRYPTOCURRENCY"):
                crypto.append({"symbol": symbol, "quantity": units,
                                "price": price, "value": value})
            else:
                stocks.append({"ticker": symbol, "shares": units,
                                "price": price, "value": value})

        # ── Option positions ──────────────────────────────────────
        for opt in (account_data.get("option_positions") or []):
            sym_obj      = opt.get("symbol") or {}
            underlying   = (sym_obj.get("underlying_symbol") or {}).get("symbol", "?")
            strike       = float((sym_obj.get("strike_price") or 0))
            expiry       = sym_obj.get("expiration_date", "?")
            opt_type     = sym_obj.get("option_type", "?")
            contracts    = float(opt.get("units", 0) or 0)
            mkt_val      = float(opt.get("price", 0) or 0) * contracts * 100
            cost         = float(opt.get("average_purchase_price", 0) or 0) * contracts * 100

            from datetime import date
            try:
                exp_date = date.fromisoformat(expiry)
                dte = (exp_date - date.today()).days
            except Exception:
                dte = -1

            options.append({
                "symbol":       f"{underlying} ${int(strike)}{opt_type[0].upper()} exp {expiry}",
                "underlying":   underlying,
                "strike":       strike,
                "expiry":       expiry,
                "opt_type":     opt_type,
                "contracts":    int(contracts),
                "cost_basis":   cost,
                "market_value": mkt_val,
                "dte":          dte,
            })

    total = (sum(s["value"] for s in stocks)
             + sum(o["market_value"] for o in options)
             + sum(c["value"] for c in crypto)
             + cash_total)

    return {
        "stocks":  stocks,
        "options": options,
        "crypto":  crypto,
        "cash":    cash_total,
        "total":   total,
    }
