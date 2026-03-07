#!/usr/bin/env python3
"""Pytest verification checks for applied reliability fixes."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


def test_core_imports():
    """Core modules should import successfully in minimal environments."""
    pytest.importorskip("pytz")
    from crypto_agent.core.scheduler import setup_scheduler  # noqa: F401
    from crypto_agent.data.cache import price_cache  # noqa: F401
    from crypto_agent.data.prices import get_price  # noqa: F401


def test_telegram_runtime_imports_when_dependency_available():
    """Telegram runtime imports should work when telegram dependency is installed."""
    pytest.importorskip("telegram")
    from telegram.ext import ConversationHandler  # noqa: F401
    from crypto_agent.main import start_bot  # noqa: F401


def test_startup_policy_wired_in_main():
    """Main runtime should enforce startup policy after V2 initialization."""
    content = Path("crypto_agent/main.py").read_text()
    assert "from crypto_agent.core.startup_policy import enforce_startup_fail_policy" in content
    assert "enforce_startup_fail_policy(config.IS_PRODUCTION, v2_ready)" in content


def test_database(tmp_path, monkeypatch):
    """Database init should create orchestrator/workflow tables."""
    monkeypatch.chdir(tmp_path)

    from crypto_agent.storage import database

    monkeypatch.setattr(database, "DB_FILE", str(tmp_path / "crypto_agent.db"))
    asyncio.run(database.init_db())

    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_runs'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_regimes'")
        assert cursor.fetchone() is not None
    finally:
        conn.close()


def test_cache():
    """Cache set/get/stats/clear should function."""
    from crypto_agent.data.cache import price_cache

    price_cache.set("test_key", {"price": 100, "change": 5})
    result = price_cache.get("test_key")
    assert result is not None
    assert result["price"] == 100

    stats = price_cache.get_stats()
    assert "hits" in stats
    assert "misses" in stats

    price_cache.clear()


def test_scheduler_config():
    """Scheduler offsets should remain configured."""
    content = Path("crypto_agent/core/scheduler.py").read_text()
    assert "seconds=30" in content
    assert "hour=7, minute=55" in content


def test_workflow_db_delegation():
    """workflow_db should delegate table ownership to storage.database."""
    content = Path("crypto_agent/storage/workflow_db.py").read_text()
    assert "delegates to database.py" in content
    assert "CREATE TABLE IF NOT EXISTS scanner_settings" not in content
