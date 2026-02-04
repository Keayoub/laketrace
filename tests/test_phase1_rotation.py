"""
Phase 1 Test Suite: Advanced Rotation Strategies

Tests rotation strategies including:
- Size-based rotation
- Time-based rotation (daily, weekly, interval)
- Callable rotation
- Multiple condition rotation (OR logic)
"""

import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, time as time_obj

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from laketrace import get_logger
from laketrace.rotation import Rotation, make_rotation_function
from laketrace.string_parsers import parse_size, parse_duration


def test_parse_size():
    """Test size parsing for rotation config"""
    print("\n=== Test: parse_size ===")
    assert parse_size("100 B") == 100
    assert parse_size("1 KB") == 1024
    assert parse_size("1 MB") == 1048576
    assert parse_size("1 GB") == 1073741824
    assert parse_size("500 MB") == 524288000
    print("[PASS] Size parsing works")


def test_parse_duration():
    """Test duration parsing for retention config"""
    print("\n=== Test: parse_duration ===")
    assert parse_duration("1 second") == timedelta(seconds=1)
    assert parse_duration("1 minute") == timedelta(minutes=1)
    assert parse_duration("1 hour") == timedelta(hours=1)
    assert parse_duration("1 day") == timedelta(days=1)
    assert parse_duration("1 week") == timedelta(weeks=1)
    assert parse_duration("7 days") == timedelta(days=7)
    print("[PASS] Duration parsing works")


def test_rotation_size():
    """Test size-based rotation"""
    print("\n=== Test: rotation by size ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create logger with size-based rotation (5 KB)
        logger = get_logger("test_rotation", config={
            "log_dir": tmpdir,
            "rotation": "5 KB",  # Rotate after 5 KB
            "retention": "3 files",  # Keep 3 rotated files
            "level": "INFO"
        })
        
        # Write enough data to trigger rotation
        for i in range(100):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logger.close()
        
        # Check that multiple log files were created
        # Logger name is "test_rotation" so files start with "test_rotation"
        log_files = [f for f in os.listdir(tmpdir) if f.startswith("test_rotation")]
        assert len(log_files) > 1, f"Expected multiple rotated files, got {log_files}"
        print(f"[PASS] Size-based rotation created {len(log_files)} files")


def test_rotation_time_daily():
    """Test daily time-based rotation"""
    print("\n=== Test: rotation daily ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_daily", config={
            "log_dir": tmpdir,
            "rotation": "daily",
            "level": "INFO"
        })
        
        # Log a message
        logger.info("Daily rotation test")
        logger.close()
        
        log_files = [f for f in os.listdir(tmpdir) if f.startswith("test_daily")]
        assert len(log_files) >= 1, "Expected at least one log file"
        print(f"[PASS] Daily rotation configured: {log_files}")


def test_rotation_interval():
    """Test interval-based rotation (timedelta)"""
    print("\n=== Test: rotation interval ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create logger with 1-hour rotation interval
        rotation_interval = timedelta(hours=1)
        logger = get_logger("test_interval", config={
            "log_dir": tmpdir,
            "rotation": rotation_interval,
            "level": "INFO"
        })
        
        logger.info("Interval rotation test")
        logger.close()
        
        log_files = [f for f in os.listdir(tmpdir) if f.startswith("test_interval")]
        assert len(log_files) >= 1, "Expected at least one log file"
        print(f"[PASS] Interval rotation configured: {log_files}")


def test_rotation_callable():
    """Test callable rotation function"""
    print("\n=== Test: rotation callable ===")
    
    call_count = {"count": 0}
    
    def should_rotate(record):
        """Rotate every 5 messages"""
        call_count["count"] += 1
        return call_count["count"] % 5 == 0
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_callable", config={
            "log_dir": tmpdir,
            "rotation": should_rotate,
            "level": "INFO"
        })
        
        for i in range(20):
            logger.info(f"Message {i}")
        
        logger.close()
        
        log_files = [f for f in os.listdir(tmpdir) if f.startswith("test_callable")]
        assert len(log_files) >= 1, "Expected at least one log file"
        print(f"[PASS] Callable rotation created {len(log_files)} files")


def test_rotation_class_methods():
    """Test Rotation class static methods"""
    print("\n=== Test: Rotation class methods ===")
    
    # Test forward_day
    now = datetime.now()
    next_day = Rotation.forward_day(now)
    assert isinstance(next_day, datetime), "forward_day should return datetime"
    assert next_day > now, "forward_day should be in future"
    print(f"[PASS] forward_day: {next_day}")
    
    # Test forward_interval
    next_time = Rotation.forward_interval(now, timedelta(hours=1))
    assert isinstance(next_time, datetime), "forward_interval should return datetime"
    assert next_time > now, "forward_interval should be in future"
    print(f"[PASS] forward_interval: {next_time}")


def test_make_rotation_function():
    """Test rotation builder for different input types"""
    print("\n=== Test: make_rotation_function ===")
    
    # Test with size string
    rot_size = make_rotation_function("10 MB")
    assert callable(rot_size), "Should return callable"
    print("[PASS] make_rotation_function('10 MB') -> callable")
    
    # Test with int (size in bytes)
    rot_int = make_rotation_function(1048576)  # 1 MB
    assert callable(rot_int), "Should return callable"
    print("[PASS] make_rotation_function(1048576) -> callable")
    
    # Test with timedelta
    rot_td = make_rotation_function(timedelta(days=1))
    assert callable(rot_td), "Should return callable"
    print("[PASS] make_rotation_function(timedelta(days=1)) -> callable")
    
    # Test with callable
    def custom_rot(record):
        return False
    rot_func = make_rotation_function(custom_rot)
    assert callable(rot_func), "Should return callable"
    print("[PASS] make_rotation_function(callable) -> callable")


def test_no_rotation():
    """Test logging without rotation (None)"""
    print("\n=== Test: no rotation ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_no_rotation", config={
            "log_dir": tmpdir,
            "rotation": None,  # Explicitly no rotation
            "level": "INFO"
        })
        
        for i in range(10):
            logger.info(f"Message {i}")
        
        logger.close()
        
        log_files = [f for f in os.listdir(tmpdir) if f.startswith("test_no_rotation")]
        # Should have exactly 1 file (no rotation)
        assert len(log_files) == 1, f"Expected 1 file with no rotation, got {log_files}"
        print(f"[PASS] No rotation: single file {log_files}")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 TEST SUITE: ROTATION STRATEGIES")
    print("=" * 60)
    
    try:
        test_parse_size()
        test_parse_duration()
        test_rotation_size()
        test_rotation_time_daily()
        test_rotation_interval()
        test_rotation_callable()
        test_rotation_class_methods()
        test_make_rotation_function()
        test_no_rotation()
        
        print("\n" + "=" * 60)
        print("[PASS] ALL ROTATION TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
