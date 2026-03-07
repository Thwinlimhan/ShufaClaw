from __future__ import annotations

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional

from crypto_agent.infrastructure.database import fetch
from crypto_agent.utils.symbols import normalize_symbol


router = APIRouter(prefix="/api/v2", tags=["V2 Data"])


@router.get("/candles")
async def get_candles(
    symbol: str,
    interval: str = "1h",
    limit: int = 500,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    """
    Query candles from TimescaleDB.

    - `start` and `end` are ISO8601 timestamps (inclusive bounds).
    - Returns ascending timestamp order for charting.
    """
    try:
        sym = normalize_symbol(symbol)
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None

        if start_dt and end_dt:
            rows = await fetch(
                """
                SELECT open_time, open, high, low, close, volume, quote_volume, source, ingested_at
                FROM candles
                WHERE symbol = $1 AND interval = $2 AND open_time >= $3 AND open_time <= $4
                ORDER BY open_time ASC
                LIMIT $5
                """,
                sym,
                interval,
                start_dt,
                end_dt,
                limit,
            )
        elif start_dt:
            rows = await fetch(
                """
                SELECT open_time, open, high, low, close, volume, quote_volume, source, ingested_at
                FROM candles
                WHERE symbol = $1 AND interval = $2 AND open_time >= $3
                ORDER BY open_time ASC
                LIMIT $4
                """,
                sym,
                interval,
                start_dt,
                limit,
            )
        else:
            rows = await fetch(
                """
                SELECT open_time, open, high, low, close, volume, quote_volume, source, ingested_at
                FROM candles
                WHERE symbol = $1 AND interval = $2
                ORDER BY open_time DESC
                LIMIT $3
                """,
                sym,
                interval,
                limit,
            )
            rows = list(reversed(rows))

        data = [
            {
                "open_time": r["open_time"].isoformat(),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"]),
                "quote_volume": float(r["quote_volume"]),
                "source": r["source"],
                "ingested_at": r["ingested_at"].isoformat() if r["ingested_at"] else None,
            }
            for r in rows
        ]
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def list_strategies(limit: int = 200):
    try:
        rows = await fetch(
            """
            SELECT id, name, type, version, params, feature_version, status,
                   best_sharpe, best_win_rate, max_drawdown, total_backtests, created_at, updated_at
            FROM strategies
            ORDER BY updated_at DESC
            LIMIT $1
            """,
            limit,
        )
        data = []
        for r in rows:
            data.append(
                {
                    "id": str(r["id"]),
                    "name": r["name"],
                    "type": r["type"],
                    "version": r["version"],
                    "params": r["params"],
                    "feature_version": r["feature_version"],
                    "status": r["status"],
                    "best_sharpe": r["best_sharpe"],
                    "best_win_rate": r["best_win_rate"],
                    "max_drawdown": r["max_drawdown"],
                    "total_backtests": r["total_backtests"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
                }
            )
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtests")
async def list_backtests(symbol: Optional[str] = None, strategy_id: Optional[str] = None, limit: int = 200):
    try:
        if symbol:
            sym = normalize_symbol(symbol)
            rows = await fetch(
                """
                SELECT *
                FROM backtest_results
                WHERE symbol = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                sym,
                limit,
            )
        elif strategy_id:
            rows = await fetch(
                """
                SELECT *
                FROM backtest_results
                WHERE strategy_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                strategy_id,
                limit,
            )
        else:
            rows = await fetch(
                """
                SELECT *
                FROM backtest_results
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
        data = []
        for r in rows:
            d = dict(r)
            # normalize datetimes/UUIDs
            d["id"] = str(d.get("id"))
            d["created_at"] = d["created_at"].isoformat() if d.get("created_at") else None
            return_fields = {
                "start_date",
                "end_date",
            }
            for f in return_fields:
                if d.get(f) is not None:
                    d[f] = d[f].isoformat()
            data.append(d)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def list_orders(symbol: Optional[str] = None, limit: int = 200):
    try:
        if symbol:
            sym = normalize_symbol(symbol)
            rows = await fetch(
                """
                SELECT *
                FROM orders
                WHERE symbol = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                sym,
                limit,
            )
        else:
            rows = await fetch(
                """
                SELECT *
                FROM orders
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
        data = []
        for r in rows:
            d = dict(r)
            d["id"] = str(d.get("id"))
            for ts_field in ["created_at", "submitted_at", "filled_at", "cancelled_at"]:
                if d.get(ts_field) is not None:
                    d[ts_field] = d[ts_field].isoformat()
            data.append(d)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/events")
async def list_risk_events(limit: int = 200):
    try:
        rows = await fetch(
            """
            SELECT *
            FROM risk_events
            ORDER BY timestamp DESC
            LIMIT $1
            """,
            limit,
        )
        data = []
        for r in rows:
            d = dict(r)
            d["id"] = str(d.get("id"))
            if d.get("timestamp") is not None:
                d["timestamp"] = d["timestamp"].isoformat()
            data.append(d)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/reports")
async def list_agent_reports(limit: int = 200, agent_type: Optional[str] = None):
    try:
        if agent_type:
            rows = await fetch(
                """
                SELECT *
                FROM agent_reports
                WHERE agent_type = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                agent_type,
                limit,
            )
        else:
            rows = await fetch(
                """
                SELECT *
                FROM agent_reports
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
        data = []
        for r in rows:
            d = dict(r)
            d["id"] = str(d.get("id"))
            if d.get("created_at") is not None:
                d["created_at"] = d["created_at"].isoformat()
            data.append(d)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

