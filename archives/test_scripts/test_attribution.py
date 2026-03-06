"""
Test suite for performance attribution system.
"""

from crypto_agent.intelligence.performance_attribution import (
    PerformanceAttributor,
    BenchmarkComparator,
    FactorAnalyzer
)


def test_performance_attributor():
    """Test performance attribution calculations."""
    print("\n🧪 Testing Performance Attributor...")
    
    attributor = PerformanceAttributor(db_path="data/test_attribution.db")
    
    # Sample portfolio positions
    positions = [
        {
            'symbol': 'BTC',
            'amount': 0.5,
            'entry_price': 60000,
            'current_price': 65000
        },
        {
            'symbol': 'ETH',
            'amount': 5.0,
            'entry_price': 3000,
            'current_price': 3400
        },
        {
            'symbol': 'SOL',
            'amount': 100,
            'entry_price': 100,
            'current_price': 125
        }
    ]
    
    # Benchmark weights
    benchmark_weights = {'BTC': 0.6, 'ETH': 0.4}
    
    # Calculate attribution
    attribution = attributor.calculate_attribution(
        positions,
        benchmark_weights,
        period_days=30
    )
    
    # Verify results
    assert 'portfolio_return' in attribution
    assert 'benchmark_return' in attribution
    assert 'total_alpha' in attribution
    assert 'selection_effect' in attribution
    assert 'allocation_effect' in attribution
    assert 'timing_effect' in attribution
    assert 'interaction_effect' in attribution
    
    print(f"Portfolio Return: {attribution['portfolio_return']:.2f}%")
    print(f"Benchmark Return: {attribution['benchmark_return']:.2f}%")
    print(f"Total Alpha: {attribution['total_alpha']:.2f}%")
    print(f"Selection Effect: {attribution['selection_effect']:.2f}%")
    print(f"Allocation Effect: {attribution['allocation_effect']:.2f}%")
    print(f"Timing Effect: {attribution['timing_effect']:.2f}%")
    
    # Save attribution
    attributor.save_attribution(attribution, benchmark_name="60/40")
    
    # Retrieve history
    history = attributor.get_attribution_history(limit=5)
    assert len(history) >= 1, "Should have at least 1 attribution record"
    
    print("✅ Performance attributor working correctly")


def test_benchmark_comparator():
    """Test benchmark comparison."""
    print("\n🧪 Testing Benchmark Comparator...")
    
    comparator = BenchmarkComparator()
    
    # Compare portfolio to BTC
    comparison = comparator.compare_to_benchmark(
        portfolio_return=18.5,
        benchmark_name='BTC',
        period_days=30
    )
    
    # Verify results
    assert 'portfolio_return' in comparison
    assert 'benchmark_return' in comparison
    assert 'alpha' in comparison
    assert 'beta' in comparison
    assert 'sharpe_ratio' in comparison
    assert 'outperformance' in comparison
    
    print(f"Portfolio Return: {comparison['portfolio_return']:.2f}%")
    print(f"Benchmark Return: {comparison['benchmark_return']:.2f}%")
    print(f"Alpha: {comparison['alpha']:.2f}%")
    print(f"Beta: {comparison['beta']:.2f}")
    print(f"Sharpe Ratio: {comparison['sharpe_ratio']:.2f}")
    print(f"Outperformance: {comparison['outperformance']}")
    
    print("✅ Benchmark comparator working correctly")


def test_factor_analyzer():
    """Test factor analysis."""
    print("\n🧪 Testing Factor Analyzer...")
    
    analyzer = FactorAnalyzer(db_path="data/test_attribution.db")
    
    # Sample positions
    positions = [
        {
            'symbol': 'BTC',
            'amount': 0.5,
            'entry_price': 60000,
            'current_price': 65000
        },
        {
            'symbol': 'SOL',
            'amount': 100,
            'entry_price': 100,
            'current_price': 125
        },
        {
            'symbol': 'AVAX',
            'amount': 200,
            'entry_price': 30,
            'current_price': 35
        }
    ]
    
    # Calculate factor exposures
    exposures = analyzer.calculate_factor_exposures(positions)
    
    # Verify results
    assert 'size' in exposures
    assert 'momentum' in exposures
    assert 'value' in exposures
    assert 'quality' in exposures
    assert 'volatility' in exposures
    
    print(f"Size Factor: {exposures['size']:.2f}")
    print(f"Momentum Factor: {exposures['momentum']:.2f}")
    print(f"Value Factor: {exposures['value']:.2f}")
    print(f"Quality Factor: {exposures['quality']:.2f}")
    print(f"Volatility Factor: {exposures['volatility']:.2f}")
    
    # Save exposures
    analyzer.save_factor_exposures(exposures)
    
    print("✅ Factor analyzer working correctly")


def test_portfolio_return_calculation():
    """Test portfolio return calculation."""
    print("\n🧪 Testing Portfolio Return Calculation...")
    
    attributor = PerformanceAttributor()
    
    # Test case 1: Profitable portfolio
    positions = [
        {'symbol': 'BTC', 'amount': 1, 'entry_price': 50000, 'current_price': 60000},
        {'symbol': 'ETH', 'amount': 10, 'entry_price': 2000, 'current_price': 2500}
    ]
    
    portfolio_return = attributor._calculate_portfolio_return(positions)
    
    # Expected: (60000 + 25000) - (50000 + 20000) / (50000 + 20000) = 15000/70000 = 21.43%
    expected_return = ((60000 + 25000) - (50000 + 20000)) / (50000 + 20000) * 100
    
    assert abs(portfolio_return - expected_return) < 0.1, f"Expected {expected_return:.2f}%, got {portfolio_return:.2f}%"
    
    print(f"Portfolio Return: {portfolio_return:.2f}% (Expected: {expected_return:.2f}%)")
    
    # Test case 2: Loss-making portfolio
    positions = [
        {'symbol': 'BTC', 'amount': 1, 'entry_price': 60000, 'current_price': 50000}
    ]
    
    portfolio_return = attributor._calculate_portfolio_return(positions)
    expected_return = -16.67  # -10000/60000
    
    assert portfolio_return < 0, "Should be negative return"
    
    print(f"Loss Portfolio Return: {portfolio_return:.2f}%")
    
    print("✅ Portfolio return calculation working correctly")


def run_all_tests():
    """Run all attribution tests."""
    print("=" * 50)
    print("PERFORMANCE ATTRIBUTION TEST SUITE")
    print("=" * 50)
    
    try:
        test_performance_attributor()
        test_benchmark_comparator()
        test_factor_analyzer()
        test_portfolio_return_calculation()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
