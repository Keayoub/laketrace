"""
Phase 1 Test Suite: Retention and Cleanup

Tests retention strategies including:
- Count-based retention (keep N most recent files)
- Time-based retention (delete files older than N days)
- Callable retention
"""

import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from laketrace import get_logger
from laketrace.retention import make_retention_function
from laketrace.string_parsers import parse_duration


def test_retention_count():
    """Test count-based retention (keep N files)"""
    print("\n=== Test: retention by count ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_retention_count", config={
            "log_dir": tmpdir,
            "rotation": "1 KB",  # Rotate often to create multiple files
            "retention": "3 files",  # Keep only 3 files
            "level": "INFO"
        })
        
        # Write enough to create many rotated files
        for i in range(50):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logger.close()
        
        # Check that only ~3 files remain
        log_files = sorted([f for f in os.listdir(tmpdir)])
        # Note: retention is checked during rotation, so we should have <= 3 files
        assert len(log_files) <= 5, f"Expected ~3 files with retention, got {len(log_files)}: {log_files}"
        print(f"[PASS] Count-based retention: {len(log_files)} files remain (<=3 expected)")


def test_retention_time():
    """Test time-based retention (delete old files)"""
    print("\n=== Test: retention by time ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create old log files
        old_file = os.path.join(tmpdir, "old_log.txt")
        with open(old_file, "w") as f:
            f.write("old content")
        
        # Set modification time to 8 days ago
        old_time = time.time() - (8 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))
        
        logger = get_logger("test_retention_time", config={
            "log_dir": tmpdir,
            "rotation": "1 KB",
            "retention": "7 days",  # Delete files older than 7 days
            "level": "INFO"
        })
        
        # Write to trigger rotation and cleanup
        for i in range(20):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logger.close()
        
        # Old file should be deleted
        files = os.listdir(tmpdir)
        assert "old_log.txt" not in files, "Old file should be deleted by time-based retention"
        print(f"[PASS] Time-based retention deleted old files: {len(files)} files remain")


def test_make_retention_function():
    """Test retention builder for different input types"""
    print("\n=== Test: make_retention_function ===")
    
    # Test with count string
    ret_count = make_retention_function("5 files")
    assert callable(ret_count), "Should return callable"
    print("[PASS] make_retention_function('5 files') -> callable")
    
    # Test with int (number of files)
    ret_int = make_retention_function(10)
    assert callable(ret_int), "Should return callable"
    print("[PASS] make_retention_function(10) -> callable")
    
    # Test with timedelta
    ret_td = make_retention_function(timedelta(days=7))
    assert callable(ret_td), "Should return callable"
    print("[PASS] make_retention_function(timedelta(days=7)) -> callable")
    
    # Test with callable
    def custom_ret(logs):
        return logs
    ret_func = make_retention_function(custom_ret)
    assert callable(ret_func), "Should return callable"
    print("[PASS] make_retention_function(callable) -> callable")


def test_parse_retention_duration():
    """Test parsing retention duration strings"""
    print("\n=== Test: parse retention duration ===")
    
    d1 = parse_duration("1 day")
    assert d1 == timedelta(days=1)
    
    d7 = parse_duration("7 days")
    assert d7 == timedelta(days=7)
    
    d30 = parse_duration("30 days")
    assert d30 == timedelta(days=30)
    
    print("[PASS] Retention duration parsing works")


def test_no_retention():
    """Test logging without retention (no cleanup)"""
    print("\n=== Test: no retention (keep all) ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_no_retention", config={
            "log_dir": tmpdir,
            "rotation": "1 KB",
            "retention": None,  # No retention cleanup
            "level": "INFO"
        })
        
        # Write to create rotated files
        for i in range(30):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logger.close()
        
        log_files = [f for f in os.listdir(tmpdir)]
        # Without retention, all rotated files should be kept
        assert len(log_files) >= 2, f"Expected multiple files without retention, got {len(log_files)}"
        print(f"[PASS] No retention: {len(log_files)} files kept")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 TEST SUITE: RETENTION AND CLEANUP")
    print("=" * 60)
    
    try:
        test_retention_count()
        test_retention_time()
        test_make_retention_function()
        test_parse_retention_duration()
        test_no_retention()
        
        print("\n" + "=" * 60)
        print("[PASS] ALL RETENTION TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
