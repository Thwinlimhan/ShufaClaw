"""
ShufaClaw V2 — Kafka Event Bus

Kafka is a message queue. Instead of modules calling each other directly,
they "publish" events to Kafka, and other modules "subscribe" to those events.

WHY THIS IS BETTER:
1. Modules don't need to know about each other
2. If one module crashes, events are saved and processed later
3. Multiple modules can react to the same event
4. Easy to add new modules without changing existing code

EXAMPLE FLOW:
  Market Data Module → publishes "new candle" to Kafka
  → Feature Engine reads candle, computes RSI, publishes "new features"
  → Regime Detector reads features, detects regime change, publishes "regime changed"
  → Strategy Engine reads regime change, adjusts weights

TOPICS (channels for different event types):
  market.raw.BTCUSDT.1h   — raw candle data
  onchain.signals          — on-chain intelligence
  features.computed        — computed feature vectors
  regime.changes           — market regime change events
  signals.trading          — trading signals
  execution.fills          — order fill events
  risk.alerts              — risk limit alerts
"""

import os
import json
import logging
from typing import Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# We'll use aiokafka for async Kafka operations
# Lazy imports so the app doesn't crash if kafka isn't running
_producer = None
_consumers = {}


def _get_bootstrap_servers() -> str:
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


class KafkaEventBus:
    """
    Simple wrapper around Kafka producer/consumer.
    Handles connecting, publishing, and subscribing to events.
    """

    def __init__(self):
        self._producer = None
        self._consumers = {}
        self._connected = False

    async def connect(self):
        """Connect the Kafka producer. Call once at startup."""
        try:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=_get_bootstrap_servers(),
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            await self._producer.start()
            self._connected = True
            logger.info("✅ Kafka producer connected")
        except ImportError:
            logger.warning("⚠️ aiokafka not installed. Run: pip install aiokafka")
            self._connected = False
            self._producer = None
        except Exception as e:
            logger.warning(f"⚠️ Kafka not available: {e}")
            logger.warning("   Events will be logged but not published.")
            self._connected = False
            if self._producer:
                try:
                    await self._producer.stop()
                except Exception:
                    pass
                self._producer = None

    async def close(self):
        """Shutdown producer and all consumers."""
        if self._producer:
            await self._producer.stop()
            self._producer = None
        for consumer in self._consumers.values():
            await consumer.stop()
        self._consumers = {}
        self._connected = False
        logger.info("Kafka connections closed")

    async def publish(self, topic: str, data: dict, key: Optional[str] = None):
        """
        Publish an event to a Kafka topic.

        Args:
            topic: Channel name, e.g. "market.raw.BTCUSDT.1h"
            data: Dictionary of event data
            key: Optional key for ordering (events with same key go to same partition)
        """
        # Add metadata
        data['_published_at'] = datetime.utcnow().isoformat()
        data['_topic'] = topic

        if self._connected and self._producer:
            try:
                await self._producer.send_and_wait(topic, value=data, key=key)
                logger.debug(f"Published to {topic}: {key or 'no-key'}")
            except Exception as e:
                logger.error(f"Failed to publish to {topic}: {e}")
        else:
            # Kafka not available — just log it
            logger.debug(f"[KAFKA-OFFLINE] {topic}: {json.dumps(data, default=str)[:200]}")

    async def subscribe(self, topic: str, handler: Callable, group_id: str = "shufaclaw"):
        """
        Subscribe to a Kafka topic and process events.

        Args:
            topic: Channel to listen to
            handler: Async function that receives each event dict
            group_id: Consumer group (allows multiple instances to share work)
        """
        if not self._connected:
            logger.warning(f"Cannot subscribe to {topic} — Kafka not connected")
            return

        try:
            from aiokafka import AIOKafkaConsumer
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=_get_bootstrap_servers(),
                group_id=group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='latest'
            )
            await consumer.start()
            self._consumers[topic] = consumer

            logger.info(f"✅ Subscribed to Kafka topic: {topic}")

            # Process messages in background
            import asyncio
            async def _consume():
                async for msg in consumer:
                    try:
                        await handler(msg.value)
                    except Exception as e:
                        logger.error(f"Error processing {topic} message: {e}")

            asyncio.create_task(_consume())

        except ImportError:
            logger.warning("aiokafka not installed for subscription")
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected


# ─── Predefined Topic Names ──────────────────────────────────
# Use these constants to avoid typos

class Topics:
    """All Kafka topic names used in the system."""

    # Module 1: Market Data
    @staticmethod
    def market_raw(symbol: str, interval: str) -> str:
        return f"market.raw.{symbol}.{interval}"

    # Module 2: On-Chain
    ONCHAIN_SIGNALS = "onchain.signals"

    # Module 3: Features
    FEATURES_COMPUTED = "features.computed"

    # Module 4: Regime
    REGIME_CHANGES = "regime.changes"

    # Module 10: Signals
    TRADING_SIGNALS = "signals.trading"

    # Module 9: Execution
    EXECUTION_FILLS = "execution.fills"

    # Module 8: Risk
    RISK_ALERTS = "risk.alerts"
    RISK_HALT = "risk.halt"


# Global event bus instance
event_bus = KafkaEventBus()
