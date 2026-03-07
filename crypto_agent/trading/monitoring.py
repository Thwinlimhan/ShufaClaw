"""
ShufaClaw V2 — Platform Monitoring Service

Continuously tracks system health, latency, executions, and strategy drift.
"""

import logging
import time
from datetime import datetime
from collections import deque
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SystemMetrics(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ingestion_lag_ms: float = 0.0
    execution_latency_ms: float = 0.0
    backtest_throughput_per_hr: int = 0
    active_strategies: int = 0
    open_orders: int = 0
    api_errors_1h: int = 0

class MonitoringService:
    def __init__(self):
        self.metrics_history = deque(maxlen=1000)
        self.current_metrics = SystemMetrics()
        
        # In memory state for real-time latency calculation
        self._last_ingest_time = time.time()
        self._execution_times = []
        
    def record_ingestion(self):
        """Called every time a WebSocket tick arrives."""
        now = time.time()
        self.current_metrics.ingestion_lag_ms = (now - self._last_ingest_time) * 1000
        self._last_ingest_time = now
        
        if self.current_metrics.ingestion_lag_ms > 5000:
            logger.warning(f"⚠️ HIGH LATENCY: Market data ingestion lag is {self.current_metrics.ingestion_lag_ms:.0f}ms!")

    def record_execution_time(self, duration_sec: float):
        """Called by Execution Engine after an order is processed."""
        self._execution_times.append(duration_sec * 1000)
        if len(self._execution_times) > 50:
            self._execution_times.pop(0)
            
        avg_latency = sum(self._execution_times) / len(self._execution_times)
        self.current_metrics.execution_latency_ms = avg_latency
        
        if self.current_metrics.execution_latency_ms > 2000:
            logger.warning(f"⚠️ EXECUTION SLOWDOWN: Average order latency is {avg_latency:.0f}ms!")

    def trigger_snapshot(self):
        """Called periodically (e.g. by Orchestrator) to freeze current metrics."""
        self.metrics_history.append(self.current_metrics.model_copy())
        # Reset specific rolling counters if needed
        return self.current_metrics

    def get_dashboard_summary(self) -> dict:
        """Exposes the telemetry to the REST API."""
        return {
            "health_status": "OK" if self.current_metrics.execution_latency_ms < 2000 else "DEGRADED",
            "ingestion_lag_ms": round(self.current_metrics.ingestion_lag_ms, ndigits=2),
            "execution_latency_ms": round(self.current_metrics.execution_latency_ms, ndigits=2),
            "active_strategies": self.current_metrics.active_strategies,
            "api_errors_1h": self.current_metrics.api_errors_1h,
            "last_updated": self.current_metrics.timestamp.isoformat()
        }

# Global Instance
monitoring_service = MonitoringService()
