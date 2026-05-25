"""Live price, RSI, MA, and volume data via yfinance."""

import yfinance as yf
import pandas as pd
from typing import Optional


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta  = series.diff()
    gain   = delta.clip(lower=0).rolling(period).mean()
    loss   = (-delta.clip(upper=0)).rolling(period).mean()
    rs     = gain / loss.replace(0, float("nan"))
    rsi    = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1) if not rsi.empty else float("nan")


def get_technicals(ticker: str) -> dict:
    """
    Returns price, RSI(14), MA150, MA200, volume ratio (vs 20-day avg).
    Falls back to NaN fields on any error.
    """
    empty = {
        "ticker": ticker, "price": None, "rsi": None,
        "ma150": None, "ma200": None, "vol_ratio": None, "error": None,
    }
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        if hist.empty or len(hist) < 15:
            empty["error"] = "insufficient_history"
            return empty

        close  = hist["Close"]
        volume = hist["Volume"]

        price     = round(float(close.iloc[-1]), 2)
        rsi       = _rsi(close)
        ma150     = round(float(close.tail(150).mean()), 2) if len(close) >= 150 else None
        ma200     = round(float(close.tail(200).mean()), 2) if len(close) >= 200 else None
        avg_vol   = float(volume.tail(20).mean())
        vol_ratio = round(float(volume.iloc[-1]) / avg_vol, 2) if avg_vol else None

        return {
            "ticker":    ticker,
            "price":     price,
            "rsi":       rsi,
            "ma150":     ma150,
            "ma200":     ma200,
            "vol_ratio": vol_ratio,
            "error":     None,
        }
    except Exception as exc:
        empty["error"] = str(exc)
        return empty


def get_bulk_technicals(tickers: list[str]) -> dict[str, dict]:
    """Fetch technicals for multiple tickers, returns {ticker: data}."""
    return {t: get_technicals(t) for t in tickers}


def fmt_technicals(data: dict) -> str:
    """Human-readable one-liner for prompt context."""
    if data.get("error") or data.get("price") is None:
        return f"{data['ticker']}: data unavailable"
    above_150 = ""
    if data["ma150"] and data["price"]:
        above_150 = "above" if data["price"] > data["ma150"] else "below"
    return (
        f"{data['ticker']}: ${data['price']} | "
        f"RSI {data['rsi']} | "
        f"MA150 ${data['ma150']} ({above_150}) | "
        f"MA200 ${data['ma200']} | "
        f"Vol {data['vol_ratio']}x avg"
    )
