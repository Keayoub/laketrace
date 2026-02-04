"""Debug script for runtime detection."""
import sys
import time

print("1. Import runtime module...")
start = time.time()
from laketrace.runtime import detect_runtime
elapsed = time.time() - start
print(f"   Took {elapsed:.3f}s")

print("2. Call detect_runtime()...")
start = time.time()
try:
    context = detect_runtime()
    elapsed = time.time() - start
    print(f"   Took {elapsed:.3f}s")
    print(f"   Platform: {context.platform.value}")
    print(f"   Type: {context.runtime_type.value}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ Runtime detection complete!")
