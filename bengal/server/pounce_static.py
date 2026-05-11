"""Compatibility helpers for Pounce static serving integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    type ASGIApp = Callable[..., Any]

_MIN_POUNCE_STATIC_FALLBACK_VERSION = "0.7.0"


def create_static_app_with_fallback(
    fallback: ASGIApp,
    *,
    mounts: dict[str, Path],
    cache_control: str,
    precompressed: bool,
    follow_symlinks: bool,
    index_file: str | None,
) -> ASGIApp:
    """Create a Pounce static app that can fall back to Bengal responses.

    Pounce exposes ``create_static_handler()`` publicly for pure static mounts,
    but that helper does not accept a fallback ASGI app. Bengal preview needs
    fallback handling for generated custom 404 pages and health checks, so keep
    the private Pounce import isolated here. ``pyproject.toml`` pins
    ``bengal-pounce>=0.7.0`` for the ``StaticFiles(app, mounts=...)`` contract.
    """
    try:
        from pounce._static import StaticFiles, StaticMount
    except ImportError as exc:
        raise RuntimeError(
            "Pounce static fallback support is unavailable. "
            f"Bengal expects bengal-pounce>={_MIN_POUNCE_STATIC_FALLBACK_VERSION}; "
            "upgrade Pounce or switch preview serving to Pounce's public static API."
        ) from exc

    return StaticFiles(
        fallback,
        mounts=[
            StaticMount(
                url_path=url_path,
                directory=directory,
                cache_control=cache_control,
                precompressed=precompressed,
                follow_symlinks=follow_symlinks,
                index_file=index_file,
            )
            for url_path, directory in mounts.items()
        ],
    )
