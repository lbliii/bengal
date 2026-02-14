"""
BENGAL_ prefix environment variable overrides (Hugo-style).

Env vars starting with BENGAL_ override config keys.

Underscore = nesting: BENGAL_PARAMS_FOO_BAR → params.foo.bar
For keys with underscores, use `x` as delimiter:
- BENGALxPARAMSxREPO_URL → params.repo_url
- BENGALxPARAMSxCOLAB_BRANCH → params.colab_branch
- BENGALxPARAMSxAPI_KEY → params.api_key

Precedence: BENGAL_ env vars override config file. They run before
context inference, so BENGALxPARAMSxREPO_URL takes precedence over
GitHub Actions inference.
"""

from __future__ import annotations

import os
from typing import Any

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

_BENGAL_PREFIX_UNDERSCORE = "BENGAL_"
_BENGAL_PREFIX_X = "BENGALx"
_DELIMITER = "_"
_SPECIAL_DELIMITER = "x"


def _parse_bengal_key(env_key: str) -> list[str] | None:
    """
    Parse env key into config path.

    - BENGAL_PARAMS_FOO_BAR → ['params', 'foo', 'bar'] (underscore = nesting)
    - BENGALxPARAMSxREPO_URL → ['params', 'repo_url'] (x = delimiter for keys with underscores)
    """
    if env_key.startswith(_BENGAL_PREFIX_X):
        suffix = env_key[len(_BENGAL_PREFIX_X) :]
        if not suffix:
            return None
        parts = suffix.split(_SPECIAL_DELIMITER)
        return [p.lower() for p in parts if p]
    if env_key.startswith(_BENGAL_PREFIX_UNDERSCORE):
        suffix = env_key[len(_BENGAL_PREFIX_UNDERSCORE) :]
        if not suffix:
            return None
        parts = suffix.split(_DELIMITER)
        return [p.lower() for p in parts if p]
    return None


def _set_nested(config: dict[str, Any], path: list[str], value: str) -> None:
    """Set config[path[0]][path[1]]...[path[-1]] = value, creating dicts as needed."""
    current: dict[str, Any] = config
    for i, key in enumerate(path[:-1]):
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[path[-1]] = value


def apply_bengal_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """
    Apply BENGAL_* environment variables as config overrides.

    Iterates os.environ for keys starting with BENGAL_, parses the
    remainder into a config path, and sets the value. Empty values
    are ignored.

    Args:
        config: Configuration dictionary (mutated in place).

    Returns:
        The same config dict (mutated).
    """
    for key, value in os.environ.items():
        if not (
            key.startswith(_BENGAL_PREFIX_UNDERSCORE) or key.startswith(_BENGAL_PREFIX_X)
        ) or not value:
            continue
        path = _parse_bengal_key(key)
        if not path:
            continue
        try:
            _set_nested(config, path, value)
        except Exception as e:
            logger.warning(
                "bengal_override_failed",
                env_key=key,
                path=path,
                error=str(e),
                action="skipping_override",
            )
    return config
