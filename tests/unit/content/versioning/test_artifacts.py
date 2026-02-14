"""Unit tests for versioning artifacts (versions.json, root redirect)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from bengal.content.versioning.artifacts import (
    _redirect_html,
    build_versions_json,
    write_root_redirect,
    write_versions_json,
)
from bengal.core.version import Version, VersionConfig


class TestBuildVersionsJson:
    """Tests for build_versions_json."""

    def test_builds_mike_compatible_structure(self) -> None:
        vc = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v2", latest=True, label="2.0"),
                Version(id="v1", latest=False, label="1.0"),
            ],
            aliases={"latest": "v2"},
        )
        data = build_versions_json(vc)
        assert len(data) == 2
        assert data[0]["version"] == "v2"
        assert data[0]["title"] == "2.0"
        assert "latest" in data[0]["aliases"]
        assert data[0]["url_prefix"] == ""
        assert data[1]["version"] == "v1"
        assert data[1]["url_prefix"] == "/v1"

    def test_empty_versions_returns_empty_list(self) -> None:
        vc = VersionConfig(enabled=True, versions=[])
        assert build_versions_json(vc) == []


class TestWriteVersionsJson:
    """Tests for write_versions_json."""

    def test_writes_when_versioning_enabled(self) -> None:
        site = MagicMock()
        site.version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v2", latest=True),
                Version(id="v1", latest=False),
            ],
            aliases={"latest": "v2"},
        )
        site.config = {"versioning": {"emit_versions_json": True}}

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_versions_json(site, out)
            path = out / "versions.json"
            assert path.exists()
            data = json.loads(path.read_text())
            assert len(data) == 2
            assert data[0]["version"] == "v2"
            assert data[1]["version"] == "v1"

    def test_skips_when_versioning_disabled(self) -> None:
        site = MagicMock()
        site.version_config = VersionConfig(enabled=False)
        with tempfile.TemporaryDirectory() as tmp:
            write_versions_json(site, Path(tmp))
            assert not (Path(tmp) / "versions.json").exists()

    def test_skips_when_emit_false(self) -> None:
        site = MagicMock()
        site.version_config = VersionConfig(
            enabled=True,
            versions=[Version(id="v1", latest=True)],
        )
        site.config = {"versioning": {"emit_versions_json": False}}
        with tempfile.TemporaryDirectory() as tmp:
            write_versions_json(site, Path(tmp))
            assert not (Path(tmp) / "versions.json").exists()


class TestWriteRootRedirect:
    """Tests for write_root_redirect."""

    def test_writes_when_default_redirect_enabled(self) -> None:
        site = MagicMock()
        site.version_config = VersionConfig(
            enabled=True,
            versions=[Version(id="v2", latest=True)],
            sections=["docs"],
        )
        site.config = {"versioning": {"default_redirect": True}}

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_root_redirect(site, out)
            path = out / "index.html"
            assert path.exists()
            html = path.read_text()
            assert 'content="0;url=/docs/"' in html or 'href="/docs/"' in html

    def test_skips_when_default_redirect_disabled(self) -> None:
        site = MagicMock()
        site.version_config = VersionConfig(
            enabled=True,
            versions=[Version(id="v1", latest=True)],
        )
        site.config = {"versioning": {"default_redirect": False}}
        with tempfile.TemporaryDirectory() as tmp:
            write_root_redirect(site, Path(tmp))
            assert not (Path(tmp) / "index.html").exists()

    def test_uses_custom_redirect_target(self) -> None:
        site = MagicMock()
        site.version_config = VersionConfig(
            enabled=True,
            versions=[Version(id="v1", latest=True)],
        )
        site.config = {
            "versioning": {
                "default_redirect": True,
                "default_redirect_target": "/guide/",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_root_redirect(site, out)
            html = (out / "index.html").read_text()
            assert "/guide/" in html

    def test_redirect_html_escapes_special_characters(self) -> None:
        """href with quotes/special chars must be escaped to avoid malformed HTML/JS."""
        html_out = _redirect_html('https://example.com/docs/" onload="alert(1)')
        assert "&quot;" in html_out
        assert 'onload="alert(1)' not in html_out
        assert "href=" in html_out
