"""Test with stdout only (no file handler)."""
import sys

print("1. Starting test...")

try:
    print("2. Importing get_logger...")
    from laketrace import get_logger
    print("3. Import successful")
    
    print("4. Creating logger with stdout only...")
    log = get_logger(
        "test",
        config={
            "log_dir": None,  # No file handler
            "stdout": True,
        }
    )
    print("5. Logger created!")
    
    print("6. Logging message...")
    log.info("Test message")
    print("7. Message logged!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ Test complete!")
