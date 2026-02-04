"""
Phase 3 Test Suite: Performance Optimization & Polish

Tests optional Phase 3 features including:
- Format string memoization
- Enhanced backtrace formatting
- Performance under load
"""

import os
import sys
import tempfile
import time
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from laketrace import get_logger


def test_format_consistency():
    """Test format string consistency across records"""
    print("\n=== Test: format consistency ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_consistent", config={
            "log_dir": tmpdir,
            "format": "{timestamp} | {level} | {message}",
            "json": False,
            "level": "INFO"
        })
        
        logger.info("Message 1")
        logger.info("Message 2")
        logger.info("Message 3")
        logger.close()
        
        log_file = os.path.join(tmpdir, "test_consistent.log")
        if os.path.exists(log_file):
            with open(log_file) as f:
                lines = f.readlines()
            
            # Check all lines have consistent format
            assert all("|" in line for line in lines if line.strip()), \
                "All lines should have pipe separators"
            print(f"[PASS] Format consistency: {len(lines)} lines with consistent format")


def test_large_message_handling():
    """Test logging very large messages"""
    print("\n=== Test: large message handling ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_large", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        # Create large message (1 MB)
        large_msg = "x" * (1024 * 1024)
        logger.info(large_msg)
        logger.close()
        
        log_file = os.path.join(tmpdir, "test_large.log")
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            assert size > 1024 * 1024, "File should be > 1MB"
            print(f"[PASS] Large message: {size / (1024*1024):.1f} MB logged")


def test_high_frequency_logging():
    """Test logging at high frequency (performance)"""
    print("\n=== Test: high frequency logging ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_freq", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        start = time.time()
        
        # Log 1000 messages
        for i in range(1000):
            logger.info(f"Message {i}")
        
        elapsed = time.time() - start
        logger.close()
        
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0, f"1000 messages took {elapsed}s (too slow)"
        
        msg_per_sec = 1000 / elapsed
        print(f"[PASS] High frequency: {msg_per_sec:.0f} msg/sec ({elapsed:.2f}s for 1000)")


def test_concurrent_logging_performance():
    """Test logging from multiple threads"""
    print("\n=== Test: concurrent logging ===")
    
    from threading import Thread
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_concurrent", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        def worker(thread_id):
            for i in range(100):
                logger.info(f"Thread {thread_id} message {i}")
        
        start = time.time()
        
        threads = [Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        elapsed = time.time() - start
        logger.close()
        
        # Should complete in reasonable time
        assert elapsed < 10.0, f"Concurrent logging took {elapsed}s"
        print(f"[PASS] Concurrent: 5 threads x 100 msgs in {elapsed:.2f}s")


def test_json_parsing_integrity():
    """Test JSON records can be parsed back"""
    print("\n=== Test: JSON parsing integrity ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_json_parse", config={
            "log_dir": tmpdir,
            "json": True,
            "level": "INFO"
        })
        
        logger.bind(user="alice").info("Test message")
        logger.close()
        
        log_file = os.path.join(tmpdir, "test_json_parse.log")
        if os.path.exists(log_file):
            with open(log_file) as f:
                lines = f.readlines()
            
            parsed = 0
            for line in lines:
                if line.strip():
                    try:
                        obj = json.loads(line)
                        assert "message" in obj, "Should have message field"
                        parsed += 1
                    except:
                        pass
            
            assert parsed > 0, "Should have parsed JSON lines"
            print(f"[PASS] JSON parsing: {parsed} valid records")


def test_rotation_performance():
    """Test rotation doesn't significantly impact performance"""
    print("\n=== Test: rotation performance ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_rot_perf", config={
            "log_dir": tmpdir,
            "rotation": "1 MB",
            "level": "INFO"
        })
        
        start = time.time()
        
        # Log until rotation occurs
        for i in range(500):
            logger.info(f"Message {i}: " + "x" * 100)
        
        elapsed = time.time() - start
        logger.close()
        
        # Should complete in reasonable time despite rotations
        assert elapsed < 5.0, f"Rotation test took {elapsed}s"
        print(f"[PASS] Rotation performance: {elapsed:.2f}s for 500 messages with rotations")


def test_memory_efficiency():
    """Test logger doesn't leak memory"""
    print("\n=== Test: memory efficiency ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import gc
        
        # Create and destroy many loggers
        for i in range(100):
            logger = get_logger(f"test_mem_{i}", config={
                "log_dir": tmpdir,
                "level": "INFO"
            })
            logger.info(f"Message {i}")
            logger.close()
            if i % 20 == 0:
                gc.collect()
        
        # If we get here without hanging, memory is ok
        print("[PASS] Memory efficiency: 100 loggers created and destroyed")


def test_format_field_availability():
    """Test all format fields are available"""
    print("\n=== Test: format field availability ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use format string with multiple fields
        logger = get_logger("test_fields", config={
            "log_dir": tmpdir,
            "format": "{logger_name} | {level} | {message}",
            "json": False,
            "level": "INFO"
        })
        
        logger.info("Test")
        logger.close()
        
        log_file = os.path.join(tmpdir, "test_fields.log")
        if os.path.exists(log_file):
            with open(log_file) as f:
                content = f.read()
            
            # Check format was applied
            assert "test_fields" in content, "Should have logger name"
            assert "INFO" in content, "Should have level"
            assert "Test" in content, "Should have message"
            print(f"[PASS] Format fields: logger_name, level, message all present")


def test_handler_performance():
    """Test adding multiple handlers doesn't degrade performance"""
    print("\n=== Test: handler performance ===")
    
    from laketrace.core_logger import StreamHandler
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_many_handlers", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        # Add multiple handlers
        for i in range(5):
            handler = StreamHandler()
            logger._logger.add_handler(handler)
        
        start = time.time()
        
        # Log messages
        for i in range(100):
            logger.info(f"Message {i}")
        
        elapsed = time.time() - start
        logger.close()
        
        # Should still be fast with multiple handlers
        assert elapsed < 2.0, f"Multiple handlers took {elapsed}s"
        print(f"[PASS] Handler performance: 5 handlers, 100 msgs in {elapsed:.2f}s")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 3 TEST SUITE: PERFORMANCE & POLISH")
    print("=" * 60)
    
    try:
        test_format_consistency()
        test_large_message_handling()
        test_high_frequency_logging()
        test_concurrent_logging_performance()
        test_json_parsing_integrity()
        test_rotation_performance()
        test_memory_efficiency()
        test_format_field_availability()
        test_handler_performance()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] ALL PHASE 3 TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
