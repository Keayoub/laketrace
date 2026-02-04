"""
Phase 1 Test Runner

Runs all Phase 1 tests and reports results
"""

import os
import sys
import subprocess

# Test files for Phase 1
PHASE_1_TESTS = [
    "test_phase1_rotation.py",
    "test_phase1_retention.py",
    "test_phase1_compression.py",
    "test_phase1_handler_ids.py",
    "test_phase1_enqueue.py",
    "test_phase1_formatters_filters.py",
]

def run_test(test_file):
    """Run a single test file"""
    print(f"\n{'='*70}")
    print(f"Running: {test_file}")
    print('='*70)
    
    result = subprocess.run(
        [sys.executable, test_file],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    return result.returncode == 0


def main():
    """Run all Phase 1 tests"""
    print("\n" + "="*70)
    print("PHASE 1 COMPREHENSIVE TEST SUITE")
    print("="*70)
    print(f"Running {len(PHASE_1_TESTS)} test modules...\n")
    
    results = {}
    for test_file in PHASE_1_TESTS:
        results[test_file] = run_test(test_file)
    
    # Summary
    print("\n" + "="*70)
    print("PHASE 1 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_file, success in results.items():
        status = "[PASS] PASS" if success else "[FAIL] FAIL"
        print(f"{status}: {test_file}")
    
    print(f"\nTotal: {passed}/{total} passed")
    print("="*70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
