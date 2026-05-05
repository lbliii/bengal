"""
PyPI version checking with TTL-based caching.

Checks are:
- Cached for 24 hours to avoid network spam
- Skipped in CI environments
- Non-blocking (2s timeout, silent failures)
- User-level cache (~/.config/bengal/)
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
            return self.current != self.latest


def get_cache_path() -> Path:
    """Get platform-appropriate cache path."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg_config) if xdg_config else Path.home() / ".config"

    return base / "bengal" / "upgrade_check.json"


def should_check() -> bool:
    """Determine if we should check for updates."""
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS", "CIRCLECI"]
    if any(os.environ.get(var) for var in ci_vars):
        return False

    if os.environ.get("BENGAL_NO_UPDATE_CHECK", "").lower() in ("1", "true", "yes"):
        return False

    return sys.stderr.isatty()


def load_cache() -> dict | None:
    """Load cached upgrade check result."""
    cache_path = get_cache_path()
    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text())
        checked_at = datetime.fromisoformat(data["checked_at"])
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - checked_at < CACHE_TTL:
            return data
    except json.JSONDecodeError, KeyError, ValueError, OSError:
        pass

    return None


def save_cache(latest_version: str) -> None:
    """Save upgrade check result to cache."""
    cache_path = get_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "latest_version": latest_version,
            "current_version": __version__,
            "checked_at": datetime.now(UTC).isoformat(),
        }
        from bengal.utils.io.atomic_write import atomic_write_text

        atomic_write_text(cache_path, json.dumps(data, indent=2))
    except OSError as e:
        import logging

        logging.getLogger("bengal.cli.upgrade").debug(
            "upgrade_cache_write_failed: %s — %s", cache_path, e
        )


def fetch_latest_version() -> str | None:
    """Fetch latest version from PyPI."""
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(PYPI_URL)
            response.raise_for_status()
            data = response.json()
            return data["info"]["version"]
    except Exception:
        return None


def check_for_upgrade() -> UpgradeInfo | None:
    """Check if a newer version of Bengal is available."""
    if not should_check():
        return None

    cached = load_cache()
    if cached:
        latest = cached["latest_version"]
    else:
        latest = fetch_latest_version()
        if latest:
            save_cache(latest)

    if not latest:
        return None

    info = UpgradeInfo(current=__version__, latest=latest)
    return info if info.is_outdated else None
