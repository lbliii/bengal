"""
Environment-based configuration overrides.

Provides automatic baseurl detection from deployment platforms
(Netlify, Vercel, GitHub Actions) for ergonomic deployments.
"""

from __future__ import annotations

import os
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """
    Apply environment-based overrides for deployment platforms.

    Auto-detects baseurl from platform environment variables when
    config baseurl is not explicitly set. Provides zero-config deployments
    for Netlify, Vercel, and GitHub Pages.

    Priority:
        1) BENGAL_BASEURL (explicit override)
        2) Netlify (URL/DEPLOY_PRIME_URL)
        3) Vercel (VERCEL_URL)
        4) GitHub Pages (owner.github.io/repo) when running in Actions
           - Set GITHUB_PAGES_ROOT=true for root deployments (user/org sites)
           - Auto-detects user/org sites when repo name is {owner}.github.io

    Behavior:
    - BENGAL_BASEURL (priority 1) can override any baseurl setting (explicit or missing)
    - Platform detection (priorities 2-4) only applies when baseurl is missing from config
    - If baseurl is explicitly set (even if empty), platform detection respects it

    Args:
        config: Configuration dictionary (flat or nested)

    Returns:
        Config with baseurl set from environment if applicable

    Examples:
        >>> import os
        >>> os.environ["GITHUB_ACTIONS"] = "true"
        >>> os.environ["GITHUB_REPOSITORY"] = "owner/repo"
        >>> # Missing baseurl allows env override
        >>> config = {}
        >>> result = apply_env_overrides(config)
        >>> result["baseurl"]
        '/repo'

        >>> # Explicit empty baseurl is respected by platform detection
        >>> config = {"baseurl": ""}
        >>> result = apply_env_overrides(config)
        >>> result["baseurl"]
        ''

        >>> # But BENGAL_BASEURL can override explicit empty
        >>> import os
        >>> os.environ["BENGAL_BASEURL"] = "https://override.com"
        >>> config = {"baseurl": ""}
        >>> result = apply_env_overrides(config)
        >>> result["baseurl"]
        'https://override.com'

        >>> # Explicit non-empty baseurl is respected
        >>> config = {"baseurl": "https://custom.com"}
        >>> result = apply_env_overrides(config)
        >>> result["baseurl"]
        'https://custom.com'
    """
    try:
        # Check if baseurl is explicitly set in config
        baseurl_explicitly_set = "baseurl" in config

        # 1) Explicit override (highest priority) - can override anything
        explicit = os.environ.get("BENGAL_BASEURL") or os.environ.get("BENGAL_BASE_URL")
        if explicit:
            config["baseurl"] = explicit.rstrip("/")
            return config

        # If baseurl is explicitly set (even if empty), don't allow platform detection to override
        # This respects explicit empty baseurl in config files and test overrides
        if baseurl_explicitly_set:
            return config

        # 2) Netlify detection (only if baseurl not explicitly set)
        if os.environ.get("NETLIFY") == "true":
            # Production has URL; previews have DEPLOY_PRIME_URL
            netlify_url = os.environ.get("URL") or os.environ.get("DEPLOY_PRIME_URL")
            if netlify_url:
                config["baseurl"] = netlify_url.rstrip("/")
                return config

        # 3) Vercel detection (only if baseurl not explicitly set)
        if os.environ.get("VERCEL") in ("1", "true"):
            vercel_host = os.environ.get("VERCEL_URL")
            if vercel_host:
                # Add https:// prefix if missing
                prefix = "https://" if not vercel_host.startswith(("http://", "https://")) else ""
                config["baseurl"] = f"{prefix}{vercel_host}".rstrip("/")
                return config

        # 4) GitHub Pages in Actions (only if baseurl not explicitly set)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            repo = os.environ.get("GITHUB_REPOSITORY", "")  # owner/repo format
            if repo and "/" in repo:
                owner, name = repo.split("/", 1)
                # Check if GITHUB_PAGES_ROOT is set (indicates root deployment)
                # or if repo name matches {owner}.github.io (user/org site)
                if os.environ.get("GITHUB_PAGES_ROOT") == "true" or name == f"{owner}.github.io":
                    # Root deployment: empty baseurl (served from root)
                    config["baseurl"] = ""
                else:
                    # Project site: deployed at /{repo-name} (path-only for relative links)
                    config["baseurl"] = f"/{name}".rstrip("/")
                return config

    except Exception as e:
        # Never fail build due to env override logic
        # Log warning since this is user-impacting (deployment URL detection)
        logger.warning(
            "env_override_detection_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="using_original_config",
            hint="Deployment platform baseurl auto-detection failed; verify environment variables",
        )

    return config
