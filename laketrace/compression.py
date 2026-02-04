"""
Compression helpers for LakeTrace.

Adapted from Loguru (MIT License): https://github.com/Delgan/loguru
Original author: Julien Danjou
"""

import gzip
import os
import zipfile
from typing import Callable, Optional, Union


CompressionFunction = Callable[[str], None]


def _gzip_compress(path: str) -> None:
    gz_path = f"{path}.gz"
    with open(path, "rb") as src, gzip.open(gz_path, "wb") as dst:
        dst.writelines(src)
    os.remove(path)


def _bz2_compress(path: str) -> None:
    try:
        import bz2
    except Exception:
        return
    bz_path = f"{path}.bz2"
    with open(path, "rb") as src, bz2.open(bz_path, "wb") as dst:
        dst.writelines(src)
    os.remove(path)


def _zip_compress(path: str) -> None:
    zip_path = f"{path}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(path, arcname=os.path.basename(path))
    os.remove(path)


def make_compression_function(compression: Optional[Union[str, CompressionFunction]]):
    """Create a compression function from configuration."""
    if compression is None or compression == "none":
        return None

    if callable(compression):
        return compression

    if isinstance(compression, str):
        normalized = compression.lower()
        if normalized == "gz":
            return _gzip_compress
        if normalized == "bz2":
            return _bz2_compress
        if normalized == "zip":
            return _zip_compress

    raise ValueError(f"Unsupported compression: {compression}")