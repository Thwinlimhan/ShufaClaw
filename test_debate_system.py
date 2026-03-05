"""
Test script for Multi-Analyst Debate System
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from crypto_agent.intelligence.debate_system import DebateSystem


class MockAI:
    """Mock AI client for testing"""
    async def get_completion(self, prompt: str) -> str:
        if "BULL" in prompt:
            return ("BTC showing strong momentum with RSI at 65, breaking above "
                   "resistance at $95k. Volume increasing, institutional buying "
                   "evident. MACD bullish crossover on 4h. Target $105k short-term. "
                   "This is a clear breakout setup with strong conviction.")
        elif "BEAR" in prompt:
            return ("BTC overbought on multiple timeframes, RSI divergence forming. "
                   "Funding rates extremely high indicating overleveraged longs. "
                   "Macro headwinds with Fed hawkish. Resistance at $100k strong. "
                   "Risk/reward unfavorable here. Expect pullback to $88k.")
        elif "QUANT" in prompt:
            return ("Historical data shows 68% win rate at current RSI levels. "
                   "Expected value +4.2% over 7 days. However, funding extremes "
                   "reduce edge to +1.8%. Probability of $100k break: 55%. "
                   "Statistical edge exists but modest. Position size accordingly.")
        elif "rebuttal" in prompt.lower():
            if "BULL" in prompt:
                return "Bear ignores institutional accumulation and breakout momentum. Short-term pullback possible but trend is up."
            else:
                return "Bull case ignores overbought conditions and funding extremes. Momentum can reverse quickly at resistance."
        elif "evaluation" in prompt.lower():
            return "Data supports 55% probability of upside. Both cases have merit. Edge exists but risk management critical."
        elif "MODERATOR" in prompt or "synthesis" in prompt.lower():
            return ("AGREEMENT: BTC at critical resistance level with elevated risk.\n"
                   "DISAGREEMENT: Bull sees breakout, Bear sees rejection.\n"
                   "MOST LIKELY: Consolidation near $95-100k before decisive move.\n"
                   "RECOMMENDATION: Small position if bullish, tight stop at $93k. "
                   "Wait for confirmation above $100k for larger position. "
                   "Risk/reward acceptable only with strict risk management.")
        return "Analysis complete."


class MockMarket:
    """Mock market service"""
    async def get_price(self, symbol: str):
        return {
            'price': 97500,
            'change_24h': 2.3,
            'volume_24h': 28000000000
        }
    
    async def get_market_overview(self):
        return {
            'sentiment': 'Bullish',
            'fear_greed': 68,
            'btc_dominance': 54.2
        }


class MockTechnical:
    """Mock technical service"""
    async def analyze(self, symbol: str, timeframe: str):
        return {
            'rsi': 65.3,
            'trend': 'Uptrend',
            'macd': 'Bullish',
            'support': 93000,
            'resistance': 100000
        }


class MockNews:
    """Mock news service"""
    async def get_news_for_symbol(self, symbol: str, limit: int = 5):
        return [
            {'title': 'BTC breaks $95k resistance', 'sentiment': 'Bullish'},
            {'title': 'Institutional buying continues', 'sentiment': 'Bullish'},
            {'title': 'Fed signals rate concerns', 'sentiment': 'Bearish'}
        ]


class MockOnchain:
    """Mock on-chain service"""
    async def get_summary(self):
        return {
            'exchange_flows': 'Outflows (Bullish)',
            'whale_activity': 'Accumulation'
        }


async def test_full_debate():
    """Test full three-round debate"""
    print("=" * 60)
    print("TEST 1: Full Debate (3 rounds)")
    print("=" * 60)
    
    # Initialize system
    debate = DebateSystem(
        ai_client=MockAI(),
        market_service=MockMarket(),
        technical_service=MockTechnical(),
        news_service=MockNews(),
        onchain_service=MockOnchain()
    )
    
    # Run debate
    result = await debate.run_debate('BTC', question="Should I buy at $97,500?")
    
    # Display results
    print(f"\n📊 Symbol: {result['symbol']}")
    print(f"❓ Question: {result['question']}")
    print(f"📈 Data: {result['data_summary']}")
    print("\n" + "=" * 60)
    print("ROUND 1: OPENING STATEMENTS")
    print("=" * 60)
    print(f"\n🐂 BULL:\n{result['round_1']['bull']}")
    print(f"\n🐻 BEAR:\n{result['round_1']['bear']}")
    print(f"\n🔢 QUANT:\n{result['round_1']['quant']}")
    
    print("\n" + "=" * 60)
    print("ROUND 2: REBUTTALS")
    print("=" * 60)
    print(f"\n🐂 BULL REBUTTAL:\n{result['round_2']['bull_rebuttal']}")
    print(f"\n🐻 BEAR REBUTTAL:\n{result['round_2']['bear_rebuttal']}")
    print(f"\n🔢 QUANT EVALUATION:\n{result['round_2']['quant_evaluation']}")
    
    print("\n" + "=" * 60)
    print("ROUND 3: SYNTHESIS")
    print("=" * 60)
    print(f"\n⚖️ MODERATOR:\n{result['synthesis']}")
    
    print("\n✅ Full debate test passed!")
    return True


async def test_quick_debate():
    """Test quick debate (faster version)"""
    print("\n\n" + "=" * 60)
    print("TEST 2: Quick Debate (opening + synthesis only)")
    print("=" * 60)
    
    # Initialize system
    debate = DebateSystem(
        ai_client=MockAI(),
        market_service=MockMarket(),
        technical_service=MockTechnical(),
        news_service=MockNews(),
        onchain_service=MockOnchain()
    )
    
    # Run quick debate
    result = await debate.quick_debate('ETH')
    
    # Display results
    print(f"\n📊 Symbol: {result['symbol']}")
    print(f"⚡ Mode: {result['mode']}")
    print(f"📈 Data: {result['data_summary']}")
    
    print("\n" + "=" * 60)
    print("ANALYST VIEWS")
    print("=" * 60)
    print(f"\n🐂 BULL:\n{result['analysts']['bull']}")
    print(f"\n🐻 BEAR:\n{result['analysts']['bear']}")
    print(f"\n🔢 QUANT:\n{result['analysts']['quant']}")
    
    print("\n" + "=" * 60)
    print("SYNTHESIS")
    print("=" * 60)
    print(f"\n⚖️ MODERATOR:\n{result['synthesis']}")
    
    print("\n✅ Quick debate test passed!")
    return True


async def test_message_formatting():
    """Test Telegram message formatting"""
    print("\n\n" + "=" * 60)
    print("TEST 3: Message Formatting")
    print("=" * 60)
    
    # Initialize system
    debate = DebateSystem(
        ai_client=MockAI(),
        market_service=MockMarket(),
        technical_service=MockTechnical(),
        news_service=MockNews(),
        onchain_service=MockOnchain()
    )
    
    # Run debate
    result = await debate.quick_debate('BTC')
    
    # Format message
    message = debate.format_debate_message(result, mode='quick')
    
    print("\n📱 TELEGRAM MESSAGE:")
    print("=" * 60)
    print(message)
    print("=" * 60)
    
    print(f"\n📏 Message length: {len(message)} characters")
    if len(message) > 4096:
        print("⚠️  Message exceeds Telegram limit (will be split)")
    else:
        print("✅ Message within Telegram limit")
    
    print("\n✅ Message formatting test passed!")
    return True


async def main():
    """Run all tests"""
    print("\n🎭 MULTI-ANALYST DEBATE SYSTEM - TEST SUITE\n")
    
    try:
        # Run tests
        test1 = await test_full_debate()
        test2 = await test_quick_debate()
        test3 = await test_message_formatting()
        
        # Summary
        print("\n\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Full Debate: {'PASSED' if test1 else 'FAILED'}")
        print(f"✅ Quick Debate: {'PASSED' if test2 else 'FAILED'}")
        print(f"✅ Message Formatting: {'PASSED' if test3 else 'FAILED'}")
        
        if all([test1, test2, test3]):
            print("\n🎉 ALL TESTS PASSED!")
            print("\n📋 Next steps:")
            print("1. Add debate_system to bot_data in main.py")
            print("2. Register debate handlers")
            print("3. Test with real Telegram bot:")
            print("   • /debate BTC")
            print("   • /debate ETH should I buy now?")
            print("   • /quickdebate SOL")
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
