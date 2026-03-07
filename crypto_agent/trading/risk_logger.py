"""
ShufaClaw V2 — Risk Event Logger

Persists risk events to TimescaleDB and publishes to Kafka.
Wired by main.post_init into risk_manager.set_event_handler.
"""

import logging
import asyncio
from crypto_agent.schemas.trading import RiskEvent
from crypto_agent.infrastructure.event_bus import event_bus, Topics

logger = logging.getLogger(__name__)


async def persist_and_publish(event: RiskEvent) -> None:
    """Persist risk event to DB and publish to Kafka."""
    try:
        from crypto_agent.infrastructure.database import execute

        await execute(
            """
            INSERT INTO risk_events (id, alert_level, limit_type, current_value, limit_value, utilization_pct, action_taken, details, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            event.id,
            event.alert_level.value,
            event.limit_type,
            event.current_value,
            event.limit_value,
            event.utilization_pct,
            event.action_taken,
            event.details,
            event.timestamp,
        )
        logger.info(f"Risk event persisted: {event.alert_level.value} {event.limit_type}")

        payload = event.model_dump(mode="json")
        await event_bus.publish(Topics.RISK_ALERTS, payload, key=event.alert_level.value)
        if event.alert_level.value == "emergency":
            await event_bus.publish(Topics.RISK_HALT, payload, key="halt")
    except Exception as e:
        logger.error(f"Failed to persist/publish risk event: {e}")
