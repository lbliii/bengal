"""Tests for loader factory functions."""

from __future__ import annotations

import importlib.util

import pytest

from bengal.content.sources.loaders import local_loader


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

    def test_github_loader_import_error(self) -> None:
        """Test github_loader raises ImportError if aiohttp not installed."""
        if importlib.util.find_spec("aiohttp") is not None:
            from bengal.content.sources.loaders import github_loader

            loader = github_loader(repo="owner/repo")
            assert loader.source_type == "github"
        else:
            with pytest.raises(ImportError, match=r"(?i)aiohttp|github"):
                from bengal.content.sources.loaders import github_loader  # noqa: F401

    def test_rest_loader_import_error(self) -> None:
        """Test rest_loader raises ImportError if aiohttp not installed."""
        if importlib.util.find_spec("aiohttp") is not None:
            from bengal.content.sources.loaders import rest_loader

            loader = rest_loader(url="https://api.example.com")
            assert loader.source_type == "rest"
        else:
            with pytest.raises(ImportError, match=r"(?i)aiohttp|rest"):
                from bengal.content.sources.loaders import rest_loader  # noqa: F401

    def test_notion_loader_import_error(self) -> None:
        """Test notion_loader raises ImportError if aiohttp not installed."""
        if importlib.util.find_spec("aiohttp") is not None:
            from bengal.content.sources.loaders import notion_loader
            from bengal.errors import BengalConfigError

            with pytest.raises(BengalConfigError, match="requires a token"):
                notion_loader(database_id="abc123")
        else:
            with pytest.raises(ImportError, match=r"(?i)aiohttp|notion"):
                from bengal.content.sources.loaders import notion_loader  # noqa: F401
