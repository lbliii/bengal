"""Unit tests for bengal/postprocess/robots_txt.py.

Covers:
- RobotsTxtGenerator initialization
- SignalPolicy dataclass
- robots.txt rendering with Content-Signal directives
- Section override aggregation
- .well-known/content-signals.json manifest generation
- Config-driven defaults
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from bengal.postprocess.robots_txt import RobotsTxtGenerator, SignalPolicy


class TestSignalPolicy:
    """Test the SignalPolicy dataclass."""

    def test_to_directive_default(self):
        policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        result = policy.to_directive()
        assert "search=yes" in result
        assert "ai-input=yes" in result
        assert "ai-train=no" in result

    def test_to_directive_all_yes(self):
        policy = SignalPolicy(search=True, ai_input=True, ai_train=True)
        result = policy.to_directive()
        assert result == "search=yes, ai-input=yes, ai-train=yes"

    def test_to_directive_all_no(self):
        policy = SignalPolicy(search=False, ai_input=False, ai_train=False)
        result = policy.to_directive()
        assert result == "search=no, ai-input=no, ai-train=no"

    def test_to_directive_with_path(self):
        policy = SignalPolicy(search=True, ai_input=True, ai_train=True)
        result = policy.to_directive("/blog/")
        assert result.startswith("/blog/ ")
        assert "search=yes" in result

    def test_equality(self):
        a = SignalPolicy(search=True, ai_input=True, ai_train=False)
        b = SignalPolicy(search=True, ai_input=True, ai_train=False)
        c = SignalPolicy(search=True, ai_input=True, ai_train=True)
        assert a == b
        assert a != c

    def test_hashable(self):
        a = SignalPolicy(search=True, ai_input=True, ai_train=False)
        b = SignalPolicy(search=True, ai_input=True, ai_train=False)
        assert hash(a) == hash(b)
        assert {a, b} == {a}


class TestRobotsTxtGeneratorInit:
    """Test RobotsTxtGenerator initialization."""

    def test_stores_site(self):
        site = MagicMock()
        gen = RobotsTxtGenerator(site)
        assert gen.site is site


class TestRobotsTxtRendering:
    """Test robots.txt content rendering."""

    def _make_site(self, config=None):
        site = MagicMock()
        _config = {
            "content_signals": {
                "enabled": True,
                "search": True,
                "ai_input": True,
                "ai_train": False,
                "include_sitemap": True,
                "user_agents": {"*": None},
            },
            "output_formats": {
                "per_page": ["json", "llm_txt"],
                "site_wide": ["index_json", "llm_full"],
            },
            "generate_rss": True,
        }
        if config:
            _config["content_signals"].update(config)
        site.config = MagicMock()
        site.config.get = lambda key, default=None: _config.get(key, default)
        site.baseurl = "https://example.com"
        site.pages = []
        site.output_dir = Path("/tmp/test-output")
        site.dev_mode = False
        site.build_time = None
        site.title = "Test Site"
        return site

    def test_contains_content_signal_preamble(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        default_policy = gen._get_default_policy(gen._get_config())
        content = gen._render_robots_txt(default_policy, {}, {"*": None}, gen._get_config())
        assert "Content Signals" in content
        assert "contentsignals.org" in content

    def test_contains_user_agent_star(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        default_policy = gen._get_default_policy(gen._get_config())
        content = gen._render_robots_txt(default_policy, {}, {"*": None}, gen._get_config())
        assert "User-Agent: *" in content

    def test_contains_default_signals(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        default_policy = gen._get_default_policy(gen._get_config())
        content = gen._render_robots_txt(default_policy, {}, {"*": None}, gen._get_config())
        assert "search=yes" in content
        assert "ai-input=yes" in content
        assert "ai-train=no" in content

    def test_contains_sitemap_directive(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        default_policy = gen._get_default_policy(gen._get_config())
        content = gen._render_robots_txt(default_policy, {}, {"*": None}, gen._get_config())
        assert "Sitemap: https://example.com/sitemap.xml" in content

    def test_sitemap_directive_omitted_when_disabled(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        config = gen._get_config()
        config["include_sitemap"] = False
        default_policy = gen._get_default_policy(config)
        content = gen._render_robots_txt(default_policy, {}, {"*": None}, config)
        assert "Sitemap:" not in content

    def test_sitemap_directive_omitted_without_baseurl(self):
        site = self._make_site()
        site.baseurl = ""
        gen = RobotsTxtGenerator(site)
        default_policy = gen._get_default_policy(gen._get_config())
        content = gen._render_robots_txt(default_policy, {}, {"*": None}, gen._get_config())
        assert "Sitemap:" not in content

    def test_section_override_rendered(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        overrides = {
            "/blog/": SignalPolicy(search=True, ai_input=True, ai_train=True),
        }
        content = gen._render_robots_txt(default_policy, overrides, {"*": None}, gen._get_config())
        assert "/blog/" in content
        assert "ai-train=yes" in content

    def test_disallow_when_all_denied(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        overrides = {
            "/internal/": SignalPolicy(search=False, ai_input=False, ai_train=False),
        }
        content = gen._render_robots_txt(default_policy, overrides, {"*": None}, gen._get_config())
        assert "Disallow: /internal/" in content

    def test_per_agent_override(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        agents = {
            "*": None,
            "GPTBot": {"search": True, "ai_input": True, "ai_train": False},
        }
        content = gen._render_robots_txt(default_policy, {}, agents, gen._get_config())
        assert "User-Agent: GPTBot" in content

    def test_section_overrides_emitted_for_each_user_agent(self):
        site = self._make_site()
        gen = RobotsTxtGenerator(site)
        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        agents = {
            "*": None,
            "GPTBot": {"search": True, "ai_input": True, "ai_train": False},
        }
        overrides = {
            "/blog/": SignalPolicy(search=True, ai_input=True, ai_train=True),
        }
        content = gen._render_robots_txt(default_policy, overrides, agents, gen._get_config())
        assert (
            "User-Agent: *\nContent-Signal: /blog/ search=yes, ai-input=yes, ai-train=yes"
            in content
        )
        assert (
            "User-Agent: GPTBot\nContent-Signal: /blog/ search=yes, ai-input=yes, ai-train=yes"
        ) in content


class TestSectionAggregation:
    """Test section-level signal aggregation from pages."""

    def _make_page(self, path, visibility=None, draft=False):
        page = MagicMock()
        page._path = path
        page.output_path = Path(f"/tmp/output{path}index.html")
        page.draft = draft
        page.visibility = {
            "search": True,
            "ai_input": True,
            "ai_train": False,
        }
        if visibility:
            page.visibility.update(visibility)
        return page

    def test_no_override_when_all_match_default(self):
        site = MagicMock()
        site.pages = [
            self._make_page("/docs/intro/"),
            self._make_page("/docs/guide/"),
        ]
        gen = RobotsTxtGenerator(site)
        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        overrides = gen._compute_section_overrides(default_policy)
        assert overrides == {}

    def test_section_override_when_different(self):
        site = MagicMock()
        site.pages = [
            self._make_page("/blog/post-1/", {"ai_train": True}),
            self._make_page("/blog/post-2/", {"ai_train": True}),
        ]
        gen = RobotsTxtGenerator(site)
        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        overrides = gen._compute_section_overrides(default_policy)
        assert "/blog/" in overrides
        assert overrides["/blog/"].ai_train is True

    def test_mixed_section_not_overridden(self):
        """If pages in a section have different signals, no override is emitted."""
        site = MagicMock()
        site.pages = [
            self._make_page("/docs/public/", {"ai_train": True}),
            self._make_page("/docs/private/", {"ai_train": False}),
        ]
        gen = RobotsTxtGenerator(site)
        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        overrides = gen._compute_section_overrides(default_policy)
        assert "/docs/" not in overrides

    def test_draft_pages_excluded(self):
        site = MagicMock()
        site.pages = [
            self._make_page("/blog/post-1/", {"ai_train": True}, draft=True),
        ]
        gen = RobotsTxtGenerator(site)
        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        overrides = gen._compute_section_overrides(default_policy)
        assert overrides == {}


class TestContentSignalsManifest:
    """Test .well-known/content-signals.json generation."""

    def _make_site(self):
        site = MagicMock()
        _config = {
            "content_signals": {
                "enabled": True,
                "search": True,
                "ai_input": True,
                "ai_train": False,
                "include_sitemap": True,
            },
            "output_formats": {
                "per_page": ["json", "llm_txt"],
                "site_wide": ["index_json", "llm_full"],
            },
            "generate_rss": True,
        }
        site.config = MagicMock()
        site.config.get = lambda key, default=None: _config.get(key, default)
        site.baseurl = "https://example.com"
        site.output_dir = Path("/tmp/test-output")
        site.dev_mode = False
        site.build_time = None
        site.title = "Test Site"

        page = MagicMock()
        page.output_path = Path("/tmp/test-output/index.html")
        page.draft = False
        site.pages = [page]
        return site

    def test_manifest_structure(self, tmp_path):
        site = self._make_site()
        site.output_dir = tmp_path
        gen = RobotsTxtGenerator(site)

        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        config = gen._get_config()
        gen._write_manifest(default_policy, {}, config)

        manifest_path = tmp_path / ".well-known" / "content-signals.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["version"] == "1.0"
        assert data["generator"] == "bengal"
        assert data["spec"] == "https://contentsignals.org/"
        assert data["default_policy"]["search"] is True
        assert data["default_policy"]["ai_input"] is True
        assert data["default_policy"]["ai_train"] is False

    def test_manifest_includes_formats(self, tmp_path):
        site = self._make_site()
        site.output_dir = tmp_path
        gen = RobotsTxtGenerator(site)

        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        gen._write_manifest(default_policy, {}, gen._get_config())

        data = json.loads((tmp_path / ".well-known" / "content-signals.json").read_text())
        assert "html" in data["formats"]
        assert "json" in data["formats"]
        assert "search_index" in data["formats"]

    def test_manifest_includes_section_overrides(self, tmp_path):
        site = self._make_site()
        site.output_dir = tmp_path
        gen = RobotsTxtGenerator(site)

        default_policy = SignalPolicy(search=True, ai_input=True, ai_train=False)
        overrides = {
            "/blog/": SignalPolicy(search=True, ai_input=True, ai_train=True),
        }
        gen._write_manifest(default_policy, overrides, gen._get_config())

        data = json.loads((tmp_path / ".well-known" / "content-signals.json").read_text())
        assert "/blog/" in data["section_overrides"]
        assert data["section_overrides"]["/blog/"]["ai_train"] is True

    def test_manifest_page_count(self, tmp_path):
        site = self._make_site()
        site.output_dir = tmp_path
        gen = RobotsTxtGenerator(site)

        gen._write_manifest(
            SignalPolicy(search=True, ai_input=True, ai_train=False), {}, gen._get_config()
        )

        data = json.loads((tmp_path / ".well-known" / "content-signals.json").read_text())
        assert data["page_count"] == 1
