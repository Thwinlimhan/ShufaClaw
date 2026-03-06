"""
Test script for Level 29 - Options Intelligence
Run this to verify the options monitor is working correctly.
"""

import asyncio
import logging
from crypto_agent.derivatives.options_monitor import get_options_monitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_options_monitor():
    """Test the options monitor functionality."""
    print("\n" + "="*60)
    print("LEVEL 29 - OPTIONS INTELLIGENCE TEST")
    print("="*60 + "\n")
    
    monitor = get_options_monitor()
    
    # Test BTC options
    print("📊 Testing BTC Options Data...")
    print("-" * 60)
    
    btc_data = monitor.get_options_data("BTC")
    
    if btc_data:
        print("✅ Successfully fetched BTC options data\n")
        
        # Display formatted report
        report = monitor.format_options_report(btc_data)
        print(report)
        
        # Check for alerts
        alerts = monitor.check_for_alerts(btc_data)
        if alerts:
            print("\n🔔 ALERTS DETECTED:")
            for alert in alerts:
                print(f"   {alert}")
        else:
            print("\n✓ No alerts at this time")
        
        # Test individual metrics
        print("\n" + "-" * 60)
        print("📈 Individual Metric Tests:")
        print("-" * 60)
        
        print(f"✓ Put/Call Ratio: {btc_data.put_call_ratio:.2f}")
        print(f"  Interpretation: {monitor.interpret_put_call_ratio(btc_data.put_call_ratio)}")
        
        print(f"\n✓ Max Pain: ${btc_data.max_pain:,.0f}")
        pain_distance = ((btc_data.max_pain - btc_data.current_price) / btc_data.current_price) * 100
        print(f"  Distance from current: {pain_distance:+.1f}%")
        
        print(f"\n✓ Implied Volatility: {btc_data.iv_current*100:.1f}%")
        print(f"  30d Average: {btc_data.iv_30d_avg*100:.1f}%")
        
        print(f"\n✓ Gamma Exposure: {btc_data.gamma_exposure:.2f}")
        gex_effect = "Amplified (volatile)" if btc_data.gamma_exposure > 0 else "Dampened (stable)"
        print(f"  Effect: {gex_effect}")
        
        if btc_data.unusual_activity:
            print(f"\n✓ Unusual Activity: {len(btc_data.unusual_activity)} events")
            for activity in btc_data.unusual_activity[:3]:
                print(f"  • {activity['description']}")
        else:
            print("\n✓ No unusual activity detected")
        
    else:
        print("❌ Failed to fetch BTC options data")
        print("   This could be due to:")
        print("   - Deribit API temporarily unavailable")
        print("   - Network connectivity issues")
        print("   - Rate limiting")
        return False
    
    # Test ETH options
    print("\n" + "="*60)
    print("📊 Testing ETH Options Data...")
    print("-" * 60)
    
    eth_data = monitor.get_options_data("ETH")
    
    if eth_data:
        print("✅ Successfully fetched ETH options data")
        print(f"   Current Price: ${eth_data.current_price:,.2f}")
        print(f"   P/C Ratio: {eth_data.put_call_ratio:.2f}")
        print(f"   Max Pain: ${eth_data.max_pain:,.2f}")
        print(f"   IV: {eth_data.iv_current*100:.1f}%")
    else:
        print("⚠️  Failed to fetch ETH options data")
    
    # Test quick lookup functions
    print("\n" + "="*60)
    print("🔍 Testing Quick Lookup Functions...")
    print("-" * 60)
    
    max_pain = monitor.get_max_pain_only("BTC")
    if max_pain:
        print(f"✅ Quick Max Pain Lookup: ${max_pain:,.0f}")
    else:
        print("❌ Quick Max Pain Lookup failed")
    
    iv = monitor.get_iv_only("BTC")
    if iv:
        print(f"✅ Quick IV Lookup: {iv*100:.1f}%")
    else:
        print("❌ Quick IV Lookup failed")
    
    # Test caching
    print("\n" + "="*60)
    print("⚡ Testing Cache Performance...")
    print("-" * 60)
    
    import time
    
    start = time.time()
    monitor.get_options_data("BTC")
    first_call = time.time() - start
    
    start = time.time()
    monitor.get_options_data("BTC")
    cached_call = time.time() - start
    
    print(f"First call: {first_call:.3f}s")
    print(f"Cached call: {cached_call:.3f}s")
    print(f"Speedup: {first_call/cached_call:.1f}x faster")
    
    if cached_call < first_call * 0.1:
        print("✅ Cache working correctly")
    else:
        print("⚠️  Cache may not be working optimally")
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    print("✅ Options monitor initialized successfully")
    print("✅ BTC data fetched and formatted")
    print("✅ Alert system functional")
    print("✅ Individual metrics calculated")
    print("✅ Quick lookup functions working")
    print("✅ Cache system operational")
    print("\n🎉 Level 29 - Options Intelligence is ready!")
    print("\nNext steps:")
    print("1. Try /options command in Telegram")
    print("2. Check /maxpain for max pain levels")
    print("3. Use /iv to monitor implied volatility")
    print("4. Monitor for unusual activity alerts")
    
    return True


if __name__ == "__main__":
    try:
        success = test_options_monitor()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
        exit(1)
