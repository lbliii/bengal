"""
Environment detection for the configuration system.

This module automatically detects the deployment environment from platform-specific
environment variables. It supports Netlify, Vercel, GitHub Actions, and allows
explicit override via ``BENGAL_ENV``.

Detected Environments:
- ``"local"``: Local development (default when no platform detected)
- ``"preview"``: Preview/staging deployments (branch deploys, PR previews)
- ``"production"``: Production deployments

Detection Priority:
1. ``BENGAL_ENV`` environment variable (explicit override)
2. Netlify (``NETLIFY=true`` + ``CONTEXT``)
3. Vercel (``VERCEL=1`` + ``VERCEL_ENV``)
4. GitHub Actions (``GITHUB_ACTIONS=true``, assumes production)
5. Default: ``"local"``

Key Functions:
    detect_environment: Detect current deployment environment.
    get_environment_file_candidates: Get candidate filenames for environment config.
    get_strict_incremental_mode: Get strict incremental debugging mode.

Example:
    >>> import os
    >>> os.environ["NETLIFY"] = "true"
    >>> os.environ["CONTEXT"] = "deploy-preview"
    >>> detect_environment()
    'preview'

See Also:
- :mod:`bengal.config.directory_loader`: Uses environment detection for config loading.
- :mod:`bengal.config.env_overrides`: Uses environment for baseurl detection.

"""

from __future__ import annotations

import os
from enum import Enum


def detect_environment() -> str:
    """
    Detect the deployment environment from platform-specific signals.

    Examines environment variables in priority order to determine whether
    the site is being built for local development, preview/staging, or
    production deployment.

    Detection Priority:
        1. ``BENGAL_ENV`` - Explicit override (highest priority)
        2. Netlify - ``NETLIFY=true`` with ``CONTEXT`` variable
        3. Vercel - ``VERCEL=1`` or ``VERCEL=true`` with ``VERCEL_ENV``
        4. GitHub Actions - ``GITHUB_ACTIONS=true`` (assumes production)
        5. Default - ``"local"`` when no platform detected

    Returns:
        Environment name: ``"local"``, ``"preview"``, or ``"production"``.

    Example:
            >>> import os
            >>> os.environ["BENGAL_ENV"] = "production"
            >>> detect_environment()
            'production'

            >>> # On Netlify preview deploy
            >>> os.environ["NETLIFY"] = "true"
            >>> os.environ["CONTEXT"] = "deploy-preview"
            >>> detect_environment()
            'preview'

    """
    # 1. Explicit override (highest priority)
    if env := os.getenv("BENGAL_ENV"):
        return env.lower().strip()

    # 2. Netlify detection
    if os.getenv("NETLIFY") == "true":
        context = os.getenv("CONTEXT", "").lower()
        if context == "production":
            return "production"
        elif context in ("deploy-preview", "branch-deploy"):
            return "preview"
        # Fallback to production for Netlify
        return "production"

    # 3. Vercel detection
    if os.getenv("VERCEL") in ("1", "true"):
        vercel_env = os.getenv("VERCEL_ENV", "").lower()
        if vercel_env == "production":
            return "production"
        elif vercel_env in ("preview", "development"):
            return "preview"
        # Fallback to production for Vercel
        return "production"

    # 4. GitHub Actions (assume production for CI)
    if os.getenv("GITHUB_ACTIONS") == "true":
        return "production"

    # 5. Default: local development
    return "local"


class StrictIncrementalMode(Enum):
    """Strict mode levels for incremental build debugging.

    RFC: rfc-incremental-build-observability

    Used to surface fallback usage during incremental builds for debugging.
    Set via BENGAL_STRICT_INCREMENTAL environment variable.

    Values:
        OFF: Normal operation (silent fallbacks)
        WARN: Log warnings when fallbacks are used
        ERROR: Raise errors when fallbacks are used
    """

    OFF = "off"
    WARN = "warn"
    ERROR = "error"


def get_strict_incremental_mode() -> StrictIncrementalMode:
    """
    Get the strict incremental mode from environment.

    RFC: rfc-incremental-build-observability

    The strict incremental mode controls how Bengal handles fallback
    paths in incremental builds. This is useful for debugging cache
    issues where fallbacks might mask problems.

    Environment Variable:
        ``BENGAL_STRICT_INCREMENTAL``: Set to "off", "warn", or "error".

    Returns:
        StrictIncrementalMode enum value.

    Example:
        >>> import os
        >>> os.environ["BENGAL_STRICT_INCREMENTAL"] = "warn"
        >>> get_strict_incremental_mode()
        <StrictIncrementalMode.WARN: 'warn'>

    """
    value = os.environ.get("BENGAL_STRICT_INCREMENTAL", "off").lower()
    try:
        return StrictIncrementalMode(value)
    except ValueError:
        return StrictIncrementalMode.OFF


def is_strict_incremental() -> bool:
    """
    Check if strict incremental mode is enabled (warn or error).

    RFC: rfc-incremental-build-observability

    Convenience function to check if any form of strict mode is active.

    Returns:
        True if strict mode is WARN or ERROR, False otherwise.

    Example:
        >>> import os
        >>> os.environ["BENGAL_STRICT_INCREMENTAL"] = "warn"
        >>> is_strict_incremental()
        True
        >>> os.environ["BENGAL_STRICT_INCREMENTAL"] = "off"
        >>> is_strict_incremental()
        False

    """
    return get_strict_incremental_mode() != StrictIncrementalMode.OFF


def get_environment_file_candidates(environment: str) -> list[str]:
    """
    Get candidate filenames for environment-specific configuration.

    Returns a list of potential filenames to search for, in priority order.
    The first matching file found should be used. This allows flexibility
    in naming (e.g., ``production.yaml`` vs ``prod.yaml``).

    Supported Aliases:
        - ``production``: production, prod
        - ``preview``: preview, staging, stage
        - ``local``: local, dev, development

    Args:
        environment: Environment name (e.g., ``"production"``).

    Returns:
        List of candidate filenames with ``.yaml`` and ``.yml`` extensions.
        First match wins when searching.

    Example:
            >>> get_environment_file_candidates("production")
        ['production.yaml', 'production.yml', 'prod.yaml', 'prod.yml']
            >>> get_environment_file_candidates("custom")
        ['custom.yaml', 'custom.yml']

    """
    # Common aliases
    aliases = {
        "production": ["production", "prod"],
        "preview": ["preview", "staging", "stage"],
        "local": ["local", "dev", "development"],
    }

    names = aliases.get(environment, [environment])

    # Generate candidates with .yaml and .yml extensions
    candidates = []
    for name in names:
        candidates.append(f"{name}.yaml")
        candidates.append(f"{name}.yml")

    return candidates
