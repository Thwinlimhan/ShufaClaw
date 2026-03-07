"""
ShufaClaw V2 — Market Data WebSocket Streamer

This replaces the old aiohttp REST API calls. Instead of asking Binance "what's the price?"
every few seconds, we connect a WebSocket and Binance PUSHES every trade and candle to us instantly.

HOW IT WORKS:
1. Connects to Binance using ccxt.pro (WebSocket wrapper).
2. Subscribes to 1m candles, trades, and order book for a list of symbols.
3. When data arrives, parses it to match our strict Pydantic rules (schemas/market.py).
4. Saves directly to TimescaleDB (for history) AND publishes to Kafka (for other modules).
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
import ccxt.pro as ccxt

from crypto_agent.schemas.market import (
    Candle, TradeTick, OrderBookSnapshot, Interval, DataSource, DataQualityLog
)
from crypto_agent.infrastructure.database import execute
from crypto_agent.infrastructure.event_bus import event_bus, Topics
from crypto_agent.utils.symbols import normalize_symbol

logger = logging.getLogger(__name__)


class MarketStreamer:
    """Manages WebSocket streams from an exchange."""

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id
        # Initialize the CCXT Pro exchange wrapper
        # enableRateLimit prevents us from getting banned during setup
        self.exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
        self.running = False
        self.tasks = []
        self._last_candle_open_time: dict[tuple[str, str], datetime] = {}

    async def start(self, symbols: list[str]):
        """Start listening for data on the specified symbols."""
        self.running = True
        logger.info(f"🚀 Starting {self.exchange_id.title()} WebSocket Streamer for {symbols}")

        # Start background tasks for different datastreams
        self.tasks.append(asyncio.create_task(self._watch_candles_loop(symbols)))
        self.tasks.append(asyncio.create_task(self._watch_trades_loop(symbols)))
        self.tasks.append(asyncio.create_task(self._watch_orderbook_loop(symbols)))

    async def stop(self):
        """Stop all streams and close connections gracefully."""
        self.running = False
        logger.info("Stopping Market Streamer...")
        
        # Cancel all running loops
        for task in self.tasks:
            task.cancel()
            
        # Close the connection accurately
        if self.exchange:
            await self.exchange.close()
        logger.info("Market Streamer stopped.")

    # ─── Stream Listeners ─────────────────────────────────────

    async def _watch_candles_loop(self, symbols: list[str]):
        """Listen for new 1-minute candles forming."""
        interval = "1m"
        db_interval = Interval.ONE_MINUTE
        source = DataSource(self.exchange_id)
        expected_seconds = 60

        while self.running:
            try:
                # CCXT watch_ohlcv connects the websocket and waits for the next candle update.
                # It handles reconnects automatically!
                # It returns the most recent OHLCV data array: [timestamp, open, high, low, close, volume]
                ohlcvs = await self.exchange.watch_ohlcv_for_symbols(symbols, timeframe=interval)
                
                # We get a dictionary where keys are symbols and values are arrays of candles
                for symbol, candles in ohlcvs.items():
                    symbol_db = normalize_symbol(symbol)
                    # Get the most recent partial/closed candle
                    latest_candle = candles[-1]
                    timestamp_ms = latest_candle[0]
                    
                    # Convert ms to strict datetime timezone-aware
                    open_time = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
                    
                    # Build our strict Pydantic model
                    candle_data = Candle(
                        symbol=symbol_db,
                        interval=db_interval,
                        open_time=open_time,
                        open=Decimal(str(latest_candle[1])),
                        high=Decimal(str(latest_candle[2])),
                        low=Decimal(str(latest_candle[3])),
                        close=Decimal(str(latest_candle[4])),
                        volume=Decimal(str(latest_candle[5])),
                        quote_volume=Decimal("0"), # Binance CCXT structure sometimes doesn't map quote volume directly here
                        source=source
                    )

                    # Data quality: detect gaps and latency (in-memory, best-effort)
                    key = (symbol_db, candle_data.interval.value)
                    prev_open = self._last_candle_open_time.get(key)
                    if prev_open is not None:
                        gap_seconds = (candle_data.open_time - prev_open).total_seconds()
                        # Allow small drift; flag any multi-candle gap
                        if gap_seconds > expected_seconds * 1.5:
                            missing = max(int(round(gap_seconds / expected_seconds)) - 1, 0)
                            dq = DataQualityLog(
                                symbol=symbol_db,
                                interval=db_interval,
                                issue_type="gap",
                                description=f"Detected candle gap of {gap_seconds:.0f}s (~{missing} missing) for {symbol_db} {db_interval.value}",
                                gap_start=prev_open,
                                gap_end=candle_data.open_time,
                                records_affected=missing,
                            )
                            try:
                                await execute(
                                    """
                                    INSERT INTO data_quality_log
                                      (symbol, interval, issue_type, description, gap_start, gap_end, records_affected, resolved)
                                    VALUES
                                      ($1, $2, $3, $4, $5, $6, $7, $8)
                                    """,
                                    dq.symbol,
                                    dq.interval.value if dq.interval else None,
                                    dq.issue_type,
                                    dq.description,
                                    dq.gap_start,
                                    dq.gap_end,
                                    dq.records_affected,
                                    dq.resolved,
                                )
                            except Exception as e:
                                logger.warning(f"Failed writing data_quality_log gap: {e}")

                    self._last_candle_open_time[key] = candle_data.open_time

                    # 1. Write to TimescaleDB
                    query = """
                        INSERT INTO candles 
                        (symbol, interval, open_time, open, high, low, close, volume, quote_volume, source)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        ON CONFLICT (symbol, interval, open_time) 
                        DO UPDATE SET
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            quote_volume = EXCLUDED.quote_volume;
                    """
                    await execute(
                        query,
                        candle_data.symbol,
                        candle_data.interval.value,
                        candle_data.open_time,
                        float(candle_data.open),
                        float(candle_data.high),
                        float(candle_data.low),
                        float(candle_data.close),
                        float(candle_data.volume),
                        float(candle_data.quote_volume),
                        candle_data.source.value
                    )

                    # 2. Publish to Kafka event bus (for other bots/modules to read live)
                    topic = Topics.market_raw(symbol_db, candle_data.interval.value)
                    
                    # Convert Decimal to float for JSON serialization
                    kafka_payload = candle_data.model_dump()
                    kafka_payload['open'] = float(kafka_payload['open'])
                    kafka_payload['high'] = float(kafka_payload['high'])
                    kafka_payload['low'] = float(kafka_payload['low'])
                    kafka_payload['close'] = float(kafka_payload['close'])
                    kafka_payload['volume'] = float(kafka_payload['volume'])
                    kafka_payload['quote_volume'] = float(kafka_payload['quote_volume'])
                    
                    await event_bus.publish(topic, kafka_payload, key=symbol_db)
                    
                    # Record ingestion time for lag telemetry!
                    from crypto_agent.trading.monitoring import monitoring_service
                    monitoring_service.record_ingestion()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in candle stream: {e}")
                await asyncio.sleep(5)  # Pause before retry

    async def _watch_trades_loop(self, symbols: list[str]):
        """Listen for every single trade that occurs (Tick data)."""
        source = DataSource(self.exchange_id)

        while self.running:
            try:
                # CCXT watch_trades waits for the next executed trade
                trades = await self.exchange.watch_trades_for_symbols(symbols)
                
                for trade in trades:
                    # Ignore trades without valid sides for safety
                    if trade.get('side') not in ['buy', 'sell']:
                        continue
                        
                    tick = TradeTick(
                        symbol=normalize_symbol(trade["symbol"]),
                        price=trade['price'],
                        quantity=trade['amount'],
                        is_buyer_maker=(trade['side'] == 'sell'), # In Binance, if seller is the taker, maker is buyer. "sell" trade implies taker hit the bid (buyer is maker).
                        timestamp=datetime.fromtimestamp(trade['timestamp'] / 1000.0, tz=timezone.utc),
                        source=source
                    )
                    
                    # Skip DB write for ticks unless specifically requested (too much data!)
                    # Instead, we just blast it to Kafka for the Volume Delta engine to aggregate.
                    await event_bus.publish(f"market.trades.{tick.symbol}", tick.model_dump(), key=tick.symbol)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trades stream: {e}")
                await asyncio.sleep(5)

    async def _watch_orderbook_loop(self, symbols: list[str]):
        """Listen for changes in the Order Book (Bids and Asks)."""
        source = DataSource(self.exchange_id)

        while self.running:
            try:
                # Limit to 20 depths to save memory and bandwidth
                limit = 20
                orderbook = await self.exchange.watch_order_book_for_symbols(symbols, limit=limit)
                
                symbol = normalize_symbol(orderbook["symbol"])
                
                snapshot = OrderBookSnapshot(
                    symbol=symbol,
                    bids=orderbook['bids'][:limit],
                    asks=orderbook['asks'][:limit],
                    timestamp=datetime.fromtimestamp(orderbook['timestamp'] / 1000.0, tz=timezone.utc) if orderbook.get('timestamp') else datetime.now(timezone.utc),
                    source=source
                )
                
                # Order books also change extremely fast. Don't DB store every tick.
                # Just publish to Kafka for the Liquidity/Imbalance scanner!
                await event_bus.publish(f"market.orderbook.{symbol}", snapshot.model_dump(), key=symbol)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Some exchanges don't support multi-symbol watch_order_book perfectly yet in CCXT
                # If we hit an error, log it and back off slowly
                logger.warning(f"OrderBook stream delay: {e}")
                await asyncio.sleep(5)


# Global streamer instance
market_streamer = MarketStreamer()
