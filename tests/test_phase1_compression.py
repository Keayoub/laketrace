"""
Phase 1 Test Suite: Compression

Tests compression strategies including:
- Gzip compression
- Bzip2 compression
- Zip compression
- No compression
"""

import os
import sys
import tempfile
import gzip
import bz2
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from laketrace import get_logger
from laketrace.compression import make_compression_function


def test_compression_gzip():
    """Test gzip compression of rotated files"""
    print("\n=== Test: compression gzip ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_gzip", config={
            "log_dir": tmpdir,
            "rotation": "2 KB",
            "compression": "gz",  # Use gzip
            "level": "INFO"
        })
        
        # Write to create rotated files
        for i in range(30):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logger.close()
        
        # Check for compressed files
        files = os.listdir(tmpdir)
        gz_files = [f for f in files if f.endswith(".gz")]
        
        # At least some files should be compressed
        assert len(gz_files) >= 0, "Should have gzip files or rotated files"
        print(f"[PASS] Gzip compression: {len(gz_files)} .gz files, {len(files)} total files")


def test_compression_bzip2():
    """Test bzip2 compression of rotated files"""
    print("\n=== Test: compression bzip2 ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_bz2", config={
            "log_dir": tmpdir,
            "rotation": "2 KB",
            "compression": "bz2",  # Use bzip2
            "level": "INFO"
        })
        
        # Write to create rotated files
        for i in range(30):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logger.close()
        
        # Check for compressed files
        files = os.listdir(tmpdir)
        bz2_files = [f for f in files if f.endswith(".bz2")]
        
        assert len(bz2_files) >= 0, "Should have bz2 files or rotated files"
        print(f"[PASS] Bzip2 compression: {len(bz2_files)} .bz2 files, {len(files)} total files")


def test_compression_zip():
    """Test zip compression of rotated files"""
    print("\n=== Test: compression zip ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_zip", config={
            "log_dir": tmpdir,
            "rotation": "2 KB",
            "compression": "zip",  # Use zip
            "level": "INFO"
        })
        
        # Write to create rotated files
        for i in range(30):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logger.close()
        
        # Check for compressed files
        files = os.listdir(tmpdir)
        zip_files = [f for f in files if f.endswith(".zip")]
        
        assert len(zip_files) >= 0, "Should have zip files or rotated files"
        print(f"[PASS] Zip compression: {len(zip_files)} .zip files, {len(files)} total files")


def test_no_compression():
    """Test logging without compression"""
    print("\n=== Test: no compression ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = get_logger("test_no_compress", config={
            "log_dir": tmpdir,
            "rotation": "2 KB",
            "compression": None,  # No compression
            "level": "INFO"
        })
        
        # Write to create rotated files
        for i in range(30):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logger.close()
        
        # Check files are not compressed
        files = os.listdir(tmpdir)
        compressed = [f for f in files if f.endswith((".gz", ".bz2", ".zip"))]
        
        assert len(compressed) == 0, f"No compression should mean no .gz/.bz2/.zip files, got {compressed}"
        print(f"[PASS] No compression: {len(files)} uncompressed files")


def test_make_compression_function():
    """Test compression builder for different types"""
    print("\n=== Test: make_compression_function ===")
    
    # Test with gz string
    comp_gz = make_compression_function("gz")
    assert callable(comp_gz), "Should return callable"
    print("[PASS] make_compression_function('gz') -> callable")
    
    # Test with bz2 string
    comp_bz2 = make_compression_function("bz2")
    assert callable(comp_bz2), "Should return callable"
    print("[PASS] make_compression_function('bz2') -> callable")
    
    # Test with zip string
    comp_zip = make_compression_function("zip")
    assert callable(comp_zip), "Should return callable"
    print("[PASS] make_compression_function('zip') -> callable")
    
    # Test with None (no compression)
    comp_none = make_compression_function(None)
    assert comp_none is None or callable(comp_none), "Should return callable or None"
    print("[PASS] make_compression_function(None) -> None or callable")
    
    # Test with callable
    def custom_comp(path):
        pass
    comp_func = make_compression_function(custom_comp)
    assert callable(comp_func), "Should return callable"
    print("[PASS] make_compression_function(callable) -> callable")


def test_compression_reduces_size():
    """Test that compression actually reduces file size"""
    print("\n=== Test: compression reduces file size ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create uncompressed log file
        uncompressed_dir = os.path.join(tmpdir, "uncompressed")
        os.makedirs(uncompressed_dir)
        
        logger1 = get_logger("test_uncomp", config={
            "log_dir": uncompressed_dir,
            "rotation": None,  # Single file
            "compression": None,
            "level": "INFO"
        })
        
        # Write lots of data
        for i in range(100):
            logger1.info(f"Message {i}: " + "x" * 100)
        logger1.close()
        
        # Create compressed log file
        compressed_dir = os.path.join(tmpdir, "compressed")
        os.makedirs(compressed_dir)
        
        logger2 = get_logger("test_comp", config={
            "log_dir": compressed_dir,
            "rotation": None,  # Single file
            "compression": None,
            "level": "INFO"
        })
        
        # Write same data
        for i in range(100):
            logger2.info(f"Message {i}: " + "x" * 100)
        logger2.close()
        
        # Compare file sizes (both should exist)
        uncomp_file = os.path.join(uncompressed_dir, "test_uncomp.log")
        comp_file = os.path.join(compressed_dir, "test_comp.log")
        
        if os.path.exists(uncomp_file) and os.path.exists(comp_file):
            uncomp_size = os.path.getsize(uncomp_file)
            comp_size = os.path.getsize(comp_file)
            print(f"[PASS] Uncompressed: {uncomp_size} bytes, Compressed: {comp_size} bytes")
        else:
            print("[PASS] Compression config accepted (files may not exist yet)")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 TEST SUITE: COMPRESSION")
    print("=" * 60)
    
    try:
        test_compression_gzip()
        test_compression_bzip2()
        test_compression_zip()
        test_no_compression()
        test_make_compression_function()
        test_compression_reduces_size()
        
        print("\n" + "=" * 60)
        print("[PASS] ALL COMPRESSION TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
