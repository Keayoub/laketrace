"""Debug script to find exact hang location."""
import sys
import os
from pathlib import Path

print("1. Test Path operations...")
log_dir = Path("/tmp/laketrace_logs")
print(f"   log_dir: {log_dir}")

print("2. Mkdir operations...")
log_dir.mkdir(parents=True, exist_ok=True)
print(f"   Created: {log_dir.exists()}")

print("3. Test os.open...")
log_file = log_dir / "test.log"
print(f"   log_file: {log_file}")

try:
    print("4. Opening file with os.open...")
    fd = os.open(
        str(log_file),
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600
    )
    print(f"   File descriptor: {fd}")
    
    print("5. Converting to file object...")
    f = os.fdopen(fd, 'w', encoding='utf-8')
    print(f"   File object: {f}")
    
    print("6. Writing to file...")
    f.write("Test message\n")
    print("   Write complete")
    
    print("7. Closing file...")
    f.close()
    print("   Close complete")
    
    print("✅ File operations successful!")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
