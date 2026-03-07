"""
ShufaClaw V2 — Historical Data Backfiller (CLI)

Downloads historical OHLCV data from Binance and saves it to TimescaleDB.
Used to get past data for backtesting or training AI models.

HOW TO USE:
    python -m crypto_agent.data.backfill_cli BTC/USDT 1h 30
    (Downloads 30 days of 1-hour candles for BTC/USDT)
"""

import sys
import asyncio
import argparse
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import ccxt.async_support as ccxt  # Using REST (async) for historical data

# Important: set up paths so we can import from the project
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crypto_agent.schemas.market import Candle, Interval, DataSource
from crypto_agent.infrastructure.database import get_pool, create_tables
from crypto_agent.utils.symbols import normalize_symbol

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def backfill(symbol: str, timeframe: str, days: int):
    """
    Downloads historical data and inserts it into TimescaleDB.
    """
    # 1. Initialize infra
    await create_tables()
    pool = await get_pool()
    
    # Map timeframe string to our Enum
    try:
        db_interval = Interval(timeframe)
    except ValueError:
        logger.error(f"❌ Invalid timeframe '{timeframe}'. Allowed: {[i.value for i in Interval]}")
        return

    # 2. Setup CCXT Exchange
    exchange = ccxt.binance({
        'enableRateLimit': True,
    })

    # 3. Calculate time window
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)
    since_ms = int(start_time.timestamp() * 1000)
    
    logger.info(f"🔄 Starting backfill for {symbol} ({timeframe}) from {start_time.date()}")
    symbol_db = normalize_symbol(symbol)
    
    total_candles = 0
    all_candles_data = []

    try:
        # 4. Paginate through history (Exchanges usually limit to 500-1000 candles per request)
        while since_ms < int(now.timestamp() * 1000):
            # Fetch from exchange
            ohlcvs = await exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=1000)
            
            if not ohlcvs:
                break
                
            # Process batch
            batch_data = []
            for c in ohlcvs:
                open_time = datetime.fromtimestamp(c[0] / 1000.0, tz=timezone.utc)
                batch_data.append((
                    symbol_db,
                    db_interval.value,
                    open_time,
                    float(c[1]),  # open
                    float(c[2]),  # high
                    float(c[3]),  # low
                    float(c[4]),  # close
                    float(c[5]),  # volume
                    0.0,          # quote_volume (setting default 0 for ease)
                    DataSource.BINANCE.value
                ))
            
            all_candles_data.extend(batch_data)
            total_candles += len(ohlcvs)
            
            # Progress update
            latest_time = datetime.fromtimestamp(ohlcvs[-1][0] / 1000.0, tz=timezone.utc)
            logger.info(f"   Downloaded {len(ohlcvs)} candles... Reached {latest_time.date()}")
            
            # Move the window forward for the next request (+1 ms so we don't duplicate)
            since_ms = ohlcvs[-1][0] + 1
            
            # Be nice to the exchange API
            await asyncio.sleep(exchange.rateLimit / 1000)
            
        # 5. Bulk Insert into TimescaleDB
        if all_candles_data:
            logger.info(f"💾 Saving {total_candles} candles to TimescaleDB...")
            
            async with pool.acquire() as conn:
                await conn.executemany("""
                    INSERT INTO candles 
                    (symbol, interval, open_time, open, high, low, close, volume, quote_volume, source)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (symbol, interval, open_time) DO NOTHING;
                """, all_candles_data)
                
            logger.info(f"✅ Successfully backfilled {total_candles} candles!")
        else:
            logger.warning("No data found to backfill.")

    except Exception as e:
        logger.error(f"❌ Backfill failed: {e}")
    finally:
        await exchange.close()


def main():
    parser = argparse.ArgumentParser(description="Download historical crypto data to TimescaleDB")
    parser.add_argument("symbol", type=str, help="Trading pair (e.g., BTC/USDT)")
    parser.add_argument("timeframe", type=str, help="Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)")
    parser.add_argument("days", type=int, help="Number of days to look back")
    
    args = parser.parse_args()
    
    asyncio.run(backfill(args.symbol, args.timeframe, args.days))


if __name__ == "__main__":
    main()
