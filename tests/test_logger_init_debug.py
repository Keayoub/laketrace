"""Debug script for Logger initialization."""
import sys
import time

print("1. Import Logger...")
start = time.time()
from laketrace.logger import Logger
elapsed = time.time() - start
print(f"   Took {elapsed:.3f}s")

print("2. Create Logger instance...")
start = time.time()
try:
    logger = Logger("test_logger")
    elapsed = time.time() - start
    print(f"   Took {elapsed:.3f}s")
    print("   ✅ Logger created!")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Error after {elapsed:.3f}s: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ Logger initialization complete!")
