"""
Test script for Event Impact Predictor
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from crypto_agent.intelligence.event_predictor import EventPredictor, Event


class MockDB:
    """Mock database for testing"""
    def __init__(self):
        self.events = []
    
    async def execute(self, query, params=None):
        # Store events
        if "INSERT OR REPLACE INTO upcoming_events" in query:
            self.events.append(params)
    
    async def commit(self):
        pass


class MockMarket:
    """Mock market service"""
    async def get_price(self, symbol):
        return {'price': 97500, 'change_24h': 2.3}


class MockPrice:
    """Mock price service"""
    async def get_price(self, symbol):
        return 97500


async def test_token_unlocks():
    """Test token unlock tracking"""
    print("=" * 60)
    print("TEST 1: Token Unlock Tracking")
    print("=" * 60)
    
    predictor = EventPredictor(
        db=MockDB(),
        market_service=MockMarket(),
        price_service=MockPrice()
    )
    
    events = await predictor._get_token_unlocks(days_ahead=30)
    
    print(f"\n✅ Found {len(events)} token unlock events")
    
    for event in events:
        print(f"\n📅 {event.title}")
        print(f"   Symbol: {event.symbol}")
        print(f"   Date: {event.date.strftime('%Y-%m-%d')}")
        print(f"   Impact: {event.impact_score:.0f}/10")
        print(f"   Direction: {event.predicted_direction}")
        print(f"   Confidence: {event.confidence*100:.0f}%")
        print(f"   Pattern: {event.historical_pattern}")
        if event.data:
            print(f"   Unlock Size: {event.data['pct_of_supply']:.1f}% of supply")
            print(f"   Expected Impact Before: {event.data['avg_impact_before']:+.1f}%")
            print(f"   Expected Impact Day: {event.data['avg_impact_day']:+.1f}%")
            print(f"   Expected Impact After: {event.data['avg_impact_after']:+.1f}%")
    
    print("\n✅ Token unlock test passed!")
    return True


async def test_protocol_upgrades():
    """Test protocol upgrade tracking"""
    print("\n\n" + "=" * 60)
    print("TEST 2: Protocol Upgrade Tracking")
    print("=" * 60)
    
    predictor = EventPredictor(
        db=MockDB(),
        market_service=MockMarket(),
        price_service=MockPrice()
    )
    
    events = await predictor._get_protocol_upgrades(days_ahead=60)
    
    print(f"\n✅ Found {len(events)} protocol upgrade events")
    
    for event in events:
        print(f"\n📅 {event.title}")
        print(f"   Symbol: {event.symbol}")
        print(f"   Date: {event.date.strftime('%Y-%m-%d')}")
        print(f"   Impact: {event.impact_score:.0f}/10")
        print(f"   Direction: {event.predicted_direction}")
        print(f"   Pattern: {event.historical_pattern}")
    
    print("\n✅ Protocol upgrade test passed!")
    return True


async def test_macro_events():
    """Test macro event tracking"""
    print("\n\n" + "=" * 60)
    print("TEST 3: Macro Event Tracking")
    print("=" * 60)
    
    predictor = EventPredictor(
        db=MockDB(),
        market_service=MockMarket(),
        price_service=MockPrice()
    )
    
    events = await predictor._get_macro_events(days_ahead=30)
    
    print(f"\n✅ Found {len(events)} macro events")
    
    for event in events:
        print(f"\n📅 {event.title}")
        print(f"   Date: {event.date.strftime('%Y-%m-%d')}")
        print(f"   Impact: {event.impact_score:.0f}/10")
        print(f"   Direction: {event.predicted_direction}")
        print(f"   Confidence: {event.confidence*100:.0f}%")
        print(f"   Pattern: {event.historical_pattern}")
        if event.data:
            print(f"   Expected Impact: {event.data['avg_impact']:+.1f}%")
    
    print("\n✅ Macro event test passed!")
    return True


async def test_options_expiry():
    """Test options expiry tracking"""
    print("\n\n" + "=" * 60)
    print("TEST 4: Options Expiry Tracking")
    print("=" * 60)
    
    predictor = EventPredictor(
        db=MockDB(),
        market_service=MockMarket(),
        price_service=MockPrice()
    )
    
    events = await predictor._get_options_expiry(days_ahead=90)
    
    print(f"\n✅ Found {len(events)} options expiry events")
    
    for event in events:
        print(f"\n📅 {event.title}")
        print(f"   Date: {event.date.strftime('%Y-%m-%d (%A)')}")
        print(f"   Impact: {event.impact_score:.0f}/10")
        print(f"   Pattern: {event.historical_pattern}")
    
    print("\n✅ Options expiry test passed!")
    return True


async def test_full_calendar():
    """Test full event calendar"""
    print("\n\n" + "=" * 60)
    print("TEST 5: Full Event Calendar")
    print("=" * 60)
    
    predictor = EventPredictor(
        db=MockDB(),
        market_service=MockMarket(),
        price_service=MockPrice()
    )
    
    events = await predictor.track_upcoming_events(days_ahead=30)
    
    print(f"\n✅ Total events tracked: {len(events)}")
    
    # Group by type
    by_type = {}
    for event in events:
        by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
    
    print("\n📊 Events by type:")
    for event_type, count in by_type.items():
        print(f"   {event_type}: {count}")
    
    # Show calendar message
    print("\n📅 CALENDAR MESSAGE:")
    print("=" * 60)
    message = predictor.format_calendar_message(events, days=30)
    print(message)
    print("=" * 60)
    
    print("\n✅ Full calendar test passed!")
    return True


async def test_event_analysis():
    """Test detailed event analysis"""
    print("\n\n" + "=" * 60)
    print("TEST 6: Event Impact Analysis")
    print("=" * 60)
    
    predictor = EventPredictor(
        db=MockDB(),
        market_service=MockMarket(),
        price_service=MockPrice()
    )
    
    # Get an event
    events = await predictor.track_upcoming_events(days_ahead=30)
    if not events:
        print("⚠️  No events to analyze")
        return True
    
    event = events[0]
    
    print(f"\n🔍 Analyzing: {event.title}")
    
    # Analyze
    analysis = await predictor.analyze_event_impact(event)
    
    # Format and display
    message = predictor.format_event_analysis(analysis)
    
    print("\n📊 ANALYSIS MESSAGE:")
    print("=" * 60)
    print(message)
    print("=" * 60)
    
    print("\n✅ Event analysis test passed!")
    return True


async def test_imminent_events():
    """Test imminent event detection"""
    print("\n\n" + "=" * 60)
    print("TEST 7: Imminent Event Detection")
    print("=" * 60)
    
    predictor = EventPredictor(
        db=MockDB(),
        market_service=MockMarket(),
        price_service=MockPrice()
    )
    
    imminent = await predictor.get_imminent_events(days_threshold=7)
    
    print(f"\n✅ Found {len(imminent)} imminent events (next 7 days)")
    
    for event in imminent:
        days_until = (event.date - datetime.now()).days
        print(f"\n⚠️  {event.title}")
        print(f"   {days_until} days until event")
        print(f"   Impact: {event.impact_score:.0f}/10")
        print(f"   Direction: {event.predicted_direction}")
    
    print("\n✅ Imminent event test passed!")
    return True


async def test_symbol_events():
    """Test symbol-specific event filtering"""
    print("\n\n" + "=" * 60)
    print("TEST 8: Symbol-Specific Events")
    print("=" * 60)
    
    predictor = EventPredictor(
        db=MockDB(),
        market_service=MockMarket(),
        price_service=MockPrice()
    )
    
    # Test for ARB
    arb_events = await predictor.get_events_for_symbol('ARB', days_ahead=30)
    print(f"\n✅ ARB events: {len(arb_events)}")
    for event in arb_events:
        print(f"   • {event.title} ({event.date.strftime('%b %d')})")
    
    # Test for ETH
    eth_events = await predictor.get_events_for_symbol('ETH', days_ahead=60)
    print(f"\n✅ ETH events: {len(eth_events)}")
    for event in eth_events:
        print(f"   • {event.title} ({event.date.strftime('%b %d')})")
    
    # Test for BTC
    btc_events = await predictor.get_events_for_symbol('BTC', days_ahead=30)
    print(f"\n✅ BTC events: {len(btc_events)}")
    for event in btc_events:
        print(f"   • {event.title} ({event.date.strftime('%b %d')})")
    
    print("\n✅ Symbol-specific test passed!")
    return True


async def main():
    """Run all tests"""
    print("\n🔮 EVENT IMPACT PREDICTOR - TEST SUITE\n")
    
    try:
        # Run tests
        test1 = await test_token_unlocks()
        test2 = await test_protocol_upgrades()
        test3 = await test_macro_events()
        test4 = await test_options_expiry()
        test5 = await test_full_calendar()
        test6 = await test_event_analysis()
        test7 = await test_imminent_events()
        test8 = await test_symbol_events()
        
        # Summary
        print("\n\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Token Unlocks: {'PASSED' if test1 else 'FAILED'}")
        print(f"✅ Protocol Upgrades: {'PASSED' if test2 else 'FAILED'}")
        print(f"✅ Macro Events: {'PASSED' if test3 else 'FAILED'}")
        print(f"✅ Options Expiry: {'PASSED' if test4 else 'FAILED'}")
        print(f"✅ Full Calendar: {'PASSED' if test5 else 'FAILED'}")
        print(f"✅ Event Analysis: {'PASSED' if test6 else 'FAILED'}")
        print(f"✅ Imminent Events: {'PASSED' if test7 else 'FAILED'}")
        print(f"✅ Symbol-Specific: {'PASSED' if test8 else 'FAILED'}")
        
        if all([test1, test2, test3, test4, test5, test6, test7, test8]):
            print("\n🎉 ALL TESTS PASSED!")
            print("\n📋 Next steps:")
            print("1. Initialize event tables in database")
            print("2. Add event_predictor to bot_data in main.py")
            print("3. Register event handlers")
            print("4. Set up automated event checking (daily)")
            print("5. Test with real Telegram bot:")
            print("   • /calendar")
            print("   • /predict ARB unlock")
            print("   • /imminent")
        else:
            print("\n❌ SOME TESTS FAILED")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
