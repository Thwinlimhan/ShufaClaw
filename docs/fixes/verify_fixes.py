#!/usr/bin/env python3
"""
Quick verification script to test all applied fixes.
Run this before deployment to ensure everything works.
"""

import sys
import traceback

def test_imports():
    """Test all critical imports."""
    print("🧪 Testing imports...")
    
    try:
        from telegram.ext import ConversationHandler
        print("  ✅ ConversationHandler import OK")
    except ImportError as e:
        print(f"  ❌ ConversationHandler import FAILED: {e}")
        return False
    
    try:
        from crypto_agent.main import start_bot
        print("  ✅ main.py imports OK")
    except ImportError as e:
        print(f"  ❌ main.py imports FAILED: {e}")
        return False
    
    try:
        from crypto_agent.core.scheduler import setup_scheduler
        print("  ✅ scheduler.py imports OK")
    except ImportError as e:
        print(f"  ❌ scheduler.py imports FAILED: {e}")
        return False
    
    try:
        from crypto_agent.data.cache import price_cache
        print("  ✅ cache.py imports OK")
    except ImportError as e:
        print(f"  ❌ cache.py imports FAILED: {e}")
        return False
    
    try:
        from crypto_agent.data.prices import get_price
        print("  ✅ prices.py imports OK")
    except ImportError as e:
        print(f"  ❌ prices.py imports FAILED: {e}")
        return False
    
    return True

def test_database():
    """Test database initialization."""
    print("\n🧪 Testing database...")
    
    try:
        from crypto_agent.storage import database
        
        # Initialize database
        database.init_db()
        print("  ✅ Database initialized")
        
        # Check if workflow tables exist
        conn = database.get_connection()
        cursor = conn.cursor()
        
        # Check for workflow_runs table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_runs'")
        if cursor.fetchone():
            print("  ✅ Workflow tables created")
        else:
            print("  ❌ Workflow tables NOT created")
            conn.close()
            return False
        
        # Check for market_regimes table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_regimes'")
        if cursor.fetchone():
            print("  ✅ Orchestrator tables created")
        else:
            print("  ❌ Orchestrator tables NOT created")
            conn.close()
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database test FAILED: {e}")
        traceback.print_exc()
        return False

def test_cache():
    """Test cache functionality."""
    print("\n🧪 Testing cache...")
    
    try:
        from crypto_agent.data.cache import price_cache
        
        # Test set and get
        price_cache.set("test_key", {"price": 100, "change": 5})
        result = price_cache.get("test_key")
        
        if result and result["price"] == 100:
            print("  ✅ Cache set/get works")
        else:
            print("  ❌ Cache set/get FAILED")
            return False
        
        # Test stats
        stats = price_cache.get_stats()
        if "hits" in stats and "misses" in stats:
            print(f"  ✅ Cache stats work (hits: {stats['hits']}, misses: {stats['misses']})")
        else:
            print("  ❌ Cache stats FAILED")
            return False
        
        # Clear cache
        price_cache.clear()
        print("  ✅ Cache clear works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Cache test FAILED: {e}")
        traceback.print_exc()
        return False

def test_scheduler_config():
    """Test scheduler configuration."""
    print("\n🧪 Testing scheduler configuration...")
    
    try:
        # Just check if the file has correct structure
        with open("crypto_agent/core/scheduler.py", "r") as f:
            content = f.read()
        
        # Check for offset in wallet watcher
        if "seconds=30" in content:
            print("  ✅ Wallet watcher offset configured")
        else:
            print("  ⚠️  Wallet watcher offset NOT found (check manually)")
        
        # Check for backup time change
        if "hour=7, minute=55" in content:
            print("  ✅ Backup time offset configured")
        else:
            print("  ⚠️  Backup time offset NOT found (check manually)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Scheduler config test FAILED: {e}")
        return False

def test_workflow_db_delegation():
    """Test that workflow_db delegates to database.py."""
    print("\n🧪 Testing workflow_db delegation...")
    
    try:
        with open("crypto_agent/storage/workflow_db.py", "r") as f:
            content = f.read()
        
        # Check for delegation comments
        if "delegates to database.py" in content:
            print("  ✅ Workflow_db delegation implemented")
        else:
            print("  ⚠️  Delegation comments not found (check manually)")
        
        # Check that duplicate table creation is removed
        if "CREATE TABLE IF NOT EXISTS scanner_settings" in content:
            print("  ❌ Duplicate scanner_settings table still exists!")
            return False
        else:
            print("  ✅ Duplicate table definitions removed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Workflow_db delegation test FAILED: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("🔍 VERIFYING ALL FIXES")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Imports", test_imports()))
    results.append(("Database", test_database()))
    results.append(("Cache", test_cache()))
    results.append(("Scheduler Config", test_scheduler_config()))
    results.append(("Workflow DB Delegation", test_workflow_db_delegation()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! System is ready for deployment.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED! Review errors above before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
