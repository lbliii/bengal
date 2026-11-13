from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def test_direction_generic_adapter(tmp_path: Path) -> None:
    """direction() is available via the generic adapter (non-Kida engines)."""
    from bengal.core.site import Site
    from bengal.rendering.template_engine import TemplateEngine

    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}, {"code": "ar"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class ArPage:
        lang = "ar"

    engine = TemplateEngine(site)
    # Generic adapter registers direction() at site-default level
    # (no page context), so it uses the default language "en" → ltr
    html = engine.render_string(
        'dir="{{ direction() }}"',
        {"page": ArPage(), "site": site},
    )
    assert 'dir="ltr"' in html


def test_direction_kida_adapter_uses_page_lang(tmp_path: Path) -> None:
    """Kida adapter's direction() uses page.lang when available."""
    from bengal.core.site import Site
    from bengal.rendering.template_engine import TemplateEngine

    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}, {"code": "ar"}],
            "rendering": {"adapter": "kida"},
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class ArPage:
        lang = "ar"

    engine = TemplateEngine(site)
    html = engine.render_string(
        'dir="{{ direction() }}"',
        {"page": ArPage(), "site": site},
    )
    assert 'dir="rtl"' in html
