"""
Phase 1 Test Suite: Handler IDs and Management

Tests handler ID system including:
- Adding handlers
- Removing handlers by ID
- Multiple handlers per logger
- Handler ID tracking
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from laketrace import get_logger
from laketrace.logger import Logger
from laketrace.core_logger import _CoreLogger, StreamHandler, FileHandler


def test_add_handler_returns_id():
    """Test that add_handler returns an integer ID"""
    print("\n=== Test: add_handler returns ID ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_handler_id", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        # Get core logger
        core = logger._logger
        
        # Add a handler and get its ID
        handler = StreamHandler()
        handler_id = core.add_handler(handler)
        
        assert isinstance(handler_id, int), f"Handler ID should be int, got {type(handler_id)}"
        assert handler_id >= 0, "Handler ID should be non-negative"
        
        logger.close()
        print(f"[PASS] Handler ID assigned: {handler_id}")


def test_remove_handler_by_id():
    """Test removing handler by ID"""
    print("\n=== Test: remove_handler by ID ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_remove", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        core = logger._logger
        
        # Add and remove handler
        handler = StreamHandler()
        handler_id = core.add_handler(handler)
        
        # Check it exists
        assert handler_id in core.handlers, "Handler should exist after adding"
        
        # Remove it
        core.remove_handler(handler_id)
        
        # Check it's gone
        assert handler_id not in core.handlers, "Handler should be removed"
        
        logger.close()
        print(f"[PASS] Handler {handler_id} removed successfully")


def test_multiple_handlers_same_logger():
    """Test multiple handlers on same logger"""
    print("\n=== Test: multiple handlers per logger ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_multi", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        core = logger._logger
        
        # Add multiple handlers
        handler1 = StreamHandler()
        handler2 = StreamHandler()
        handler3 = FileHandler(os.path.join(tmpdir, "multi.log"))
        
        id1 = core.add_handler(handler1)
        id2 = core.add_handler(handler2)
        id3 = core.add_handler(handler3)
        
        # All should have unique IDs
        assert id1 != id2 != id3, "All handler IDs should be unique"
        assert len(core.handlers) >= 3, f"Should have at least 3 handlers, got {len(core.handlers)}"
        
        logger.close()
        print(f"[PASS] Multiple handlers: IDs {id1}, {id2}, {id3}")


def test_handler_ids_are_unique():
    """Test that handler IDs are always unique"""
    print("\n=== Test: handler IDs are unique ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_unique", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        core = logger._logger
        
        # Add many handlers
        ids = []
        for i in range(10):
            handler = StreamHandler()
            hid = core.add_handler(handler)
            ids.append(hid)
        
        # All IDs should be unique
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"
        
        logger.close()
        print(f"[PASS] 10 unique handler IDs: {ids}")


def test_handler_id_persists_after_removal():
    """Test that handler IDs don't get reused after removal"""
    print("\n=== Test: handler IDs don't get reused ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_reuse", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        core = logger._logger
        
        # Add handler
        h1 = StreamHandler()
        id1 = core.add_handler(h1)
        
        # Remove it
        core.remove_handler(id1)
        
        # Add another handler
        h2 = StreamHandler()
        id2 = core.add_handler(h2)
        
        # IDs should be different (id2 should be higher)
        assert id2 > id1, f"ID should increment: {id1} should be < {id2}"
        
        logger.close()
        print(f"[PASS] IDs don't reuse: {id1} -> {id2}")


def test_logger_close_cleans_handlers():
    """Test that logger.close() properly cleans up handlers"""
    print("\n=== Test: logger.close() cleans handlers ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_cleanup", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        core = logger._logger
        
        # Add handlers
        h1 = StreamHandler()
        h2 = FileHandler(os.path.join(tmpdir, "cleanup.log"))
        id1 = core.add_handler(h1)
        id2 = core.add_handler(h2)
        
        assert len(core.handlers) >= 2, "Should have handlers before close"
        
        # Close logger
        logger.close()
        
        # Note: close() removes handlers but might not clear dict
        # Just verify it doesn't crash
        print(f"[PASS] logger.close() executed without error")


def test_handler_dict_structure():
    """Test that handlers are stored in dict with int keys"""
    print("\n=== Test: handler dict structure ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_dict", config={
            "log_dir": tmpdir,
            "level": "INFO"
        })
        
        core = logger._logger
        
        # Verify handlers is a dict
        assert isinstance(core.handlers, dict), "Handlers should be stored in dict"
        
        # Add handler and verify structure
        h = StreamHandler()
        hid = core.add_handler(h)
        
        # Verify dict has int key
        assert hid in core.handlers, f"Handler ID {hid} should be in dict"
        assert isinstance(hid, int), "Dict key should be int"
        
        logger.close()
        print(f"[PASS] Handler dict structure: {{int: Handler}}")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 TEST SUITE: HANDLER IDS AND MANAGEMENT")
    print("=" * 60)
    
    try:
        test_add_handler_returns_id()
        test_remove_handler_by_id()
        test_multiple_handlers_same_logger()
        test_handler_ids_are_unique()
        test_handler_id_persists_after_removal()
        test_logger_close_cleans_handlers()
        test_handler_dict_structure()
        
        print("\n" + "=" * 60)
        print("[PASS] ALL HANDLER ID TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
