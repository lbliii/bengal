"""
Environment detection for config system.

Automatically detects deployment environment from platform-specific
environment variables (Netlify, Vercel, GitHub Actions, etc).
"""

from __future__ import annotations

import os


def detect_environment() -> str:
    """
    Detect deployment environment from platform signals.

    Checks in order:
    1. BENGAL_ENV (explicit override)
    2. Netlify (NETLIFY=true + CONTEXT)
    3. Vercel (VERCEL=1 + VERCEL_ENV)
    4. GitHub Actions (GITHUB_ACTIONS=true)
    5. Default: "local"

    Returns:
        Environment name: "local", "preview", or "production"

    Examples:
        >>> os.environ["BENGAL_ENV"] = "production"
        >>> detect_environment()
        "production"

        >>> os.environ.clear()
        >>> os.environ["NETLIFY"] = "true"
        >>> os.environ["CONTEXT"] = "production"
        >>> detect_environment()
        "production"
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


def get_environment_file_candidates(environment: str) -> list[str]:
    """
    Get candidate filenames for environment config.

    Returns list in priority order (first match wins).

    Args:
        environment: Environment name (e.g., "production")

    Returns:
        List of candidate filenames

    Examples:
        >>> get_environment_file_candidates("production")
        ["production.yaml", "production.yml", "prod.yaml", "prod.yml"]
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
