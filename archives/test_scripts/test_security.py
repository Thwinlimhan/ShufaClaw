"""
Test suite for security system.
"""

import time
import asyncio
from crypto_agent.security.security_manager import SecurityManager
from crypto_agent.security.rate_limiter import RateLimiter
from crypto_agent.security.audit_logger import AuditLogger
from crypto_agent.security.anomaly_detector import AnomalyDetector
from crypto_agent.security.encryption import DataEncryption


def test_rate_limiter():
    """Test rate limiting functionality."""
    print("\n🧪 Testing Rate Limiter...")
    
    limiter = RateLimiter()
    user_id = 12345
    
    # Test message limit
    for i in range(30):
        allowed, remaining = limiter.check_message_limit(user_id)
        assert allowed, f"Message {i+1} should be allowed"
    
    # 31st message should be blocked
    allowed, remaining = limiter.check_message_limit(user_id)
    assert not allowed, "31st message should be blocked"
    assert remaining == 0, "No remaining quota"
    
    print("✅ Rate limiter working correctly")


def test_encryption():
    """Test data encryption."""
    print("\n🧪 Testing Encryption...")
    
    encryption = DataEncryption()
    
    # Test string encryption
    original = "sensitive_api_key_12345"
    encrypted = encryption.encrypt(original)
    decrypted = encryption.decrypt(encrypted)
    
    assert encrypted != original, "Data should be encrypted"
    assert decrypted == original, "Decryption should restore original"
    
    # Test dict encryption
    data = {
        'symbol': 'BTC',
        'api_key': 'secret123',
        'amount': 1.5
    }
    
    encrypted_dict = encryption.encrypt_dict(data, ['api_key'])
    assert encrypted_dict['api_key'] != data['api_key'], "API key should be encrypted"
    assert encrypted_dict['symbol'] == data['symbol'], "Other fields unchanged"
    
    decrypted_dict = encryption.decrypt_dict(encrypted_dict, ['api_key'])
    assert decrypted_dict['api_key'] == data['api_key'], "API key should be decrypted"
    
    print("✅ Encryption working correctly")


def test_audit_logger():
    """Test audit logging."""
    print("\n🧪 Testing Audit Logger...")
    
    logger = AuditLogger(db_path="data/test_security.db")
    user_id = 12345
    
    # Log some actions
    logger.log(user_id, 'portfolio_view', result='success')
    logger.log(user_id, 'backup_data', result='success', 
               details={'size': '1.2MB'}, encrypt=True)
    logger.log(user_id, 'invalid_command', result='failed')
    
    # Retrieve logs
    logs = logger.get_recent_logs(user_id, limit=10)
    assert len(logs) >= 3, "Should have at least 3 logs"
    
    # Check failed attempts
    failed = logger.get_failed_attempts(user_id, hours=1)
    assert len(failed) >= 1, "Should have at least 1 failed attempt"
    
    # Get stats
    stats = logger.get_action_stats(user_id, days=1)
    assert stats['total_actions'] >= 3, "Should have at least 3 actions"
    
    print("✅ Audit logger working correctly")


def test_anomaly_detector():
    """Test anomaly detection."""
    print("\n🧪 Testing Anomaly Detector...")
    
    detector = AnomalyDetector()
    user_id = 12345
    
    # Simulate high volume
    for i in range(60):
        detector.record_activity(user_id, f'action_{i}')
    
    anomalies = detector.check_anomalies(user_id)
    high_volume_detected = any(a['type'] == 'high_volume' for a in anomalies)
    assert high_volume_detected, "Should detect high volume"
    
    # Check risk score
    score, level = detector.get_risk_score(user_id)
    assert score > 0, "Risk score should be elevated"
    assert level in ['low', 'medium', 'high', 'critical'], "Valid risk level"
    
    # Get activity summary
    summary = detector.get_activity_summary(user_id, hours=1)
    assert summary['total_actions'] == 60, "Should track all actions"
    
    print("✅ Anomaly detector working correctly")


async def test_security_manager():
    """Test security manager integration."""
    print("\n🧪 Testing Security Manager...")
    
    manager = SecurityManager(db_path="data/test_security.db")
    user_id = 12345
    
    # Test authentication
    allowed, reason = await manager.authenticate(user_id, 'test_action', is_command=True)
    assert allowed, f"Authentication should succeed: {reason}"
    
    # Test 2FA
    manager.enable_2fa(user_id, '1234')
    assert manager.twofa_enabled[user_id], "2FA should be enabled"
    
    verified = manager.verify_pin(user_id, '1234')
    assert verified, "PIN verification should succeed"
    
    # Test encryption
    sensitive = "my_secret_data"
    encrypted = manager.encrypt_sensitive_data(sensitive)
    decrypted = manager.decrypt_sensitive_data(encrypted)
    assert decrypted == sensitive, "Encryption round-trip should work"
    
    # Test security status
    status = manager.get_security_status(user_id)
    assert 'rate_limits' in status, "Status should include rate limits"
    assert 'session' in status, "Status should include session info"
    assert 'risk' in status, "Status should include risk assessment"
    
    print("✅ Security manager working correctly")


def run_all_tests():
    """Run all security tests."""
    print("=" * 50)
    print("SECURITY SYSTEM TEST SUITE")
    print("=" * 50)
    
    try:
        test_rate_limiter()
        test_encryption()
        test_audit_logger()
        test_anomaly_detector()
        asyncio.run(test_security_manager())
        
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
