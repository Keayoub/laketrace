# Unified Test Runner

## Overview

`tests/run_tests.py` is the **single consolidated test script** for LakeTrace, designed for use in CI/CD pipelines. It combines:

1. **Quick Tests** (5 tests) - Core functionality verification (~2 seconds)
2. **Workload Tests** (13+ tests) - Comprehensive coverage (varies by workload)

## Quick Start

```bash
# Run all tests (default)
python tests/run_tests.py

# Run only quick tests
python tests/run_tests.py --quick

# Run only workload tests  
python tests/run_tests.py --workloads

# Verbose output
python tests/run_tests.py --verbose
```

## Pipeline Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: python tests/run_tests.py
```

### Azure Pipelines Example
```yaml
- script: python tests/run_tests.py
  displayName: 'Run Tests'
```

### Jenkins Example
```groovy
stage('Test') {
    steps {
        sh 'python tests/run_tests.py'
    }
}
```

## Exit Codes

- **0** - All tests passed ✓
- **1** - One or more tests failed ✗

## Quick Tests (Core Functionality)

These 5 tests verify basic logger functionality:

1. **Basic Logger** - Logger creation and message logging
2. **Security Features** - All 7 security classes (DataLeakDetector, FieldWhitelist, etc.)
3. **PII Masking** - Email, SSN, credit card masking
4. **Logger Binding** - Context binding and propagation
5. **Runtime Detection** - Environment platform detection

**Runtime:** ~2 seconds
**Dependencies:** Only laketrace imports (no external workloads)

## Workload Tests (Comprehensive)

Automatically discovers and runs test modules under `tests/workloads/`:

- `basic/` - Core functionality tests
- `core/` - Rotation, retention, compression, handlers
- `advanced/` - Advanced features
- `performance/` - Performance benchmarks
- `security/` - Security features validation

**Runtime:** Varies (typically 10-30 seconds)
**Modules:** Auto-discovered

## Test Output

### Default Output (Compact)
```
======================================================================
LAKETRACE UNIFIED TEST SUITE
======================================================================

======================================================================
QUICK TESTS (Core Functionality)
======================================================================
.....

  5 passed, 0 failed

======================================================================
WORKLOAD TESTS (Comprehensive)
======================================================================
Discovered 13 test modules

.............

  13 passed, 0 failed

======================================================================
TEST SUMMARY
======================================================================
Quick Tests:    ✓ PASSED
Workload Tests: ✓ PASSED
======================================================================

✓ ALL TESTS PASSED
```

### Verbose Output
```
======================================================================
QUICK TESTS (Core Functionality)
======================================================================

  Running: Basic Logger... ✓
  Running: Security Features... ✓
  Running: PII Masking... ✓
  Running: Logger Binding... ✓
  Running: Runtime Detection... ✓

  5 passed, 0 failed
```

## Usage in Scripts

```bash
#!/bin/bash

# Run tests
if ! python tests/run_tests.py; then
    echo "Tests failed!"
    exit 1
fi

echo "All tests passed!"
```

## Deprecated Scripts

The following individual test scripts are now consolidated into `run_tests.py`:

- ~~`test_suite.py`~~ → Use `run_tests.py --quick`
- ~~`run_workloads.py`~~ → Use `run_tests.py --workloads`

Both old scripts are still functional but should not be used in new pipelines.

## Adding New Tests

### Quick Test
Add to the `QUICK_TESTS` list in `run_tests.py`:

```python
def test_my_feature():
    """Test my feature."""
    # Test code here
    pass

QUICK_TESTS = [
    # ... existing tests
    ("My Feature", test_my_feature),
]
```

### Workload Test
Create a new file in `tests/workloads/` subdirectory:

```
tests/workloads/my_category/my_test.py
```

The runner will automatically discover and run it.

## Troubleshooting

### Tests fail with import errors
```bash
# Ensure PYTHONPATH includes repo root
cd d:\laketrace
python tests/run_tests.py
```

### Quick tests pass but workloads fail
```bash
# Run with verbose output to see details
python tests/run_tests.py --verbose

# Or test individual workload
cd tests/workloads/basic
python minimal_smoke.py
```

### Slow test execution
- Use `--quick` for faster feedback: `python tests/run_tests.py --quick`
- Performance workloads are slow by design
- Disable performance tests if needed in pipeline

## CI/CD Best Practices

1. **Use `--quick` for every commit** - Fast feedback
2. **Use full suite on PR merges** - Comprehensive validation
3. **Run nightly with `--workloads`** - Thorough testing
4. **Parse exit code in pipeline** - Fail on non-zero

Example matrix in GitHub Actions:
```yaml
test:
  strategy:
    matrix:
      test-type: [quick, full]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
    - run: python tests/run_tests.py ${{ matrix.test-type == 'quick' && '--quick' || '' }}
```

## Related Files

- [TEST_RESULTS.md](../TEST_RESULTS.md) - Test results documentation
- [TESTS_WORKING.md](../TESTS_WORKING.md) - System status
- [laketrace/](../laketrace/) - Main module
- [examples/](../examples/) - Usage examples
