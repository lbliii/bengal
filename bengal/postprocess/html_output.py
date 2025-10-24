from __future__ import annotations

import re
from typing import Any

_WS_SENSITIVE_TAGS = ("pre", "code", "textarea", "script", "style")


def _split_protected_regions(html: str) -> list[tuple[str, bool]]:
    """
    Split HTML into segments, marking whitespace-sensitive regions to preserve.

    Returns list of tuples: (segment_text, is_protected)
    """
    if not html:
        return [("", False)]

    # Regex to capture protected blocks with minimal, case-insensitive matching
    # Handles nested text but not nested same tags (sufficient for our use)
    pattern = re.compile(
        r"("
        + r"|".join(rf"<(?:{tag})(?:[^>]*)>.*?</(?:{tag})>" for tag in _WS_SENSITIVE_TAGS)
        + r")",
        re.IGNORECASE | re.DOTALL,
    )

    parts: list[tuple[str, bool]] = []
    last = 0
    for m in pattern.finditer(html):
        if m.start() > last:
            parts.append((html[last : m.start()], False))
        parts.append((m.group(0), True))
        last = m.end()
    if last < len(html):
        parts.append((html[last:], False))
    if not parts:
        return [(html, False)]
    return parts


def _collapse_blank_lines(text: str) -> str:
    # Replace 3+ newlines or 2+ blank lines with a single blank line
    return re.sub(r"\n\s*\n(\s*\n)+", "\n\n", text)


def _strip_trailing_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+(?=\n)", "", text)


def _collapse_intertag_whitespace(text: str) -> str:
    # Collapse whitespace between tags: ">   <" -> "> <"
    # Avoid touching text content; this focuses on inter-tag gaps only
    text = re.sub(r">\s+<", "> <", text)
    # Collapse runs of blank lines to single newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _remove_html_comments(text: str) -> str:
    # Remove standard HTML comments, preserve conditional IE comments `<!--[if ...]>` and `<![endif]-->`
    return re.sub(r"<!--(?!\[if|<!\s*\[endif\])(?:(?!-->).)*-->", "", text, flags=re.DOTALL)


def format_html_output(html: str, mode: str = "raw", options: dict[str, Any] | None = None) -> str:
    """
    Format HTML to produce pristine output, preserving whitespace-sensitive regions.

    Args:
        html: Input HTML string
        mode: "raw" (no-op), "pretty" (stable whitespace), or "minify" (compact inter-tag spacing)
        options: optional flags, e.g., {"remove_comments": True, "collapse_blank_lines": True}

    Returns:
        Formatted HTML string
    """
    if not html or mode == "raw":
        return html or ""

    opts = options or {}
    remove_comments = bool(opts.get("remove_comments", mode == "minify"))
    collapse_blanks = bool(opts.get("collapse_blank_lines", True))

    segments = _split_protected_regions(html)
    out: list[str] = []

    for segment, is_protected in segments:
        if is_protected:
            out.append(segment)
            continue

        transformed = segment

        if remove_comments:
            transformed = _remove_html_comments(transformed)

        # Trim trailing whitespace first for stability
        transformed = _strip_trailing_whitespace(transformed)

        if mode == "pretty":
            if collapse_blanks:
                transformed = _collapse_blank_lines(transformed)
        elif mode == "minify":
            transformed = _collapse_intertag_whitespace(transformed)
            if collapse_blanks:
                transformed = _collapse_blank_lines(transformed)

        out.append(transformed)

    result = "".join(out)

    # Final stabilization: ensure single trailing newline (do not strip spaces inside protected regions)
    if not result.endswith("\n"):
        result += "\n"
    return result
