from __future__ import annotations

import re


_PAIR_SEP_RE = re.compile(r"[\s/_:-]+")


def normalize_symbol(symbol: str) -> str:
    """
    Normalize symbols into a consistent internal representation.

    Canonical form (internal / DB / APIs): "BTCUSDT"
    Accepted inputs: "BTCUSDT", "BTC/USDT", "btc-usdt", "BTC_USDT", "BTC:USDT"
    """
    s = (symbol or "").strip().upper()
    if not s:
        return s

    # If already like BTCUSDT (no separators), keep it.
    if "/" not in s and "_" not in s and "-" not in s and ":" not in s and " " not in s:
        return s

    parts = [p for p in _PAIR_SEP_RE.split(s) if p]
    if len(parts) >= 2:
        return f"{parts[0]}{parts[1]}"
    return s.replace("/", "").replace("_", "").replace("-", "").replace(":", "").replace(" ", "")


def to_ccxt_symbol(symbol: str, quote: str = "USDT") -> str:
    """
    Convert internal canonical symbol into CCXT pair form (default quote USDT).

    Examples:
    - "BTCUSDT" -> "BTC/USDT"
    - "BTC/USDT" -> "BTC/USDT"
    - "BTC" -> "BTC/USDT"
    """
    s = (symbol or "").strip().upper()
    if not s:
        return s
    if "/" in s:
        return s

    s = normalize_symbol(s)
    if s.endswith(quote):
        base = s[: -len(quote)]
        return f"{base}/{quote}"
    if len(s) <= len(quote):
        return f"{s}/{quote}"
    # fallback: assume it is base-only
    return f"{s}/{quote}"

