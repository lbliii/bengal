"""
Output normalization utilities for deterministic testing.

Provides helpers to normalize HTML and JSON output by removing
volatile elements like timestamps, hashes, and absolute paths.
"""

import json
import re
from typing import Any


def normalize_html(html_str: str, preserve_structure: bool = True) -> str:
    """
    Normalize HTML for deterministic assertions.

    Removes or replaces volatile elements:
    - Absolute file paths → 'PATH'
    - Asset hashes (style.abc123.css) → style.HASH.css
    - Timestamps → 'TIMESTAMP'
    - Optionally normalizes whitespace

    Args:
        html_str: HTML string to normalize
        preserve_structure: If True, preserve basic structure (minimal whitespace changes)

    Returns:
        Normalized HTML string

    Example:
        html = '<link href="/assets/css/style.abc123.css" />'
        normalized = normalize_html(html)
        # normalized: '<link href="/assets/css/style.HASH.css" />'
    """
    html = html_str

    # Replace asset hashes FIRST (before path normalization)
    # e.g., style.abc123def.css -> style.HASH.css
    html = re.sub(r"\.([a-f0-9]{8,})\.", ".HASH.", html)

    # Replace absolute paths (Windows, Unix, UNC, file:// URLs)
    # Order matters: most specific patterns first
    html = re.sub(r'file:///[^\s"\'<>]*', "PATH", html)  # file:/// URLs
    html = re.sub(r'[A-Za-z]:[/\\][^\s"\'<>]*', "PATH", html)  # C:\path or C:/path
    html = re.sub(r'\\\\[^\s"\'<>]+', "PATH", html)  # UNC paths \\server\share
    # Unix system paths (not web paths like /assets/...)
    # Match common system roots: /home, /usr, /tmp, /var, /private, /Users
    html = re.sub(r'/(home|usr|tmp|var|private|Users|opt|etc|Library)/[^\s"\'<>]*', "PATH", html)

    # Strip timestamps
    html = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "TIMESTAMP", html)
    html = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "TIMESTAMP", html)

    if not preserve_structure:
        # Aggressive whitespace normalization
        html = re.sub(r"\n\s*\n", "\n", html)  # Remove blank lines
        html = re.sub(r"  +", " ", html)  # Collapse multiple spaces

    return html


def normalize_json(data: dict | list | Any) -> dict | list | Any:
    """
    Normalize JSON data for deterministic assertions.

    Recursively:
    - Sorts dict keys
    - Strips known volatile fields (timestamps, build_time, etc.)
    - Normalizes paths

    Args:
        data: JSON data (dict, list, or primitive)

    Returns:
        Normalized data structure

    Example:
        data = {"z": 1, "a": 2, "build_time": "2024-01-01"}
        normalized = normalize_json(data)
        # normalized: {"a": 2, "z": 1}  # sorted, volatile removed
    """
    if isinstance(data, dict):
        normalized = {}
        for key, value in data.items():
            # Skip known volatile keys
            if key in {"build_time", "generated_at", "timestamp"}:
                continue

            # Recursively normalize values
            normalized[key] = normalize_json(value)

        # Return sorted by keys
        return {k: normalized[k] for k in sorted(normalized.keys())}

    elif isinstance(data, list):
        return [normalize_json(item) for item in data]

    elif isinstance(data, str):
        # Normalize paths in strings (Windows, Unix, UNC, file:// URLs)
        # Order matters: most specific patterns first
        normalized = re.sub(r'file:///[^\s"\'<>]*', "PATH", data)  # file:/// URLs
        normalized = re.sub(r'[A-Za-z]:[/\\][^\s"\'<>]*', "PATH", normalized)  # C:\path
        normalized = re.sub(r'\\\\[^\s"\'<>]+', "PATH", normalized)  # UNC \\server\share
        # Unix system paths (not web paths)
        normalized = re.sub(
            r'/(home|usr|tmp|var|private|Users|opt|etc|Library)/[^\s"\'<>]*', "PATH", normalized
        )
        return normalized

    else:
        # Primitives (int, bool, None) pass through
        return data


def json_dumps_normalized(data: Any, **kwargs) -> str:
    """
    Dump JSON with normalization and stable formatting.

    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps

    Returns:
        Normalized JSON string with consistent formatting
    """
    normalized = normalize_json(data)
    return json.dumps(normalized, sort_keys=True, indent=2, **kwargs)
