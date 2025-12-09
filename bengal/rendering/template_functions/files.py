"""
File system functions for templates.

Provides 3 functions for reading files and checking file existence.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: Environment, site: Site) -> None:
    """Register file system functions with Jinja2 environment."""

    # Create closures that have access to site
    def read_file_with_site(path: str) -> str:
        return read_file(path, site.root_path)

    def file_exists_with_site(path: str) -> bool:
        return file_exists(path, site.root_path)

    def file_size_with_site(path: str) -> str:
        return file_size(path, site.root_path)

    env.globals.update(
        {
            "read_file": read_file_with_site,
            "file_exists": file_exists_with_site,
            "file_size": file_size_with_site,
        }
    )


def read_file(path: str, root_path: Path) -> str:
    """
    Read file contents.

    Uses bengal.utils.file_io.read_text_file internally for robust file reading
    with UTF-8/latin-1 encoding fallback and comprehensive error handling.

    Args:
        path: Relative path to file
        root_path: Site root path

    Returns:
        File contents as string

    Example:
        {% set license = read_file('LICENSE') %}
        {{ license }}
    """
    if not path:
        logger.debug("read_file_empty_path", caller="template")
        return ""

    from bengal.utils.file_io import read_text_file

    file_path = Path(root_path) / path

    # Use file_io utility for robust reading with encoding fallback
    # on_error='return_empty' returns '' for missing/invalid files
    content = read_text_file(
        file_path, fallback_encoding="latin-1", on_error="return_empty", caller="template"
    )
    return content if content is not None else ""


def file_exists(path: str, root_path: Path) -> bool:
    """
    Check if file exists.

    Args:
        path: Relative path to file
        root_path: Site root path

    Returns:
        True if file exists

    Example:
        {% if file_exists('custom.css') %}
            <link rel="stylesheet" href="{{ asset_url('custom.css') }}">
        {% endif %}
    """
    if not path:
        return False

    file_path = Path(root_path) / path
    return file_path.exists() and file_path.is_file()


def file_size(path: str, root_path: Path) -> str:
    """
    Get human-readable file size.

    Args:
        path: Relative path to file
        root_path: Site root path

    Returns:
        File size as human-readable string (e.g., "1.5 MB")

    Example:
        {{ file_size('downloads/manual.pdf') }}  # "2.3 MB"
    """
    if not path:
        logger.debug("file_size_empty_path", caller="template")
        return "0 B"

    file_path = Path(root_path) / path

    if not file_path.exists():
        logger.warning("file_not_found", path=path, attempted=str(file_path), caller="template")
        return "0 B"

    if not file_path.is_file():
        logger.warning(
            "path_not_file",
            path=path,
            file_path=str(file_path),
            message="Path exists but is not a file",
            caller="template",
        )
        return "0 B"

    try:
        size_bytes: float = file_path.stat().st_size

        # Convert to human-readable format
        original_size = size_bytes
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                result = f"{size_bytes:.1f} {unit}"
                logger.debug(
                    "file_size_computed", path=path, size_bytes=original_size, human_readable=result
                )
                return result
            size_bytes /= 1024.0

        result = f"{size_bytes:.1f} PB"
        logger.debug(
            "file_size_computed", path=path, size_bytes=original_size, human_readable=result
        )
        return result

    except OSError as e:
        logger.error(
            "file_stat_error",
            path=path,
            file_path=str(file_path),
            error=str(e),
            error_type=type(e).__name__,
            caller="template",
        )
        return "0 B"
