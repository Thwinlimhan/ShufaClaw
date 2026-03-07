"""
ShufaClaw V2 — Execution Engine

Reliably routes orders to the exchange and manages the Order Lifecycle.
Calculates the delta between current holdings and the TargetPortfolio from the Strategy layer.
Persists orders to TimescaleDB and publishes fills to Kafka execution.fills.
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from crypto_agent.schemas.trading import Order, OrderStatus, ExecutionAlgorithm, TargetPortfolio, Position
from crypto_agent.data import prices
from crypto_agent.trading.risk_manager import risk_manager

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """Manages the lifecycle of exchange orders."""
    
    def __init__(self):
        self.active_orders: Dict[str, Order] = {}
        # In a fully deployed setup, this wraps the ccxt.pro authenticated exchange instance
        self.paper_mode = True 
        
    async def process_target_portfolio(self, current_positions: List[Position], target: TargetPortfolio, nav: float):
        """
        Calculates the delta between current and target portfolio, 
        and dispatches necessary orders to reconcile the difference.
        
        This also feeds the target portfolio through the Risk Manager Gatekeeper first.
        """
        # 1. GATEKEEPER CHECK: Veto or modify the portfolio if it violently breaches limits
        safe_target = risk_manager.vet_target_portfolio(target, nav)
        
        logger.info("⚡ Executing Target Portfolio Rebalance...")
        
        # Build symbol maps
        curr_map = {p.symbol: p for p in current_positions}
        tgt_map = {p.symbol: p for p in safe_target.positions}
        
        orders_to_create = []
        
        # 2. Reconcile existing positions (Close or Reduce)
        for sym, curr_pos in curr_map.items():
            if sym not in tgt_map:
                # Target does not hold this asset. Close completely.
                logger.info(f"Target indicates Closing position completely: {sym}")
                orders_to_create.append(
                    self._build_order(sym, "sell" if curr_pos.side == "long" else "buy", curr_pos.size)
                )
            else:
                tgt_pos = tgt_map[sym]
                if tgt_pos.size < curr_pos.size:
                    # Target holds less than we do. Reduce position.
                    diff = curr_pos.size - tgt_pos.size
                    orders_to_create.append(
                        self._build_order(sym, "sell" if curr_pos.side == "long" else "buy", diff)
                    )
                    
        # 3. Open or Add to positions
        for sym, tgt_pos in tgt_map.items():
            if sym not in curr_map:
                # We don't hold this asset yet
                logger.info(f"Target indicates Opening position: {sym}")
                orders_to_create.append(
                    self._build_order(sym, "buy" if tgt_pos.side == "long" else "sell", tgt_pos.size)
                )
            else:
                curr_pos = curr_map[sym]
                if tgt_pos.size > curr_pos.size:
                    # We hold less than target wants
                    diff = tgt_pos.size - curr_pos.size
                    orders_to_create.append(
                        self._build_order(sym, "buy" if tgt_pos.side == "long" else "sell", diff)
                    )
                    
        if not orders_to_create:
            logger.info("No delta found. Portfolio matches target. No action taken.")
            return []
            
        # 4. Dispatch the Orders concurrently to the Exchange wrapper
        tasks = [self._execute_order(o) for o in orders_to_create]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def _build_order(self, symbol: str, side: str, qty: float) -> Order:
        """Helper to scaffold the Pydantic Order structure"""
        return Order(
            symbol=symbol,
            side=side,
            quantity=qty,
            order_type="market",
            is_paper=self.paper_mode
        )
        
    async def _execute_order(self, order: Order) -> Order:
        """
        Lifecycle manager for an individual order.
        Simulates network latency and slippage if in Paper Mode.
        """
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.utcnow()
        logger.info(f"Submitting Order: {order.side.upper()} {order.quantity} {order.symbol}")

        # Persist order to TimescaleDB
        await self._persist_order(order)

        # Capture Arrival Price (The price we expected the moment we hit send)
        # This is strictly tracked to measure execution quality and slippage later.
        try:
            price_tuple = await prices.get_price(order.symbol.replace("USDT", ""))
            arrival_p = price_tuple[0] if price_tuple else 0.0
            order.arrival_price = arrival_p
        except Exception:
            arrival_p = 0.0
        
        if self.paper_mode:
            # Simulate a fill with 0.1% network slippage against realistic prices
            await asyncio.sleep(0.5) # Time spent transmitting to exchange
            fill_p = arrival_p * 1.001 if order.side == "buy" else arrival_p * 0.999
            
            order.avg_fill_price = fill_p
            order.filled_quantity = order.quantity
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.utcnow()
            
            if arrival_p > 0:
                diff = abs(fill_p - arrival_p)
                order.slippage_bps = (diff / arrival_p) * 10000
                
            logger.info(f"✅ PAPER Execution Filled: {order.side.upper()} {order.symbol} @ ${fill_p:.2f} (Slippage: {order.slippage_bps:.1f} bps)")
            
        else:
            # TODO: Integrate CCXT Auth payload here: `exchange.create_order(symbol, type, side, qty)`
            # V2 architecture listens on Kafka topic `execution.fills` to async update statuses
            pass
            
        # Persist status update and publish fill to Kafka
        await self._update_order(order)
        if order.status == OrderStatus.FILLED:
            from crypto_agent.infrastructure.event_bus import event_bus, Topics
            payload = {
                "order_id": str(order.id),
                "symbol": order.symbol,
                "side": order.side,
                "filled_quantity": order.filled_quantity,
                "avg_fill_price": order.avg_fill_price,
                "slippage_bps": order.slippage_bps,
                "is_paper": order.is_paper,
            }
            await event_bus.publish(Topics.EXECUTION_FILLS, payload, key=order.symbol)

        # Record Telemetry
        from crypto_agent.trading.monitoring import monitoring_service
        execution_time = (datetime.utcnow() - order.submitted_at).total_seconds()
        monitoring_service.record_execution_time(execution_time)
            
        return order

    async def _persist_order(self, order: Order) -> None:
        """Insert order into TimescaleDB."""
        try:
            from crypto_agent.infrastructure.database import execute
            await execute(
                """
                INSERT INTO orders (id, symbol, side, order_type, quantity, price, algorithm, status,
                    filled_quantity, avg_fill_price, total_fees, arrival_price, slippage_bps, strategy_id,
                    exchange, retry_count, error_message, is_paper, created_at, submitted_at, filled_at, cancelled_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
                """,
                order.id, order.symbol, order.side, order.order_type, order.quantity, order.price,
                order.algorithm.value if hasattr(order.algorithm, "value") else str(order.algorithm),
                order.status.value, order.filled_quantity, order.avg_fill_price, order.total_fees,
                order.arrival_price, order.slippage_bps, order.strategy_id, order.exchange,
                order.retry_count, order.error_message, order.is_paper,
                order.created_at, order.submitted_at, order.filled_at, order.cancelled_at,
            )
        except Exception as e:
            logger.warning(f"Order persist failed (DB may be unavailable): {e}")

    async def _update_order(self, order: Order) -> None:
        """Update order status in TimescaleDB."""
        try:
            from crypto_agent.infrastructure.database import execute
            await execute(
                """
                UPDATE orders SET status = $1, filled_quantity = $2, avg_fill_price = $3,
                    slippage_bps = $4, filled_at = $5
                WHERE id = $6
                """,
                order.status.value, order.filled_quantity, order.avg_fill_price,
                order.slippage_bps, order.filled_at, order.id,
            )
        except Exception as e:
            logger.warning(f"Order update failed: {e}")

# Global Singleton
execution_engine = ExecutionEngine()
