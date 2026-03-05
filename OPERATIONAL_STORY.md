# ShufaClaw Operational Reliability & Long-Running Strategy

This document outlines the architecture and strategies used to ensure ShufaClaw remains reliable, resilient, and performant over long periods of autonomous operation.

## 1. Resilience & Network Hardware
- **Urllib for Windows**: We use `urllib` instead of `aiohttp` for core data fetching to bypass common Windows-specific DNS resolution issues.
- **Circuit Breakers**: Every external API (Binance, CoinGecko, Etherscan) is protected by a `CircuitBreaker`. If an API fails 3 times, the circuit opens for 60 seconds, preventing the system from wasting resources on a failing service.
- **Token Bucket Rate Limiting**: Outgoing requests are metered using a token bucket algorithm to ensure we stay within API free-tier limits (e.g., CoinGecko's 30/min limit).

## 2. Failure Modes & Fallbacks
- **Stale Data Fallback**: If a price fetch fails, the system automatically falls back to the last known price stored in the SQLite `price_cache` table (allowing data up to 60 minutes old).
- **Graceful Degradation**: If the AI engine (OpenRouter/Claude) is down, the bot provides a "Temporarily Unavailable" message instead of crashing, allowing non-AI commands (/portfolio, /alerts) to keep working.
- **Process Supervisor**: The `main.py` entry point spawns Dashboard and Discord as sub-processes. If one crashes, the others continue running.

## 3. Workflow Reliability
- **Timeout Protection**: Every workflow step has a strict 5-minute timeout. The entire workflow has a 30-minute global timeout.
- **State Persistence**: Workflow runs are logged to the database, allowing us to audit why a scheduled task (like the Morning Briefing) might have failed.
- **Linear Execution**: Steps are executed sequentially. If step 2 fails, step 3 is aborted to prevent acting on partial or corrupt data.

## 4. Resource Management
- **SQLite Database**: Uses `WAL` (Write-Ahead Logging) mode to handle concurrent reads from the Bot, Dashboard, and Discord processes without locking.
- **Memory Management**: The `price_cache` and `message_history` are pruned regularly to prevent memory bloat.
- **Connection Pooling**: Database connections are managed to ensure we don't exceed file handle limits on long-running VPS deployments.

## 5. Monitoring
- **Health Dashboard**: Accessible via `/health` on Telegram or the Web Dashboard.
- **Metrics Tracking**: Real-time tracking of message volume, error rates, and API success percentages.
- **Audit Logs**: Every security-sensitive action (2FA toggle, rate limit change) is logged for review.
- **Live Logs**: Streamed directly to the Web Dashboard for real-time debugging without terminal access.
