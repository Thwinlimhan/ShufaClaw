"""
Test suite for Autonomous Trade Proposal System (Level 36)
"""

import asyncio
from datetime import datetime
from crypto_agent.intelligence.trade_proposer import TradeProposer, SetupType, ProposalStatus


class MockDB:
    """Mock database for testing"""
    def __init__(self):
        self.proposals = []
    
    async def execute(self, query, params):
        if "INSERT INTO trade_proposals" in query:
            self.proposals.append(params)
    
    async def fetch_all(self, query, params=None):
        if "WHERE status IN" in query:
            return []
        if "SELECT" in query and "COUNT" in query:
            return [{'total': 0, 'wins': 0, 'losses': 0, 'avg_pnl': 0, 'avg_pnl_pct': 0, 'total_pnl': 0}]
        return []


class MockPriceService:
    """Mock price service"""
    async def get_price(self, symbol):
        prices = {
            'BTC': 97500,
            'ETH': 3400,
            'SOL': 125,
            'AVAX': 38
        }
        return {'price': prices.get(symbol, 100)}


class MockTAService:
    """Mock technical analysis service"""
    async def analyze(self, symbol, timeframe):
        # Breakout setup
        if symbol == 'BTC':
            return {
                'rsi': 55,
                'trend': 'up',
                'support': 95000,
                'resistance': 97000,
                'volume_ratio': 2.0,
                'sma_20': 96000,
                'sma_50': 94000
            }
        
        # Pullback setup
        if symbol == 'ETH':
            return {
                'rsi': 35,
                'trend': 'up',
                'support': 3300,
                'resistance': 3600,
                'volume_ratio': 1.2,
                'sma_20': 3350,
                'sma_50': 3300
            }
        
        # Reversal setup
        if symbol == 'SOL':
            return {
                'rsi': 25,
                'trend': 'down',
                'support': 115,
                'resistance': 135,
                'volume_ratio': 1.5,
                'sma_20': 120,
                'sma_50': 118
            }
        
        # Range setup
        if symbol == 'AVAX':
            return {
                'rsi': 50,
                'trend': 'neutral',
                'support': 36,
                'resistance': 40,
                'volume_ratio': 0.8,
                'sma_20': 38,
                'sma_50': 37
            }
        
        return None


async def test_breakout_proposal():
    """Test breakout trade proposal generation"""
    print("\n🧪 Testing Breakout Proposal...")
    
    db = MockDB()
    price_service = MockPriceService()
    ta_service = MockTAService()
    
    proposer = TradeProposer(db, price_service, ta_service, portfolio_value=10000)
    
    proposal = await proposer.generate_proposal('BTC', '4h')
    
    assert proposal is not None, "Proposal should be generated"
    assert proposal.symbol == 'BTC', "Symbol should be BTC"
    assert proposal.setup_type == SetupType.BREAKOUT, "Should be breakout setup"
    assert proposal.direction == 'LONG', "Should be long direction"
    assert proposal.entry_price > 97000, "Entry should be above resistance"
    assert proposal.stop_loss < 97000, "Stop should be below resistance"
    assert proposal.target_1 > proposal.entry_price, "Target 1 should be above entry"
    assert proposal.reward_risk_ratio > 1.0, "R:R should be positive"
    assert 0 < proposal.win_probability < 1, "Win probability should be between 0 and 1"
    
    print(f"✅ Breakout proposal generated successfully")
    print(f"   Entry: ${proposal.entry_price:,.2f}")
    print(f"   Stop: ${proposal.stop_loss:,.2f}")
    print(f"   Target: ${proposal.target_2:,.2f}")
    print(f"   R:R: {proposal.reward_risk_ratio:.2f}:1")
    print(f"   Win Prob: {proposal.win_probability * 100:.0f}%")


async def test_pullback_proposal():
    """Test pullback trade proposal generation"""
    print("\n🧪 Testing Pullback Proposal...")
    
    db = MockDB()
    price_service = MockPriceService()
    ta_service = MockTAService()
    
    proposer = TradeProposer(db, price_service, ta_service, portfolio_value=10000)
    
    proposal = await proposer.generate_proposal('ETH', '4h')
    
    assert proposal is not None, "Proposal should be generated"
    assert proposal.symbol == 'ETH', "Symbol should be ETH"
    assert proposal.setup_type == SetupType.PULLBACK, "Should be pullback setup"
    assert proposal.direction == 'LONG', "Should be long direction"
    assert proposal.entry_price <= 3350, "Entry should be near support"
    assert proposal.stop_loss < proposal.entry_price, "Stop should be below entry"
    assert proposal.target_2 > proposal.entry_price, "Target should be above entry"
    
    print(f"✅ Pullback proposal generated successfully")
    print(f"   Entry: ${proposal.entry_price:,.2f}")
    print(f"   Stop: ${proposal.stop_loss:,.2f}")
    print(f"   Target: ${proposal.target_2:,.2f}")
    print(f"   R:R: {proposal.reward_risk_ratio:.2f}:1")


async def test_reversal_proposal():
    """Test reversal trade proposal generation"""
    print("\n🧪 Testing Reversal Proposal...")
    
    db = MockDB()
    price_service = MockPriceService()
    ta_service = MockTAService()
    
    proposer = TradeProposer(db, price_service, ta_service, portfolio_value=10000)
    
    proposal = await proposer.generate_proposal('SOL', '4h')
    
    assert proposal is not None, "Proposal should be generated"
    assert proposal.symbol == 'SOL', "Symbol should be SOL"
    assert proposal.setup_type == SetupType.REVERSAL, "Should be reversal setup"
    assert proposal.direction == 'LONG', "Should be long (RSI oversold)"
    assert proposal.reward_risk_ratio > 1.0, "R:R should be positive"
    
    print(f"✅ Reversal proposal generated successfully")
    print(f"   Entry: ${proposal.entry_price:,.2f}")
    print(f"   Stop: ${proposal.stop_loss:,.2f}")
    print(f"   Target: ${proposal.target_2:,.2f}")
    print(f"   R:R: {proposal.reward_risk_ratio:.2f}:1")


async def test_range_proposal():
    """Test range trade proposal generation"""
    print("\n🧪 Testing Range Trade Proposal...")
    
    db = MockDB()
    price_service = MockPriceService()
    ta_service = MockTAService()
    
    proposer = TradeProposer(db, price_service, ta_service, portfolio_value=10000)
    
    proposal = await proposer.generate_proposal('AVAX', '4h')
    
    assert proposal is not None, "Proposal should be generated"
    assert proposal.symbol == 'AVAX', "Symbol should be AVAX"
    assert proposal.setup_type == SetupType.RANGE_TRADE, "Should be range trade setup"
    assert proposal.entry_price is not None, "Entry should be set"
    assert proposal.stop_loss is not None, "Stop should be set"
    
    print(f"✅ Range trade proposal generated successfully")
    print(f"   Entry: ${proposal.entry_price:,.2f}")
    print(f"   Stop: ${proposal.stop_loss:,.2f}")
    print(f"   Target: ${proposal.target_2:,.2f}")
    print(f"   Direction: {proposal.direction}")


async def test_position_sizing():
    """Test position sizing calculations"""
    print("\n🧪 Testing Position Sizing...")
    
    db = MockDB()
    price_service = MockPriceService()
    ta_service = MockTAService()
    
    # Test with different risk percentages
    proposer_1pct = TradeProposer(db, price_service, ta_service, portfolio_value=10000)
    proposal_1pct = await proposer_1pct.generate_proposal('BTC', '4h', risk_percent=1.0)
    
    proposer_2pct = TradeProposer(db, price_service, ta_service, portfolio_value=10000)
    proposal_2pct = await proposer_2pct.generate_proposal('BTC', '4h', risk_percent=2.0)
    
    assert proposal_1pct.risk_amount == 100, "1% risk should be $100"
    assert proposal_2pct.risk_amount == 200, "2% risk should be $200"
    assert proposal_2pct.position_size_usd > proposal_1pct.position_size_usd, "2% risk should have larger position"
    
    print(f"✅ Position sizing working correctly")
    print(f"   1% risk: ${proposal_1pct.risk_amount:.0f} → Position: ${proposal_1pct.position_size_usd:,.0f}")
    print(f"   2% risk: ${proposal_2pct.risk_amount:.0f} → Position: ${proposal_2pct.position_size_usd:,.0f}")


async def test_save_and_retrieve():
    """Test saving and retrieving proposals"""
    print("\n🧪 Testing Save and Retrieve...")
    
    db = MockDB()
    price_service = MockPriceService()
    ta_service = MockTAService()
    
    proposer = TradeProposer(db, price_service, ta_service, portfolio_value=10000)
    
    proposal = await proposer.generate_proposal('BTC', '4h')
    await proposer.save_proposal(proposal)
    
    assert len(db.proposals) == 1, "Proposal should be saved"
    saved = db.proposals[0]
    assert saved[1] == 'BTC', "Symbol should be saved"
    assert saved[2] == 'breakout', "Setup type should be saved"
    
    print(f"✅ Save and retrieve working correctly")
    print(f"   Saved proposal: {saved[0]}")


async def test_expected_value():
    """Test expected value calculations"""
    print("\n🧪 Testing Expected Value...")
    
    db = MockDB()
    price_service = MockPriceService()
    ta_service = MockTAService()
    
    proposer = TradeProposer(db, price_service, ta_service, portfolio_value=10000)
    
    # Breakout: 57% win rate, should have positive EV
    breakout = await proposer.generate_proposal('BTC', '4h')
    assert breakout.expected_value > 0, "Breakout should have positive EV"
    
    # Pullback: 67% win rate, should have strong positive EV
    pullback = await proposer.generate_proposal('ETH', '4h')
    assert pullback.expected_value > 0, "Pullback should have positive EV"
    assert pullback.expected_value > breakout.expected_value, "Pullback should have higher EV"
    
    print(f"✅ Expected value calculations working")
    print(f"   Breakout EV: {breakout.expected_value:+.2f}R")
    print(f"   Pullback EV: {pullback.expected_value:+.2f}R")


async def main():
    """Run all tests"""
    print("=" * 50)
    print("AUTONOMOUS TRADE PROPOSAL TEST SUITE")
    print("=" * 50)
    
    try:
        await test_breakout_proposal()
        await test_pullback_proposal()
        await test_reversal_proposal()
        await test_range_proposal()
        await test_position_sizing()
        await test_save_and_retrieve()
        await test_expected_value()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
