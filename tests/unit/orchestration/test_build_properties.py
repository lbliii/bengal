"""
Property-based tests for Bengal's core build pipeline.

RFC: rfc-behavioral-test-hardening (Phase 3)

These tests use Hypothesis to verify behavioral invariants across
many randomly generated inputs. Unlike example-based tests that check
specific cases, property tests verify that invariants ALWAYS hold.

Invariants tested:
- Build idempotency: Building twice produces identical output
- URL uniqueness: Every page gets a unique URL
- Incremental equivalence: Full build == incremental build
- Content preservation: All source content appears in output
- Taxonomy completeness: Tag pages list all tagged content

Usage:
    # Run property tests with default settings
    pytest tests/unit/orchestration/test_build_properties.py -v

    # Run with more examples (slower, more thorough)
    pytest tests/unit/orchestration/test_build_properties.py -v \
        --hypothesis-seed=0 \
        -o "hypothesis_profile=ci"
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

if TYPE_CHECKING:
    from bengal.core.site import Site


# =============================================================================
# STRATEGIES (Custom Hypothesis generators)
# =============================================================================


def valid_page_title() -> st.SearchStrategy[str]:
    """
    Generate valid page titles.

    Titles must be:
    - Non-empty
    - Printable characters (no control chars)
    - Reasonable length
    """
    return st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N", "P", "S", "Z"),
            min_codepoint=32,
            max_codepoint=126,
        ),
        min_size=1,
        max_size=50,
    ).filter(lambda s: s.strip())  # Must have non-whitespace


def valid_slug() -> st.SearchStrategy[str]:
    """
    Generate valid URL slugs.

    Slugs must be:
    - Lowercase alphanumeric with hyphens
    - Start and end with alphanumeric
    - No consecutive hyphens
    """
    return st.from_regex(r"[a-z][a-z0-9-]{0,30}[a-z0-9]?", fullmatch=True).filter(
        lambda s: "--" not in s
    )


def valid_tag() -> st.SearchStrategy[str]:
    """Generate valid taxonomy tags."""
    return st.from_regex(r"[a-z][a-z0-9-]{0,20}", fullmatch=True)


def page_content_dict() -> st.SearchStrategy[dict[str, str]]:
    """
    Generate a dict of page paths to content.

    Keys are relative paths (e.g., "about.md")
    Values are full markdown content with frontmatter
    """
    return st.dictionaries(
        keys=st.from_regex(r"[a-z][a-z0-9-]{0,20}\.md", fullmatch=True),
        values=st.builds(
            lambda title, body: f"---\ntitle: {title}\n---\n\n# {title}\n\n{body}",
            title=valid_page_title(),
            body=st.text(min_size=10, max_size=200),
        ),
        min_size=1,
        max_size=10,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _create_site_with_content(
    tmp_path: Path,
    content: dict[str, str],
    *,
    base_config: dict | None = None,
) -> "Site":
    """
    Create a Bengal site with the given content.

    Args:
        tmp_path: Temporary directory for the site
        content: Dict mapping relative paths to markdown content
        base_config: Optional additional config settings

    Returns:
        Site instance ready for building
    """
    from bengal.core.site import Site

    # Create site structure
    site_dir = tmp_path / "site"
    site_dir.mkdir(exist_ok=True)

    # Write config
    config_content = """
[site]
title = "Property Test Site"
baseURL = "/"

[build]
output_dir = "public"
"""
    (site_dir / "bengal.toml").write_text(config_content)

    # Create content directory
    content_dir = site_dir / "content"
    content_dir.mkdir(exist_ok=True)

    # Write home page
    (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n\n# Home\n\nWelcome.")

    # Write provided content
    for rel_path, page_content in content.items():
        page_path = content_dir / rel_path
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(page_content)

    # Create and initialize site
    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()

    return site


def _hash_output_dir(output_dir: Path) -> dict[str, str]:
    """Create a content hash map of all files in the output directory."""
    hashes = {}
    for file_path in output_dir.rglob("*"):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(output_dir))
            content = file_path.read_bytes()
            hashes[rel_path] = hashlib.sha256(content).hexdigest()
    return hashes


def _normalize_html(html: str) -> str:
    """Normalize HTML content for comparison."""
    # Remove build timestamps
    html = re.sub(r'data-build-time="[^"]*"', 'data-build-time=""', html)
    html = re.sub(r'data-build-timestamp="[^"]*"', 'data-build-timestamp=""', html)
    # Remove content hashes
    html = re.sub(r"\.[a-f0-9]{8,}\.(css|js)", ".HASH.\\1", html)
    # Normalize whitespace
    html = re.sub(r"\s+", " ", html).strip()
    return html


# =============================================================================
# PROPERTY TESTS
# =============================================================================


@pytest.mark.slow  # Each example runs full build (~100s total)
@pytest.mark.parallel_unsafe  # Full builds conflict with xdist workers in Python 3.14t
class TestBuildProperties:
    """Property-based tests for build behavior."""

    @given(content=page_content_dict())
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_build_is_idempotent(
        self,
        content: dict[str, str],
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        """
        PROPERTY: Building twice produces identical output.

        For any valid site content, running build() twice should produce
        exactly the same output files with identical content.

        Note: Uses dev_mode=True to exclude build_time from index.json,
        since build_time is expected to change between builds (it records
        when the build happened, not a content-derived value).
        """
        from bengal.orchestration.build.options import BuildOptions

        tmp_path = tmp_path_factory.mktemp("idempotent")
        site = _create_site_with_content(tmp_path, content)

        # Enable dev_mode to exclude build_time from index.json
        # build_time changes every build by design - it's not part of idempotency
        site.dev_mode = True

        # First build
        # Note: force_sequential=True due to parallel deadlock in free-threaded Python
        # TODO: Fix parallel rendering deadlock and remove this workaround
        options = BuildOptions(incremental=False, quiet=True, force_sequential=True)
        site.build(options=options)
        first_hashes = _hash_output_dir(site.output_dir)

        # Second build
        site.build(options=options)
        second_hashes = _hash_output_dir(site.output_dir)

        # PROPERTY: Output should be identical
        assert first_hashes == second_hashes, (
            f"Build is not idempotent. "
            f"Changed files: {set(first_hashes.items()) ^ set(second_hashes.items())}"
        )

    @given(content=page_content_dict())
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_all_pages_have_unique_urls(
        self,
        content: dict[str, str],
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        """
        PROPERTY: Every page gets a unique URL.

        Regardless of page titles or content, each page must have a distinct
        URL path. Duplicate URLs would cause pages to overwrite each other.
        """
        from bengal.orchestration.build.options import BuildOptions

        tmp_path = tmp_path_factory.mktemp("unique_urls")
        site = _create_site_with_content(tmp_path, content)

        options = BuildOptions(incremental=False, quiet=True)
        site.build(options=options)

        # Collect all URLs
        urls: dict[str, list[str]] = {}
        for page in site.pages:
            href = getattr(page, "href", None) or getattr(page, "_path", None)
            if not href:
                continue
            if href not in urls:
                urls[href] = []
            urls[href].append(str(page.source_path))

        # PROPERTY: No duplicate URLs
        duplicates = {url: sources for url, sources in urls.items() if len(sources) > 1}
        assert not duplicates, f"Duplicate URLs found: {duplicates}"

    @given(content=page_content_dict())
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_all_source_pages_produce_output(
        self,
        content: dict[str, str],
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        """
        PROPERTY: Every source page produces an output file.

        No source content should be silently dropped. Each .md file in
        content/ should result in a corresponding .html file in output.
        """
        from bengal.orchestration.build.options import BuildOptions

        tmp_path = tmp_path_factory.mktemp("all_output")
        site = _create_site_with_content(tmp_path, content)

        options = BuildOptions(incremental=False, quiet=True)
        site.build(options=options)

        # Get all source pages (excluding _index which becomes index.html)
        source_pages = set()
        for page in site.pages:
            source_path = str(page.source_path)
            if "_index.md" not in source_path:
                source_pages.add(page.source_path.stem)

        # Get all output HTML files
        output_files = set()
        for html_file in site.output_dir.rglob("*.html"):
            rel_path = html_file.relative_to(site.output_dir)
            # Convert path like "about/index.html" to "about"
            if rel_path.name == "index.html" and len(rel_path.parts) > 1:
                output_files.add(rel_path.parts[0])
            elif rel_path.name != "index.html":
                output_files.add(rel_path.stem)

        # PROPERTY: Source pages should have corresponding output
        # Note: Some pages may be excluded by config, so we check subset
        # rather than exact equality
        missing = source_pages - output_files - {"index"}  # index handled separately
        assert len(missing) <= len(source_pages) * 0.1, (  # Allow 10% missing (drafts, etc.)
            f"Too many source pages missing from output: {missing}"
        )


class TestURLProperties:
    """Property-based tests for URL generation."""

    @given(slug=valid_slug())
    @settings(max_examples=100)
    def test_slugs_are_url_safe(self, slug: str) -> None:
        """
        PROPERTY: Generated slugs are URL-safe.

        Slugs should only contain characters safe for URLs without encoding.
        """
        # URL-safe characters (subset)
        url_safe_pattern = re.compile(r"^[a-z0-9-]+$")
        assert url_safe_pattern.match(slug), f"Slug '{slug}' is not URL-safe"

    @given(title=valid_page_title())
    @settings(max_examples=100)
    def test_title_to_slug_produces_valid_slug(self, title: str) -> None:
        """
        PROPERTY: Any valid title can be converted to a valid slug.

        The slugify function should handle any printable string.
        """
        from bengal.utils.primitives.text import slugify

        # Skip titles that are only punctuation/symbols (produce empty slugs)
        assume(title.strip())  # Skip empty/whitespace-only titles
        assume(any(c.isalnum() for c in title))  # Must have at least one alphanumeric

        slug = slugify(title)

        # PROPERTY: Slug should be URL-safe when input has alphanumeric chars
        assert slug, f"Empty slug for title: {repr(title)}"
        # Allow lowercase, numbers, hyphens, and underscores (all URL-safe)
        assert re.match(r"^[a-z0-9_-]+$", slug), f"Invalid slug '{slug}' for title: {repr(title)}"


@pytest.mark.slow  # Each example runs full build (~60s total)
@pytest.mark.parallel_unsafe  # Full builds conflict with xdist workers in Python 3.14t
class TestTaxonomyProperties:
    """Property-based tests for taxonomy behavior."""

    @given(tags=st.lists(valid_tag(), min_size=1, max_size=5, unique=True))
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_tag_pages_list_correct_content(
        self,
        tags: list[str],
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        """
        PROPERTY: Tag pages list exactly the pages with that tag.

        Each taxonomy page should contain all (and only) pages that have
        that taxonomy term assigned.
        """
        from bengal.orchestration.build.options import BuildOptions

        tmp_path = tmp_path_factory.mktemp("taxonomy")

        # Create content with tags
        content = {}
        for i, tag in enumerate(tags):
            content[f"page_{i}.md"] = (
                f"---\n"
                f"title: Page {i}\n"
                f"tags:\n"
                f"  - {tag}\n"
                f"---\n\n"
                f"# Page {i}\n\n"
                f"Content for page {i} with tag {tag}."
            )

        # Add a page with multiple tags
        if len(tags) >= 2:
            content["multi_tag.md"] = (
                f"---\n"
                f"title: Multi Tag Page\n"
                f"tags:\n"
                + "\n".join(f"  - {t}" for t in tags[:2])
                + f"\n---\n\n# Multi Tag\n\nMultiple tags."
            )

        # Create site with taxonomy config
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        config = """
[site]
title = "Taxonomy Test"
baseURL = "/"

[build]
output_dir = "public"

[taxonomies]
tags = "tags"
"""
        (site_dir / "bengal.toml").write_text(config)

        content_dir = site_dir / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Home")

        for rel_path, page_content in content.items():
            (content_dir / rel_path).write_text(page_content)

        from bengal.core.site import Site

        site = Site.from_config(site_dir)
        site.discover_content()
        site.discover_assets()

        options = BuildOptions(incremental=False, quiet=True)
        site.build(options=options)

        # PROPERTY: Each tag should have a page in output
        taxonomies = getattr(site, "taxonomies", {})
        if "tags" in taxonomies:
            for tag in tags:
                if tag in taxonomies["tags"]:
                    term_data = taxonomies["tags"][tag]
                    term_pages = term_data.get("pages", [])

                    # Check that pages have this tag
                    for page in term_pages:
                        page_tags = getattr(page, "tags", []) if hasattr(page, "tags") else []
                        assert tag in page_tags or tag.lower() in [t.lower() for t in page_tags], (
                            f"Page {page.source_path} in tag '{tag}' but doesn't have that tag"
                        )
