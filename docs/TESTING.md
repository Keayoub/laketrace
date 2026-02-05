# Testing Guide

## Quick Start

Run the unified test suite:

```bash
# Full test suite (quick + workloads)
python tests/run_tests.py

# Fast feedback only
python tests/run_tests.py --quick

# Detailed output
python tests/run_tests.py --verbose
```

## Test Coverage

### Quick Tests (5 tests, ~2 seconds)
- Basic logger functionality
- Security features (field whitelisting, PII masking, etc.)
- Context binding
- Runtime detection

### Workload Tests (13+ modules, ~28 seconds)
- Core functionality
- Rotation and retention
- Compression
- Advanced features
- Performance
- Security

## Test Modes

| Command | Time | Purpose |
|---------|------|---------|
| `python tests/run_tests.py` | ~30s | Full validation |
| `python tests/run_tests.py --quick` | ~2s | Fast feedback |
| `python tests/run_tests.py --workloads` | ~28s | Comprehensive only |
| `python tests/run_tests.py --verbose` | Varies | Detailed output |

## Exit Codes

- `0` = All tests passed
- `1` = One or more tests failed

## Local Testing

```bash
# Before committing
python tests/run_tests.py --quick

# Before merging
python tests/run_tests.py
```

## CI/CD Integration

Tests run automatically on every push to main via GitHub Actions.

See `.github/workflows/check-and-test.yml` for workflow configuration.

## Adding Tests

### Quick Test
Add to `QUICK_TESTS` list in `tests/run_tests.py`

### Workload Test
Create file in `tests/workloads/` subdirectory
Auto-discovered and run by test runner

---

## Related Documentation

- [README.md](../README.md) - Main documentation
- [tests/UNIFIED_TEST_RUNNER.md](../tests/UNIFIED_TEST_RUNNER.md) - Complete test reference
- [.github/workflows/check-and-test.yml](../.github/workflows/check-and-test.yml) - CI/CD workflow
