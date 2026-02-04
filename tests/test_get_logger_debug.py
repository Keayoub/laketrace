"""Debug script for get_logger function."""
import sys
import time

print("1. Import get_logger...")
start = time.time()
from laketrace import get_logger
elapsed = time.time() - start
print(f"   Took {elapsed:.3f}s")

print("2. Call get_logger('test')...")
start = time.time()
try:
    logger = get_logger("test")
    elapsed = time.time() - start
    print(f"   Took {elapsed:.3f}s")
    print("   ✅ Logger returned!")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Error after {elapsed:.3f}s: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("3. Log a message...")
start = time.time()
try:
    logger.info("Test message")
    elapsed = time.time() - start
    print(f"   Took {elapsed:.3f}s")
    print("   ✅ Message logged!")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Error after {elapsed:.3f}s: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ All complete!")
