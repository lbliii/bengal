"""
Orchestration config helpers.

Extracts common config access patterns used across orchestrators
to reduce duplication and ensure consistent behavior.
"""

from __future__ import annotations

from typing import Any


def get_max_workers(config: Any) -> int | None:
    """
    Get max_workers from build config, supporting both Config and dict.

    Args:
        config: Site config (Config object or raw dict)

    Returns:
        max_workers value if set, None otherwise

    Example:
        >>> max_workers = get_max_workers(site.config)
        >>> workers = max_workers or cpu_count()
    """
    build_section = getattr(config, "build", None)
    if build_section is not None:
        return getattr(build_section, "max_workers", None)
    if hasattr(config, "get"):
        build_section = config.get("build", {})
        if isinstance(build_section, dict):
            return build_section.get("max_workers")
        return config.get("max_workers")
    return None
