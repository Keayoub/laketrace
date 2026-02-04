"""Debug script for logger initialization."""
import sys

print("1. Import core_logger...")
from laketrace.core_logger import FileHandler, LogLevel, LogRecord
from datetime import datetime, timezone
from pathlib import Path
import tempfile

print("2. Create temp dir...")
tmpdir = Path(tempfile.gettempdir()) / "laketrace_test"
tmpdir.mkdir(exist_ok=True)
log_file = tmpdir / "test.log"
print(f"   {log_file}")

print("3. Create formatter...")
def test_formatter(record):
    return f"{record.level.name}: {record.message}\n"

print("4. Create FileHandler...")
try:
    handler = FileHandler(str(log_file), formatter=test_formatter)
    print("   ✅ FileHandler created successfully")
except Exception as e:
    print(f"   ❌ Error creating FileHandler: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("5. Create LogRecord...")
try:
    record = LogRecord(
        level=LogLevel.INFO,
        message="Test message",
        logger_name="test",
        timestamp=datetime.now(timezone.utc)
    )
    print("   ✅ LogRecord created")
except Exception as e:
    print(f"   ❌ Error creating LogRecord: {e}")
    sys.exit(1)

print("6. Emit record...")
try:
    handler.emit(record)
    print("   ✅ Record emitted")
except Exception as e:
    print(f"   ❌ Error emitting record: {e}")
    sys.exit(1)

print("✅ All steps complete!")
