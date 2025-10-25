"""
Centralized configuration for traceback formatting and rendering.

Provides a simple configuration object with a style (full/compact/minimal/off),
and utilities to install Rich's global exception hook based on the active style.

MVP: Sources configuration from CLI-provided env var (BENGAL_TRACEBACK) → defaults.
Future: Extend to read from site config and config files.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING


class TracebackStyle(Enum):
    FULL = "full"
    COMPACT = "compact"
    MINIMAL = "minimal"
    OFF = "off"


DEFAULT_SUPPRESS: tuple[str, ...] = ("click", "jinja2")


if TYPE_CHECKING:
    # For type checkers and linters only; avoids runtime import cycle
    from bengal.utils.traceback_renderer import TracebackRenderer


@dataclass
class TracebackConfig:
    """Configuration for traceback display and rich install options."""

    style: TracebackStyle = TracebackStyle.COMPACT
    show_locals: bool = False
    max_frames: int = 10
    suppress: tuple[str, ...] = DEFAULT_SUPPRESS

    @classmethod
    def from_environment(cls) -> TracebackConfig:
        """Load configuration from environment variables (MVP).

        Precedence: BENGAL_TRACEBACK → defaults.
        """
        style_env = (os.getenv("BENGAL_TRACEBACK") or "").strip().lower()
        style: TracebackStyle
        if style_env in {s.value for s in TracebackStyle}:
            style = TracebackStyle(style_env)
        else:
            # Auto defaults: prefer compact for terminals, minimal in CI falls out via should_use_rich.
            style = TracebackStyle.COMPACT

        # Base heuristics by style
        if style == TracebackStyle.FULL:
            default_show_locals = True
            default_max_frames = 25
        elif style == TracebackStyle.COMPACT:
            default_show_locals = False
            default_max_frames = 10
        else:
            default_show_locals = False
            default_max_frames = 5

        # Optional detailed overrides from env
        show_locals_env = os.getenv("BENGAL_TRACEBACK_SHOW_LOCALS")
        max_frames_env = os.getenv("BENGAL_TRACEBACK_MAX_FRAMES")
        suppress_env = os.getenv("BENGAL_TRACEBACK_SUPPRESS")

        show_locals = (
            default_show_locals
            if show_locals_env is None
            else show_locals_env.strip() in {"1", "true", "True", "yes"}
        )
        try:
            max_frames = default_max_frames if not max_frames_env else int(max_frames_env.strip())
        except ValueError:
            max_frames = default_max_frames

        suppress: tuple[str, ...] = DEFAULT_SUPPRESS
        if suppress_env:
            parts = [p.strip() for p in suppress_env.split(",") if p.strip()]
            if parts:
                suppress = tuple(parts)

        return cls(style=style, show_locals=show_locals, max_frames=max_frames, suppress=suppress)

    def install(self) -> None:
        """Install Rich traceback handler according to config and environment.

        - If style == OFF: do not install rich hook (use standard Python)
        - If in CI or non-TTY, rely on rich_console.should_use_rich to skip
        """
        if self.style == TracebackStyle.OFF:
            return

        # Only attempt install if rich is available and terminal is suitable
        try:
            from rich.traceback import install as rich_install

            from bengal.utils.rich_console import get_console, should_use_rich

            if not should_use_rich():
                return

            # Build suppress modules from names
            suppress_modules: list[object] = []
            for name in self.suppress:
                try:
                    mod = __import__(name)
                    suppress_modules.append(mod)
                except Exception:
                    # Best-effort; ignore unknown modules
                    pass

            rich_install(
                console=get_console(),
                show_locals=self.show_locals,
                suppress=tuple(suppress_modules),
                max_frames=self.max_frames,
                width=None,
            )
        except Exception:
            # Silently skip if rich not available or any failure during install
            return

    def get_renderer(self) -> TracebackRenderer:
        from bengal.utils.traceback_renderer import (
            CompactTracebackRenderer,
            FullTracebackRenderer,
            MinimalTracebackRenderer,
            OffTracebackRenderer,
        )

        if self.style == TracebackStyle.FULL:
            return FullTracebackRenderer(self)
        if self.style == TracebackStyle.COMPACT:
            return CompactTracebackRenderer(self)
        if self.style == TracebackStyle.MINIMAL:
            return MinimalTracebackRenderer(self)
        return OffTracebackRenderer(self)


def set_effective_style_from_cli(style_value: str | None) -> None:
    """Helper to set the process env for traceback style from a CLI flag.

    This allows downstream code that calls TracebackConfig.from_environment()
    to see the user choice consistently.
    """
    if not style_value:
        return
    value = style_value.strip().lower()
    if value in {s.value for s in TracebackStyle}:
        os.environ["BENGAL_TRACEBACK"] = value


def map_debug_flag_to_traceback(debug: bool, current: str | None = None) -> None:
    """Map legacy --debug flag to traceback=full unless user explicitly set one."""
    if debug and not (current and current.strip()):
        os.environ["BENGAL_TRACEBACK"] = TracebackStyle.FULL.value


def apply_file_traceback_to_env(site_config: dict | None) -> None:
    """Apply file-based traceback config ([dev.traceback]) to environment.

    Precedence: existing env vars win. Only set if not already present.
    Expected structure:
        site_config["dev"]["traceback"] = {
            "style": "compact|full|minimal|off",
            "show_locals": bool,
            "max_frames": int,
            "suppress": ["click", "jinja2"],
        }
    """
    if not isinstance(site_config, dict):
        return
    dev = site_config.get("dev") if isinstance(site_config.get("dev"), dict) else None
    if not dev:
        return
    tb_cfg = dev.get("traceback") if isinstance(dev.get("traceback"), dict) else None
    if not tb_cfg:
        return

    # Style
    if os.getenv("BENGAL_TRACEBACK") is None:
        style = str(tb_cfg.get("style", "")).strip().lower()
        if style in {s.value for s in TracebackStyle}:
            os.environ["BENGAL_TRACEBACK"] = style

    # show_locals
    if os.getenv("BENGAL_TRACEBACK_SHOW_LOCALS") is None and "show_locals" in tb_cfg:
        os.environ["BENGAL_TRACEBACK_SHOW_LOCALS"] = "1" if tb_cfg.get("show_locals") else "0"

    # max_frames
    if os.getenv("BENGAL_TRACEBACK_MAX_FRAMES") is None and "max_frames" in tb_cfg:
        with contextlib.suppress(Exception):
            os.environ["BENGAL_TRACEBACK_MAX_FRAMES"] = str(int(tb_cfg.get("max_frames")))

    # suppress (comma-separated)
    if os.getenv("BENGAL_TRACEBACK_SUPPRESS") is None and "suppress" in tb_cfg:
        suppress = tb_cfg.get("suppress")
        if isinstance(suppress, (list, tuple)):
            os.environ["BENGAL_TRACEBACK_SUPPRESS"] = ",".join(str(x) for x in suppress)
