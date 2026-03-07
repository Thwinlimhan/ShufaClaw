"""
ShufaClaw V2 — Database Connection (TimescaleDB)

This replaces the old SQLite database.py with a PostgreSQL/TimescaleDB connection.
TimescaleDB is PostgreSQL with special optimizations for time-series data
(like candle history, feature vectors, signals).

HOW IT WORKS:
- We use 'asyncpg' for fast async database connections.
- A "connection pool" keeps several connections open and reuses them.
- Tables are created automatically on first run.
"""

import os
import logging
import asyncpg
from typing import Optional

logger = logging.getLogger(__name__)

# Connection pool — shared across the entire application
_pool: Optional[asyncpg.Pool] = None


def _get_db_url() -> str:
    """Build database URL from environment variables with production-safe guards."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "shufaclaw")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "shufaclaw")

    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env in {"prod", "production"} and not password:
        raise RuntimeError("DB_PASSWORD must be set in production mode")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


async def get_pool() -> asyncpg.Pool:
    """
    Get or create the database connection pool.
    A pool keeps multiple connections ready so queries are fast.
    """
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                _get_db_url(),
                min_size=2,      # Always keep 2 connections open
                max_size=10,     # Max 10 simultaneous connections
                command_timeout=30
            )
            logger.info("✅ TimescaleDB connection pool created")
        except Exception as e:
            logger.error(f"❌ Failed to connect to TimescaleDB: {e}")
            logger.error("   Make sure Docker is running: docker-compose up -d")
            raise
    return _pool


async def close_pool():
    """Close all database connections. Call this when shutting down."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("TimescaleDB connection pool closed")


async def execute(query: str, *args):
    """Run a query that doesn't return results (INSERT, UPDATE, CREATE)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch(query: str, *args) -> list:
    """Run a query and return all matching rows."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args):
    """Run a query and return a single row."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args):
    """Run a query and return a single value."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


# ─── Table Creation ───────────────────────────────────────────

async def create_tables():
    """
    Create all database tables if they don't already exist.
    TimescaleDB hypertables are used for time-series data (candles, features, etc.)
    Hypertables automatically partition data by time for fast queries.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:

        # Enable TimescaleDB extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

        # ── Module 1: Market Data ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                symbol          TEXT NOT NULL,
                interval        TEXT NOT NULL,
                open_time       TIMESTAMPTZ NOT NULL,
                open            NUMERIC NOT NULL,
                high            NUMERIC NOT NULL,
                low             NUMERIC NOT NULL,
                close           NUMERIC NOT NULL,
                volume          NUMERIC NOT NULL,
                quote_volume    NUMERIC NOT NULL,
                source          TEXT NOT NULL,
                ingested_at     TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, interval, open_time)
            );
        """)

        # Convert to hypertable (TimescaleDB magic for fast time queries)
        try:
            await conn.execute("""
                SELECT create_hypertable('candles', 'open_time',
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
            """)
        except Exception:
            pass  # Already a hypertable

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS funding_rates (
                symbol          TEXT NOT NULL,
                rate            DOUBLE PRECISION NOT NULL,
                timestamp       TIMESTAMPTZ NOT NULL,
                next_funding    TIMESTAMPTZ,
                source          TEXT NOT NULL,
                PRIMARY KEY (symbol, timestamp)
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS open_interest (
                symbol          TEXT NOT NULL,
                value_usd       DOUBLE PRECISION NOT NULL,
                change_1h_pct   DOUBLE PRECISION,
                timestamp       TIMESTAMPTZ NOT NULL,
                source          TEXT NOT NULL,
                PRIMARY KEY (symbol, timestamp)
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS liquidations (
                id              SERIAL,
                symbol          TEXT NOT NULL,
                side            TEXT NOT NULL,
                quantity        DOUBLE PRECISION NOT NULL,
                price           DOUBLE PRECISION NOT NULL,
                value_usd       DOUBLE PRECISION NOT NULL,
                timestamp       TIMESTAMPTZ NOT NULL,
                source          TEXT NOT NULL
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS data_quality_log (
                id              SERIAL PRIMARY KEY,
                symbol          TEXT NOT NULL,
                interval        TEXT,
                issue_type      TEXT NOT NULL,
                description     TEXT NOT NULL,
                gap_start       TIMESTAMPTZ,
                gap_end         TIMESTAMPTZ,
                records_affected INTEGER DEFAULT 0,
                resolved        BOOLEAN DEFAULT FALSE,
                timestamp       TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # ── Module 2: On-Chain Intelligence ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS onchain_signals (
                id              SERIAL,
                symbol          TEXT NOT NULL,
                signal_type     TEXT NOT NULL,
                value           DOUBLE PRECISION NOT NULL,
                z_score         DOUBLE PRECISION DEFAULT 0,
                is_anomaly      BOOLEAN DEFAULT FALSE,
                direction       TEXT,
                description     TEXT,
                timestamp       TIMESTAMPTZ NOT NULL,
                source          TEXT NOT NULL
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS whale_transfers (
                id              SERIAL,
                symbol          TEXT NOT NULL,
                from_address    TEXT NOT NULL,
                to_address      TEXT NOT NULL,
                value_usd       DOUBLE PRECISION NOT NULL,
                is_to_exchange  BOOLEAN DEFAULT FALSE,
                is_from_exchange BOOLEAN DEFAULT FALSE,
                tx_hash         TEXT NOT NULL,
                block_number    BIGINT,
                timestamp       TIMESTAMPTZ NOT NULL,
                source          TEXT NOT NULL
            );
        """)

        # ── Module 3: Features ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS features (
                symbol          TEXT NOT NULL,
                interval        TEXT NOT NULL,
                timestamp       TIMESTAMPTZ NOT NULL,
                feature_version TEXT DEFAULT 'v1.0.0',
                feature_name    TEXT NOT NULL,
                value           DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (symbol, interval, timestamp, feature_name)
            );
        """)

        try:
            await conn.execute("""
                SELECT create_hypertable('features', 'timestamp',
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
            """)
        except Exception:
            pass

        # ── Module 4: Market Regimes ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS market_regimes (
                symbol              TEXT NOT NULL,
                interval            TEXT NOT NULL,
                timestamp           TIMESTAMPTZ NOT NULL,
                trending_bull       DOUBLE PRECISION DEFAULT 0,
                trending_bear       DOUBLE PRECISION DEFAULT 0,
                choppy_ranging      DOUBLE PRECISION DEFAULT 0,
                high_volatility     DOUBLE PRECISION DEFAULT 0,
                liquidity_crisis    DOUBLE PRECISION DEFAULT 0,
                dominant_regime     TEXT NOT NULL,
                confidence          DOUBLE PRECISION NOT NULL,
                method              TEXT DEFAULT 'rule_based',
                PRIMARY KEY (symbol, interval, timestamp)
            );
        """)

        # ── Module 5 & 6: Strategies & Backtests ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id              UUID PRIMARY KEY,
                name            TEXT NOT NULL,
                type            TEXT NOT NULL,
                version         TEXT DEFAULT 'v1.0.0',
                params          JSONB DEFAULT '{}',
                feature_version TEXT DEFAULT 'v1.0.0',
                status          TEXT DEFAULT 'candidate',
                best_sharpe     DOUBLE PRECISION,
                best_win_rate   DOUBLE PRECISION,
                max_drawdown    DOUBLE PRECISION,
                total_backtests INTEGER DEFAULT 0,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                updated_at      TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id                      UUID PRIMARY KEY,
                strategy_id             TEXT NOT NULL,
                symbol                  TEXT NOT NULL,
                interval                TEXT NOT NULL,
                start_date              DATE NOT NULL,
                end_date                DATE NOT NULL,
                total_return            DOUBLE PRECISION NOT NULL,
                annualized_return       DOUBLE PRECISION NOT NULL,
                sharpe_ratio            DOUBLE PRECISION NOT NULL,
                sortino_ratio           DOUBLE PRECISION NOT NULL,
                max_drawdown            DOUBLE PRECISION NOT NULL,
                max_drawdown_duration   INTEGER DEFAULT 0,
                profit_factor           DOUBLE PRECISION NOT NULL,
                win_rate                DOUBLE PRECISION NOT NULL,
                expectancy              DOUBLE PRECISION DEFAULT 0,
                num_trades              INTEGER NOT NULL,
                avg_holding_hours       DOUBLE PRECISION DEFAULT 0,
                regime_breakdown        JSONB DEFAULT '{}',
                monthly_returns         JSONB DEFAULT '[]',
                initial_capital         DOUBLE PRECISION DEFAULT 10000,
                final_capital           DOUBLE PRECISION DEFAULT 0,
                slippage_bps            DOUBLE PRECISION DEFAULT 10,
                fee_rate                DOUBLE PRECISION DEFAULT 0.001,
                created_at              TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # ── Module 8: Risk Events ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id              UUID PRIMARY KEY,
                alert_level     TEXT NOT NULL,
                limit_type      TEXT NOT NULL,
                current_value   DOUBLE PRECISION NOT NULL,
                limit_value     DOUBLE PRECISION NOT NULL,
                utilization_pct DOUBLE PRECISION NOT NULL,
                action_taken    TEXT NOT NULL,
                details         TEXT,
                timestamp       TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # ── Module 9: Orders ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id              UUID PRIMARY KEY,
                symbol          TEXT NOT NULL,
                side            TEXT NOT NULL,
                order_type      TEXT DEFAULT 'market',
                quantity        DOUBLE PRECISION NOT NULL,
                price           DOUBLE PRECISION,
                algorithm       TEXT DEFAULT 'market',
                status          TEXT DEFAULT 'pending',
                filled_quantity DOUBLE PRECISION DEFAULT 0,
                avg_fill_price  DOUBLE PRECISION DEFAULT 0,
                total_fees      DOUBLE PRECISION DEFAULT 0,
                arrival_price   DOUBLE PRECISION,
                slippage_bps    DOUBLE PRECISION,
                strategy_id     TEXT,
                exchange        TEXT DEFAULT 'binance',
                retry_count     INTEGER DEFAULT 0,
                error_message   TEXT,
                is_paper        BOOLEAN DEFAULT TRUE,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                submitted_at    TIMESTAMPTZ,
                filled_at       TIMESTAMPTZ,
                cancelled_at    TIMESTAMPTZ
            );
        """)

        # ── Module 11: Agent Reports ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_reports (
                id                  UUID PRIMARY KEY,
                agent_type          TEXT NOT NULL,
                trigger             TEXT NOT NULL,
                priority            TEXT DEFAULT 'normal',
                summary             TEXT NOT NULL,
                analysis            TEXT NOT NULL,
                recommendations     JSONB DEFAULT '[]',
                data_snapshot       JSONB DEFAULT '{}',
                execution_time_sec  DOUBLE PRECISION DEFAULT 0,
                tokens_used         INTEGER DEFAULT 0,
                model_used          TEXT,
                created_at          TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # ── Module 10: Signals ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id              SERIAL,
                symbol          TEXT NOT NULL,
                direction       TEXT NOT NULL,
                confidence      DOUBLE PRECISION NOT NULL,
                expected_return DOUBLE PRECISION,
                time_horizon    TEXT DEFAULT '4h',
                source          TEXT NOT NULL,
                source_detail   TEXT,
                entry_price     DOUBLE PRECISION,
                stop_loss       DOUBLE PRECISION,
                take_profit     DOUBLE PRECISION,
                passed_threshold BOOLEAN DEFAULT FALSE,
                timestamp       TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        logger.info("✅ All V2 database tables created successfully")


async def check_connection() -> bool:
    """Quick health check — can we reach the database?"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
