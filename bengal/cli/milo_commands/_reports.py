"""Small helpers for verdict-first CLI report contexts."""

from __future__ import annotations


def bar(value: int, total: int, *, width: int = 18, fill: str = "#", empty: str = ".") -> str:
    """Return a stable fixed-width bar for command summaries."""
    filled = 0 if total <= 0 else round(value / total * width)
    filled = min(width, max(0, filled))
    return fill * filled + empty * (width - filled)


def palette(style: str) -> dict[str, str]:
    """Return glyphs for human, ASCII, or CI output."""
    if style in {"ascii", "ci"}:
        return {
            "error": "x",
            "warning": "!",
            "suggestion": "^",
            "info": ".",
            "success": "v",
            "ok": "v",
            "fill": "#",
            "empty": ".",
        }
    return {
        "error": "✖",
        "warning": "▲",
        "suggestion": "◆",
        "info": "•",
        "success": "✓",
        "ok": "✓",
        "fill": "█",
        "empty": "░",
    }
