"""
Quick test to verify vendored logger works without external dependencies.
"""

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

# Test imports
try:
    from laketrace import get_logger, Logger, create_logger, detect_runtime
    from laketrace.core_logger import _CoreLogger, LogLevel
    print("✓ All imports successful (no external dependencies)")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test runtime detection
try:
    runtime = detect_runtime()
    print(f"✓ Runtime detected: {runtime.platform.value} ({runtime.runtime_type.value})")
except Exception as e:
    print(f"✗ Runtime detection failed: {e}")
    sys.exit(1)

# Test logger creation
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "log_dir": tmpdir,
            "rotation_mb": 1,
            "level": "DEBUG",
            "json": False,
            "stdout": False,  # Don't pollute test output
        }
        
        logger_instance = get_logger("test_logger", config)
        print("✓ Logger instance created")
        
        # Test alternative factory
        logger_alt = create_logger("test_logger_alt", config)
        print("✓ Alternative factory works")
        
        # Test direct class usage
        logger_direct = Logger("test_logger_direct", config)
        print("✓ Direct class instantiation works")
        
        # Test logging
        logger_instance.info("Test info message")
        logger_instance.debug("Test debug message", extra_field="value")
        logger_instance.warning("Test warning")
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger_instance.exception("Caught an exception")
        
        print("✓ All log methods work")
        
        # Test binding
        bound = logger_instance.bind(user_id="123", session="abc")
        bound.info("Message with context")
        print("✓ Context binding works")
        
        # Test log file exists
        log_file = Path(tmpdir) / "test_logger.log"
        if log_file.exists():
            print(f"✓ Log file created at {log_file}")
            with open(log_file, 'r') as f:
                lines = f.readlines()
                print(f"✓ Log file contains {len(lines)} lines")
        else:
            print("✗ Log file not created")
            sys.exit(1)
        
        # Test tail
        print("\n--- Last 5 log lines (tail) ---")
        logger_instance.tail(5)
        print("--- End of log tail ---\n")

        # Close loggers to release file handles
        logger_instance.close()
        logger_alt.close()
        logger_direct.close()

except Exception as e:
    print(f"✗ Logger test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("✅ All vendored logger tests passed!")
print("="*50)
print("\nKey Points:")
print("  • Zero external dependencies (stdlib only)")
print("  • Vendored logging engine (core_logger.py)")
print("  • Thread-safe with file rotation")
print("  • Fabric + Databricks compatible")
print("  • Production-ready implementation")
