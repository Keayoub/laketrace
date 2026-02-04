"""Super simple direct test."""
import sys
from pathlib import Path
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from laketrace.core_logger import _CoreLogger, FileHandler, LogLevel

print("1. Create temp dir...")
tmpdir = tempfile.mkdtemp()
print(f"   Temp dir: {tmpdir}")

print("2. Create file handler...")
log_file = Path(tmpdir) / "test.log"
handler = FileHandler(str(log_file))
print(f"   Handler created for: {log_file}")

print("3. Create core logger...")
logger = _CoreLogger.get_logger("test")
print("   Logger created")

print("4. Add handler...")
logger.add_handler(handler)
print("   Handler added")

print("5. Log message...")
logger.info("Test message")
print("   Message logged!")

print("✅ Direct core logger test passed!")
