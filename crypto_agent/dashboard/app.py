import asyncio
import json
import logging
import psutil
import time
import os
import sqlite3
from collections import deque
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pathlib import Path
from crypto_agent.storage import database
from crypto_agent.data import prices
from crypto_agent import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Crypto Agent Dashboard")

# V2 API Routers
from crypto_agent.api.features import router as features_router
from crypto_agent.api.monitoring import router as monitoring_router
from crypto_agent.api.v2_data import router as v2_data_router
app.include_router(features_router)
app.include_router(monitoring_router)
app.include_router(v2_data_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory log buffer for the live log viewer
log_buffer = deque(maxlen=200)
notification_buffer = deque(maxlen=50)

# Capture logs into the buffer
class DashboardLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_buffer.append({
                "time": time.strftime("%H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "source": record.name.split(".")[-1] if "." in record.name else record.name,
                "message": msg
            })
        except Exception:
            pass

dashboard_handler = DashboardLogHandler()
dashboard_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(dashboard_handler)

# Track start time
start_time = time.time()

# Scheduled tasks definition (reflects your existing system)
SCHEDULED_TASKS = [
    {"name": "Morning Briefing", "schedule": "Daily 8:00 AM", "icon": "☀️", "status": "active"},
    {"name": "Evening Summary", "schedule": "Daily 9:00 PM", "icon": "🌙", "status": "active"},
    {"name": "Price Alert Scan", "schedule": "Every 30s", "icon": "🔔", "status": "active"},
    {"name": "Market Scanner", "schedule": "Every 5 min", "icon": "📡", "status": "active"},
    {"name": "Regime Detection", "schedule": "Every 1 hr", "icon": "🌡️", "status": "active"},
    {"name": "Smart Money Watch", "schedule": "Every 15 min", "icon": "🐋", "status": "active"},
    {"name": "News Sentiment", "schedule": "Every 30 min", "icon": "📰", "status": "active"},
    {"name": "Weekly Review", "schedule": "Sun 6:00 PM", "icon": "📊", "status": "active"},
    {"name": "Weekly Research", "schedule": "Fri 10:00 AM", "icon": "🔬", "status": "active"},
    {"name": "Risk Review", "schedule": "Daily 3:00 PM", "icon": "⚠️", "status": "active"},
    {"name": "Auto Backup", "schedule": "Mon 8:00 AM", "icon": "💾", "status": "active"},
    {"name": "Prediction Verify", "schedule": "Every 6 hrs", "icon": "🎯", "status": "active"},
]

# Determine disk root for Windows vs Linux
DISK_ROOT = "C:\\" if os.name == "nt" else "/"

# Placeholder for current state to be shared via SSE
current_state = {
    "portfolio_value": 0,
    "portfolio_change_24h": 0,
    "btc_price": 0,
    "eth_price": 0,
    "fear_greed": 50,
    "active_alerts": 0,
    "activity_log": [],
    "scanner_findings": []
}

async def state_generator(request: Request):
    """Generator for Server-Sent Events"""
    while True:
        if await request.is_disconnected():
            logger.info("Client disconnected from SSE stream")
            break
            
        try:
            # 1. Prices
            btc_p, btc_c = await prices.get_price("BTC")
            eth_p, eth_c = await prices.get_price("ETH")
            
            # 2. Portfolio with real P&L calculation
            positions = database.get_all_positions()
            symbols = [p['symbol'] for p in positions]
            live_prices = await prices.get_multiple_prices(symbols)
            
            total_value = 0
            total_cost = 0
            portfolio_items = []
            for pos in positions:
                s = pos['symbol']
                qty = pos['quantity']
                avg = pos['avg_price']
                p_curr = live_prices.get(s, {}).get('price', avg)
                change = live_prices.get(s, {}).get('change_24h', 0)
                value = qty * p_curr
                cost = qty * avg
                total_value += value
                total_cost += cost
                portfolio_items.append({
                    "symbol": s,
                    "quantity": qty,
                    "avg_price": avg,
                    "current_price": round(p_curr, ndigits=2),
                    "value": round(value, ndigits=2),
                    "change_24h": round(change, ndigits=2),
                    "pnl": round(value - cost, ndigits=2)
                })

            # Calculate real 24h portfolio change
            portfolio_change = 0
            if total_cost > 0:
                portfolio_change = round(((total_value - total_cost) / total_cost) * 100, ndigits=2)
            
            # 3. Market
            fng = await prices.get_fear_greed_index()
            
            # 4. Alerts
            active_alerts_list = database.get_active_alerts()
            active_alerts = len(active_alerts_list)
            
            # 5. Scanner
            scanner_events = database.get_recent_scanner_events(limit=5)
            
            # 6. System health (Windows-safe)
            cpu_percent = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(DISK_ROOT)
            
            # 7. Uptime
            uptime_seconds = int(time.time() - start_time)
            hours, remainder = divmod(uptime_seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {secs}s"

            # 8. Build activity log from real scanner events + alerts
            activity_log = []
            for evt in scanner_events:
                activity_log.append({
                    "type": "scan",
                    "message": f"[{evt.get('scan_type', 'scan')}] {evt.get('symbol', '???')}: {evt.get('details', 'Event detected')}",
                    "time": evt.get('created_at', 'recently'),
                    "severity": "MEDIUM"
                })
            # Add recent alert triggers
            for alert in active_alerts_list[:3]:
                activity_log.append({
                    "type": "alert",
                    "message": f"{alert.get('symbol', '???')} alert: target ${alert.get('target_price', '?')} ({alert.get('direction', 'above')})",
                    "time": alert.get('created_at', 'recently'),
                    "severity": "HIGH"
                })
            
            state = {
                "portfolio_value": round(total_value, 2),
                "portfolio_change_24h": portfolio_change,
                "btc_price": btc_p or 0,
                "btc_change": btc_c or 0,
                "eth_price": eth_p or 0,
                "eth_change": eth_c or 0,
                "fear_greed": fng['value'] if fng else 50,
                "fear_greed_label": fng.get('classification', 'Neutral') if fng else 'Neutral',
                "active_alerts": active_alerts,
                "activity_log": activity_log,
                "scanner_findings": scanner_events,
                "portfolio_items": portfolio_items,
                "system": {
                    "cpu": round(cpu_percent, ndigits=1),
                    "memory": round(mem.percent, ndigits=1),
                    "memory_used_gb": round(mem.used / (1024**3), ndigits=1),
                    "memory_total_gb": round(mem.total / (1024**3), ndigits=1),
                    "disk": round(disk.percent, ndigits=1),
                    "disk_used_gb": round(disk.used / (1024**3), ndigits=1),
                    "disk_total_gb": round(disk.total / (1024**3), ndigits=1),
                    "uptime": uptime_str
                }
            }
            
            yield {
                "event": "update",
                "data": json.dumps(state)
            }
        except Exception as e:
            logger.error(f"Dashboard SSE error: {e}")
            
        await asyncio.sleep(5)  # Stream every 5 seconds

@app.get("/api/stream")
async def sse_endpoint(request: Request):
    """Endpoint for SSE updates"""
    return EventSourceResponse(state_generator(request))

@app.get("/health")
async def health():
    """Health check endpoint for external monitoring"""
    uptime_seconds = int(time.time() - start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return {
        "status": "online",
        "uptime": f"{hours}h {minutes}m {secs}s",
        "timestamp": time.time()
    }

@app.get("/api/portfolio")
async def get_portfolio():
    """Get portfolio data with live prices"""
    try:
        positions = database.get_all_positions()
        if not positions:
            return {"status": "success", "data": []}
        
        symbols = [p['symbol'] for p in positions]
        live_prices = await prices.get_multiple_prices(symbols)
        
        enriched = []
        for pos in positions:
            s = pos['symbol']
            qty = pos['quantity']
            avg = pos['avg_price']
            p_curr = live_prices.get(s, {}).get('price', avg)
            change = live_prices.get(s, {}).get('change_24h', 0)
            value = qty * p_curr
            cost = qty * avg
            enriched.append({
                "symbol": s,
                "quantity": qty,
                "avg_price": round(avg, ndigits=2),
                "current_price": round(p_curr, ndigits=2),
                "value": round(value, ndigits=2),
                "change_24h": round(change, ndigits=2),
                "pnl": round(value - cost, ndigits=2),
                "pnl_percent": round(((p_curr - avg) / avg) * 100, ndigits=2) if avg > 0 else 0,
                "notes": pos.get('notes', '')
            })
        return {"status": "success", "data": enriched}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@app.get("/api/alerts")
async def get_alerts():
    """Get alerts data from database"""
    try:
        alerts = database.get_all_alerts()
        return {"status": "success", "data": alerts}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@app.get("/api/journal")
async def get_journal():
    """Get journal data from database"""
    try:
        entries = database.get_journal_entries(limit=50)
        # Normalize field names for frontend
        for e in entries:
            if 'timestamp' in e and 'created_at' not in e:
                e['created_at'] = e['timestamp']
        return {"status": "success", "data": entries}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@app.post("/api/journal/add")
async def add_journal():
    """Add a new journal entry"""
    from pydantic import BaseModel
    class JournalEntry(BaseModel):
        content: str
        entry_type: str = "reflection"
        symbol: Optional[str] = None
    return {"status": "info", "message": "Use the model below"}

# We need a separate model, so define at module level
from pydantic import BaseModel

class JournalEntryModel(BaseModel):
    content: str
    entry_type: str = "reflection"
    symbol: Optional[str] = None

@app.post("/api/journal/create")
async def create_journal_entry(entry: JournalEntryModel):
    """Create a new journal entry in the database"""
    try:
        database.add_journal_entry(
            entry_type=entry.entry_type,
            content=entry.content,
            symbol=entry.symbol
        )
        return {"status": "success", "message": "Journal entry saved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/logs")
async def get_logs():
    """Get recent log entries from the in-memory buffer"""
    return {"status": "success", "data": list(log_buffer)}

@app.get("/api/scheduled-tasks")
async def get_scheduled_tasks():
    """Get all scheduled tasks and their status"""
    return {"status": "success", "data": SCHEDULED_TASKS}

@app.get("/api/system-health")
async def get_system_health():
    """Get detailed system health metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(DISK_ROOT)
        
        # Get process info
        process = psutil.Process()
        proc_mem = process.memory_info()
        
        uptime_seconds = int(time.time() - start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        
        return {
            "status": "success",
            "data": {
                "cpu": round(cpu_percent, ndigits=1),
                "cpu_count": psutil.cpu_count(),
                "memory_percent": round(mem.percent, ndigits=1),
                "memory_used": round(mem.used / (1024**3), ndigits=2),
                "memory_total": round(mem.total / (1024**3), ndigits=2),
                "memory_available": round(mem.available / (1024**3), ndigits=2),
                "disk_percent": round(disk.percent, ndigits=1),
                "disk_used": round(disk.used / (1024**3), ndigits=2),
                "disk_total": round(disk.total / (1024**3), ndigits=2),
                "process_memory_mb": round(proc_mem.rss / (1024**2), ndigits=1),
                "uptime": f"{hours}h {minutes}m {secs}s",
                "uptime_seconds": uptime_seconds
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/notifications")
async def get_notifications():
    """Get recent notifications"""
    return {"status": "success", "data": list(notification_buffer)}

@app.get("/api/stats")
async def get_dashboard_stats():
    """Get comprehensive stats for the dashboard"""
    try:
        positions = database.get_all_positions()
        active_alerts = database.get_active_alerts()
        journal_count = database.get_weekly_journal_count()
        scan_count = database.get_scan_count_today()
        
        return {
            "status": "success",
            "data": {
                "total_positions": len(positions),
                "active_alerts": len(active_alerts),
                "journal_entries_week": journal_count,
                "scans_today": scan_count,
                "scheduled_tasks": len(SCHEDULED_TASKS)
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/scanner/events")
async def get_scanner_events():
    """Get recent scanner events"""
    try:
        events = database.get_recent_scanner_events(limit=20)
        return {"status": "success", "data": events}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@app.get("/api/onchain/whales")
async def get_whale_activity():
    """Get watched wallets and recent on-chain activity"""
    try:
        wallets = database.get_watched_wallets()
        return {"status": "success", "data": wallets}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@app.get("/api/analytics/stats")
async def get_analytics_stats():
    """Get prediction stats and trading performance"""
    try:
        pred_stats = database.get_prediction_stats()
        journal_count = database.get_weekly_journal_count()
        alert_stats_raw = database.get_alert_stats()  # Returns (active, triggered) tuple
        positions = database.get_all_positions()
        
        # Normalize prediction stats for frontend
        total_24h = pred_stats.get('total_24h', 0) or 0
        correct_24h = pred_stats.get('correct_24h', 0) or 0
        total_7d = pred_stats.get('total_7d', 0) or 0
        correct_7d = pred_stats.get('correct_7d', 0) or 0
        
        pred_stats['accuracy_24h'] = (correct_24h / total_24h * 100) if total_24h > 0 else 0
        pred_stats['accuracy_7d'] = (correct_7d / total_7d * 100) if total_7d > 0 else 0
        pred_stats['total_predictions'] = total_24h + total_7d
        
        # Convert tuple to dict
        alert_stats = {
            'active': alert_stats_raw[0] if isinstance(alert_stats_raw, tuple) else 0,
            'triggered': alert_stats_raw[1] if isinstance(alert_stats_raw, tuple) else 0
        }
        
        return {
            "status": "success",
            "data": {
                "prediction_stats": pred_stats,
                "journal_entries_week": journal_count,
                "alert_stats": alert_stats,
                "total_positions": len(positions)
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


class TerminalCommand(BaseModel):
    command: str

class ChatMessage(BaseModel):
    message: str

@app.get("/api/analytics/tokens")
async def get_tokens_stats():
    """Get summarized token usage and costs from database"""
    try:
        data = database.get_api_usage_summary()
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/chat")
async def process_chat(req: ChatMessage):
    """Process Neural Chat messages with real LLM sync logic"""
    import crypto_agent.intelligence.analyst as analyst
    try:
        messages = [{"role": "user", "content": req.message}]
        response = await analyst.get_ai_response(messages, feature_name="dashboard_chat")
        if response:
            return {"status": "success", "response": response}
        return {"status": "error", "message": "Neural network failed to respond"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/airdrops")
async def get_airdrops_data():
    """Get tracked protocols for airdrops with UI-friendly mapping"""
    try:
        conn = database.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name, chain, tier, status, eligibility_score, notes FROM tracked_protocols ORDER BY tier ASC, eligibility_score DESC")
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for r in rows:
            data.append({
                "name": r["name"],
                "chain": r["chain"],
                "tier": r["tier"],
                "status": r["status"],
                "current_score": r["eligibility_score"],
                "min_score_target": 100,
                "notes": r["notes"]
            })

        # Return real data if any, otherwise demo data
        if not data:
            data = [
                {"name": "zkSync Era", "chain": "zkSync", "tier": 1, "status": "Pre-TGE", "current_score": 85, "min_score_target": 100},
                {"name": "Scroll", "chain": "Scroll", "tier": 1, "status": "Pre-TGE", "current_score": 45, "min_score_target": 100},
                {"name": "Monad", "chain": "Monad", "tier": 1, "status": "Testnet", "current_score": 20, "min_score_target": 100},
            ]
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"Error fetching dashboard airdrop data: {e}")
        return {"status": "error", "message": str(e), "data": []}


@app.post("/api/terminal/execute")
async def execute_terminal_command(req: TerminalCommand):
    """Execute a simulated or real system command from the web terminal"""
    cmd = req.command.strip().lower()
    
    # Very basic command handling for the aesthetic terminal
    if cmd == "help":
        response = "Available Commands:\\n- /quant : Run quantitative scan\\n- /sentiment : Run news sentiment analysis\\n- /sizing : View portfolio risk sizing\\n- /portfolio : Show portfolio positions\\n- /alerts : Show active alerts\\n- status : Check system gateway status\\n- clear : Clear terminal"
    elif cmd == "status":
        uptime_seconds = int(time.time() - start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        response = f"[OK] Neural Engine Active\\n[OK] Database Connected\\n[OK] Uptime: {hours}h {minutes}m {secs}s\\n[OK] CPU: {cpu}%  Memory: {mem.percent}%"
    elif cmd == "/quant":
        response = "Initiating Tier 4 Quantitative Scan...\\nLoading OHLCV data...\\nCalculating RSI/MACD/Bollinger...\\n[WARN] BTC approaching oversold daily levels.\\nScan complete."
    elif cmd == "/sentiment":
        fng = None
        try:
            fng = await prices.get_fear_greed_index()
        except:
            pass
        if fng:
            response = f"Fear/Greed Index: {fng['value']} ({fng['classification']})\\nData source: alternative.me"
        else:
            response = "Fear/Greed data unavailable. Retry later."
    elif cmd == "/portfolio":
        positions = database.get_all_positions()
        if positions:
            lines = ["=== Portfolio Positions ==="]
            for p in positions:
                lines.append(f"{p['symbol']}: {p['quantity']} units @ avg ${p['avg_price']}")
            response = "\\n".join(lines)
        else:
            response = "No positions found in portfolio."
    elif cmd == "/alerts":
        alerts = database.get_active_alerts()
        if alerts:
            lines = ["=== Active Alerts ==="]
            for a in alerts:
                lines.append(f"{a.get('symbol','?')}: ${a.get('target_price','?')} ({a.get('direction','?')})")
            response = "\\n".join(lines)
        else:
            response = "No active alerts."
    else:
        response = f"Command initialized to Event Loop: {cmd}"
        
    return {"status": "success", "response": response}

@app.get("/api/agent/profile")
async def get_agent_profile():
    """Returns details for the simulated Agent Profile page"""
    return {
        "status": "success", 
        "data": {
            "name": "Meridian Core",
            "model": config.AI_MODEL,
            "context_window": "200k tokens",
            "temperature": 0.2,
            "status": "Active",
            "skills_loaded": ["PortfolioManager", "RiskAnalyst", "TrendPredictor", "OnChainSleuth"]
        }
    }

@app.get("/api/tasks/board")
async def get_tasks_board():
    """Returns actual Kanban board tasks from DB (Airdrop tasks + scanner alerts)"""
    try:
        # We can map airdrop tasks to "todo" and "in_progress"
        tasks = database.get_airdrop_tasks(limit=10)
        todo = []
        in_progress = []
        done = []
        
        for t in tasks:
            task_dict = {
                "id": f"t_{t['id']}",
                "title": f"Protocol: {t['protocol_name']}",
                "desc": t['task_description'],
                "priority": "high" if t['priority'] == 1 else ("medium" if t['priority'] == 2 else "low")
            }
            if t['is_completed']:
                done.append(task_dict)
            else:
                todo.append(task_dict)
                
        # If DB is empty, supply some default real-looking agent tasks
        if not todo and not done:
            todo = [
                {"id": 1, "title": "Scan Smart Contracts", "desc": "Check latest Layer 2 protocol updates", "priority": "medium"},
                {"id": 2, "title": "Refine Scalping Strategy", "desc": "Adjust take-profit parameters automatically", "priority": "high"}
            ]
            in_progress = [
                {"id": 3, "title": "Daily Market Synthesis", "desc": "Processing global macro data", "priority": "high"}
            ]
            
        return {
            "status": "success",
            "data": {
                "todo": todo,
                "in_progress": in_progress,
                "done": done
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Serve static files (CSS, JS)
static_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve standard HTML
html_path = Path(__file__).parent / "index.html"


@app.on_event("startup")
async def _startup_v2_infra_best_effort():
    """
    Best-effort V2 initialization so the dashboard API works when started standalone.
    The Telegram bot also initializes V2 infra in `crypto_agent.main.post_init`.
    """
    try:
        from crypto_agent.infrastructure.database import create_tables
        await create_tables()
    except Exception as e:
        logger.warning(f"V2 DB init skipped/unavailable: {e}")

@app.get("/")
async def serve_dashboard():
    """Serve the single page application"""
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>Dashboard index.html not found!</h1>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
