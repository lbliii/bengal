"""
File I/O utilities for Bengal.

This sub-package provides robust file operations including reading, writing,
atomic writes (crash-safe), and cross-platform file locking.

Modules:
    file_io: Robust file reading/writing with encoding fallback
    atomic_write: Crash-safe writes using temp-then-rename pattern
    file_lock: Cross-platform file locking for concurrent builds
    json_compat: JSON serialization with atomic file writes

Example:
    >>> from bengal.utils.io import read_text_file, load_yaml, atomic_write_text
    >>> content = read_text_file(path, fallback_encoding='latin-1')
    >>> data = load_yaml('config.yaml')
    >>> atomic_write_text('output.html', html_content)

"""

from bengal.utils.io.atomic_write import AtomicFile, atomic_write_bytes, atomic_write_text
from bengal.utils.io.file_io import (
    load_data_file,
    load_json,
    load_toml,
    load_yaml,
    read_text_file,
    rmtree_robust,
    write_json,
    write_text_file,
)
from bengal.utils.io.file_lock import (
    DEFAULT_LOCK_TIMEOUT,
    LockAcquisitionError,
    file_lock,
    is_locked,
    remove_stale_lock,
)
from bengal.utils.io.json_compat import JSONDecodeError, dump, dumps, load, loads

__all__ = [
    # atomic_write
    "atomic_write_text",
    "atomic_write_bytes",
    "AtomicFile",
    # file_io
    "read_text_file",
    "load_json",
    "load_yaml",
    "load_toml",
    "load_data_file",
    "write_text_file",
    "write_json",
    "rmtree_robust",
    # file_lock
    "file_lock",
    "is_locked",
    "remove_stale_lock",
    "LockAcquisitionError",
    "DEFAULT_LOCK_TIMEOUT",
    # json_compat
    "dumps",
    "loads",
    "dump",
    "load",
    "JSONDecodeError",
]
