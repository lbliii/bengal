"""
File I/O utilities with robust error handling.

Provides standardized file reading/writing operations with consistent error handling,
logging, and encoding fallback. Consolidates duplicate file I/O patterns found
throughout the codebase.

Example:

```python
from bengal.utils.file_io import read_text_file, load_json, load_yaml, rmtree_robust

# Read text file with encoding fallback
content = read_text_file(path, fallback_encoding='latin-1')

# Load JSON with error handling
data = load_json(path, on_error='return_empty')

# Auto-detect and load data file
data = load_data_file(path)  # Works for .json, .yaml, .toml

# Robust directory removal (handles macOS quirks)
rmtree_robust(Path('/path/to/dir'))
```
"""

from __future__ import annotations

import errno
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, cast

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def _strip_bom(content: str, file_path: Path, encoding: str, caller: str | None = None) -> str:
    """
    Strip UTF-8 BOM from content if present.

    Args:
        content: File content
        file_path: Path to file (for logging)
        encoding: Encoding used (for logging)
        caller: Caller identifier for logging

    Returns:
        Content with BOM removed if present, otherwise unchanged
    """
    if content and content[0] == "\ufeff":
        logger.debug(
            "bom_stripped",
            path=str(file_path),
            encoding=encoding,
            caller=caller or "file_io",
        )
        # Remove only the first BOM character
        return content[1:]
    return content


def read_text_file(
    file_path: Path | str,
    encoding: str = "utf-8",
    fallback_encoding: str | None = "latin-1",
    on_error: str = "raise",
    caller: str | None = None,
) -> str | None:
    """
    Read text file with robust error handling and encoding fallback.

    Consolidates patterns from:
    - bengal/discovery/content_discovery.py:192 (UTF-8 with latin-1 fallback)
    - bengal/rendering/template_functions/files.py:78 (file reading with logging)
    - bengal/config/loader.py:137 (config file reading)

    Args:
        file_path: Path to file to read
        encoding: Primary encoding to try (default: 'utf-8')
        fallback_encoding: Fallback encoding if primary fails (default: 'latin-1')
        on_error: Error handling strategy:
            - 'raise': Raise exception on error
            - 'return_empty': Return empty string on error
            - 'return_none': Return None on error
        caller: Caller identifier for logging context

    Returns:
        File contents as string, or None/empty string based on on_error.

    Encoding notes:
    - Strips UTF-8 BOM when present.
    - If primary decode fails, tries `utf-8-sig` before the configured fallback.

    Raises:
        FileNotFoundError: If file doesn't exist and on_error='raise'
        ValueError: If path is not a file and on_error='raise'
        IOError: If file cannot be read and on_error='raise'

    Examples:
        >>> content = read_text_file('config.txt')
        >>> content = read_text_file('data.txt', fallback_encoding='latin-1')
        >>> content = read_text_file('optional.txt', on_error='return_empty')
    """
    file_path = Path(file_path)

    # Check if file exists
    if not file_path.exists():
        logger.warning("file_not_found", path=str(file_path), caller=caller or "file_io")
        if on_error == "raise":
            raise FileNotFoundError(f"File not found: {file_path}")
        return "" if on_error == "return_empty" else None

    # Check if path is a file
    if not file_path.is_file():
        logger.warning(
            "path_not_file",
            path=str(file_path),
            note="Path exists but is not a file",
            caller=caller or "file_io",
        )
        if on_error == "raise":
            from bengal.errors import BengalError

            raise BengalError(
                f"Path is not a file: {file_path}",
                file_path=file_path,
                suggestion="Ensure the path points to a file, not a directory",
            )
        return "" if on_error == "return_empty" else None

    # Try reading with primary encoding
    try:
        with open(file_path, encoding=encoding) as f:
            content = f.read()

        # Strip UTF-8 BOM if present to avoid confusing downstream parsers
        content = _strip_bom(content, file_path, encoding, caller)

        logger.debug(
            "file_read",
            path=str(file_path),
            encoding=encoding,
            size_bytes=len(content),
            lines=content.count("\n") + 1,
            caller=caller or "file_io",
        )
        return content

    except UnicodeDecodeError as e:
        # Try fallback encoding if available
        if fallback_encoding:
            # First, attempt UTF-8 with BOM if primary UTF-8 failed
            try:
                with open(file_path, encoding="utf-8-sig") as f:
                    content = f.read()

                # utf-8-sig automatically strips BOM, but apply for consistency
                content = _strip_bom(content, file_path, "utf-8-sig", caller)

                logger.debug(
                    "file_read_utf8_sig",
                    path=str(file_path),
                    encoding="utf-8-sig",
                    size_bytes=len(content),
                    caller=caller or "file_io",
                )
                return content
            except Exception as sig_error:
                # Fall through to configured fallback, but log debug
                logger.debug(
                    "utf8_sig_fallback_failed",
                    path=str(file_path),
                    error=str(sig_error),
                    caller=caller or "file_io",
                )
                pass

            logger.warning(
                "encoding_fallback",
                path=str(file_path),
                primary=encoding,
                fallback=fallback_encoding,
                error=str(e),
                caller=caller or "file_io",
            )

            try:
                with open(file_path, encoding=fallback_encoding) as f:
                    content = f.read()

                logger.debug(
                    "file_read_fallback",
                    path=str(file_path),
                    encoding=fallback_encoding,
                    size_bytes=len(content),
                    caller=caller or "file_io",
                )
                return content

            except Exception as fallback_error:
                logger.error(
                    "encoding_fallback_failed",
                    path=str(file_path),
                    primary=encoding,
                    fallback=fallback_encoding,
                    error=str(fallback_error),
                    caller=caller or "file_io",
                )

        if on_error == "raise":
            raise OSError(f"Cannot decode {file_path}: {e}") from e
        return "" if on_error == "return_empty" else None

    except OSError as e:
        logger.error(
            "file_read_error",
            path=str(file_path),
            error=str(e),
            error_type=type(e).__name__,
            caller=caller or "file_io",
        )
        if on_error == "raise":
            raise
        return "" if on_error == "return_empty" else None


def load_json(
    file_path: Path | str, on_error: str = "return_empty", caller: str | None = None
) -> Any:
    """
    Load JSON file with error handling.

    Consolidates patterns from:
    - bengal/rendering/template_functions/data.py:80 (JSON loading)

    Args:
        file_path: Path to JSON file
        on_error: Error handling strategy ('raise', 'return_empty', 'return_none')
        caller: Caller identifier for logging

    Returns:
        Parsed JSON data, or {} / None based on on_error

    Raises:
        FileNotFoundError: If file not found and on_error='raise'
        json.JSONDecodeError: If JSON is invalid and on_error='raise'

    Examples:
        >>> data = load_json('config.json')
        >>> data = load_json('optional.json', on_error='return_none')
    """
    file_path = Path(file_path)

    # Read file content
    content = read_text_file(file_path, on_error=on_error, caller=caller)
    if not content:
        return {} if on_error == "return_empty" else None

    # Parse JSON (using orjson if available for 3-10x speedup)
    try:
        data = json.loads(content)

        logger.debug(
            "json_loaded",
            path=str(file_path),
            size_bytes=len(content),
            keys=len(data) if isinstance(data, dict) else None,
            type=type(data).__name__,
            caller=caller or "file_io",
        )
        return data

    except json.JSONDecodeError as e:
        logger.error(
            "json_parse_error",
            path=str(file_path),
            error=str(e),
            line=getattr(e, "lineno", None),
            column=getattr(e, "colno", None),
            caller=caller or "file_io",
        )

        if on_error == "raise":
            raise
        return {} if on_error == "return_empty" else None


def load_yaml(
    file_path: Path | str, on_error: str = "return_empty", caller: str | None = None
) -> dict[str, Any] | None:
    """
    Load YAML file with error handling.

    Consolidates patterns from:
    - bengal/config/loader.py:142 (YAML config loading)
    - bengal/rendering/template_functions/data.py:94 (YAML data loading)

    Args:
        file_path: Path to YAML file
        on_error: Error handling strategy ('raise', 'return_empty', 'return_none')
        caller: Caller identifier for logging

    Returns:
        Parsed YAML data, or {} / None based on on_error

    Raises:
        FileNotFoundError: If file not found and on_error='raise'
        yaml.YAMLError: If YAML is invalid and on_error='raise'
        ImportError: If PyYAML not installed and on_error='raise'

    Examples:
        >>> data = load_yaml('config.yaml')
        >>> data = load_yaml('optional.yml', on_error='return_none')
    """
    file_path = Path(file_path)

    # Check if PyYAML is available
    try:
        import yaml
    except ImportError:
        logger.warning(
            "yaml_not_available",
            path=str(file_path),
            note="PyYAML not installed, cannot load YAML files",
            caller=caller or "file_io",
        )
        if on_error == "raise":
            raise ImportError("PyYAML is required to load YAML files") from None
        return {} if on_error == "return_empty" else None

    # Read file content
    content = read_text_file(file_path, on_error=on_error, caller=caller)
    if not content:
        return {} if on_error == "return_empty" else None

    # Parse YAML
    try:
        data_raw = yaml.safe_load(content)

        # YAML can return None for empty files
        if data_raw is None:
            data: dict[str, Any] = {}
        elif isinstance(data_raw, dict):
            # Type narrowing: ensure we return dict[str, Any]
            data = cast(dict[str, Any], data_raw)
        else:
            # YAML can return non-dict types, but we expect dict
            data = {}

        logger.debug(
            "yaml_loaded",
            path=str(file_path),
            size_bytes=len(content),
            keys=len(data) if isinstance(data, dict) else None,
            type=type(data).__name__,
            caller=caller or "file_io",
        )
        return data

    except yaml.YAMLError as e:
        logger.error(
            "yaml_parse_error", path=str(file_path), error=str(e), caller=caller or "file_io"
        )

        if on_error == "raise":
            raise
        return {} if on_error == "return_empty" else None


def load_toml(
    file_path: Path | str, on_error: str = "return_empty", caller: str | None = None
) -> dict[str, Any] | None:
    """
    Load TOML file with error handling.

    Consolidates patterns from:
    - bengal/config/loader.py:137 (TOML config loading)

    Args:
        file_path: Path to TOML file
        on_error: Error handling strategy ('raise', 'return_empty', 'return_none')
        caller: Caller identifier for logging

    Returns:
        Parsed TOML data, or {} / None based on on_error

    Raises:
        FileNotFoundError: If file not found and on_error='raise'
        toml.TomlDecodeError: If TOML is invalid and on_error='raise'

    Examples:
        >>> data = load_toml('config.toml')
        >>> data = load_toml('optional.toml', on_error='return_none')
    """
    file_path = Path(file_path)

    # Read file content
    content = read_text_file(file_path, on_error=on_error, caller=caller)
    if not content:
        return {} if on_error == "return_empty" else None

    # Parse TOML (using stdlib tomllib - Python 3.11+)
    try:
        import tomllib

        data_raw = tomllib.loads(content)

        # TOML should always return a dict, but type checker sees Any
        data = cast(dict[str, Any], data_raw) if isinstance(data_raw, dict) else {}

        logger.debug(
            "toml_loaded",
            path=str(file_path),
            size_bytes=len(content),
            keys=len(data) if isinstance(data, dict) else None,
            caller=caller or "file_io",
        )
        return data

    except Exception as e:  # tomllib.TOMLDecodeError or AttributeError
        logger.error(
            "toml_parse_error",
            path=str(file_path),
            error=str(e),
            error_type=type(e).__name__,
            caller=caller or "file_io",
        )

        if on_error == "raise":
            raise
        return {} if on_error == "return_empty" else None


def load_data_file(
    file_path: Path | str, on_error: str = "return_empty", caller: str | None = None
) -> dict[str, Any] | None:
    """
    Auto-detect and load JSON/YAML/TOML file.

    Consolidates pattern from:
    - bengal/rendering/template_functions/data.py:40 (get_data function)

    Args:
        file_path: Path to data file (.json, .yaml, .yml, .toml)
        on_error: Error handling strategy ('raise', 'return_empty', 'return_none')
        caller: Caller identifier for logging

    Returns:
        Parsed data, or {} / None based on on_error

    Raises:
        ValueError: If file format is unsupported and on_error='raise'

    Examples:
        >>> data = load_data_file('config.json')
        >>> data = load_data_file('settings.yaml')
        >>> data = load_data_file('pyproject.toml')
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    # Route to appropriate loader based on file extension
    if suffix == ".json":
        result = load_json(file_path, on_error=on_error, caller=caller)
        return cast(dict[str, Any] | None, result)
    elif suffix in (".yaml", ".yml"):
        return load_yaml(file_path, on_error=on_error, caller=caller)
    elif suffix == ".toml":
        return load_toml(file_path, on_error=on_error, caller=caller)
    else:
        logger.warning(
            "unsupported_format",
            path=str(file_path),
            suffix=suffix,
            supported=[".json", ".yaml", ".yml", ".toml"],
            caller=caller or "file_io",
        )

        if on_error == "raise":
            from bengal.errors import BengalError

            raise BengalError(
                f"Unsupported file format: {suffix}",
                suggestion="Use .json, .yaml, .yml, or .toml file format",
            )
        return {} if on_error == "return_empty" else None


def write_text_file(
    file_path: Path | str,
    content: str,
    encoding: str = "utf-8",
    create_parents: bool = True,
    caller: str | None = None,
) -> None:
    """
    Write text to file with parent directory creation.

    Args:
        file_path: Path to file to write
        content: Text content to write
        encoding: Text encoding (default: 'utf-8')
        create_parents: Create parent directories if they don't exist
        caller: Caller identifier for logging

    Raises:
        IOError: If write fails

    Examples:
        >>> write_text_file('output/data.txt', 'Hello World')
        >>> write_text_file('result.json', json.dumps(data))
    """
    file_path = Path(file_path)

    # Create parent directories if needed
    if create_parents and not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("created_parent_dirs", path=str(file_path.parent), caller=caller or "file_io")

    # Write file
    try:
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)

        logger.debug(
            "file_written",
            path=str(file_path),
            size_bytes=len(content),
            encoding=encoding,
            caller=caller or "file_io",
        )

    except OSError as e:
        logger.error(
            "file_write_error", path=str(file_path), error=str(e), caller=caller or "file_io"
        )
        raise


def write_json(
    file_path: Path | str,
    data: Any,
    indent: int | None = 2,
    create_parents: bool = True,
    caller: str | None = None,
) -> None:
    """
    Write data as JSON file.

    Uses orjson for Rust-accelerated serialization (3-10x faster) if available.

    Args:
        file_path: Path to JSON file
        data: Data to serialize as JSON
        indent: JSON indentation (None for compact)
        create_parents: Create parent directories if needed
        caller: Caller identifier for logging

    Raises:
        TypeError: If data is not JSON serializable
        IOError: If write fails

    Examples:
        >>> write_json('output.json', {'key': 'value'})
        >>> write_json('data.json', data, indent=None)  # Compact
    """
    try:
        content = json.dumps(data, indent=indent)
        write_text_file(file_path, content, create_parents=create_parents, caller=caller)

    except TypeError as e:
        logger.error(
            "json_serialize_error", path=str(file_path), error=str(e), caller=caller or "file_io"
        )
        raise


# =============================================================================
# Directory Operations
# =============================================================================

# Retry delay multiplier for transient filesystem errors
_RETRY_DELAY_BASE = 0.1  # seconds


def _remove_hidden_files(dir_path: Path) -> int:
    """
    Remove macOS hidden files that may prevent directory deletion.

    Targets .DS_Store, ._* files, and other dotfiles that macOS creates
    and can interfere with shutil.rmtree.

    Args:
        dir_path: Directory to clean hidden files from

    Returns:
        Number of hidden files removed
    """
    removed = 0
    for hidden in dir_path.rglob(".*"):
        try:
            if hidden.is_file():
                hidden.unlink(missing_ok=True)
                removed += 1
            elif hidden.is_dir():
                shutil.rmtree(hidden, ignore_errors=True)
                removed += 1
        except OSError as e:
            logger.debug(
                "hidden_file_removal_failed",
                path=str(hidden),
                error=str(e),
            )
    return removed


def rmtree_robust(
    path: Path,
    max_retries: int = 3,
    caller: str | None = None,
) -> None:
    """
    Remove directory tree with robust error handling for filesystem quirks.

    On macOS, shutil.rmtree can fail with Errno 66 (Directory not empty)
    due to race conditions with Spotlight indexing, Finder metadata files
    (.DS_Store, ._*), or other processes briefly accessing the directory.

    Strategy:
        1. Try normal shutil.rmtree
        2. On ENOTEMPTY, remove hidden files (.DS_Store, ._*) and retry
        3. Fall back to subprocess `rm -rf` on macOS as last resort

    Args:
        path: Directory to remove
        max_retries: Number of retry attempts (default 3)
        caller: Caller identifier for logging

    Raises:
        OSError: If deletion fails after all retries
        FileNotFoundError: If path does not exist

    Examples:
        >>> rmtree_robust(Path('/path/to/output'))
        >>> rmtree_robust(Path('.bengal'), max_retries=5)
    """
    caller = caller or "file_io"

    if not path.exists():
        logger.debug("rmtree_path_not_exists", path=str(path), caller=caller)
        return

    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            logger.debug(
                "rmtree_success",
                path=str(path),
                attempt=attempt + 1,
                caller=caller,
            )
            return

        except OSError as e:
            # Errno 66 (ENOTEMPTY) on macOS, Errno 39 (ENOTEMPTY) on Linux
            is_not_empty = e.errno in (errno.ENOTEMPTY, 66, 39)

            if not is_not_empty:
                # Different error - don't retry
                logger.error(
                    "rmtree_failed",
                    path=str(path),
                    error=str(e),
                    errno=e.errno,
                    caller=caller,
                )
                raise

            logger.debug(
                "rmtree_retry",
                path=str(path),
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
                caller=caller,
            )

            # Try removing hidden files before retrying
            hidden_removed = _remove_hidden_files(path)
            if hidden_removed > 0:
                logger.debug(
                    "rmtree_hidden_removed",
                    path=str(path),
                    count=hidden_removed,
                    caller=caller,
                )

            # Brief delay to let filesystem operations settle
            time.sleep(_RETRY_DELAY_BASE * (attempt + 1))

            # Not last attempt - continue to retry
            if attempt < max_retries - 1:
                continue

            # Last resort on macOS: use rm -rf
            if platform.system() == "Darwin":
                logger.debug(
                    "rmtree_fallback_rm",
                    path=str(path),
                    caller=caller,
                )
                result = subprocess.run(
                    ["rm", "-rf", str(path)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    logger.debug(
                        "rmtree_rm_success",
                        path=str(path),
                        caller=caller,
                    )
                    return

                # rm -rf failed - include its stderr in error
                logger.error(
                    "rmtree_rm_failed",
                    path=str(path),
                    returncode=result.returncode,
                    stderr=result.stderr.strip() if result.stderr else None,
                    caller=caller,
                )

            # All retries exhausted - raise original error with context
            raise OSError(
                f"Failed to remove directory after {max_retries} attempts: {path}\n"
                f"Last error: {e}\n"
                f"Tip: Check for processes holding files open (lsof +D {path})"
            ) from e
