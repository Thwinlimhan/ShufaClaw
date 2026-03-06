#!/usr/bin/env python3
"""
Verification script to test all code quality fixes.
Run this to verify the fixes are working correctly.
"""

import sys
import traceback

def test_database_validation():
    """Test database path validation."""
    print("Testing database path validation...")
    from intelligence.database import Database
    
    # Test valid path
    try:
        db = Database("test_memory.db")
        print("  [OK] Valid path accepted")
    except Exception as e:
        print(f"  [FAIL] Valid path rejected: {e}")
        return False
    
    # Test invalid path with ..
    try:
        db = Database("../../../etc/passwd")
        print("  [FAIL] Path traversal not blocked!")
        return False
    except ValueError as e:
        print(f"  [OK] Path traversal blocked: {e}")
    
    # Test empty path
    try:
        db = Database("")
        print("  [FAIL] Empty path not blocked!")
        return False
    except ValueError as e:
        print(f"  [OK] Empty path blocked: {e}")
    
    return True

def test_memory_validation():
    """Test memory system input validation."""
    print("\nTesting memory system validation...")
    from intelligence.memory import MemorySystem
    
    memory = MemorySystem("test_memory.db")
    
    # Test valid insight
    try:
        memory.record_market_insight(
            'BTC', 
            'pattern', 
            'Test insight',
            confidence=3
        )
        print("  [OK] Valid insight accepted")
    except Exception as e:
        print(f"  [FAIL] Valid insight rejected: {e}")
        return False
    
    # Test invalid confidence
    try:
        memory.record_market_insight(
            'BTC',
            'pattern',
            'Test insight',
            confidence=10  # Invalid!
        )
        print("  [FAIL] Invalid confidence not blocked!")
        return False
    except ValueError as e:
        print(f"  [OK] Invalid confidence blocked: {e}")
    
    # Test empty symbol
    try:
        memory.record_market_insight(
            '',  # Invalid!
            'pattern',
            'Test insight',
            confidence=3
        )
        print("  [FAIL] Empty symbol not blocked!")
        return False
    except ValueError as e:
        print(f"  [OK] Empty symbol blocked: {e}")
    
    # Test too long insight
    try:
        memory.record_market_insight(
            'BTC',
            'pattern',
            'x' * 2000,  # Too long!
            confidence=3
        )
        print("  [FAIL] Long insight not blocked!")
        return False
    except ValueError as e:
        print(f"  [OK] Long insight blocked: {e}")
    
    return True

def test_cache_limits():
    """Test cache size limits."""
    print("\nTesting cache size limits...")
    from crypto_agent.data.cache import InMemoryCache
    
    # Create small cache
    cache = InMemoryCache(default_ttl_seconds=60, max_size=3)
    
    # Add items
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    if cache.get_stats()['size'] != 3:
        print(f"  [FAIL] Cache size incorrect: {cache.get_stats()['size']}")
        return False
    
    print(f"  [OK] Cache at max size: {cache.get_stats()['size']}")
    
    # Add one more - should evict oldest
    cache.set("key4", "value4")
    
    if cache.get_stats()['size'] != 3:
        print(f"  [FAIL] Cache exceeded max size: {cache.get_stats()['size']}")
        return False
    
    if cache.get_stats()['evictions'] != 1:
        print(f"  [FAIL] Eviction not tracked: {cache.get_stats()['evictions']}")
        return False
    
    print(f"  [OK] Cache evicted oldest entry")
    print(f"  [OK] Evictions tracked: {cache.get_stats()['evictions']}")
    
    # Verify oldest was evicted
    if cache.get("key1") is not None:
        print("  [FAIL] Oldest entry not evicted!")
        return False
    
    print("  [OK] Oldest entry correctly evicted")
    
    return True

def test_workflow_validation():
    """Test workflow validation."""
    print("\nTesting workflow validation...")
    from crypto_agent.core.workflow_engine import Workflow, WorkflowStep
    
    # Test valid workflow
    try:
        async def dummy_action(context):
            return "done"
        
        step = WorkflowStep("Test Step", dummy_action)
        workflow = Workflow("test", "Test workflow", [step])
        print("  [OK] Valid workflow accepted")
    except Exception as e:
        print(f"  [FAIL] Valid workflow rejected: {e}")
        return False
    
    # Test empty name
    try:
        workflow = Workflow("", "Test workflow", [step])
        print("  [FAIL] Empty name not blocked!")
        return False
    except ValueError as e:
        print(f"  [OK] Empty name blocked: {e}")
    
    # Test empty steps
    try:
        workflow = Workflow("test", "Test workflow", [])
        print("  [FAIL] Empty steps not blocked!")
        return False
    except ValueError as e:
        print(f"  [OK] Empty steps blocked: {e}")
    
    return True

def test_json_parsing():
    """Test safe JSON parsing."""
    print("\nTesting safe JSON parsing...")
    from intelligence.memory import MemorySystem
    
    memory = MemorySystem("test_memory.db")
    
    # Get profile (should handle missing/invalid JSON gracefully)
    try:
        profile = memory.get_trading_profile()
        print("  [OK] Profile retrieved without crash")
        
        if isinstance(profile, dict):
            print("  [OK] Profile is valid dict")
        else:
            print(f"  [FAIL] Profile is not dict: {type(profile)}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Profile retrieval failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("CODE QUALITY VERIFICATION")
    print("=" * 60)
    
    tests = [
        ("Database Validation", test_database_validation),
        ("Memory Validation", test_memory_validation),
        ("Cache Limits", test_cache_limits),
        ("Workflow Validation", test_workflow_validation),
        ("JSON Parsing", test_json_parsing),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n[FAIL] {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n[FAIL] {name} CRASHED: {e}")
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\nALL TESTS PASSED!")
        print("\nCode quality fixes are working correctly.")
        return 0
    else:
        print(f"\n{failed} TEST(S) FAILED")
        print("\nPlease review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
