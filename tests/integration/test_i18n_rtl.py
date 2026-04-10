"""Integration tests for RTL (right-to-left) layout support.

Verifies that Arabic/Hebrew pages render with correct reading direction,
and that the default theme uses CSS logical properties for RTL compatibility.
"""

from __future__ import annotations

import pytest

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine


@pytest.mark.bengal(testroot="test-i18n-rtl")
class TestI18nRTL:
    """Test RTL layout support for i18n."""

    def test_arabic_pages_discovered(self, shared_site) -> None:
        """Arabic content should be discovered with lang=ar."""
        ar_pages = [p for p in shared_site.pages if getattr(p, "lang", None) == "ar"]
        assert len(ar_pages) >= 1, "At least one Arabic page should exist"

    def test_english_pages_discovered(self, shared_site) -> None:
        """English content should be discovered with lang=en."""
        en_pages = [p for p in shared_site.pages if getattr(p, "lang", None) == "en"]
        assert len(en_pages) >= 1, "At least one English page should exist"

    def test_direction_rtl_for_arabic_page(self, shared_site) -> None:
        """direction() should return 'rtl' for Arabic pages."""
        from bengal.rendering.template_functions.i18n import _direction

        ar_page = next((p for p in shared_site.pages if getattr(p, "lang", None) == "ar"), None)
        assert ar_page is not None
        assert _direction(shared_site, ar_page) == "rtl"

    def test_direction_ltr_for_english_page(self, shared_site) -> None:
        """direction() should return 'ltr' for English pages."""
        from bengal.rendering.template_functions.i18n import _direction

        en_page = next((p for p in shared_site.pages if getattr(p, "lang", None) == "en"), None)
        assert en_page is not None
        assert _direction(shared_site, en_page) == "ltr"


class TestRTLTemplateRendering:
    """Test that RTL attributes render correctly in templates."""

    def test_html_dir_rtl_for_arabic(self, tmp_path) -> None:
        """Arabic page renders <html dir="rtl">."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [
                    {"code": "en", "name": "English"},
                    {"code": "ar", "name": "العربية"},
                ],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        engine = TemplateEngine(site)

        class ArabicPage:
            lang = "ar"
            title = "حول"

        html = engine.render_string(
            '<html lang="{{ current_lang() }}" dir="{{ direction() }}">',
            {"page": ArabicPage(), "site": site},
        )
        assert 'lang="ar"' in html
        assert 'dir="rtl"' in html

    def test_html_dir_ltr_for_english(self, tmp_path) -> None:
        """English page renders <html dir="ltr">."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [{"code": "en"}, {"code": "ar"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        engine = TemplateEngine(site)

        class EnglishPage:
            lang = "en"

        html = engine.render_string(
            '<html lang="{{ current_lang() }}" dir="{{ direction() }}">',
            {"page": EnglishPage(), "site": site},
        )
        assert 'lang="en"' in html
        assert 'dir="ltr"' in html

    def test_direction_config_override_rtl(self, tmp_path) -> None:
        """Config rtl=true forces RTL even for non-RTL language codes."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [
                    {"code": "en"},
                    {"code": "custom-lang", "rtl": True},
                ],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        engine = TemplateEngine(site)

        class CustomPage:
            lang = "custom-lang"

        html = engine.render_string(
            "{{ direction() }}",
            {"page": CustomPage(), "site": site},
        )
        assert "rtl" in html

    def test_nt_in_rtl_context(self, tmp_path) -> None:
        """nt() works correctly in RTL page context."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [{"code": "en"}, {"code": "ar"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        engine = TemplateEngine(site)

        class ArabicPage:
            lang = "ar"

        html = engine.render_string(
            "{{ nt('1 item', '{n} items', 3) }}",
            {"page": ArabicPage(), "site": site},
        )
        assert "3 items" in html


class TestCSSLogicalProperties:
    """Verify the default theme uses CSS logical properties (no physical directional)."""

    def test_no_physical_margin_left_right_in_main_css(self) -> None:
        """Main component CSS should not use margin-left/right (use margin-inline-start/end)."""
        import re
        from pathlib import Path

        css_dir = Path("bengal/themes/default/assets/css")
        violations = []

        for css_file in css_dir.rglob("*.css"):
            # Skip vendor and experimental files
            if any(
                skip in str(css_file)
                for skip in (
                    "tabulator.min",
                    "border-styles-demo",
                    "holo-tcg",
                    "border-gradient",
                    "palettes/",
                )
            ):
                continue

            content = css_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # Skip comments
                if stripped.startswith(("/*", "*")):
                    continue
                # Skip lines that are comments about the change
                if "Changed from" in line:
                    continue
                # Check for physical properties (not inside logical property names)
                if re.search(r"(?<!inline-)(?<!block-)margin-left\s*:", stripped):
                    violations.append(f"{css_file.name}:{i}: {stripped}")
                if re.search(r"(?<!inline-)(?<!block-)margin-right\s*:", stripped):
                    violations.append(f"{css_file.name}:{i}: {stripped}")

        assert not violations, (
            f"Found {len(violations)} physical margin-left/right properties:\n"
            + "\n".join(violations[:10])
        )

    def test_no_physical_padding_left_right_in_main_css(self) -> None:
        """Main component CSS should not use padding-left/right (use padding-inline-start/end)."""
        import re
        from pathlib import Path

        css_dir = Path("bengal/themes/default/assets/css")
        violations = []

        for css_file in css_dir.rglob("*.css"):
            if any(
                skip in str(css_file)
                for skip in (
                    "tabulator.min",
                    "border-styles-demo",
                    "holo-tcg",
                    "border-gradient",
                    "palettes/",
                )
            ):
                continue

            content = css_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith(("/*", "*")):
                    continue
                if "Changed from" in line:
                    continue
                if re.search(r"(?<!inline-)(?<!block-)padding-left\s*:", stripped):
                    violations.append(f"{css_file.name}:{i}: {stripped}")
                if re.search(r"(?<!inline-)(?<!block-)padding-right\s*:", stripped):
                    violations.append(f"{css_file.name}:{i}: {stripped}")

        assert not violations, (
            f"Found {len(violations)} physical padding-left/right properties:\n"
            + "\n".join(violations[:10])
        )
