"""
ShufaClaw V2 — Feature Engineering API

Exposes REST endpoints for the dashboard, backtesting engine, 
and external ML services to access processed feature vectors.
"""

from fastapi import APIRouter, HTTPException
from crypto_agent.data import technical as tech
from crypto_agent.intelligence.feature_engine import feature_engine
from typing import Optional
from datetime import datetime, timezone
from crypto_agent.infrastructure.database import fetch, execute
from crypto_agent.utils.symbols import normalize_symbol

router = APIRouter(prefix="/api/features", tags=["Features"])

async def _get_klines_from_db(symbol: str, timeframe: str, limit: int = 200) -> list:
    rows = await fetch(
        """
        SELECT open_time, open, high, low, close, volume
        FROM candles
        WHERE symbol = $1 AND interval = $2
        ORDER BY open_time DESC
        LIMIT $3
        """,
        symbol,
        timeframe,
        limit,
    )
    if not rows:
        return []
    # Convert to Binance-like kline arrays expected by feature_engine/technical:
    # [open_time_ms, open, high, low, close, volume]
    out = []
    for r in reversed(rows):
        ts_ms = int(r["open_time"].timestamp() * 1000)
        out.append([ts_ms, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"])])
    return out


async def _persist_feature_vector(vector) -> None:
    # Persist as key/value rows in `features`
    payload = vector.model_dump()
    symbol = payload["symbol"]
    interval = payload["interval"]
    ts = payload.get("timestamp") or datetime.now(timezone.utc)
    feature_version = payload.get("feature_version") or "v1.0.0"

    # Exclude metadata
    for k, v in payload.items():
        if k in {"feature_version", "symbol", "interval", "timestamp"}:
            continue
        if v is None:
            continue
        await execute(
            """
            INSERT INTO features (symbol, interval, timestamp, feature_version, feature_name, value)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (symbol, interval, timestamp, feature_name)
            DO UPDATE SET value = EXCLUDED.value, feature_version = EXCLUDED.feature_version
            """,
            symbol,
            interval,
            ts,
            feature_version,
            k,
            float(v),
        )


async def _persist_regime(symbol: str, timeframe: str, timestamp: datetime, dominant: str, probs: dict[str, float], method: str = "rule_based") -> None:
    # Map detector regimes to DB columns (V2 table shape)
    trending_bull = probs.get("bull_trend", 0.0)
    trending_bear = probs.get("bear_trend", 0.0)
    choppy = probs.get("chop_accumulation", 0.0) + probs.get("chop_distribution", 0.0)
    high_vol = probs.get("high_volatility_expansion", 0.0)
    liquidity_crisis = 0.0
    confidence = max(trending_bull, trending_bear, choppy, high_vol, liquidity_crisis)

    await execute(
        """
        INSERT INTO market_regimes
          (symbol, interval, timestamp, trending_bull, trending_bear, choppy_ranging, high_volatility, liquidity_crisis,
           dominant_regime, confidence, method)
        VALUES
          ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (symbol, interval, timestamp)
        DO UPDATE SET
          trending_bull = EXCLUDED.trending_bull,
          trending_bear = EXCLUDED.trending_bear,
          choppy_ranging = EXCLUDED.choppy_ranging,
          high_volatility = EXCLUDED.high_volatility,
          liquidity_crisis = EXCLUDED.liquidity_crisis,
          dominant_regime = EXCLUDED.dominant_regime,
          confidence = EXCLUDED.confidence,
          method = EXCLUDED.method
        """,
        symbol,
        timeframe,
        timestamp,
        float(trending_bull),
        float(trending_bear),
        float(choppy),
        float(high_vol),
        float(liquidity_crisis),
        dominant,
        float(confidence),
        method,
    )


@router.get("/current/{symbol}")
async def get_current_features(symbol: str, timeframe: str = "1h", source: str = "live", persist: bool = False):
    """
    Computes and returns the most recent FeatureVector and Market Regime 
    for the requested symbol.
    """
    try:
        symbol_norm = normalize_symbol(symbol)
        # We need historical klines to compute features for the snapshot
        if source == "db":
            klines = await _get_klines_from_db(symbol_norm, timeframe, limit=200)
        else:
            # For now, live mode uses Binance REST (technical.fetch_klines expects "BTC" or "BTCUSDT")
            klines = await tech.fetch_klines(symbol_norm, interval=timeframe, limit=200)
        
        if not klines or len(klines) < 200:
            raise HTTPException(status_code=400, detail="Not enough data to compute features")
            
        # Compute the Feature Vector
        vector = feature_engine.compute_features(
            symbol=symbol_norm,
            interval=timeframe,
            klines=klines
        )
        
        # Calculate Regime
        from crypto_agent.intelligence.regime_detector import regime_detector
        regime = regime_detector.detect_regime(vector)
        probs = regime_detector.detect_regime_probs(vector)

        if persist:
            await _persist_feature_vector(vector)
            await _persist_regime(symbol_norm, timeframe, vector.timestamp, regime.value, probs, method="rule_based")
        
        return {
            "status": "success",
            "data": {
                "vector": vector.model_dump(),
                "regime": regime.value,
                "regime_probs": probs
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_feature_history(
    symbol: str,
    timeframe: str = "1h",
    feature: str = "rsi_14",
    limit: int = 500,
):
    """
    Returns a single feature history from TimescaleDB for charting.
    """
    try:
        symbol_norm = normalize_symbol(symbol)
        rows = await fetch(
            """
            SELECT timestamp, value, feature_version
            FROM features
            WHERE symbol = $1 AND interval = $2 AND feature_name = $3
            ORDER BY timestamp DESC
            LIMIT $4
            """,
            symbol_norm,
            timeframe,
            feature,
            limit,
        )
        data = [
            {"timestamp": r["timestamp"].isoformat(), "value": float(r["value"]), "feature_version": r["feature_version"]}
            for r in reversed(rows)
        ]
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
