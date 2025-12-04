"""
HTML output processing and minification utilities.

Provides HTML minification with whitespace preservation for sensitive tags.
Handles HTML minification while preserving whitespace in code blocks, scripts,
and other whitespace-sensitive content.

Key Concepts:
    - HTML minification: Remove unnecessary whitespace and comments
    - Whitespace preservation: Preserve whitespace in sensitive tags
    - Protected regions: Code blocks, scripts, styles protected from minification
    - Void tags: Self-closing tags that don't need closing tags

Related Modules:
    - bengal.postprocess: Post-processing orchestration
    - bengal.config.defaults: HTML output configuration

See Also:
    - bengal/postprocess/html_output.py:minify_html() for HTML minification
"""

from __future__ import annotations

import re
from typing import Any

_WS_SENSITIVE_TAGS = ("pre", "code", "textarea", "script", "style")
_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


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
    # Replace 2+ consecutive blank lines with a single blank line
    return re.sub(r"\n\s*\n(\s*\n)+", "\n\n", text)


def _strip_trailing_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+(?=\n)", "", text)


def _collapse_intertag_whitespace(text: str) -> str:
    # Collapse whitespace between tags while preserving line breaks if present
    # Example:
    #   ">   <"     -> "> <"
    #   ">\n   <"  -> ">\n<" (keeps a single newline for structure)
    def _repl(match: re.Match[str]) -> str:
        s = match.group(0)
        return ">\n<" if "\n" in s else "> <"

    text = re.sub(r">\s+<", _repl, text)
    # Collapse runs of blank lines to single newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _remove_html_comments(text: str) -> str:
    # Remove standard HTML comments, preserve conditional IE comments `<!--[if ...]>` and `<![endif]-->`
    return re.sub(r"<!--(?!\[if|<!\s*\[endif\])(?:(?!-->).)*-->", "", text, flags=re.DOTALL)


def _normalize_class_attributes(text: str) -> str:
    # Collapse internal whitespace inside class attributes: class="a   b c" -> class="a b c"
    def _repl(match: re.Match[str]) -> str:
        before, value, after = match.group(1), match.group(2), match.group(3)
        normalized = " ".join(value.split())
        return f"{before}{normalized}{after}"

    return re.sub(r"(class=\")([^\"]*)(\")", _repl, text)


def _trim_title_text(text: str) -> str:
    # Trim and collapse whitespace inside <title> ... </title>
    def _repl(match: re.Match[str]) -> str:
        start, value, end = match.group(1), match.group(2), match.group(3)
        collapsed = " ".join(value.split())
        return f"{start}{collapsed}{end}"

    return re.sub(r"(<title>)([\s\S]*?)(</title>)", _repl, text, flags=re.IGNORECASE)


def _pretty_indent_html(html: str) -> str:
    """
    Indent non-protected HTML lines with two spaces per nesting level.

    Depth carries across protected segments, but protected content is left untouched.
    """
    segments = _split_protected_regions(html)
    depth = 0
    result_parts: list[str] = []

    open_tag_re = re.compile(r"^<([a-zA-Z0-9:_-]+)(?:\s[^>]*)?>\s*$")
    close_tag_re = re.compile(r"^</([a-zA-Z0-9:_-]+)\s*>\s*$")

    for seg, is_protected in segments:
        if is_protected:
            result_parts.append(seg)
            continue

        for raw_line in seg.splitlines(keepends=True):
            line = raw_line[:-1] if raw_line.endswith("\n") else raw_line
            stripped = line.strip()

            if stripped == "":
                result_parts.append(raw_line)
                continue

            # Outdent on closing tag lines first
            if close_tag_re.match(stripped):
                depth = max(depth - 1, 0)

            indent = "  " * depth
            result_parts.append(f"{indent}{stripped}{'\n' if raw_line.endswith('\n') else ''}")

            # Increase depth after opening tag (non-void, not self-closing)
            m_open = open_tag_re.match(stripped)
            if m_open and not stripped.endswith("/>"):
                tag_name = m_open.group(1).lower()
                if tag_name not in _VOID_TAGS and not tag_name.startswith("!"):
                    depth += 1

    return "".join(result_parts)


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
            # Apply indentation for readability
            transformed = _pretty_indent_html(transformed)
        elif mode == "minify":
            transformed = _collapse_intertag_whitespace(transformed)
            if collapse_blanks:
                transformed = _collapse_blank_lines(transformed)

        # Attribute and inline text normalizations (safe, tag-scoped)
        transformed = _normalize_class_attributes(transformed)
        transformed = _trim_title_text(transformed)

        out.append(transformed)

    result = "".join(out)

    # Final stabilization: ensure single trailing newline (do not strip spaces inside protected regions)
    if not result.endswith("\n"):
        result += "\n"
    return result
