"""Unit tests for bengal.utils.xref link resolution.

Lightweight tests - no kida, rendering pipeline, or template engine deps.
"""

from tests._testing.mocks import MockPage


class TestResolvePage:
    """Tests for resolve_page (page object lookup)."""

    def test_relative_dot_slash_with_current_page_dir(self):
        """./child resolves to current_page_dir/child."""
        from bengal.utils.xref import resolve_page

        child = MockPage(title="Child", href="/docs/guides/child/")
        xref = {"by_path": {"docs/guides/child": child}, "by_slug": {}, "by_id": {}}
        assert resolve_page(xref, "./child", "docs/guides") is child

    def test_relative_dot_slash_without_current_page_dir(self):
        """./child returns None when current_page_dir is None."""
        from bengal.utils.xref import resolve_page

        xref = {"by_path": {"docs/guides/child": MockPage()}, "by_slug": {}, "by_id": {}}
        assert resolve_page(xref, "./child", None) is None

    def test_relative_dot_dot_slash(self):
        """../sibling resolves to parent/sibling."""
        from bengal.utils.xref import resolve_page

        sibling = MockPage(title="Sibling", href="/docs/sibling/")
        xref = {"by_path": {"docs/sibling": sibling}, "by_slug": {}, "by_id": {}}
        assert resolve_page(xref, "../sibling", "docs/guides") is sibling

    def test_id_prefix(self):
        """id:page-id resolves via by_id."""
        from bengal.utils.xref import resolve_page

        page = MockPage(title="Page", href="/page/")
        xref = {"by_path": {}, "by_slug": {}, "by_id": {"my-page": page}}
        assert resolve_page(xref, "id:my-page") is page

    def test_path_prefix(self):
        """path:docs/page resolves via by_path."""
        from bengal.utils.xref import resolve_page

        page = MockPage(title="Page", href="/docs/page/")
        xref = {"by_path": {"docs/page": page}, "by_slug": {}, "by_id": {}}
        assert resolve_page(xref, "path:docs/page") is page

    def test_slug_prefix(self):
        """slug:page-slug resolves via by_slug."""
        from bengal.utils.xref import resolve_page

        page = MockPage(title="Page", href="/page/", slug="page-slug")
        xref = {"by_path": {}, "by_slug": {"page-slug": [page]}, "by_id": {}}
        assert resolve_page(xref, "slug:page-slug") is page

    def test_implicit_path(self):
        """docs/guides/page resolves via by_path (no prefix)."""
        from bengal.utils.xref import resolve_page

        page = MockPage(title="Page", href="/docs/guides/page/")
        xref = {"by_path": {"docs/guides/page": page}, "by_slug": {}, "by_id": {}}
        assert resolve_page(xref, "docs/guides/page") is page

    def test_empty_link_returns_none(self):
        """Empty link returns None."""
        from bengal.utils.xref import resolve_page

        xref = {"by_path": {}, "by_slug": {}, "by_id": {}}
        assert resolve_page(xref, "") is None


class TestResolveLinkToUrlAndPage:
    """Tests for resolve_link_to_url_and_page (url + page tuple)."""

    def test_resolved_returns_url_and_page(self):
        """Resolved link returns (url, page)."""
        from bengal.utils.xref import resolve_link_to_url_and_page

        page = MockPage(title="Page", href="/docs/page/")
        xref = {"by_path": {"docs/page": page}, "by_slug": {}, "by_id": {}}
        url, p = resolve_link_to_url_and_page(
            xref, "docs/page", current_page_dir="docs"
        )
        assert url == "/docs/page/"
        assert p is page

    def test_external_url_passthrough(self):
        """http:// and https:// pass through as-is."""
        from bengal.utils.xref import resolve_link_to_url_and_page

        xref = {"by_path": {}, "by_slug": {}, "by_id": {}}
        url, p = resolve_link_to_url_and_page(xref, "https://example.com")
        assert url == "https://example.com"
        assert p is None

    def test_absolute_path_passthrough(self):
        """Paths starting with / pass through."""
        from bengal.utils.xref import resolve_link_to_url_and_page

        xref = {"by_path": {}, "by_slug": {}, "by_id": {}}
        url, p = resolve_link_to_url_and_page(xref, "/docs/page/")
        assert url == "/docs/page/"
        assert p is None

    def test_unresolved_returns_original_link(self):
        """Unresolved link returns (link, None)."""
        from bengal.utils.xref import resolve_link_to_url_and_page

        xref = {"by_path": {}, "by_slug": {}, "by_id": {}}
        url, p = resolve_link_to_url_and_page(
            xref, "./missing/", current_page_dir="docs"
        )
        assert url == "./missing/"
        assert p is None
