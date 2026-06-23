"""Integration test for the theme showcase example (#545)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

bs4 = pytest.importorskip("bs4", reason="beautifulsoup4 required")
BeautifulSoup = bs4.BeautifulSoup

SHOWCASE = Path("examples/showcase")


@pytest.fixture(scope="module")
def built_showcase(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("showcase")
    site_dir = tmp / "site"
    shutil.copytree(SHOWCASE / "content", site_dir / "content")
    shutil.copytree(SHOWCASE / "assets", site_dir / "assets")
    shutil.copy(SHOWCASE / "bengal.toml", site_dir / "bengal.toml")

    site = Site.from_config(site_dir)
    site.build(BuildOptions(strict=False))
    return site.output_dir


@pytest.mark.slow
class TestShowcaseExample:
    def test_showcase_page_builds(self, built_showcase: Path) -> None:
        showcase_html = built_showcase / "showcase" / "index.html"
        assert showcase_html.exists()
        content = showcase_html.read_text()
        assert "Theme Showcase Gallery" in content
        assert "Quality Gate" in content

    def test_showcase_has_cls_safe_image(self, built_showcase: Path) -> None:
        content = (built_showcase / "showcase" / "index.html").read_text()
        assert 'width="128"' in content
        assert 'height="128"' in content

    def test_showcase_has_pwa_and_llm_affordances(self, built_showcase: Path) -> None:
        content = (built_showcase / "showcase" / "index.html").read_text()
        soup = BeautifulSoup(content, "html.parser")
        assert soup.find("link", rel="manifest") is not None
        assert soup.find("meta", property="og:title") is not None
        assert "copy-theme-tokens" in content
        assert (built_showcase / "llms.txt").exists()
        assert (built_showcase / "sitemap.xml").exists()
