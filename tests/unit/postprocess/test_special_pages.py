"""
Unit tests for SpecialPagesGenerator (404 + search page).
"""

from pathlib import Path

from bengal.core.url_ownership import URLRegistry
from bengal.postprocess.special_pages import SpecialPagesGenerator


class DummyTemplate:
    def render(self, **kwargs):
        return "<html>ok</html>"


class DummyEnv:
    def __init__(self, available):
        self.available = set(available)

    def get_template(self, name):
        if name in self.available:
            return DummyTemplate()
        raise Exception("missing")


class DummyTemplateEngine:
    def __init__(self, available):
        self.env = DummyEnv(available)

    def render(self, template_name, context):
        return "<html>ok</html>"


class DummySite:
    def __init__(self, tmp_path: Path, config=None, available_templates=None):
        self.root_path = tmp_path
        self.output_dir = tmp_path / "public"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir = tmp_path / "content"
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}
        self.theme = "default"
        self.template_engine = DummyTemplateEngine(available_templates or [])
        self.pages = []

    @property
    def baseurl(self) -> str:
        """Return baseurl from config."""
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and site_section.get("baseurl"):
            return site_section.get("baseurl", "")
        return self.config.get("baseurl", "")
        self.url_registry = URLRegistry()


def test_search_generated_by_default(tmp_path):
    site = DummySite(
        tmp_path,
        config={"search": {"enabled": True}},
        available_templates=["search.html", "404.html"],
    )
    gen = SpecialPagesGenerator(site)
    gen.generate()
    # search/index.html should exist
    assert (site.output_dir / "search" / "index.html").exists()


def test_search_skips_when_disabled(tmp_path):
    site = DummySite(
        tmp_path, config={"search": {"enabled": False}}, available_templates=["search.html"]
    )
    gen = SpecialPagesGenerator(site)
    gen.generate()
    assert not (site.output_dir / "search" / "index.html").exists()


def test_search_skips_when_user_page_exists(tmp_path):
    site = DummySite(
        tmp_path, config={"search": {"enabled": True}}, available_templates=["search.html"]
    )
    # create user override content
    (site.content_dir / "search.md").write_text("---\ntitle: Search\n---\n")
    # Claim URL in registry to simulate content discovery (priority 100 = user content)
    site.url_registry.claim(
        url="/search/",
        owner="content",
        source="content/search.md",
        priority=100,  # User content always wins
    )
    gen = SpecialPagesGenerator(site)
    gen.generate()
    assert not (site.output_dir / "search" / "index.html").exists()


def test_search_custom_path_and_template(tmp_path):
    site = DummySite(
        tmp_path,
        config={"search": {"enabled": True, "path": "/finder/", "template": "search.html"}},
        available_templates=["search.html"],
    )
    gen = SpecialPagesGenerator(site)
    gen.generate()
    assert (site.output_dir / "finder" / "index.html").exists()


def test_search_boolean_true_config(tmp_path):
    # search = true (boolean form)
    site = DummySite(tmp_path, config={"search": True}, available_templates=["search.html"])
    gen = SpecialPagesGenerator(site)
    gen.generate()
    assert (site.output_dir / "search" / "index.html").exists()


def test_search_boolean_false_config(tmp_path):
    # search = false (boolean form)
    site = DummySite(tmp_path, config={"search": False}, available_templates=["search.html"])
    gen = SpecialPagesGenerator(site)
    gen.generate()
    assert not (site.output_dir / "search" / "index.html").exists()
