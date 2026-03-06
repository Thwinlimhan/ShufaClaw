import os
import sys
import asyncio
import importlib
from datetime import datetime

# Set encoding for Windows console
os.environ["PYTHONIOENCODING"] = "utf-8"

# Global test results
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def test_result(name, passed, message=""):
    """Record test result"""
    if passed:
        test_results['passed'].append(name)
        print(f"[PASSED] {name}")
    else:
        test_results['failed'].append((name, message))
        print(f"[FAILED] {name}: {message}")

def test_warning(name, message):
    """Record test warning"""
    test_results['warnings'].append((name, message))
    print(f"[WARNING] {name}: {message}")

# ============================================================
# SECTION 1: IMPORT TESTS
# ============================================================

def test_imports():
    print("\n" + "="*60)
    print("SECTION 1: IMPORT TESTS")
    print("="*60 + "\n")
    
    modules = [
        # Core
        ('crypto_agent.core.agent', 'Agent core'),
        ('crypto_agent.core.orchestrator', 'Orchestrator'),
        ('crypto_agent.core.workflow_engine', 'Workflow engine'),
        ('crypto_agent.core.task_queue', 'Task queue'),
        
        # Data
        ('crypto_agent.data.prices', 'Market data'),
        ('crypto_agent.data.technical', 'Technical analysis'),
        ('crypto_agent.data.news', 'News service'),
        ('crypto_agent.data.onchain', 'On-chain data'),
        ('crypto_agent.data.cache', 'Cache system'),
        
        # Intelligence
        ('crypto_agent.intelligence.advisor', 'Strategy advisor'),
        ('crypto_agent.intelligence.research_agent', 'Research agent'),
        ('crypto_agent.intelligence.portfolio_optimizer', 'Portfolio optimizer'),
        ('crypto_agent.intelligence.debate_system', 'Debate system'),
        ('crypto_agent.intelligence.event_predictor', 'Event predictor'),
        ('crypto_agent.intelligence.macro_monitor', 'Macro monitor'),
        ('crypto_agent.intelligence.performance_attribution', 'Performance attribution'),
        ('crypto_agent.intelligence.trade_proposer', 'Trade proposer'),
        ('crypto_agent.intelligence.intelligence_hub', 'Intelligence hub'),
        
        # Storage
        ('crypto_agent.storage.database', 'Database'),
        ('crypto_agent.storage.backup', 'Backup service'),
        ('crypto_agent.storage.workflow_db', 'Workflow DB'),
        ('crypto_agent.storage.event_db', 'Event DB'),
        
        # Bot
        ('crypto_agent.bot.handlers', 'Bot handlers'),
        ('crypto_agent.bot.keyboards', 'Keyboards'),
        
        # Security
        ('crypto_agent.security.security_manager', 'Security manager'),
        ('crypto_agent.security.encryption', 'Encryption'),
        ('crypto_agent.security.audit_logger', 'Audit logger'),
        ('crypto_agent.security.anomaly_detector', 'Anomaly detector'),
        
        # Education
        ('crypto_agent.education.academy', 'Academy'),
        
        # Testing
        ('crypto_agent.testing.mock_services', 'Mock services'),
        ('crypto_agent.testing.data_generators', 'Data generators'),
        ('crypto_agent.testing.scenario_tester', 'Scenario tester'),
        
        # API
        ('crypto_agent.api.server', 'API server')
    ]
    
    for module_path, name in modules:
        try:
            importlib.import_module(module_path)
            test_result(f"Import {name}", True)
        except Exception as e:
            test_result(f"Import {name}", False, str(e))

# ============================================================
# SECTION 2: DATABASE TESTS
# ============================================================

async def test_database():
    print("\n" + "="*60)
    print("SECTION 2: DATABASE TESTS")
    print("="*60 + "\n")
    
    try:
        from crypto_agent.storage import database
        
        # Test initialization
        await database.init_db()
        test_result("Database initialization", True)
        
        # Test table existence
        tables = [
            'conversations', 'positions', 'price_cache', 'price_alerts',
            'trade_journal', 'permanent_notes', 'watched_wallets',
            'predictions', 'advice_log', 'complex_alerts', 'scanner_settings',
            'scanner_log', 'workflow_runs', 'custom_workflows',
            'risk_history', 'market_regimes', 'orchestrator_decisions',
            'upcoming_events', 'event_outcomes', 'event_alerts'
        ]
        
        import sqlite3
        import time
        
        # Small delay to ensure DB is free
        time.sleep(0.5)
        
        conn = sqlite3.connect('crypto_agent.db')
        cursor = conn.cursor()
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                test_result(f"Table '{table}' exists", True)
            except Exception as e:
                test_result(f"Table '{table}' exists", False, str(e))
        
        conn.close()
        
    except Exception as e:
        test_result("Database tests", False, str(e))

# ============================================================
# SECTION 3: CONFIGURATION TESTS
# ============================================================

def test_config():
    print("\n" + "="*60)
    print("SECTION 3: CONFIGURATION TESTS")
    print("="*60 + "\n")
    
    if os.path.exists('.env'):
        test_result(".env file exists", True)
    else:
        test_warning(".env file", "Missing - system will use defaults but many features will fail")
        
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'OPENROUTER_API_KEY',
        'MY_TELEGRAM_ID'
    ]
    
    for var in required_vars:
        if os.getenv(var):
            test_result(f"Environment variable {var}", True)
        else:
            test_warning(f"Environment variable {var}", "Not set")

# ============================================================
# SECTION 4: DEPENDENCY TESTS
# ============================================================

def test_dependencies():
    print("\n" + "="*60)
    print("SECTION 4: DEPENDENCY TESTS")
    print("="*60 + "\n")
    
    packages = [
        'telegram', 'aiohttp', 'apscheduler', 'cryptography', 'fastapi'
    ]
    
    for pkg in packages:
        try:
            if pkg == 'telegram':
                import telegram.ext
            else:
                importlib.import_module(pkg)
            test_result(f"Package {pkg}", True)
        except:
            test_result(f"Package {pkg}", False, "Not installed")

# ============================================================
# SECTION 5: MOCK SERVICE TESTS
# ============================================================

async def test_mock_services():
    print("\n" + "="*60)
    print("SECTION 5: MOCK SERVICE TESTS")
    print("="*60 + "\n")
    
    try:
        from crypto_agent.testing.mock_services import MockPriceService, MockNewsService, MockOnChainService
        
        price_service = MockPriceService()
        price = await price_service.get_price('BTC')
        test_result("Mock price service", price['price'] > 0)
        
        news_service = MockNewsService()
        news = await news_service.get_news('') # Empty string to get all news
        test_result("Mock news service", len(news) > 0)
        
        onchain_service = MockOnChainService()
        stats = await onchain_service.get_network_stats('BTC') # Use 'BTC'
        test_result("Mock on-chain service", 'active_addresses' in stats)
        
    except Exception as e:
        test_result("Mock service tests", False, str(e))

# ============================================================
# SECTION 6: DATA GENERATOR TESTS
# ============================================================

def test_data_generators():
    print("\n" + "="*60)
    print("SECTION 6: DATA GENERATOR TESTS")
    print("="*60 + "\n")
    
    try:
        from crypto_agent.testing.data_generators import generate_portfolio_scenario, generate_price_history, generate_market_scenario
        
        portfolio = generate_portfolio_scenario('diversified')
        test_result("Generate portfolio scenario", len(portfolio['positions']) > 0)
        
        history = generate_price_history('BTC', 50000, days=7)
        test_result("Generate price history", len(history) > 0)
        
        market = generate_market_scenario('bull_run')
        test_result("Generate market scenario", 'btc_price' in market)
        
    except Exception as e:
        test_result("Data generator tests", False, str(e))

# ============================================================
# SECTION 7: INTEGRATION TESTS
# ============================================================

async def test_integration():
    print("\n" + "="*60)
    print("SECTION 7: INTEGRATION TESTS")
    print("="*60 + "\n")
    
    try:
        from crypto_agent.storage import database
        
        # Test adding a position and retrieving it
        database.add_or_update_position('TEST_BTC_FINAL', 1.0, 95000, 'Test position')
        pos = database.get_position('TEST_BTC_FINAL')
        test_result("Add and retrieve position", pos is not None and pos['quantity'] == 1.0)
        
        # Clean up
        database.delete_position('TEST_BTC_FINAL')
        
        # Test intelligence hub (Integration piece)
        from crypto_agent.intelligence.intelligence_hub import IntelligenceHub
        hub = IntelligenceHub({}) # Fix init
        test_result("Intelligence Hub instantiation", hub is not None)
        
    except Exception as e:
        test_result("Integration tests", False, str(e))

# ============================================================
# SECTION 8: SECURITY TESTS
# ============================================================

def test_security():
    print("\n" + "="*60)
    print("SECTION 8: SECURITY TESTS")
    print("="*60 + "\n")
    
    try:
        from crypto_agent.security.encryption import DataEncryption
        encryptor = DataEncryption()
        
        data = "Secret message 123"
        encrypted = encryptor.encrypt(data)
        decrypted = encryptor.decrypt(encrypted)
        
        test_result("Encryption round-trip", data == decrypted)
        
    except Exception as e:
        test_result("Security tests", False, str(e))

# ============================================================
# SECTION 9: API TESTS
# ============================================================

def test_api():
    print("\n" + "="*60)
    print("SECTION 9: API TESTS")
    print("="*60 + "\n")
    
    try:
        from crypto_agent.api import create_app
        # Mocking empty bot_data and config
        app = create_app({}, {'TESTING': True, 'API_KEYS': {'test_key': {'user_id': 123}}})
        test_result("API app creation", app is not None)
        
    except Exception as e:
        test_result("API tests", False, str(e))

# ============================================================
# SECTION 10: PERFORMANCE TESTS
# ============================================================

def test_performance():
    print("\n" + "="*60)
    print("SECTION 10: PERFORMANCE TESTS")
    print("="*60 + "\n")
    
    import time
    
    start = time.time()
    for _ in range(100):
        _ = 123 * 456
    duration = time.time() - start
    test_result("Calculation performance", duration < 0.1)
    
    from crypto_agent.storage import database
    start = time.time()
    for i in range(10):
        database.save_message('user', f'Perf check {i}')
    duration = time.time() - start
    test_result("DB Write performance", duration < 1.0)

# ============================================================
# MAIN TEST RUNNER
# ============================================================

async def run_all_tests():
    print("="*60)
    print("COMPREHENSIVE SYSTEM TEST SUITE (FINAL)")
    print("Testing all 40 levels")
    print("="*60)
    
    test_imports()
    await test_database()
    test_config()
    test_dependencies()
    await test_mock_services()
    test_data_generators()
    await test_integration()
    test_security()
    test_api()
    test_performance()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60 + "\n")
    
    passed_count = len(test_results['passed'])
    failed_count = len(test_results['failed'])
    
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    
    if failed_count > 0:
        print(f"\n{failed_count} TESTS FAILED")
        for name, msg in test_results['failed']:
            print(f"- {name}: {msg}")
    else:
        print("\nALL CRITICAL TESTS PASSED! System is ready.")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
