"""Tests for loader factory functions."""

from __future__ import annotations

import builtins
import sys

import pytest

from bengal.content.sources.loaders import local_loader


def _simulate_missing_aiohttp(monkeypatch: pytest.MonkeyPatch, source_module: str) -> None:
    """Force a source module to re-import with aiohttp unavailable."""
    original_import = builtins.__import__

    def blocked_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "aiohttp" or name.startswith("aiohttp."):
            raise ImportError("No module named 'aiohttp'")
        return original_import(name, globals, locals, fromlist, level)

    sys.modules.pop(source_module, None)
    monkeypatch.setattr(builtins, "__import__", blocked_import)


class TestLocalLoader:
    """Tests for local_loader factory function."""

    def test_basic_creation(self) -> None:
        """Test creating local loader with directory."""
        loader = local_loader("content/docs")

        assert loader.source_type == "local"
        assert loader.config["directory"] == "content/docs"

    def test_with_options(self) -> None:
        """Test creating local loader with options."""
        loader = local_loader(
            "content/docs",
            glob="*.mdx",
            exclude=["_drafts/*"],
        )

        assert loader.config["glob"] == "*.mdx"
        assert loader.config["exclude"] == ["_drafts/*"]

    def test_name_includes_directory(self) -> None:
        """Test loader name includes directory."""
        loader = local_loader("content/docs")

        assert "content/docs" in loader.name


class TestRemoteLoaderImports:
    """Tests for remote loader import behavior."""

    def test_github_loader_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test github_loader raises ImportError if aiohttp not installed."""
        _simulate_missing_aiohttp(monkeypatch, "bengal.content.sources.github")

        from bengal.content.sources.loaders import github_loader

        with pytest.raises(ImportError, match=r"(?i)aiohttp|github"):
            github_loader(repo="owner/repo")

    def test_rest_loader_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test rest_loader raises ImportError if aiohttp not installed."""
        _simulate_missing_aiohttp(monkeypatch, "bengal.content.sources.rest")

        from bengal.content.sources.loaders import rest_loader

        with pytest.raises(ImportError, match=r"(?i)aiohttp|rest"):
            rest_loader(url="https://api.example.com")

    def test_notion_loader_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test notion_loader raises ImportError if aiohttp not installed."""
        _simulate_missing_aiohttp(monkeypatch, "bengal.content.sources.notion")

        from bengal.content.sources.loaders import notion_loader

        with pytest.raises(ImportError, match=r"(?i)aiohttp|notion"):
            notion_loader(database_id="abc123")
