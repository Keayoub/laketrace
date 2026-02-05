#!/usr/bin/env python
"""
Unified Test Runner for LakeTrace

Consolidates quick tests + comprehensive workloads into a single pipeline-ready script.
Suitable for CI/CD pipelines with clear exit codes and structured output.

Usage:
    python tests/run_tests.py              # Run all tests (quick + workloads)
    python tests/run_tests.py --quick      # Run only quick tests
    python tests/run_tests.py --workloads  # Run only workload tests
    python tests/run_tests.py --verbose    # Detailed output
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)
WORKLOADS_DIR = os.path.join(BASE_DIR, "workloads")


# ============================================================================
# QUICK TESTS (Core Functionality)
# ============================================================================

def test_basic_logger():
    """Test basic logger creation and usage."""
    from laketrace import get_logger
    
    logger = get_logger("test_basic")
    logger.info("Test message from basic logger")


def test_security_features():
    """Test newly added security features."""
    from laketrace.security import (
        DataLeakDetector,
        FieldWhitelist,
        SensitiveDataRedactor,
        LogIntegrityVerifier,
        get_secure_file_opener,
    )
    
    # DataLeakDetector
    detector = DataLeakDetector(max_log_size_kb=50)
    is_safe, _ = detector.check_log_record("test", {"field": "value"})
    assert is_safe, "Simple log should be safe"
    
    # FieldWhitelist
    whitelist = FieldWhitelist(
        allowed_fields={"user_id", "action", "status"},
        strict=True,
    )
    data = {"user_id": "123", "action": "login", "password": "secret"}
    safe_data, _ = whitelist.validate_record(data)
    assert "password" not in safe_data, "Password should be blocked"
    assert "user_id" in safe_data, "user_id should be allowed"
    
    # SensitiveDataRedactor
    redactor = SensitiveDataRedactor()
    text = "Connecting with password=Secret123"
    redacted = redactor.redact(text)
    assert "[REDACTED_PASSWORD]" in redacted, "Password should be redacted"
    assert "Secret123" not in redacted, "Original password should not appear"
    
    # LogIntegrityVerifier
    verifier = LogIntegrityVerifier()
    record = {"action": "login", "user_id": "123"}
    signed = verifier.add_hash_header(record)
    assert "_integrity_hash" in signed, "Hash should be added"
    is_valid = verifier.verify_record(record, signed["_integrity_hash"])
    assert is_valid, "Hash should verify"
    
    # secure file opener
    opener = get_secure_file_opener()
    assert callable(opener), "Opener should be callable"


def test_pii_masking():
    """Test PII detection and masking."""
    from laketrace.security import mask_pii, SecurityConfig
    
    config = SecurityConfig(enable_pii_masking=True)
    data = {
        "email": "john@example.com",
        "ssn": "123-45-6789",
        "credit_card": "4111-1111-1111-1111",
        "action": "update",
    }
    
    masked = mask_pii(data, config)
    assert masked["email"] != "john@example.com", "Email should be masked"
    assert masked["ssn"] != "123-45-6789", "SSN should be masked"
    assert masked["credit_card"] != "4111-1111-1111-1111", "Credit card should be masked"
    assert masked["action"] == "update", "Non-PII should not be masked"


def test_logger_binding():
    """Test logger context binding."""
    from laketrace import get_logger
    
    logger = get_logger("test_binding")
    bound_logger = logger.bind(user_id="user_123", request_id="req_456")
    bound_logger.info("Message with context")


def test_runtime_detection():
    """Test runtime environment detection."""
    from laketrace.runtime import detect_runtime
    
    runtime = detect_runtime()
    assert runtime.platform is not None, "Should detect platform"
    assert hasattr(runtime, 'runtime_type'), "Should detect runtime type"


QUICK_TESTS = [
    ("Basic Logger", test_basic_logger),
    ("Security Features", test_security_features),
    ("PII Masking", test_pii_masking),
    ("Logger Binding", test_logger_binding),
    ("Runtime Detection", test_runtime_detection),
]


# ============================================================================
# WORKLOAD TESTS (Comprehensive)
# ============================================================================

def discover_workload_tests():
    """Discover workload test files under tests/workloads."""
    tests = []
    for root, _, files in os.walk(WORKLOADS_DIR):
        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            if filename.startswith("_"):
                continue
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, BASE_DIR)
            tests.append(rel_path)
    return sorted(tests)


def run_workload_test(test_file, verbose=False):
    """Run a single workload test file."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing}"
        if existing
        else REPO_ROOT
    )

    result = subprocess.run(
        [sys.executable, test_file],
        cwd=BASE_DIR,
        env=env,
        capture_output=not verbose,
        text=True,
    )

    return result.returncode == 0, result


# ============================================================================
# RUNNER
# ============================================================================

def run_quick_tests(verbose=False):
    """Run all quick tests."""
    print("\n" + "=" * 70)
    print("QUICK TESTS (Core Functionality)")
    print("=" * 70)
    
    # Add repo to path for imports
    sys.path.insert(0, REPO_ROOT)
    
    passed = 0
    failed = 0
    
    for test_name, test_func in QUICK_TESTS:
        try:
            if verbose:
                print(f"\n  Running: {test_name}...", end=" ")
            test_func()
            passed += 1
            if verbose:
                print("OK")
            else:
                print(".", end="", flush=True)
        except Exception as e:
            failed += 1
            if verbose:
                print(f"FAIL\n    {type(e).__name__}: {e}")
            else:
                print("F", end="", flush=True)
    
    if not verbose:
        print()  # newline after dots
    
    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


def run_workload_tests(verbose=False):
    """Run all workload tests."""
    print("\n" + "=" * 70)
    print("WORKLOAD TESTS (Comprehensive)")
    print("=" * 70)
    
    test_files = discover_workload_tests()
    
    if not test_files:
        print("No workload tests found.")
        return True
    
    print(f"Discovered {len(test_files)} test modules\n")
    
    passed = 0
    failed = 0
    results = {}
    
    for test_file in test_files:
        if verbose:
            print(f"\n  Running: {test_file}...", end=" ")
        
        success, result = run_workload_test(test_file, verbose=verbose)
        results[test_file] = success
        
        if success:
            passed += 1
            if verbose:
                print("OK")
            else:
                print(".", end="", flush=True)
        else:
            failed += 1
            if verbose:
                print(f"FAIL\n    {result.stderr or result.stdout}")
            else:
                print("F", end="", flush=True)
    
    if not verbose:
        print()  # newline after dots
    
    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified test runner for LakeTrace"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only quick tests",
    )
    parser.add_argument(
        "--workloads",
        action="store_true",
        help="Run only workload tests",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    # Default: run both if neither specified
    run_quick = not args.workloads or (not args.quick and not args.workloads)
    run_workloads = not args.quick or (not args.quick and not args.workloads)
    
    print("\n" + "=" * 70)
    print("LAKETRACE UNIFIED TEST SUITE")
    print("=" * 70)
    
    results = {}
    
    if run_quick:
        results['quick'] = run_quick_tests(verbose=args.verbose)
    
    if run_workloads:
        results['workloads'] = run_workload_tests(verbose=args.verbose)
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = all(results.values())
    
    if 'quick' in results:
        status = "PASSED" if results['quick'] else "FAILED"
        print(f"Quick Tests:    {status}")
    
    if 'workloads' in results:
        status = "PASSED" if results['workloads'] else "FAILED"
        print(f"Workload Tests: {status}")
    
    print("=" * 70)
    
    if all_passed:
        print("\nALL TESTS PASSED\n")
        return 0
    else:
        print("\nSOME TESTS FAILED\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
