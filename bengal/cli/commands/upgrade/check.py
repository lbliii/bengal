"""
PyPI version checking with TTL-based caching.

Checks are:
- Cached for 24 hours to avoid network spam
- Skipped in CI environments
- Non-blocking (2s timeout, silent failures)
- User-level cache (~/.config/bengal/)

Related:
- bengal/cli/commands/upgrade/command.py: Uses this for upgrade checks
- bengal/cli/__init__.py: Uses this for passive notifications
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

import httpx
from packaging.version import Version

from bengal import __version__

# Cache TTL: 24 hours
CACHE_TTL = timedelta(hours=24)

# PyPI endpoint
PYPI_URL = "https://pypi.org/pypi/bengal/json"

# Request timeout (don't slow down CLI)
TIMEOUT = 2.0


class UpgradeInfo(NamedTuple):
    """Information about available upgrade."""

    current: str
    latest: str

    @property
    def is_outdated(self) -> bool:
        """True if current version is older than latest."""
        try:
            return Version(self.current) < Version(self.latest)
        except Exception:
            # If version parsing fails, fall back to string comparison
            return self.current != self.latest


def get_cache_path() -> Path:
    """
    Get platform-appropriate cache path.

    Returns:
        Path to the upgrade check cache file.

    Locations:
        - Linux/macOS: ~/.config/bengal/upgrade_check.json (XDG)
        - Windows: %APPDATA%/bengal/upgrade_check.json
        - Fallback: ~/.bengal/upgrade_check.json
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"

    return base / "bengal" / "upgrade_check.json"


def should_check() -> bool:
    """
    Determine if we should check for updates.

    Returns False if:
    - Running in CI environment (CI, GITHUB_ACTIONS, etc.)
    - BENGAL_NO_UPDATE_CHECK=1 is set
    - Not running in interactive terminal (stderr not TTY)

    Returns:
        True if update check should proceed.
    """
    # Skip in CI environments
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS", "CIRCLECI"]
    if any(os.environ.get(var) for var in ci_vars):
        return False

    # Skip if explicitly disabled
    if os.environ.get("BENGAL_NO_UPDATE_CHECK", "").lower() in ("1", "true", "yes"):
        return False

    # Skip if not interactive terminal
    if not sys.stderr.isatty():
        return False

    return True


def load_cache() -> dict | None:
    """
    Load cached upgrade check result.

    Returns cached data if:
    - Cache file exists
    - Cache is valid JSON
    - Cache is not expired (< CACHE_TTL old)

    Returns:
        Cached data dict or None if cache is stale/missing.
    """
    cache_path = get_cache_path()
    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text())
        checked_at = datetime.fromisoformat(data["checked_at"])
        # Ensure timezone-aware comparison
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - checked_at < CACHE_TTL:
            return data
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        pass

    return None


def save_cache(latest_version: str) -> None:
    """
    Save upgrade check result to cache.

    Creates parent directories if needed. Silently fails on write errors
    (cache is best-effort, not critical).

    Args:
        latest_version: The latest version string from PyPI.
    """
    cache_path = get_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "latest_version": latest_version,
            "current_version": __version__,
            "checked_at": datetime.now(UTC).isoformat(),
        }
        cache_path.write_text(json.dumps(data, indent=2))
    except OSError:
        # Cache write failures are non-fatal
        pass


def fetch_latest_version() -> str | None:
    """
    Fetch latest version from PyPI.

    Uses a short timeout (2s) to avoid slowing down CLI operations.
    Returns None on any error (network, timeout, parse error).

    Returns:
        Latest version string or None on failure.
    """
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(PYPI_URL)
            response.raise_for_status()
            data = response.json()
            return data["info"]["version"]
    except Exception:
        return None


def check_for_upgrade() -> UpgradeInfo | None:
    """
    Check if a newer version of Bengal is available.

    This is the main entry point for upgrade checking. It:
    1. Checks if we should run (CI, disabled, non-TTY)
    2. Uses cached result if fresh (< 24h old)
    3. Fetches from PyPI if cache is stale
    4. Updates cache with new result
    5. Returns UpgradeInfo only if upgrade is available

    Returns:
        UpgradeInfo if upgrade available, None otherwise.
        Also returns None on any error (network, parse, etc.)
    """
    if not should_check():
        return None

    # Try cache first
    cached = load_cache()
    if cached:
        latest = cached["latest_version"]
    else:
        # Fetch from PyPI
        latest = fetch_latest_version()
        if latest:
            save_cache(latest)

    if not latest:
        return None

    info = UpgradeInfo(current=__version__, latest=latest)
    return info if info.is_outdated else None
