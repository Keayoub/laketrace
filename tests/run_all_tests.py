"""
Unified Test Runner

Runs all reusable test modules in the tests folder.
"""

import os
import sys
import subprocess


TEST_FILES = [
    "test_core_direct.py",
    "test_minimal.py",
    "test_stdout_only.py",
    "test_vendored_logger.py",
    "test_security.py",
    "test_phase1_rotation.py",
    "test_phase1_retention.py",
    "test_phase1_compression.py",
    "test_phase1_handler_ids.py",
    "test_phase1_enqueue.py",
    "test_phase1_formatters_filters.py",
    "test_phase2_advanced.py",
    "test_phase3_performance.py",
]


def run_test(test_file):
    """Run a single test file."""
    print(f"\n{'=' * 70}")
    print(f"Running: {test_file}")
    print("=" * 70)

    result = subprocess.run(
        [sys.executable, test_file],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    return result.returncode == 0


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("LAKETRACE COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"Running {len(TEST_FILES)} test modules...\n")

    results = {}
    for test_file in TEST_FILES:
        results[test_file] = run_test(test_file)

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_file, success in results.items():
        status = "[PASS] PASS" if success else "[FAIL] FAIL"
        print(f"{status}: {test_file}")

    print(f"\nTotal: {passed}/{total} passed")
    print("=" * 70)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())