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
    config baseurl is empty or missing. Provides zero-config deployments
    for Netlify, Vercel, and GitHub Pages.

    Priority:
        1) BENGAL_BASEURL (explicit override)
        2) Netlify (URL/DEPLOY_PRIME_URL)
        3) Vercel (VERCEL_URL)
        4) GitHub Pages (owner.github.io/repo) when running in Actions
           - Set GITHUB_PAGES_ROOT=true for root deployments (user/org sites)
           - Auto-detects user/org sites when repo name is {owner}.github.io

    Only applies when config baseurl is empty or missing.
    Explicit baseurl in config is never overridden.

    Args:
        config: Configuration dictionary (flat or nested)

    Returns:
        Config with baseurl set from environment if applicable

    Examples:
        >>> import os
        >>> os.environ["GITHUB_ACTIONS"] = "true"
        >>> os.environ["GITHUB_REPOSITORY"] = "owner/repo"
        >>> config = {"baseurl": ""}
        >>> result = apply_env_overrides(config)
        >>> result["baseurl"]
        'https://owner.github.io/repo'

        >>> # Explicit baseurl not overridden
        >>> config = {"baseurl": "https://custom.com"}
        >>> result = apply_env_overrides(config)
        >>> result["baseurl"]
        'https://custom.com'
    """
    try:
        # Only apply env overrides if baseurl is not set to a non-empty value
        # Empty string ("") or missing baseurl allows env overrides
        baseurl_current = config.get("baseurl", "")
        if baseurl_current:  # Non-empty string means explicit config, don't override
            return config

        # 1) Explicit override (highest priority)
        explicit = os.environ.get("BENGAL_BASEURL") or os.environ.get("BENGAL_BASE_URL")
        if explicit:
            config["baseurl"] = explicit.rstrip("/")
            return config

        # 2) Netlify detection
        if os.environ.get("NETLIFY") == "true":
            # Production has URL; previews have DEPLOY_PRIME_URL
            netlify_url = os.environ.get("URL") or os.environ.get("DEPLOY_PRIME_URL")
            if netlify_url:
                config["baseurl"] = netlify_url.rstrip("/")
                return config

        # 3) Vercel detection
        if os.environ.get("VERCEL") in ("1", "true"):
            vercel_host = os.environ.get("VERCEL_URL")
            if vercel_host:
                # Add https:// prefix if missing
                prefix = "https://" if not vercel_host.startswith(("http://", "https://")) else ""
                config["baseurl"] = f"{prefix}{vercel_host}".rstrip("/")
                return config

        # 4) GitHub Pages in Actions (best-effort computation)
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
