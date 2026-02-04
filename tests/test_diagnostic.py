"""Quick diagnostic test for file handler"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from laketrace import get_logger

with tempfile.TemporaryDirectory() as tmpdir:
    logger = get_logger("test_diag", config={
        "log_dir": tmpdir,
        "level": "INFO",
        "json": True,
        "stdout": True
    })
    
    print(f"Log dir: {tmpdir}")
    print(f"Logger: {logger}")
    print(f"Core logger: {logger._logger}")
    print(f"Handlers: {logger._logger.handlers}")
    
    logger.info("Test message 1")
    logger.info("Test message 2")
    
    # List files
    files = os.listdir(tmpdir)
    print(f"Files in dir: {files}")
    
    # Check handler file
    for hid, handler in logger._logger.handlers.items():
        print(f"Handler {hid}: {handler}")
        if hasattr(handler, 'filepath'):
            print(f"  Filepath: {handler.filepath}")
        if hasattr(handler, '_file'):
            print(f"  File: {handler._file}")
    
    logger.close()
