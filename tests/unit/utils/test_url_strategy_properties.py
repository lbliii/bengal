"""
Property-based tests for URL strategy using Hypothesis.

These tests verify that URL generation maintains critical invariants
across ALL possible inputs.
"""

import string
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bengal.core.section import Section
from bengal.utils.url_strategy import URLStrategy


class TestUrlFromOutputPathProperties:
    """
    Property tests for url_from_output_path method.

    This is the most critical method - converts file paths to URLs.
    """

    @pytest.mark.hypothesis
    @given(
        parts=st.lists(
            st.text(
                alphabet=string.ascii_lowercase + string.digits + "-_", min_size=1, max_size=20
            ),
            min_size=0,
            max_size=5,
        )
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_urls_always_start_with_slash(self, parts):
        """
        Property: URLs always start with / (absolute path).

        This is critical for correct linking in HTML.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"
            mock_site.config = {}

            # Create a path under output_dir
            if parts:
                output_path = mock_site.output_dir / "/".join(parts) / "index.html"
            else:
                output_path = mock_site.output_dir / "index.html"

            url = URLStrategy.url_from_output_path(output_path, mock_site)

            assert url.startswith("/"), f"URL '{url}' should start with '/'"

    @pytest.mark.hypothesis
    @given(
        parts=st.lists(
            st.text(
                alphabet=string.ascii_lowercase + string.digits + "-_", min_size=1, max_size=20
            ),
            min_size=1,
            max_size=5,
        )
    )
    def test_no_consecutive_slashes(self, parts):
        """
        Property: URLs never have consecutive slashes (//).

        Double slashes can break routing and look unprofessional.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"
            mock_site.config = {}

            output_path = mock_site.output_dir / "/".join(parts) / "index.html"
            url = URLStrategy.url_from_output_path(output_path, mock_site)

            assert "//" not in url, f"URL '{url}' contains consecutive slashes"

    @pytest.mark.hypothesis
    @given(
        parts=st.lists(
            st.text(
                alphabet=string.ascii_lowercase + string.digits + "-_", min_size=1, max_size=20
            ),
            min_size=0,
            max_size=5,
        )
    )
    def test_urls_end_with_slash(self, parts):
        """
        Property: Pretty URLs end with / (directory style).

        /about/ is cleaner than /about for pretty URLs.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"
            mock_site.config = {}

            if parts:
                output_path = mock_site.output_dir / "/".join(parts) / "index.html"
            else:
                output_path = mock_site.output_dir / "index.html"

            url = URLStrategy.url_from_output_path(output_path, mock_site)

            assert url.endswith("/"), f"Pretty URL '{url}' should end with '/'"

    @pytest.mark.hypothesis
    @given(
        parts=st.lists(
            st.text(
                alphabet=string.ascii_lowercase + string.digits + "-_", min_size=1, max_size=20
            ),
            min_size=0,
            max_size=5,
        )
    )
    def test_no_html_in_urls(self, parts):
        """
        Property: Pretty URLs don't contain .html extension.

        /about/ not /about.html or /about/index.html
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"
            mock_site.config = {}

            if parts:
                output_path = mock_site.output_dir / "/".join(parts) / "index.html"
            else:
                output_path = mock_site.output_dir / "index.html"

            url = URLStrategy.url_from_output_path(output_path, mock_site)

            assert ".html" not in url, f"Pretty URL '{url}' should not contain .html"
            # Don't check for 'index' string - it's valid in directory names
            # Just ensure we're not exposing index.html in the URL
            assert "index.html" not in url, f"Pretty URL '{url}' should not contain index.html"

    @pytest.mark.hypothesis
    @given(depth=st.integers(min_value=0, max_value=10))
    def test_url_depth_matches_path_depth(self, depth):
        """
        Property: URL depth corresponds to path depth.

        More nested paths → deeper URLs.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"
            mock_site.config = {}

            # Create nested path
            parts = [f"dir{i}" for i in range(depth)]
            if parts:
                output_path = mock_site.output_dir / "/".join(parts) / "index.html"
            else:
                output_path = mock_site.output_dir / "index.html"

            url = URLStrategy.url_from_output_path(output_path, mock_site)

            # Count slashes (excluding leading/trailing)
            url_parts = [p for p in url.split("/") if p]

            assert len(url_parts) == depth, (
                f"URL '{url}' depth ({len(url_parts)}) doesn't match path depth ({depth})"
            )

    @pytest.mark.hypothesis
    @given(
        name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "-_", min_size=1, max_size=30
        )
    )
    def test_roundtrip_consistency(self, name):
        """
        Property: Same path always produces same URL.

        Deterministic behavior is critical for caching and consistency.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"
            mock_site.config = {}

            output_path = mock_site.output_dir / name / "index.html"

            # Generate URL twice
            url1 = URLStrategy.url_from_output_path(output_path, mock_site)
            url2 = URLStrategy.url_from_output_path(output_path, mock_site)

            assert url1 == url2, f"URL generation not deterministic: '{url1}' != '{url2}'"


class TestMakeVirtualPathProperties:
    """Property tests for make_virtual_path method."""

    @pytest.mark.hypothesis
    @given(
        segments=st.lists(
            st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=15),
            min_size=1,
            max_size=5,
        )
    )
    def test_virtual_paths_always_end_with_index_md(self, segments):
        """
        Property: Virtual paths always end with index.md.

        Generated paths should be valid markdown file paths.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.root_path = Path(tmpdir)
            mock_site.paths.generated_dir = Path(tmpdir) / ".bengal" / "generated"

            virtual_path = URLStrategy.make_virtual_path(mock_site, *segments)

            assert virtual_path.name == "index.md", (
                f"Virtual path should end with index.md: {virtual_path}"
            )

    @pytest.mark.hypothesis
    @given(
        segments=st.lists(
            st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=15),
            min_size=1,
            max_size=5,
        )
    )
    def test_virtual_paths_under_bengal_dir(self, segments):
        """
        Property: Virtual paths are under .bengal/generated/.

        Keeps generated files separate from user content.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.root_path = Path(tmpdir)
            mock_site.paths.generated_dir = Path(tmpdir) / ".bengal" / "generated"

            virtual_path = URLStrategy.make_virtual_path(mock_site, *segments)

            assert ".bengal" in virtual_path.parts, (
                f"Virtual path should be under .bengal: {virtual_path}"
            )
            assert "generated" in virtual_path.parts, (
                f"Virtual path should be under generated: {virtual_path}"
            )

    @pytest.mark.hypothesis
    @given(
        segments=st.lists(
            st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=15),
            min_size=1,
            max_size=5,
        )
    )
    def test_virtual_paths_are_absolute(self, segments):
        """
        Property: Virtual paths are absolute.

        Absolute paths avoid ambiguity.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.root_path = Path(tmpdir)
            mock_site.paths.generated_dir = Path(tmpdir) / ".bengal" / "generated"

            virtual_path = URLStrategy.make_virtual_path(mock_site, *segments)

            assert virtual_path.is_absolute(), f"Virtual path should be absolute: {virtual_path}"

    @pytest.mark.hypothesis
    @given(
        segments=st.lists(
            st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=15),
            min_size=1,
            max_size=5,
        )
    )
    def test_virtual_path_preserves_segment_order(self, segments):
        """
        Property: Segments appear in order in the path.

        make_virtual_path("a", "b", "c") should have a before b before c.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.root_path = Path(tmpdir)
            mock_site.paths.generated_dir = Path(tmpdir) / ".bengal" / "generated"

            virtual_path = URLStrategy.make_virtual_path(mock_site, *segments)

            # Check segments appear in order
            path_str = str(virtual_path)
            last_index = -1
            for segment in segments:
                index = path_str.find(segment, last_index + 1)
                assert index > last_index, (
                    f"Segment '{segment}' not found in order in {virtual_path}"
                )
                last_index = index


class TestArchiveOutputPathProperties:
    """Property tests for compute_archive_output_path method."""

    @pytest.mark.hypothesis
    @given(
        section_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=20),
        page_num=st.integers(min_value=1, max_value=100),
    )
    def test_page_1_at_section_root(self, section_name, page_num):
        """
        Property: Page 1 is at section root (/blog/), page 2+ has /page/N/.

        Standard pagination pattern.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"

            section = Section(name=section_name, path=Path(tmpdir) / "content" / section_name)

            output_path = URLStrategy.compute_archive_output_path(section, page_num, mock_site)

            if page_num == 1:
                # Page 1 at root: /blog/index.html
                assert "page" not in str(output_path), (
                    f"Page 1 should not have /page/ in path: {output_path}"
                )
            else:
                # Page 2+ has /page/N/: /blog/page/2/index.html
                assert "page" in str(output_path), (
                    f"Page {page_num} should have /page/ in path: {output_path}"
                )
                assert str(page_num) in str(output_path), (
                    f"Page {page_num} should have {page_num} in path: {output_path}"
                )

    @pytest.mark.hypothesis
    @given(section_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=20))
    def test_archive_paths_end_with_index_html(self, section_name):
        """
        Property: Archive paths end with index.html.

        Standard directory-style output.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"

            section = Section(name=section_name, path=Path(tmpdir) / "content" / section_name)

            output_path = URLStrategy.compute_archive_output_path(section, 1, mock_site)

            assert output_path.name == "index.html", (
                f"Archive path should end with index.html: {output_path}"
            )


class TestTagOutputPathProperties:
    """Property tests for tag-related path methods."""

    @pytest.mark.hypothesis
    @given(
        tag_slug=st.text(alphabet=string.ascii_lowercase + "-", min_size=1, max_size=30),
        page_num=st.integers(min_value=1, max_value=50),
    )
    def test_tag_paths_under_tags_directory(self, tag_slug, page_num):
        """
        Property: Tag pages are under /tags/ directory.

        Standard taxonomy URL pattern.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"

            output_path = URLStrategy.compute_tag_output_path(tag_slug, page_num, mock_site)

            assert "tags" in output_path.parts, f"Tag path should be under /tags/: {output_path}"

    @pytest.mark.hypothesis
    @given(tag_slug=st.text(alphabet=string.ascii_lowercase + "-", min_size=1, max_size=30))
    def test_tag_index_at_tags_root(self, tag_slug):
        """
        Property: Tag index is at /tags/index.html.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_site = Mock()
            mock_site.output_dir = Path(tmpdir) / "public"

            output_path = URLStrategy.compute_tag_index_output_path(mock_site)

            assert output_path == mock_site.output_dir / "tags" / "index.html", (
                f"Tag index should be at /tags/index.html: {output_path}"
            )


# Example output documentation
"""
EXAMPLE HYPOTHESIS OUTPUT
-------------------------

Running these tests generates thousands of URL examples like:

1. Simple paths:
   - /about/
   - /blog/
   - /docs/guide/

2. Nested paths:
   - /api/v2/users/
   - /blog/2024/10/post/

3. Pagination:
   - /blog/ (page 1)
   - /blog/page/2/
   - /blog/page/10/

4. Tags:
   - /tags/
   - /tags/python/
   - /tags/static-site-generators/page/2/

5. Edge cases:
   - Root: /
   - Deep nesting: /a/b/c/d/e/f/
   - Special chars in segments

Each test runs 100+ times with different combinations,
automatically discovering edge cases like:
- Consecutive slashes
- Missing leading/trailing slashes
- Incorrect depth
- Path/URL mismatches

To see statistics:
    pytest tests/unit/utils/test_url_strategy_properties.py --hypothesis-show-statistics
"""
