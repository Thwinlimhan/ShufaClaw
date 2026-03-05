"""
Scenario Tester (Level 38)

Test bot components against predefined scenarios to ensure
correct behavior in various market conditions.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from .mock_services import (
    MockPriceService,
    MockMarketService,
    MockTAService,
    MockDatabase
)
from .data_generators import (
    generate_market_scenario,
    generate_portfolio_scenario,
    generate_trade_setup_scenario
)


class ScenarioTester:
    """
    Test bot components against various market scenarios.
    """
    
    def __init__(self):
        self.price_service = MockPriceService()
        self.market_service = MockMarketService()
        self.ta_service = MockTAService()
        self.db = MockDatabase()
        
        self.test_results = []
    
    async def test_trade_proposal_scenarios(self, proposer) -> Dict[str, Any]:
        """
        Test trade proposer against all setup types.
        """
        print("\n🧪 Testing Trade Proposal Scenarios...")
        
        results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        setup_types = ['breakout', 'pullback', 'reversal', 'range', 'momentum']
        
        for setup_type in setup_types:
            # Generate scenario
            scenario = generate_trade_setup_scenario(setup_type, 'BTC')
            
            # Set TA service to return this scenario
            self.ta_service.set_scenario('BTC', scenario)
            
            # Generate proposal
            proposal = await proposer.generate_proposal('BTC', '4h')
            
            results['total_tests'] += 1
            
            # Verify correct setup detected
            if proposal and proposal.setup_type.value == scenario['expected_setup']:
                results['passed'] += 1
                status = '✅'
            else:
                results['failed'] += 1
                status = '❌'
            
            results['details'].append({
                'scenario': setup_type,
                'expected': scenario['expected_setup'],
                'actual': proposal.setup_type.value if proposal else None,
                'status': status
            })
            
            print(f"{status} {setup_type.upper()}: Expected {scenario['expected_setup']}, "
                  f"Got {proposal.setup_type.value if proposal else 'None'}")
        
        # Clear scenarios
        self.ta_service.clear_scenarios()
        
        return results
    
    async def test_market_scenarios(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test bot behavior in different market conditions.
        """
        print("\n🧪 Testing Market Scenarios...")
        
        results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        scenarios = ['bull_run', 'bear_market', 'sideways', 'volatile', 'crash', 'recovery']
        
        for scenario_name in scenarios:
            scenario = generate_market_scenario(scenario_name)
            
            # Configure services
            self.market_service.set_fear_greed(scenario['fear_greed'])
            self.price_service.set_trend(scenario['trend'])
            self.price_service.set_volatility(scenario['volatility'])
            
            # Test components
            test_passed = True
            
            # Test 1: Fear & Greed matches
            fg = await self.market_service.get_fear_greed_index()
            if abs(fg['value'] - scenario['fear_greed']) > 10:
                test_passed = False
            
            # Test 2: Price trend matches
            initial_price = self.price_service.base_prices['BTC']
            await asyncio.sleep(0.1)  # Simulate time passing
            new_price_data = await self.price_service.get_price('BTC')
            new_price = new_price_data['price']
            
            price_change = (new_price - initial_price) / initial_price
            trend_matches = (
                (scenario['trend'] > 0 and price_change > 0) or
                (scenario['trend'] < 0 and price_change < 0) or
                (scenario['trend'] == 0)
            )
            
            if not trend_matches:
                test_passed = False
            
            results['total_tests'] += 1
            if test_passed:
                results['passed'] += 1
                status = '✅'
            else:
                results['failed'] += 1
                status = '❌'
            
            results['details'].append({
                'scenario': scenario_name,
                'fear_greed': fg['value'],
                'trend_correct': trend_matches,
                'status': status
            })
            
            print(f"{status} {scenario['name']}: F&G={fg['value']}, Trend={'✓' if trend_matches else '✗'}")
            
            # Reset for next scenario
            self.price_service.reset_prices()
        
        return results
    
    async def test_portfolio_scenarios(self, optimizer=None) -> Dict[str, Any]:
        """
        Test portfolio optimizer against different portfolio types.
        """
        print("\n🧪 Testing Portfolio Scenarios...")
        
        results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        scenarios = ['diversified', 'concentrated', 'risky', 'conservative', 'losing', 'winning']
        
        for scenario_name in scenarios:
            scenario = generate_portfolio_scenario(scenario_name, 10000)
            
            # Add positions to mock database
            self.db.clear_all()
            for pos in scenario['positions']:
                await self.db.add_position(
                    user_id=123,
                    symbol=pos['symbol'],
                    amount=pos['amount'],
                    entry_price=pos['entry_price']
                )
            
            # Get positions
            positions = await self.db.get_positions(123)
            
            results['total_tests'] += 1
            
            # Verify positions match scenario
            if len(positions) == len(scenario['positions']):
                results['passed'] += 1
                status = '✅'
            else:
                results['failed'] += 1
                status = '❌'
            
            results['details'].append({
                'scenario': scenario_name,
                'expected_positions': len(scenario['positions']),
                'actual_positions': len(positions),
                'risk_level': scenario['risk_level'],
                'status': status
            })
            
            print(f"{status} {scenario['name']}: {len(positions)} positions, "
                  f"Risk: {scenario['risk_level']}")
        
        return results
    
    async def test_alert_system(self) -> Dict[str, Any]:
        """
        Test alert creation and triggering.
        """
        print("\n🧪 Testing Alert System...")
        
        results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        # Test 1: Create alert
        alert_id = await self.db.create_alert(
            user_id=123,
            symbol='BTC',
            target_price=100000,
            direction='above'
        )
        
        results['total_tests'] += 1
        if alert_id:
            results['passed'] += 1
            print("✅ Alert creation: Success")
        else:
            results['failed'] += 1
            print("❌ Alert creation: Failed")
        
        # Test 2: Get active alerts
        alerts = await self.db.get_active_alerts(123)
        
        results['total_tests'] += 1
        if len(alerts) == 1:
            results['passed'] += 1
            print("✅ Get active alerts: Success")
        else:
            results['failed'] += 1
            print("❌ Get active alerts: Failed")
        
        # Test 3: Deactivate alert
        await self.db.deactivate_alert(alert_id)
        alerts = await self.db.get_active_alerts(123)
        
        results['total_tests'] += 1
        if len(alerts) == 0:
            results['passed'] += 1
            print("✅ Deactivate alert: Success")
        else:
            results['failed'] += 1
            print("❌ Deactivate alert: Failed")
        
        return results
    
    async def test_journal_system(self) -> Dict[str, Any]:
        """
        Test journal entry creation and retrieval.
        """
        print("\n🧪 Testing Journal System...")
        
        results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        # Test 1: Add journal entry
        await self.db.add_journal_entry(
            user_id=123,
            entry="Bought BTC at support",
            symbol='BTC'
        )
        
        entries = await self.db.get_journal_entries(123, days=7)
        
        results['total_tests'] += 1
        if len(entries) == 1:
            results['passed'] += 1
            print("✅ Add journal entry: Success")
        else:
            results['failed'] += 1
            print("❌ Add journal entry: Failed")
        
        # Test 2: Add multiple entries
        await self.db.add_journal_entry(123, "Sold ETH at resistance", 'ETH')
        await self.db.add_journal_entry(123, "Market looking bullish", None)
        
        entries = await self.db.get_journal_entries(123, days=7)
        
        results['total_tests'] += 1
        if len(entries) == 3:
            results['passed'] += 1
            print("✅ Multiple journal entries: Success")
        else:
            results['failed'] += 1
            print("❌ Multiple journal entries: Failed")
        
        return results
    
    async def run_full_test_suite(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run complete test suite across all scenarios.
        
        Args:
            components: Dict with 'proposer', 'optimizer', etc.
        """
        print("=" * 60)
        print("SCENARIO TEST SUITE")
        print("=" * 60)
        
        all_results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'total_passed': 0,
            'total_failed': 0,
            'test_suites': {}
        }
        
        # Test 1: Trade Proposals
        if 'proposer' in components:
            proposal_results = await self.test_trade_proposal_scenarios(
                components['proposer']
            )
            all_results['test_suites']['trade_proposals'] = proposal_results
            all_results['total_tests'] += proposal_results['total_tests']
            all_results['total_passed'] += proposal_results['passed']
            all_results['total_failed'] += proposal_results['failed']
        
        # Test 2: Market Scenarios
        market_results = await self.test_market_scenarios(components)
        all_results['test_suites']['market_scenarios'] = market_results
        all_results['total_tests'] += market_results['total_tests']
        all_results['total_passed'] += market_results['passed']
        all_results['total_failed'] += market_results['failed']
        
        # Test 3: Portfolio Scenarios
        portfolio_results = await self.test_portfolio_scenarios(
            components.get('optimizer')
        )
        all_results['test_suites']['portfolio_scenarios'] = portfolio_results
        all_results['total_tests'] += portfolio_results['total_tests']
        all_results['total_passed'] += portfolio_results['passed']
        all_results['total_failed'] += portfolio_results['failed']
        
        # Test 4: Alert System
        alert_results = await self.test_alert_system()
        all_results['test_suites']['alert_system'] = alert_results
        all_results['total_tests'] += alert_results['total_tests']
        all_results['total_passed'] += alert_results['passed']
        all_results['total_failed'] += alert_results['failed']
        
        # Test 5: Journal System
        journal_results = await self.test_journal_system()
        all_results['test_suites']['journal_system'] = journal_results
        all_results['total_tests'] += journal_results['total_tests']
        all_results['total_passed'] += journal_results['passed']
        all_results['total_failed'] += journal_results['failed']
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {all_results['total_tests']}")
        print(f"Passed: {all_results['total_passed']} ✅")
        print(f"Failed: {all_results['total_failed']} ❌")
        
        success_rate = (all_results['total_passed'] / all_results['total_tests'] * 100) if all_results['total_tests'] > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if all_results['total_failed'] == 0:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {all_results['total_failed']} tests failed")
        
        print("=" * 60)
        
        return all_results
    
    def get_mock_services(self) -> Dict[str, Any]:
        """Get mock services for use in tests"""
        return {
            'price_service': self.price_service,
            'market_service': self.market_service,
            'ta_service': self.ta_service,
            'db': self.db
        }
