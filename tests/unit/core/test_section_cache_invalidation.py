"""
Guardrail test: every @cached_property on Section that depends on pages
must be invalidated by _invalidate_page_caches().

If you add a new @cached_property to SectionQueryMixin or
SectionErgonomicsMixin and this test fails, add the property name to the
_invalidate_page_caches() tuple in bengal/core/section/queries.py.
"""

import inspect
from functools import cached_property

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.section.queries import SectionQueryMixin


def _get_invalidation_keys() -> set[str]:
    """Extract the cache keys from _invalidate_page_caches source."""
    source = inspect.getsource(SectionQueryMixin._invalidate_page_caches)
    keys = set()
    for line in source.splitlines():
        stripped = line.strip().strip(",").strip('"').strip("'")
        if (
            stripped
            and not stripped.startswith(("#", "def ", "for ", "self", ")", '"', "Must"))
            and (stripped.isidentifier() or stripped.startswith("_"))
        ):
            keys.add(stripped)
    return keys


def _get_cached_properties(cls: type) -> set[str]:
    """Find all @cached_property names defined on a class and its MRO (excluding object)."""
    props = set()
    for klass in cls.__mro__:
        if klass is object:
            continue
        for name, value in vars(klass).items():
            if isinstance(value, cached_property):
                props.add(name)
    return props


class TestCacheInvalidationCompleteness:
    """Ensure _invalidate_page_caches covers all page-dependent caches."""

    KNOWN_INDEPENDENT = frozenset(
        {
            "ancestors",
            "subsection_index_urls",
            "hierarchy",
            "depth",
            "has_nav_children",
            "sorted_subsections",
            "_path",
            "root",
            "href",
            "icon",
        }
    )

    def test_all_cached_properties_are_invalidated(self):
        """Every @cached_property on Section must be in invalidation list or KNOWN_INDEPENDENT."""
        all_cached = _get_cached_properties(Section)
        invalidation_keys = _get_invalidation_keys()

        uncovered = all_cached - invalidation_keys - self.KNOWN_INDEPENDENT
        assert not uncovered, (
            f"@cached_property names not covered by _invalidate_page_caches(): {uncovered}. "
            "Add them to the invalidation tuple in bengal/core/section/queries.py "
            "or to KNOWN_INDEPENDENT in this test if they don't depend on pages."
        )

    def test_add_page_invalidates_sorted_pages(self, tmp_path):
        """Adding a page after accessing sorted_pages must return fresh data."""
        section = Section(name="blog", path=tmp_path / "blog")

        page_a = Page(
            source_path=tmp_path / "blog/a.md",
            _raw_content="A",
            _raw_metadata={"title": "A", "weight": 1},
        )
        section.add_page(page_a)

        first = section.sorted_pages
        assert len(first) == 1

        page_b = Page(
            source_path=tmp_path / "blog/b.md",
            _raw_content="B",
            _raw_metadata={"title": "B", "weight": 2},
        )
        section.add_page(page_b)

        second = section.sorted_pages
        assert len(second) == 2, "sorted_pages was stale after add_page()"

    def test_add_page_invalidates_content_pages(self, tmp_path):
        """Adding a page after accessing content_pages must return fresh data."""
        section = Section(name="blog", path=tmp_path / "blog")

        page_a = Page(
            source_path=tmp_path / "blog/a.md",
            _raw_content="A",
            _raw_metadata={"title": "A"},
        )
        section.add_page(page_a)

        first = section.content_pages
        assert len(first) == 1

        page_b = Page(
            source_path=tmp_path / "blog/b.md",
            _raw_content="B",
            _raw_metadata={"title": "B"},
        )
        section.add_page(page_b)

        second = section.content_pages
        assert len(second) == 2, "content_pages was stale after add_page()"

    def test_add_page_invalidates_tag_index(self, tmp_path):
        """Adding a tagged page after accessing _tag_index must include it."""
        section = Section(name="blog", path=tmp_path / "blog")

        page_a = Page(
            source_path=tmp_path / "blog/a.md",
            _raw_content="A",
            _raw_metadata={"title": "A", "tags": ["python"]},
        )
        section.add_page(page_a)

        first = section.pages_with_tag("python")
        assert len(first) == 1

        page_b = Page(
            source_path=tmp_path / "blog/b.md",
            _raw_content="B",
            _raw_metadata={"title": "B", "tags": ["python"]},
        )
        section.add_page(page_b)

        second = section.pages_with_tag("python")
        assert len(second) == 2, "_tag_index was stale after add_page()"
