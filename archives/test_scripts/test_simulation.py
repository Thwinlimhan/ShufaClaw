"""
Simulation Environment Test Suite (Level 38)

Comprehensive testing using mock services and scenario generators.
"""

import asyncio
from crypto_agent.testing import (
    MockPriceService,
    MockMarketService,
    MockTAService,
    MockDatabase,
    generate_price_history,
    generate_market_scenario,
    generate_portfolio_scenario,
    ScenarioTester
)
from crypto_agent.intelligence.trade_proposer import TradeProposer


async def test_mock_price_service():
    """Test mock price service"""
    print("\n🧪 Testing Mock Price Service...")
    
    service = MockPriceService()
    
    # Test 1: Get price
    btc_data = await service.get_price('BTC')
    assert btc_data is not None, "Should return price data"
    assert 'price' in btc_data, "Should have price field"
    assert 'change_24h' in btc_data, "Should have change_24h field"
    print(f"✅ BTC Price: ${btc_data['price']:,.2f} ({btc_data['change_24h']:+.2f}%)")
    
    # Test 2: Set trend
    service.set_trend(0.05)  # 5% daily growth
    initial_price = btc_data['price']
    
    # Simulate multiple price updates
    for _ in range(10):
        btc_data = await service.get_price('BTC')
    
    final_price = btc_data['price']
    assert final_price > initial_price, "Price should increase with positive trend"
    print(f"✅ Trend test: ${initial_price:,.2f} → ${final_price:,.2f}")
    
    # Test 3: Unknown symbol
    unknown = await service.get_price('UNKNOWN')
    assert unknown is None, "Should return None for unknown symbol"
    print("✅ Unknown symbol handling: Correct")


async def test_mock_market_service():
    """Test mock market service"""
    print("\n🧪 Testing Mock Market Service...")
    
    service = MockMarketService()
    
    # Test 1: Fear & Greed
    fg = await service.get_fear_greed_index()
    assert 'value' in fg, "Should have value"
    assert 'classification' in fg, "Should have classification"
    assert 0 <= fg['value'] <= 100, "Value should be 0-100"
    print(f"✅ Fear & Greed: {fg['value']} ({fg['classification']})")
    
    # Test 2: Market overview
    overview = await service.get_market_overview()
    assert 'total_market_cap' in overview, "Should have market cap"
    assert 'btc_dominance' in overview, "Should have BTC dominance"
    print(f"✅ Market Cap: ${overview['total_market_cap']/1e12:.2f}T")
    
    # Test 3: Top coins
    top_coins = await service.get_top_coins(5)
    assert len(top_coins) == 5, "Should return 5 coins"
    assert top_coins[0]['symbol'] == 'BTC', "BTC should be #1"
    print(f"✅ Top 5 coins: {', '.join([c['symbol'] for c in top_coins])}")


async def test_mock_ta_service():
    """Test mock TA service"""
    print("\n🧪 Testing Mock TA Service...")
    
    service = MockTAService()
    
    # Test 1: Analyze
    ta = await service.analyze('BTC', '4h')
    assert 'rsi' in ta, "Should have RSI"
    assert 'trend' in ta, "Should have trend"
    assert 'support' in ta, "Should have support"
    assert 'resistance' in ta, "Should have resistance"
    print(f"✅ BTC Analysis: RSI={ta['rsi']:.1f}, Trend={ta['trend']}")
    
    # Test 2: Set scenario
    custom_scenario = {
        'rsi': 25,
        'trend': 'down',
        'support': 90000,
        'resistance': 100000
    }
    service.set_scenario('BTC', custom_scenario)
    
    ta = await service.analyze('BTC', '4h')
    assert ta['rsi'] == 25, "Should use custom RSI"
    assert ta['trend'] == 'down', "Should use custom trend"
    print("✅ Custom scenario: Applied correctly")
    
    # Test 3: Clear scenarios
    service.clear_scenarios()
    ta = await service.analyze('BTC', '4h')
    assert ta['rsi'] != 25, "Should generate new random data"
    print("✅ Clear scenarios: Working")


async def test_mock_database():
    """Test mock database"""
    print("\n🧪 Testing Mock Database...")
    
    db = MockDatabase()
    
    # Test 1: Add position
    await db.add_position(123, 'BTC', 0.5, 95000)
    positions = await db.get_positions(123)
    assert len(positions) == 1, "Should have 1 position"
    assert positions[0]['symbol'] == 'BTC', "Should be BTC"
    print(f"✅ Add position: {positions[0]['amount']} {positions[0]['symbol']}")
    
    # Test 2: Create alert
    alert_id = await db.create_alert(123, 'BTC', 100000, 'above')
    alerts = await db.get_active_alerts(123)
    assert len(alerts) == 1, "Should have 1 alert"
    print(f"✅ Create alert: ID={alert_id}")
    
    # Test 3: Journal entry
    await db.add_journal_entry(123, "Test entry", 'BTC')
    entries = await db.get_journal_entries(123, 7)
    assert len(entries) == 1, "Should have 1 entry"
    print(f"✅ Journal entry: {entries[0]['entry']}")
    
    # Test 4: Clear all
    db.clear_all()
    positions = await db.get_positions(123)
    assert len(positions) == 0, "Should be empty"
    print("✅ Clear all: Working")


def test_price_history_generator():
    """Test price history generator"""
    print("\n🧪 Testing Price History Generator...")
    
    # Test 1: Generate history
    history = generate_price_history('BTC', 97500, days=30, volatility=0.02)
    assert len(history) == 30 * 24, "Should have 720 hourly candles"
    assert all('open' in c for c in history), "All candles should have OHLC"
    print(f"✅ Generated {len(history)} candles")
    
    # Test 2: Uptrend
    uptrend = generate_price_history('BTC', 90000, days=10, trend=0.02)
    first_price = uptrend[0]['close']
    last_price = uptrend[-1]['close']
    assert last_price > first_price, "Uptrend should increase price"
    print(f"✅ Uptrend: ${first_price:,.0f} → ${last_price:,.0f}")
    
    # Test 3: Downtrend
    downtrend = generate_price_history('BTC', 100000, days=10, trend=-0.02)
    first_price = downtrend[0]['close']
    last_price = downtrend[-1]['close']
    assert last_price < first_price, "Downtrend should decrease price"
    print(f"✅ Downtrend: ${first_price:,.0f} → ${last_price:,.0f}")


def test_market_scenario_generator():
    """Test market scenario generator"""
    print("\n🧪 Testing Market Scenario Generator...")
    
    scenarios = ['bull_run', 'bear_market', 'sideways', 'volatile', 'crash', 'recovery']
    
    for scenario_name in scenarios:
        scenario = generate_market_scenario(scenario_name)
        assert 'name' in scenario, "Should have name"
        assert 'fear_greed' in scenario, "Should have fear_greed"
        assert 'trend' in scenario, "Should have trend"
        print(f"✅ {scenario['name']}: F&G={scenario['fear_greed']}, Trend={scenario['trend']:+.2%}")


def test_portfolio_scenario_generator():
    """Test portfolio scenario generator"""
    print("\n🧪 Testing Portfolio Scenario Generator...")
    
    scenarios = ['diversified', 'concentrated', 'risky', 'conservative', 'losing', 'winning']
    
    for scenario_name in scenarios:
        scenario = generate_portfolio_scenario(scenario_name, 10000)
        assert 'name' in scenario, "Should have name"
        assert 'positions' in scenario, "Should have positions"
        assert 'risk_level' in scenario, "Should have risk_level"
        print(f"✅ {scenario['name']}: {len(scenario['positions'])} positions, "
              f"Risk={scenario['risk_level']}")


async def test_scenario_tester():
    """Test scenario tester"""
    print("\n🧪 Testing Scenario Tester...")
    
    tester = ScenarioTester()
    
    # Get mock services
    services = tester.get_mock_services()
    
    # Create trade proposer with mock services
    proposer = TradeProposer(
        db=services['db'],
        price_service=services['price_service'],
        ta_service=services['ta_service'],
        portfolio_value=10000
    )
    
    # Run test suite
    components = {
        'proposer': proposer
    }
    
    results = await tester.run_full_test_suite(components)
    
    assert results['total_tests'] > 0, "Should run tests"
    assert results['total_passed'] > 0, "Should have passing tests"
    print(f"\n✅ Scenario tester: {results['total_passed']}/{results['total_tests']} passed")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("SIMULATION ENVIRONMENT TEST SUITE")
    print("=" * 60)
    
    try:
        # Mock services
        await test_mock_price_service()
        await test_mock_market_service()
        await test_mock_ta_service()
        await test_mock_database()
        
        # Data generators
        test_price_history_generator()
        test_market_scenario_generator()
        test_portfolio_scenario_generator()
        
        # Scenario tester
        await test_scenario_tester()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
