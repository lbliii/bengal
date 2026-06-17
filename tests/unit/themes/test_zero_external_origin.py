"""
Zero-external-origin guard for the default theme.

Default build output must not reference third-party CDN origins at runtime.
Opt-in self-hosted capabilities (#550) may add local asset URLs only.
"""

from __future__ import annotations

import re
from pathlib import Path

THEME_ROOT = Path(__file__).resolve().parents[3] / "bengal" / "themes" / "default"

# Runtime CDN origins that must not appear in shipped theme assets.
FORBIDDEN_ORIGINS = (
    "cdn.jsdelivr.net",
    "d3js.org",
    "unpkg.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)

# Scan these paths relative to the theme root.
SCAN_GLOBS = (
    "templates/**/*.html",
    "assets/js/**/*.js",
    "assets/css/**/*.css",
)

ORIGIN_RE = re.compile(
    r"https?://(" + "|".join(re.escape(o) for o in FORBIDDEN_ORIGINS) + r")",
    re.IGNORECASE,
)


def _collect_violations() -> list[tuple[str, int, str]]:
    violations: list[tuple[str, int, str]] = []
    for pattern in SCAN_GLOBS:
        for path in sorted(THEME_ROOT.glob(pattern)):
            if not path.is_file():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if ORIGIN_RE.search(line):
                    rel = path.relative_to(THEME_ROOT)
                    violations.append((str(rel), lineno, line.strip()))
    return violations


def test_default_theme_has_no_external_cdn_origins() -> None:
    """Shipped theme templates/CSS/JS must not reference CDN origins."""
    violations = _collect_violations()
    if violations:
        details = "\n".join(f"  {path}:{lineno}: {text}" for path, lineno, text in violations)
        raise AssertionError(
            "Default theme must make zero external network requests. "
            f"Found forbidden CDN origins:\n{details}"
        )


def test_zero_external_origin_guard_detects_planted_cdn() -> None:
    """Guard must fail on a planted CDN URL."""
    sample = "loadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js');"
    assert ORIGIN_RE.search(sample) is not None
