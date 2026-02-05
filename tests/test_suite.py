#!/usr/bin/env python
"""
Quick test suite to verify LakeTrace is working correctly.

Focuses on core functionality and newly added security features.
"""

import sys
import os

# Add repo root to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

def test_basic_logger():
    """Test basic logger creation and usage."""
    print("\n" + "=" * 70)
    print("TEST 1: Basic Logger Creation & Usage")
    print("=" * 70)
    
    from laketrace import get_logger
    
    logger = get_logger("test_basic")
    logger.info("Test message from basic logger")
    print("✓ Basic logger works")


def test_security_features():
    """Test newly added security features."""
    print("\n" + "=" * 70)
    print("TEST 2: Security Features")
    print("=" * 70)
    
    from laketrace.security import (
        DataLeakDetector,
        FieldWhitelist,
        SensitiveDataRedactor,
        LogIntegrityVerifier,
        get_secure_file_opener,
    )
    
    # Test DataLeakDetector
    print("\n  Testing DataLeakDetector...")
    detector = DataLeakDetector(max_log_size_kb=50)
    is_safe, warnings = detector.check_log_record("test", {"field": "value"})
    assert is_safe, "Simple log should be safe"
    print("  ✓ DataLeakDetector works")
    
    # Test FieldWhitelist
    print("\n  Testing FieldWhitelist...")
    whitelist = FieldWhitelist(
        allowed_fields={"user_id", "action", "status"},
        strict=True,
    )
    data = {"user_id": "123", "action": "login", "password": "secret"}
    safe_data, warnings = whitelist.validate_record(data)
    assert "password" not in safe_data, "Password should be blocked"
    assert "user_id" in safe_data, "user_id should be allowed"
    print("  ✓ FieldWhitelist works (blocks sensitive fields)")
    
    # Test SensitiveDataRedactor
    print("\n  Testing SensitiveDataRedactor...")
    redactor = SensitiveDataRedactor()
    text = "Connecting with password=Secret123"
    redacted = redactor.redact(text)
    assert "[REDACTED_PASSWORD]" in redacted, "Password should be redacted"
    assert "Secret123" not in redacted, "Original password should not appear"
    print("  ✓ SensitiveDataRedactor works")
    
    # Test LogIntegrityVerifier
    print("\n  Testing LogIntegrityVerifier...")
    verifier = LogIntegrityVerifier()
    record = {"action": "login", "user_id": "123"}
    signed = verifier.add_hash_header(record)
    assert "_integrity_hash" in signed, "Hash should be added"
    is_valid = verifier.verify_record(record, signed["_integrity_hash"])
    assert is_valid, "Hash should verify"
    print("  ✓ LogIntegrityVerifier works")
    
    # Test secure file opener
    print("\n  Testing get_secure_file_opener...")
    opener = get_secure_file_opener()
    assert callable(opener), "Opener should be callable"
    print("  ✓ get_secure_file_opener works")


def test_pii_masking():
    """Test PII detection and masking."""
    print("\n" + "=" * 70)
    print("TEST 3: PII Masking")
    print("=" * 70)
    
    from laketrace.security import mask_pii, SecurityConfig
    
    config = SecurityConfig(enable_pii_masking=True)
    
    data = {
        "email": "john@example.com",
        "ssn": "123-45-6789",
        "credit_card": "4111-1111-1111-1111",
        "action": "update",
    }
    
    masked = mask_pii(data, config)
    
    # Check that PII is masked
    assert masked["email"] != "john@example.com", "Email should be masked"
    assert masked["ssn"] != "123-45-6789", "SSN should be masked"
    assert masked["credit_card"] != "4111-1111-1111-1111", "Credit card should be masked"
    assert masked["action"] == "update", "Non-PII should not be masked"
    
    print("✓ PII masking works (masks emails, SSN, credit cards, etc.)")


def test_logger_binding():
    """Test logger context binding."""
    print("\n" + "=" * 70)
    print("TEST 4: Logger Context Binding")
    print("=" * 70)
    
    from laketrace import get_logger
    
    logger = get_logger("test_binding")
    bound_logger = logger.bind(user_id="user_123", request_id="req_456")
    bound_logger.info("Message with context")
    
    print("✓ Logger binding works")


def test_runtime_detection():
    """Test runtime environment detection."""
    print("\n" + "=" * 70)
    print("TEST 5: Runtime Detection")
    print("=" * 70)
    
    from laketrace.runtime import detect_runtime
    
    runtime = detect_runtime()
    assert runtime.platform is not None, "Should detect platform"
    assert hasattr(runtime, 'runtime_type'), "Should detect runtime type"
    
    print(f"✓ Runtime detection works")
    print(f"  Detected platform: {runtime.platform.value}")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("LAKETRACE TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Basic Logger", test_basic_logger),
        ("Security Features", test_security_features),
        ("PII Masking", test_pii_masking),
        ("Logger Binding", test_logger_binding),
        ("Runtime Detection", test_runtime_detection),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_name} FAILED:")
            print(f"  {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print("=" * 70)
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED!\n")
        return 0
    else:
        print(f"\n✗ {failed} TEST(S) FAILED\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
