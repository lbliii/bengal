from types import SimpleNamespace

from bengal.core.page_site import get_page_site, set_page_site


def test_get_page_site_returns_none_when_site_context_is_absent() -> None:
    page = SimpleNamespace()

    assert get_page_site(page) is None


def test_set_page_site_attaches_legacy_site_context() -> None:
    page = SimpleNamespace()
    site = object()

    set_page_site(page, site)

    assert get_page_site(page) is site
