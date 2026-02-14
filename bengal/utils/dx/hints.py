"""
DX hints registry and collector.

Contextual tips surfaced when running in Docker, WSL, Kubernetes, etc.
Hints are collected by context (build, serve, config) and filtered by opt-out.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from bengal.utils.dx.detection import is_docker, is_kubernetes, is_wsl


@dataclass(frozen=True, slots=True)
class Hint:
    """A single DX hint to display to the user."""

    id: str
    message: str
    priority: int
    context: frozenset[str]


def _hint_docker_baseurl(
    *,
    baseurl: str = "",
    context: str = "",
    **_: object,
) -> Hint | None:
    if not is_docker():
        return None
    if baseurl:
        return None
    return Hint(
        id="docker_baseurl",
        message="Running in Docker. Set BENGAL_BASEURL for correct canonical URLs.",
        priority=10,
        context=frozenset({"build", "serve", "config"}),
    )


def _hint_kubernetes_baseurl(
    *,
    baseurl: str = "",
    context: str = "",
    **_: object,
) -> Hint | None:
    if not is_kubernetes():
        return None
    if baseurl:
        return None
    return Hint(
        id="kubernetes_baseurl",
        message="Running in Kubernetes. Set BENGAL_BASEURL for correct canonical URLs.",
        priority=10,
        context=frozenset({"build", "serve", "config"}),
    )


def _hint_wsl_watchfiles(
    *,
    context: str = "",
    **_: object,
) -> Hint | None:
    if context != "serve":
        return None
    if not is_wsl():
        return None
    return Hint(
        id="wsl_watchfiles",
        message="On WSL. If live reload is unreliable, try WATCHFILES_FORCE_POLLING=1",
        priority=20,
        context=frozenset({"serve"}),
    )


def _hint_dev_server_container(
    *,
    host: str = "localhost",
    context: str = "",
    **_: object,
) -> Hint | None:
    if context != "serve":
        return None
    if not is_docker():
        return None
    if host not in ("localhost", "127.0.0.1"):
        return None
    return Hint(
        id="dev_server_container",
        message="Serving on localhost. For host access, use bengal serve --host 0.0.0.0",
        priority=15,
        context=frozenset({"serve"}),
    )


def _hint_gil(
    *,
    context: str = "",
    **_: object,
) -> Hint | None:
    from bengal.utils.concurrency.gil import get_gil_status_message

    result = get_gil_status_message()
    if result is None:
        return None
    _, tip = result
    return Hint(
        id="gil",
        message=tip,
        priority=30,
        context=frozenset({"build", "serve"}),
    )


_HINT_FUNCTIONS: list[Callable[..., Hint | None]] = [
    _hint_docker_baseurl,
    _hint_kubernetes_baseurl,
    _hint_wsl_watchfiles,
    _hint_dev_server_container,
    _hint_gil,
]


def _hints_enabled() -> bool:
    """Check if hints are globally enabled."""
    if os.environ.get("BENGAL_HINTS") == "0":
        return False
    if os.environ.get("BENGAL_NO_HINTS") in ("1", "true"):
        return False
    return True


def _hint_opted_out(hint_id: str) -> bool:
    """Check if a specific hint is opted out by env var."""
    env_key = f"BENGAL_HINT_{hint_id.upper().replace('-', '_')}"
    return os.environ.get(env_key) in ("0", "false")


def collect_hints(
    context: str,
    *,
    baseurl: str = "",
    host: str = "localhost",
    quiet: bool = False,
    max_hints: int = 1,
    site_root: Path | str | None = None,
) -> list[Hint]:
    """
    Collect DX hints for the given context.

    Args:
        context: One of "build", "serve", "config".
        baseurl: Current site baseurl (empty means unset).
        host: Dev server host (for serve context).
        quiet: If True, return empty (suppress hints).
        max_hints: Maximum hints to return (default 1).
        site_root: Optional site root path (for future path-based hints).

    Returns:
        List of hints, sorted by priority, up to max_hints.
    """
    if not _hints_enabled() or quiet:
        return []

    hints: list[Hint] = []
    kwargs: dict[str, object] = {
        "baseurl": baseurl,
        "host": host,
        "context": context,
    }

    for fn in _HINT_FUNCTIONS:
        if len(hints) >= max_hints:
            break

        try:
            hint = fn(**kwargs)

            if hint is None:
                continue
            if context not in hint.context:
                continue
            if _hint_opted_out(hint.id):
                continue

            hints.append(hint)
        except Exception:
            continue

    hints.sort(key=lambda h: h.priority)
    return hints[:max_hints]
