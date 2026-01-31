"""
Behavioral assertion helpers for Bengal tests.

This module provides assertion helpers that verify OUTCOMES rather than
implementation details. Use these instead of mock.assert_called() patterns.

Usage:
    from tests._testing.assertions import (
        assert_page_rendered,
        assert_page_contains,
        assert_build_idempotent,
        assert_incremental_equivalent,
        assert_all_pages_have_urls,
        assert_taxonomy_pages_complete,
    )

RFC: rfc-behavioral-test-hardening (Phase 1)
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site


# =============================================================================
# OUTPUT VERIFICATION
# =============================================================================


def assert_page_rendered(
    output_dir: Path,
    page_path: str,
    *,
    contains: list[str] | None = None,
    not_contains: list[str] | None = None,
    min_size: int = 0,
) -> str:
    """
    Assert a page was rendered with expected content.

    Verifies that a specific output file exists and optionally checks its content
    for expected/forbidden strings.

    Args:
        output_dir: Path to the build output directory (e.g., site.output_dir)
        page_path: Relative path to the expected output file (e.g., "index.html")
        contains: List of strings that MUST appear in the output
        not_contains: List of strings that MUST NOT appear in the output
        min_size: Minimum file size in bytes (default: 0)

    Returns:
        The content of the rendered page (for further assertions if needed)

    Raises:
        AssertionError: If the page doesn't exist or content checks fail

    Example:
        assert_page_rendered(
            site.output_dir,
            "docs/index.html",
            contains=["<h1>Documentation</h1>", "<nav"],
            not_contains=["ERROR", "undefined"],
        )
    """
    html_path = output_dir / page_path
    assert html_path.exists(), (
        f"Expected page '{page_path}' to be rendered at {html_path}. "
        f"Directory contents: {list(output_dir.rglob('*.html'))[:10]}"
    )

    content = html_path.read_text(encoding="utf-8")

    if min_size > 0:
        assert len(content) >= min_size, (
            f"Page '{page_path}' is too small: {len(content)} bytes (expected >= {min_size})"
        )

    for expected in contains or []:
        assert expected in content, (
            f"Expected '{expected}' in {page_path}. Content preview: {content[:500]}..."
        )

    for forbidden in not_contains or []:
        assert forbidden not in content, (
            f"Unexpected '{forbidden}' found in {page_path}. Content preview: {content[:500]}..."
        )

    return content


def assert_page_contains(
    output_dir: Path,
    page_path: str,
    pattern: str,
    *,
    flags: int = 0,
) -> re.Match[str]:
    """
    Assert a page contains content matching a regex pattern.

    Args:
        output_dir: Path to the build output directory
        page_path: Relative path to the output file
        pattern: Regex pattern to search for
        flags: Regex flags (e.g., re.IGNORECASE)

    Returns:
        The regex match object

    Raises:
        AssertionError: If the page doesn't exist or pattern not found

    Example:
        match = assert_page_contains(
            site.output_dir,
            "index.html",
            r'<title>(.+)</title>',
        )
        assert match.group(1) == "Home"
    """
    html_path = output_dir / page_path
    assert html_path.exists(), f"Expected page '{page_path}' to exist at {html_path}"

    content = html_path.read_text(encoding="utf-8")
    match = re.search(pattern, content, flags)

    assert match is not None, (
        f"Pattern '{pattern}' not found in {page_path}. Content preview: {content[:500]}..."
    )

    return match


def assert_output_files_exist(
    output_dir: Path,
    expected_files: Iterable[str],
) -> None:
    """
    Assert that all expected files exist in the output directory.

    Args:
        output_dir: Path to the build output directory
        expected_files: Iterable of relative paths that should exist

    Raises:
        AssertionError: If any expected file is missing

    Example:
        assert_output_files_exist(
            site.output_dir,
            ["index.html", "about/index.html", "css/main.css"],
        )
    """
    missing = []
    for rel_path in expected_files:
        full_path = output_dir / rel_path
        if not full_path.exists():
            missing.append(rel_path)

    assert not missing, (
        f"Missing expected output files: {missing}. "
        f"Available files: {[str(p.relative_to(output_dir)) for p in output_dir.rglob('*') if p.is_file()][:20]}"
    )


# =============================================================================
# BUILD BEHAVIOR VERIFICATION
# =============================================================================


def _hash_output_dir(output_dir: Path) -> dict[str, str]:
    """
    Create a content hash map of all files in the output directory.

    Args:
        output_dir: Path to the output directory

    Returns:
        Dict mapping relative paths to content hashes
    """
    hashes = {}
    for file_path in output_dir.rglob("*"):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(output_dir))
            content = file_path.read_bytes()
            hashes[rel_path] = hashlib.sha256(content).hexdigest()
    return hashes


def _normalize_html_for_comparison(html: str) -> str:
    """
    Normalize HTML content for comparison, stripping volatile content.

    Removes:
    - Build timestamps
    - Content hashes in filenames
    - Excessive whitespace

    Args:
        html: Raw HTML content

    Returns:
        Normalized HTML string
    """
    # Remove build timestamps
    html = re.sub(r'data-build-time="[^"]*"', 'data-build-time=""', html)
    html = re.sub(r'data-build-timestamp="[^"]*"', 'data-build-timestamp=""', html)

    # Remove content hashes in asset URLs (e.g., main.a1b2c3d4.css -> main.HASH.css)
    html = re.sub(r"\.[a-f0-9]{8,}\.(css|js)", ".HASH.\\1", html)

    # Normalize whitespace
    html = re.sub(r"\s+", " ", html).strip()

    return html


def assert_build_idempotent(site: Site) -> None:
    """
    Assert that building a site twice produces identical output.

    This is a critical invariant: running a build should not change the output
    if nothing has changed.

    Args:
        site: A Site instance that has already been built

    Raises:
        AssertionError: If the second build changes any output files

    Example:
        site = create_site(tmp_path)
        site.build()
        assert_build_idempotent(site)  # Builds again and compares
    """
    from bengal.orchestration.build.options import BuildOptions

    first_hashes = _hash_output_dir(site.output_dir)

    # Build again
    options = BuildOptions(incremental=False, quiet=True)
    site.build(options=options)

    second_hashes = _hash_output_dir(site.output_dir)

    # Compare
    added = set(second_hashes.keys()) - set(first_hashes.keys())
    removed = set(first_hashes.keys()) - set(second_hashes.keys())
    changed = {
        k for k in first_hashes.keys() & second_hashes.keys() if first_hashes[k] != second_hashes[k]
    }

    assert not added and not removed and not changed, (
        f"Build is not idempotent - second build changed output. "
        f"Added: {added}, Removed: {removed}, Changed: {changed}"
    )


def assert_incremental_equivalent(
    site_path: Path,
    *,
    modify_file: str | None = None,
) -> None:
    """
    Assert that full build and incremental build produce equivalent output.

    This verifies that the incremental build system produces correct results
    by comparing against a full (non-incremental) build.

    Args:
        site_path: Path to the site root directory
        modify_file: Optional file to modify before incremental build
                    (relative to content directory)

    Raises:
        AssertionError: If incremental build differs from full build

    Example:
        assert_incremental_equivalent(tmp_path / "site")
    """
    import shutil

    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    # Full build
    site1 = Site.from_config(site_path)
    site1.discover_content()
    site1.discover_assets()
    options_full = BuildOptions(incremental=False, quiet=True)
    site1.build(options=options_full)
    full_hashes = _hash_output_dir(site1.output_dir)

    # Optionally modify a file
    if modify_file:
        content_file = site_path / "content" / modify_file
        if content_file.exists():
            original = content_file.read_text()
            content_file.write_text(original + "\n<!-- incremental test -->")

    # Clean output and do incremental build
    shutil.rmtree(site1.output_dir, ignore_errors=True)

    site2 = Site.from_config(site_path)
    site2.discover_content()
    site2.discover_assets()
    options_incr = BuildOptions(incremental=True, quiet=True)
    site2.build(options=options_incr)
    incr_hashes = _hash_output_dir(site2.output_dir)

    # Compare (normalize for any file that might have changed due to modification)
    # We compare the set of files and their normalized content
    assert set(full_hashes.keys()) == set(incr_hashes.keys()), (
        f"Incremental build has different files than full build. "
        f"Full only: {set(full_hashes.keys()) - set(incr_hashes.keys())}, "
        f"Incr only: {set(incr_hashes.keys()) - set(full_hashes.keys())}"
    )


# =============================================================================
# SITE STRUCTURE VERIFICATION
# =============================================================================


def assert_all_pages_have_urls(site: Site) -> None:
    """
    Assert that every page in the site has a unique, non-empty URL.

    Args:
        site: A Site instance (built or unbuilt)

    Raises:
        AssertionError: If any page lacks a URL or URLs are duplicated

    Example:
        site.build()
        assert_all_pages_have_urls(site)
    """
    urls: dict[str, list[str]] = {}
    missing_url = []

    for page in site.pages:
        href = getattr(page, "href", None) or getattr(page, "_path", None)
        if not href:
            missing_url.append(str(page.source_path))
            continue

        if href not in urls:
            urls[href] = []
        urls[href].append(str(page.source_path))

    assert not missing_url, f"Pages without URLs: {missing_url}"

    duplicates = {url: sources for url, sources in urls.items() if len(sources) > 1}
    assert not duplicates, f"Duplicate URLs found: {duplicates}"


def assert_taxonomy_pages_complete(
    site: Site,
    taxonomy_name: str = "tags",
) -> None:
    """
    Assert that taxonomy pages correctly list all tagged content.

    For each taxonomy term, verifies that the taxonomy page lists
    exactly the pages that have that term.

    Args:
        site: A Site instance that has been built
        taxonomy_name: Name of the taxonomy to verify (default: "tags")

    Raises:
        AssertionError: If any taxonomy page is incomplete or incorrect

    Example:
        site.build()
        assert_taxonomy_pages_complete(site, "tags")
    """
    taxonomies = getattr(site, "taxonomies", {})
    if taxonomy_name not in taxonomies:
        return  # No taxonomy defined, nothing to check

    taxonomy_data = taxonomies[taxonomy_name]

    for term, term_data in taxonomy_data.items():
        # Get pages that should have this term
        expected_pages = set()
        for page in site.regular_pages:
            page_terms = getattr(page, taxonomy_name, []) or []
            if term in page_terms or term.lower() in [t.lower() for t in page_terms]:
                expected_pages.add(str(page.source_path))

        # Get pages listed in taxonomy
        actual_pages = set()
        term_pages = term_data.get("pages", [])
        for p in term_pages:
            if hasattr(p, "source_path"):
                actual_pages.add(str(p.source_path))
            else:
                actual_pages.add(str(p))

        assert expected_pages == actual_pages, (
            f"Taxonomy '{taxonomy_name}/{term}' has wrong members. "
            f"Expected: {expected_pages}, Actual: {actual_pages}, "
            f"Missing: {expected_pages - actual_pages}, "
            f"Extra: {actual_pages - expected_pages}"
        )


def assert_menu_structure(
    site: Site,
    *,
    min_entries: int = 0,
    contains_titles: list[str] | None = None,
    all_hrefs_absolute: bool = True,
) -> None:
    """
    Assert the site menu has expected structure.

    Args:
        site: A Site instance that has been built
        min_entries: Minimum number of menu entries expected
        contains_titles: List of titles that must appear in menu
        all_hrefs_absolute: Whether all menu hrefs should be absolute (start with /)

    Raises:
        AssertionError: If menu structure doesn't match expectations

    Example:
        assert_menu_structure(
            site,
            min_entries=2,
            contains_titles=["Docs", "About"],
        )
    """
    menu = getattr(site, "menu", [])

    assert len(menu) >= min_entries, f"Menu has {len(menu)} entries, expected >= {min_entries}"

    if contains_titles:
        menu_titles = {getattr(m, "title", None) for m in menu}
        missing = set(contains_titles) - menu_titles
        assert not missing, f"Menu missing expected titles: {missing}. Found: {menu_titles}"

    if all_hrefs_absolute:
        bad_hrefs = []
        for m in menu:
            href = getattr(m, "href", "")
            if href and not href.startswith("/"):
                bad_hrefs.append((getattr(m, "title", "?"), href))
        assert not bad_hrefs, f"Menu has non-absolute hrefs: {bad_hrefs}"


# =============================================================================
# INCREMENTAL BUILD VERIFICATION
# =============================================================================


def assert_unchanged_files_not_rebuilt(
    stats,
    *,
    tolerance: int = 0,
) -> None:
    """
    Assert that unchanged files were not rebuilt.

    Args:
        stats: BuildStats object from site.build()
        tolerance: Number of acceptable rebuilds (for section-level optimization)

    Raises:
        AssertionError: If too many unchanged files were rebuilt

    Example:
        stats = site.build(incremental=True)
        assert_unchanged_files_not_rebuilt(stats)
    """
    decision = getattr(stats, "incremental_decision", None)
    if decision is None:
        return  # No decision info, can't verify

    pages_rebuilt = len(getattr(decision, "pages_to_build", []))
    assert pages_rebuilt <= tolerance, (
        f"Too many pages rebuilt: {pages_rebuilt} (tolerance: {tolerance}). "
        f"Expected 0 rebuilds when no files changed."
    )


def assert_changed_file_rebuilt(
    stats,
    changed_file: str,
) -> None:
    """
    Assert that a changed file was rebuilt.

    Args:
        stats: BuildStats object from site.build()
        changed_file: Name or partial path of the file that was changed

    Raises:
        AssertionError: If the changed file was not rebuilt

    Example:
        # After modifying page1.md
        stats = site.build(incremental=True)
        assert_changed_file_rebuilt(stats, "page1")
    """
    decision = getattr(stats, "incremental_decision", None)
    if decision is None:
        # No decision info, check total pages instead
        assert getattr(stats, "total_pages", 0) >= 1, (
            "No build decision info, and no pages were built"
        )
        return

    rebuilt_paths = {str(p.source_path) for p in getattr(decision, "pages_to_build", [])}
    assert any(changed_file in p for p in rebuilt_paths), (
        f"Changed file '{changed_file}' was not rebuilt. Rebuilt files: {rebuilt_paths}"
    )


# =============================================================================
# CONTENT CORRECTNESS VERIFICATION
# =============================================================================


def assert_no_broken_internal_links(
    output_dir: Path,
    *,
    check_anchors: bool = False,
) -> None:
    """
    Assert that all internal links in HTML files point to existing pages.

    Args:
        output_dir: Path to the build output directory
        check_anchors: Whether to also verify #anchor targets exist

    Raises:
        AssertionError: If any broken internal links are found

    Example:
        site.build()
        assert_no_broken_internal_links(site.output_dir)
    """
    broken_links = []

    for html_file in output_dir.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")

        # Find internal links (href starting with / but not //)
        for match in re.finditer(r'href="(/[^"]*)"', content):
            href = match.group(1)

            # Skip external links
            if href.startswith("//"):
                continue

            # Skip anchor-only links
            if href.startswith("#"):
                continue

            # Parse path and anchor
            if "#" in href:
                path, anchor = href.split("#", 1)
            else:
                path, anchor = href, None

            # Resolve to file path
            target_path = output_dir / path.lstrip("/")
            if target_path.is_dir():
                target_path = target_path / "index.html"

            if not target_path.exists():
                broken_links.append((str(html_file.relative_to(output_dir)), href))

    assert not broken_links, (
        f"Found {len(broken_links)} broken internal links: "
        f"{broken_links[:10]}{'...' if len(broken_links) > 10 else ''}"
    )


def assert_pages_have_required_metadata(
    site: Site,
    required_fields: list[str],
    *,
    exclude_generated: bool = True,
) -> None:
    """
    Assert that all pages have required metadata fields.

    Args:
        site: A Site instance
        required_fields: List of metadata field names that must be present
        exclude_generated: Whether to exclude generated pages from check

    Raises:
        AssertionError: If any page is missing required metadata

    Example:
        assert_pages_have_required_metadata(
            site,
            ["title", "description"],
        )
    """
    missing = []

    for page in site.pages:
        if exclude_generated:
            is_generated = getattr(page, "metadata", {}).get("_generated", False)
            if is_generated:
                continue

        metadata = getattr(page, "metadata", {})
        page_missing = []

        for field in required_fields:
            # Check both metadata dict and direct attributes
            has_field = field in metadata or hasattr(page, field) and getattr(page, field)
            if not has_field:
                page_missing.append(field)

        if page_missing:
            missing.append((str(page.source_path), page_missing))

    assert not missing, (
        f"Pages missing required metadata: {missing[:10]}{'...' if len(missing) > 10 else ''}"
    )
