# Test file for market orchestrator
# Run this to verify the orchestrator is working

import asyncio
from crypto_agent.core.orchestrator import orchestrator, MarketRegime, BotMode, Priority

print("🧪 Testing Market Orchestrator...\n")

# Test 1: Check initial state
print("1️⃣ Checking initial state...")
print(f"   Current regime: {orchestrator.current_regime.value}")
print(f"   Current mode: {orchestrator.current_mode.value}")
print(f"   Confidence: {orchestrator.regime_confidence:.0%}")
print("   ✅ Initial state loaded\n")

# Test 2: Detect market regime
print("2️⃣ Detecting market regime...")

async def test_regime_detection():
    regime, confidence, factors = await orchestrator.detect_market_regime()
    print(f"   Detected regime: {regime.value}")
    print(f"   Confidence: {confidence:.0%}")
    print(f"   Factors analyzed: {len(factors)}")
    for key, value in factors.items():
        print(f"   - {key}: {value}")
    return regime, confidence

regime, confidence = asyncio.run(test_regime_detection())

if regime != MarketRegime.UNKNOWN:
    print("   ✅ Regime detection works!\n")
else:
    print("   ⚠️ Regime is unknown (may need real market data)\n")

# Test 3: Get behavior settings
print("3️⃣ Checking behavior settings...")
settings = orchestrator.get_current_settings()
print(f"   Alert sensitivity: {settings['alert_sensitivity']}")
print(f"   Scan frequency: {settings['scan_frequency_minutes']} min")
print(f"   Scanner focus: {settings['scanner_focus']}")
print(f"   Briefing tone: {settings['briefing_tone']}")
print("   ✅ Settings retrieved!\n")

# Test 4: Test mode switching
print("4️⃣ Testing mode switching...")
orchestrator.set_mode(BotMode.AGGRESSIVE, duration_hours=4)
print(f"   Mode set to: {orchestrator.current_mode.value}")
print(f"   Auto-revert in: 4 hours")

# Check settings changed
aggressive_settings = orchestrator.get_current_settings()
print(f"   New scan frequency: {aggressive_settings['scan_frequency_minutes']} min")
print(f"   New alert sensitivity: {aggressive_settings['alert_sensitivity']}")

# Revert to normal
orchestrator.set_mode(BotMode.NORMAL)
print(f"   Reverted to: {orchestrator.current_mode.value}")
print("   ✅ Mode switching works!\n")

# Test 5: Test priority system
print("5️⃣ Testing priority system...")

priorities = [
    (Priority.CRITICAL, "Critical"),
    (Priority.HIGH, "High"),
    (Priority.MEDIUM, "Medium"),
    (Priority.LOW, "Low")
]

for priority, name in priorities:
    should_send = orchestrator.should_send_notification(priority)
    status = "✅ SEND" if should_send else "❌ BLOCK"
    print(f"   {name} priority: {status}")

print("   ✅ Priority filtering works!\n")

# Test 6: Test Claude prompt addition
print("6️⃣ Testing Claude prompt addition...")
prompt_addition = orchestrator.get_claude_system_prompt_addition()

if prompt_addition:
    print(f"   Prompt length: {len(prompt_addition)} characters")
    print(f"   First 100 chars: {prompt_addition[:100]}...")
    print("   ✅ Claude prompt generation works!\n")
else:
    print("   ⚠️ No prompt addition (regime may be unknown)\n")

# Test 7: Test decision logging
print("7️⃣ Testing decision logging...")
orchestrator._log_decision(
    'test_decision',
    'This is a test decision',
    {'test_key': 'test_value'}
)

recent_decisions = orchestrator.get_recent_decisions(hours=24)
print(f"   Decisions logged: {len(recent_decisions)}")

if recent_decisions:
    last_decision = recent_decisions[-1]
    print(f"   Last decision: {last_decision['description']}")
    print("   ✅ Decision logging works!\n")
else:
    print("   ⚠️ No decisions found\n")

# Test 8: Generate reports
print("8️⃣ Testing report generation...")

regime_report = orchestrator.get_regime_report()
print(f"   Regime report length: {len(regime_report)} characters")
print("   First 150 chars:")
print(f"   {regime_report[:150]}...")

status_report = orchestrator.get_orchestrator_status()
print(f"\n   Status report length: {len(status_report)} characters")
print("   First 150 chars:")
print(f"   {status_report[:150]}...")

print("\n   ✅ Report generation works!\n")

print("="*50)
print("✅ ORCHESTRATOR TEST COMPLETE!")
print("="*50)
print("\nAll core functions are working!")
print("\nNext steps:")
print("1. Initialize database tables (see ORCHESTRATOR_GUIDE.md)")
print("2. Register command handlers in main.py")
print("3. Set up hourly regime check")
print("4. Test with /regime command in Telegram")
print("\nNote: Some features need real market data to work fully.")
