"""
Tests for external references (cross-project documentation linking).

Tests the [[ext:project:target]] syntax and related functionality.

See: plan/rfc-external-references.md
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.config.defaults import DEFAULTS
from bengal.postprocess.xref_index import XRefIndexGenerator, should_export_xref_index
from bengal.rendering.external_refs import ExternalRefResolver, resolve_template
from bengal.rendering.external_refs.resolver import IndexCache
from bengal.rendering.plugins.cross_references import CrossReferencePlugin


class TestResolveTemplate:
    """Tests for URL template resolution."""

    def test_python_stdlib_template(self) -> None:
        """Test Python stdlib URL template resolution."""
        template = "https://docs.python.org/3/library/{module}.html#{name}"
        url = resolve_template(template, "pathlib.Path")

        assert url == "https://docs.python.org/3/library/pathlib.html#Path"

    def test_simple_target_no_module(self) -> None:
        """Test resolution when target has no module part."""
        template = "https://example.com/api/#{name}"
        url = resolve_template(template, "MyClass")

        assert url == "https://example.com/api/#MyClass"

    def test_name_lower_variable(self) -> None:
        """Test {name_lower} variable for lowercase names."""
        template = "https://example.com/api/#{name_lower}"
        url = resolve_template(template, "MyClass")

        assert url == "https://example.com/api/#myclass"

    def test_target_variable(self) -> None:
        """Test {target} variable for full target string."""
        template = "https://example.com/search?q={target}"
        url = resolve_template(template, "pathlib.Path")

        assert url == "https://example.com/search?q=pathlib.Path"


class TestExternalRefResolver:
    """Tests for ExternalRefResolver."""

    @pytest.fixture
    def resolver(self) -> ExternalRefResolver:
        """Create resolver with default templates."""
        config = {"external_refs": DEFAULTS.get("external_refs", {})}
        return ExternalRefResolver(config)

    def test_resolve_python_stdlib(self, resolver: ExternalRefResolver) -> None:
        """Test resolving Python stdlib references."""
        html = resolver.resolve("python", "pathlib.Path")

        assert 'href="https://docs.python.org/3/library/pathlib.html#Path"' in html
        assert 'class="extref"' in html
        assert ">Path</a>" in html

    def test_resolve_with_custom_text(self, resolver: ExternalRefResolver) -> None:
        """Test resolving with custom link text."""
        html = resolver.resolve("python", "pathlib.Path", text="Path class")

        assert ">Path class</a>" in html

    def test_resolve_numpy(self, resolver: ExternalRefResolver) -> None:
        """Test resolving NumPy references."""
        html = resolver.resolve("numpy", "ndarray")

        assert "numpy.org" in html
        assert "ndarray" in html

    def test_can_resolve_true(self, resolver: ExternalRefResolver) -> None:
        """Test can_resolve returns True for resolvable refs."""
        assert resolver.can_resolve("python", "pathlib.Path") is True

    def test_can_resolve_false(self, resolver: ExternalRefResolver) -> None:
        """Test can_resolve returns False for unknown projects."""
        assert resolver.can_resolve("unknown_project", "SomeClass") is False

    def test_graceful_fallback(self, resolver: ExternalRefResolver) -> None:
        """Test fallback for unknown projects."""
        html = resolver.resolve("unknown_project", "SomeClass")

        # Should return code element, not link
        assert "<code" in html
        assert "extref-unresolved" in html
        assert "ext:unknown_project:SomeClass" in html

    def test_tracks_unresolved(self, resolver: ExternalRefResolver) -> None:
        """Test that unresolved refs are tracked."""
        source_file = Path("/test/page.md")
        resolver.resolve("unknown", "Target", source_file=source_file, line=42)

        assert len(resolver.unresolved) == 1
        assert resolver.unresolved[0].project == "unknown"
        assert resolver.unresolved[0].target == "Target"
        assert resolver.unresolved[0].source_file == source_file
        assert resolver.unresolved[0].line == 42


class TestCrossReferencePluginExternal:
    """Tests for CrossReferencePlugin external reference handling."""

    @pytest.fixture
    def xref_index(self) -> dict:
        """Create minimal xref index."""
        return {
            "by_path": {},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
            "by_anchor": {},
        }

    @pytest.fixture
    def resolver(self) -> ExternalRefResolver:
        """Create resolver with default templates."""
        config = {"external_refs": DEFAULTS.get("external_refs", {})}
        return ExternalRefResolver(config)

    def test_external_ref_parsing(self, xref_index: dict, resolver: ExternalRefResolver) -> None:
        """Test that [[ext:project:target]] is parsed correctly."""
        plugin = CrossReferencePlugin(xref_index, external_ref_resolver=resolver)

        html = plugin._resolve_external("python:pathlib.Path", None)

        assert 'href="https://docs.python.org/3/library/pathlib.html#Path"' in html

    def test_external_ref_with_custom_text(
        self, xref_index: dict, resolver: ExternalRefResolver
    ) -> None:
        """Test external ref with custom text."""
        plugin = CrossReferencePlugin(xref_index, external_ref_resolver=resolver)

        html = plugin._resolve_external("python:pathlib.Path", "Path handling")

        assert ">Path handling</a>" in html

    def test_external_ref_invalid_format(
        self, xref_index: dict, resolver: ExternalRefResolver
    ) -> None:
        """Test handling of invalid external ref format."""
        plugin = CrossReferencePlugin(xref_index, external_ref_resolver=resolver)

        # Missing colon between project and target
        html = plugin._resolve_external("python-pathlib.Path", None)

        assert "<code" in html
        assert "Invalid format" in html

    def test_external_ref_no_resolver(self, xref_index: dict) -> None:
        """Test graceful handling when no resolver is configured."""
        plugin = CrossReferencePlugin(xref_index, external_ref_resolver=None)

        html = plugin._resolve_external("python:pathlib.Path", None)

        assert "<code" in html
        assert "External references not configured" in html


class TestXRefIndexGenerator:
    """Tests for xref.json generation."""

    @pytest.fixture
    def mock_site(self, tmp_path: Path) -> MagicMock:
        """Create mock site for testing."""
        site = MagicMock()
        site.title = "Test Site"
        site.baseurl = "/test/"
        site.output_dir = tmp_path

        # Create mock pages
        page1 = MagicMock()
        page1.title = "Getting Started"
        page1.slug = "getting-started"
        page1.href = "/test/docs/getting-started/"
        page1.url = "/test/docs/getting-started/"
        page1.metadata = {"description": "Quick start guide"}
        page1.source_path = Path("content/docs/getting-started.md")

        page2 = MagicMock()
        page2.title = "API Reference"
        page2.slug = "api-reference"
        page2.href = "/test/api/"
        page2.url = "/test/api/"
        page2.metadata = {"description": "API documentation"}
        page2.source_path = Path("content/api.md")

        site.pages = [page1, page2]
        site.config = {"external_refs": {"enabled": True, "export_index": True}}

        return site

    def test_generate_xref_json(self, mock_site: MagicMock) -> None:
        """Test xref.json generation."""
        generator = XRefIndexGenerator(mock_site)
        output_path = generator.generate()

        assert output_path.exists()
        assert output_path.name == "xref.json"

        with open(output_path) as f:
            data = json.load(f)

        assert data["version"] == "1"
        assert "bengal" in data["generator"]
        assert data["project"]["name"] == "Test Site"
        assert "getting-started" in data["entries"]
        assert "api-reference" in data["entries"]

    def test_entry_format(self, mock_site: MagicMock) -> None:
        """Test entry format in xref.json."""
        generator = XRefIndexGenerator(mock_site)
        output_path = generator.generate()

        with open(output_path) as f:
            data = json.load(f)

        entry = data["entries"]["getting-started"]
        assert entry["type"] == "page"
        assert entry["path"] == "/test/docs/getting-started/"
        assert entry["title"] == "Getting Started"
        assert entry["summary"] == "Quick start guide"

    def test_should_export_enabled(self) -> None:
        """Test should_export_xref_index when enabled."""
        site = MagicMock()
        site.config = {"external_refs": {"export_index": True}}

        assert should_export_xref_index(site) is True

    def test_should_export_disabled(self) -> None:
        """Test should_export_xref_index when disabled."""
        site = MagicMock()
        site.config = {"external_refs": {"export_index": False}}

        assert should_export_xref_index(site) is False

    def test_should_export_bool_config(self) -> None:
        """Test should_export_xref_index with bool config."""
        site = MagicMock()
        site.config = {"external_refs": False}

        assert should_export_xref_index(site) is False


class TestIndexCache:
    """Tests for IndexCache fetching and headers."""

    def test_fetch_uses_auth_header(self, monkeypatch, tmp_path) -> None:
        """Ensure auth headers are sent on fetch."""
        cache = IndexCache(cache_dir=tmp_path)
        captured: dict[str, str] = {}

        class _Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self) -> bytes:
                return b'{"entries":{}}'

        def fake_urlopen(request, timeout=10):
            captured.update(request.headers)
            return _Response()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

        cache._fetch(
            "proj",
            "https://example.com/xref.json",
            tmp_path / "proj.json",
            headers={"Authorization": "Token 123"},
        )

        assert captured.get("Authorization") == "Token 123"
        assert (tmp_path / "proj.json").exists()

    def test_stale_cache_triggers_background_refresh(self, monkeypatch, tmp_path) -> None:
        """Stale cache returns cached data and triggers refresh."""
        cache = IndexCache(cache_dir=tmp_path)
        cache_file = tmp_path / "proj.json"
        cache_file.write_text('{"entries":{"cached":{}}}')
        # Make cache stale
        old_time = time.time() - 86400
        os.utime(cache_file, (old_time, old_time))

        refresh_called: dict[str, tuple] = {}

        def fake_refresh(project, url, cache_file_arg, headers, max_age) -> None:
            refresh_called["called"] = (project, url, cache_file_arg, headers, max_age)

        class DummyThread:
            def __init__(self, target, args, daemon=False):
                self._target = target
                self._args = args

            def start(self) -> None:
                self._target(*self._args)

        monkeypatch.setattr("bengal.rendering.external_refs.resolver.Thread", DummyThread)
        monkeypatch.setattr(cache, "_refresh_cache", fake_refresh)

        result = cache.get("proj", "https://example.com/xref.json", max_age_days=0)

        # Should return cached data immediately
        assert result["entries"]["cached"] == {}
        # Background refresh should be triggered
        assert refresh_called.get("called") is not None
        assert refresh_called["called"][0] == "proj"


class TestConfigDefaults:
    """Tests for external_refs configuration defaults."""

    def test_defaults_exist(self) -> None:
        """Test that external_refs defaults exist."""
        external_refs = DEFAULTS.get("external_refs", {})

        assert external_refs is not None
        assert "enabled" in external_refs
        assert "templates" in external_refs
        assert "indexes" in external_refs

    def test_default_templates(self) -> None:
        """Test default URL templates are present."""
        templates = DEFAULTS.get("external_refs", {}).get("templates", {})

        assert "python" in templates
        assert "numpy" in templates
        assert "pandas" in templates

    def test_default_enabled(self) -> None:
        """Test external_refs is enabled by default."""
        external_refs = DEFAULTS.get("external_refs", {})

        assert external_refs.get("enabled") is True

    def test_default_export_disabled(self) -> None:
        """Test export_index is disabled by default."""
        external_refs = DEFAULTS.get("external_refs", {})

        # Export should be opt-in
        assert external_refs.get("export_index") is False
