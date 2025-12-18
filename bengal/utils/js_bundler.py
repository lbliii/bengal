"""
Pure Python JavaScript Bundler for Bengal SSG.

Bundles multiple JavaScript files into a single file without any Node.js dependencies.
Uses concatenation with IIFE preservation to avoid variable conflicts.

Features:
- Preserves IIFEs (Immediately Invoked Function Expressions)
- Adds source file comments for debugging
- Configurable load order via manifest or naming convention
- Minification via jsmin (optional)

Performance Impact:
- Reduces HTTP requests from ~20 to 1 on mobile (saves ~1-2s on slow 4G)
- Single bundled file can be cached efficiently
"""

from __future__ import annotations

from pathlib import Path

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def bundle_js_files(
    files: list[Path],
    *,
    minify: bool = False,
    add_source_comments: bool = True,
) -> str:
    """
    Bundle multiple JavaScript files into a single string.

    Files are concatenated in the order provided. Each file's content
    is separated by a newline. Source comments can be added for debugging.

    Args:
        files: List of JS file paths in load order (dependencies first)
        minify: Whether to minify the bundled output
        add_source_comments: Whether to add /* source: filename */ comments

    Returns:
        Bundled JavaScript content as a single string

    Example:
        >>> files = [Path("js/utils.js"), Path("js/main.js")]
        >>> bundled = bundle_js_files(files, minify=True)
    """
    if not files:
        return ""

    chunks: list[str] = []

    # Header comment
    chunks.append("/* Bengal JS Bundle - Auto-generated */")
    chunks.append("")

    for file_path in files:
        if not file_path.exists():
            logger.warning("js_bundle_file_not_found", path=str(file_path))
            continue

        try:
            content = file_path.read_text(encoding="utf-8").strip()
            if not content:
                continue

            if add_source_comments:
                chunks.append(f"/* === {file_path.name} === */")

            chunks.append(content)
            chunks.append("")  # Blank line between files

        except Exception as e:
            logger.error(
                "js_bundle_read_failed",
                path=str(file_path),
                error=str(e),
            )
            continue

    bundled = "\n".join(chunks)

    if minify and bundled:
        try:
            from jsmin import jsmin

            bundled = jsmin(bundled)
        except ImportError:
            logger.warning("jsmin_unavailable_for_bundle")

    return bundled


def get_theme_js_bundle_order() -> list[str]:
    """
    Return the canonical load order for Bengal default theme JS files.

    This order ensures dependencies are loaded before dependents:
    1. utils.js - Core utilities (BengalUtils namespace)
    2. bengal-enhance.js - Enhancement registry (load second)
    3. core/theme.js - Theme switching (merged from theme-toggle.js + theme-init.js)
    4. core/search.js - Search (merged from search.js, search-modal.js, search-page.js, search-preload.js)
    5. core/nav-dropdown.js - Navigation dropdowns (always needed)
    6. core/session-path-tracker.js - Analytics (always needed)
    7. core/build-badge.js - Footer build-time badge (optional; no-op if absent)
    8. enhancements/mobile-nav.js - Mobile navigation
    9. enhancements/tabs.js - Tab component
    10. enhancements/toc.js - Table of contents
    11. enhancements/action-bar.js - Action bar (copy, etc.)
    12. enhancements/interactive.js - Interactive elements
    13. main.js - Main initialization
    14. enhancements/copy-link.js - Copy link functionality
    15. enhancements/holo.js - Holographic effects (merged from holo.js + holo-cards.js)
    16. enhancements/lazy-loaders.js - Lazy loading (Mermaid, D3, etc.)

    Returns:
        List of JS filenames in load order (with paths relative to js/ directory)
    """
    return [
        "utils.js",
        "bengal-enhance.js",
        "core/theme.js",
        "core/search.js",
        "core/nav-dropdown.js",
        "core/session-path-tracker.js",
        "core/build-badge.js",
        "enhancements/mobile-nav.js",
        "enhancements/tabs.js",
        "enhancements/toc.js",
        "enhancements/action-bar.js",
        "enhancements/interactive.js",
        "main.js",
        "enhancements/copy-link.js",
        "enhancements/holo.js",
        "enhancements/lazy-loaders.js",
    ]


def get_theme_js_excluded() -> set[str]:
    """
    Return JS files that should NOT be bundled.

    These are either:
    - Third-party minified libraries (already optimized)
    - Conditionally loaded scripts (loaded via lazy-loaders.js)
    - Feature-specific scripts that may not be enabled

    Returns:
        Set of filenames to exclude from bundling
    """
    return {
        # Third-party libraries (in vendor/)
        "vendor/lunr.min.js",
        "vendor/tabulator.min.js",
        # Lazy-loaded scripts (loaded on demand by lazy-loaders.js)
        "enhancements/data-table.js",
        "graph-contextual.js",
        "graph-minimap.js",
        "mermaid-theme.js",
        "mermaid-toolbar.js",
        # Feature-specific (loaded conditionally)
        "enhancements/lightbox.js",
    }


def discover_js_files(
    js_dir: Path,
    *,
    bundle_order: list[str] | None = None,
    excluded: set[str] | None = None,
) -> list[Path]:
    """
    Discover and order JS files for bundling from a directory.

    Files are ordered according to bundle_order if provided,
    with any remaining files appended at the end.

    Args:
        js_dir: Directory containing JS files
        bundle_order: Explicit load order (filenames only)
        excluded: Set of filenames to skip

    Returns:
        List of file paths in bundling order
    """
    if not js_dir.exists():
        return []

    bundle_order = bundle_order or get_theme_js_bundle_order()
    excluded = excluded or get_theme_js_excluded()

    # Find all JS files recursively (including subdirectories)
    # Maps relative path -> file path (e.g., "core/theme.js" -> Path(...))
    all_files: dict[str, Path] = {}
    # Also track files by filename for backward compatibility in bundle_order
    files_by_name: dict[str, Path] = {}

    for js_file in js_dir.rglob("*.js"):
        # Get relative path from js_dir (e.g., "core/theme.js" or "utils.js")
        rel_path = js_file.relative_to(js_dir)
        rel_path_str = str(rel_path).replace("\\", "/")  # Normalize Windows paths
        all_files[rel_path_str] = js_file
        # Also index by filename for backward compatibility in bundle_order lookup
        files_by_name[js_file.name] = js_file

    # Build ordered list
    ordered: list[Path] = []
    seen_paths: set[Path] = set()

    # First: files in explicit order (using relative paths or filename)
    for name in bundle_order:
        # Try relative path first, then filename
        ordered_js_file: Path | None = all_files.get(name) or files_by_name.get(name)
        if ordered_js_file and name not in excluded and ordered_js_file not in seen_paths:
            ordered.append(ordered_js_file)
            seen_paths.add(ordered_js_file)

    # Then: any remaining files not already added or excluded (alphabetically)
    # Check exclusion using the canonical relative path
    for rel_path_str, remaining_js_file in sorted(all_files.items()):
        if remaining_js_file not in seen_paths and rel_path_str not in excluded:
            ordered.append(remaining_js_file)
            seen_paths.add(remaining_js_file)

    return ordered


def create_js_bundle(
    js_dir: Path,
    output_path: Path | None = None,
    *,
    minify: bool = True,
    bundle_order: list[str] | None = None,
    excluded: set[str] | None = None,
) -> str:
    """
    Create a JavaScript bundle from a theme's JS directory.

    High-level function that discovers files and bundles them.

    Args:
        js_dir: Directory containing JS files
        output_path: Optional path to write bundle (if None, returns string only)
        minify: Whether to minify output
        bundle_order: Explicit load order (filenames only)
        excluded: Set of filenames to skip

    Returns:
        Bundled JavaScript content

    Example:
        >>> content = create_js_bundle(
        ...     js_dir=Path("themes/default/assets/js"),
        ...     output_path=Path("public/assets/js/bundle.js"),
        ...     minify=True,
        ... )
    """
    files = discover_js_files(js_dir, bundle_order=bundle_order, excluded=excluded)

    if not files:
        logger.info("js_bundle_no_files", js_dir=str(js_dir))
        return ""

    logger.info(
        "js_bundle_start",
        file_count=len(files),
        js_dir=str(js_dir),
        files=[f.name for f in files],
    )

    bundled = bundle_js_files(files, minify=minify, add_source_comments=not minify)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(bundled, encoding="utf-8")
        logger.info(
            "js_bundle_written",
            output=str(output_path),
            size_kb=len(bundled) / 1024,
        )

    return bundled
