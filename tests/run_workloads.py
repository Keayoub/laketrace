"""
Unified Workload Test Runner

Discovers and runs all reusable workload test modules.
"""

import os
import sys
import subprocess


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKLOADS_DIR = os.path.join(BASE_DIR, "workloads")
REPO_ROOT = os.path.dirname(BASE_DIR)


def discover_tests():
    """Discover workload test files under tests/workloads."""
    tests = []
    for root, _, files in os.walk(WORKLOADS_DIR):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            if filename.startswith("_"):
                continue
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, BASE_DIR)
            tests.append(rel_path)

    return sorted(tests)


def run_test(test_file):
    """Run a single test file."""
    print(f"\n{'=' * 70}")
    print(f"Running: {test_file}")
    print("=" * 70)

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
    )

    return result.returncode == 0


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("LAKETRACE COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    test_files = discover_tests()
    print(f"Running {len(test_files)} test modules...\n")

    results = {}
    for test_file in test_files:
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