"""
Tests for the SiteContext Protocol structural conformance.

Sprint B2 introduced `bengal.core.site.context.SiteContext` — a runtime-checkable
Protocol that defines the read-only Site surface consumed by Page and Section.
The Site dataclass implements this Protocol structurally (no explicit base
class), so these tests act as a tripwire: if anyone removes or renames an
attribute that Page/Section depend on, the isinstance check fails.

The Protocol is the contract; the dataclass is the implementation. Drift
between them is what these tests catch.
"""

from __future__ import annotations

import pytest

from bengal.core.registry import ContentRegistry
from bengal.core.site import Site
from bengal.core.site.context import RegistryContext, SiteContext


@pytest.fixture
def site(tmp_path):
    (tmp_path / "content").mkdir()
    return Site(root_path=tmp_path)


def test_site_satisfies_site_context_protocol(site):
    """Site implements SiteContext structurally."""
    assert isinstance(site, SiteContext)


def test_content_registry_satisfies_registry_context_protocol():
    """ContentRegistry exposes the registry surface Page consumes (epoch + page_index)."""
    registry = ContentRegistry()
    assert isinstance(registry, RegistryContext)


def test_site_registry_attribute_satisfies_protocol(site):
    """site.registry — the attribute Page reads — satisfies RegistryContext."""
    assert isinstance(site.registry, RegistryContext)


def test_registry_page_index_is_memoized():
    """RegistryContext.page_index returns the same dict until pages length changes."""
    registry = ContentRegistry()

    class FakePage:
        def __init__(self, name: str) -> None:
            self.name = name

    pages = [FakePage("a"), FakePage("b"), FakePage("c")]
    first = registry.page_index(pages)
    second = registry.page_index(pages)
    assert first is second, "page_index must memoize while pages length is stable"
    assert first == {pages[0]: 0, pages[1]: 1, pages[2]: 2}


def test_registry_page_index_invalidates_on_length_change():
    """Appending a page rebuilds the index (taxonomy/archive generation case)."""
    registry = ContentRegistry()

    class FakePage:
        def __init__(self, name: str) -> None:
            self.name = name

    pages = [FakePage("a"), FakePage("b")]
    first = registry.page_index(pages)
    pages.append(FakePage("c"))
    second = registry.page_index(pages)
    assert first is not second
    assert second[pages[2]] == 2


def test_registry_page_index_resets_on_clear():
    """ContentRegistry.clear() invalidates the page_index memo."""
    registry = ContentRegistry()

    class FakePage:
        def __init__(self, name: str) -> None:
            self.name = name

    pages = [FakePage("a")]
    first = registry.page_index(pages)
    registry.clear()
    second = registry.page_index(pages)
    assert first is not second
