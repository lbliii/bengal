"""
Build badge and duration formatting utilities.

Generates self-contained build artifacts (SVG badges, duration strings) that
can be served from the built site to display build metrics (e.g., a footer
badge showing "built in 1m 02s").

Functions:
    format_duration_ms_compact
        Formats milliseconds into compact human-readable strings:
        950 → "950ms", 1200 → "1.2s", 62000 → "1m 02s", 3726000 → "1h 02m"
    build_shields_like_badge_svg
        Generates a shields.io-style SVG badge with configurable label,
        message, and colors. Self-contained (no external fonts or images).

Design Principles:
    - Pure functions: No I/O, no logging, no side effects
    - Self-contained output: SVG badges work without external dependencies
    - Called from postprocess layer which handles file writing

Usage:
    from bengal.orchestration.badge import format_duration_ms_compact, build_shields_like_badge_svg

    duration_str = format_duration_ms_compact(3500)  # "3.5s"
    svg = build_shields_like_badge_svg(label="built", message=duration_str)

See Also:
    bengal.orchestration.postprocess: Calls badge generation during post-processing
"""

from __future__ import annotations

import math


def format_duration_ms_compact(ms: float) -> str:
    """
    Format milliseconds into a compact, human-friendly string.

    Examples:
        - 950 -> "950ms"
        - 1200 -> "1.2s"
        - 62_000 -> "1m 02s"
        - 3_726_000 -> "1h 02m"
    """
    if ms <= 0:
        return "0ms"

    if ms < 1000:
        return f"{int(ms)}ms"

    total_seconds = ms / 1000.0
    if total_seconds < 60:
        # One decimal place, trimmed (e.g. 1.0s -> 1s)
        s = round(total_seconds, 1)
        if math.isclose(s, round(s)):
            return f"{int(round(s))}s"
        return f"{s:.1f}s"

    total_minutes = int(total_seconds // 60)
    seconds = int(round(total_seconds - (total_minutes * 60)))
    if seconds == 60:
        total_minutes += 1
        seconds = 0

    if total_minutes < 60:
        return f"{total_minutes}m {seconds:02d}s"

    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes:02d}m"


def build_shields_like_badge_svg(
    *,
    label: str,
    message: str,
    label_color: str = "#555",
    message_color: str = "#4c1d95",
    height: int = 20,
) -> str:
    """
    Generate a small "shields.io-like" SVG badge.

    This is intentionally minimal and self-contained (no external fonts, no images).
    Width is estimated from character counts; rendering is stable across platforms.
    """
    # Rough width estimate (similar to shields.io rendering): 7px per char + padding.
    # This does not need pixel-perfect accuracy for our use case.
    char_w = 7
    pad = 10
    label_w = max(30, (len(label) * char_w) + pad)
    message_w = max(30, (len(message) * char_w) + pad)
    total_w = label_w + message_w

    label_x = label_w / 2
    message_x = label_w + (message_w / 2)
    text_y = (height / 2) + 4  # baseline-ish

    # Small corner radius similar to shields badges
    r = 3

    # Note: keep SVG compact and deterministic
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{height}" role="img"'
        f' aria-label="{label}: {message}">\n'
        f"  <title>{label}: {message}</title>\n"
        f'  <linearGradient id="s" x2="0" y2="100%">\n'
        f'    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>\n'
        f'    <stop offset="1" stop-opacity=".1"/>\n'
        f"  </linearGradient>\n"
        f'  <clipPath id="r">\n'
        f'    <rect width="{total_w}" height="{height}" rx="{r}" fill="#fff"/>\n'
        f"  </clipPath>\n"
        f'  <g clip-path="url(#r)">\n'
        f'    <rect width="{label_w}" height="{height}" fill="{label_color}"/>\n'
        f'    <rect x="{label_w}" width="{message_w}" height="{height}" fill="{message_color}"/>\n'
        f'    <rect width="{total_w}" height="{height}" fill="url(#s)"/>\n'
        f"  </g>\n"
        f'  <g fill="#fff" text-anchor="middle"\n'
        f'     font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">\n'
        f'    <text x="{label_x}" y="{text_y}">{_escape_xml(label)}</text>\n'
        f'    <text x="{message_x}" y="{text_y}">{_escape_xml(message)}</text>\n'
        f"  </g>\n"
        f"</svg>\n"
    )


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
