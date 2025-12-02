"""Tests for loader factory functions."""

from __future__ import annotations

import pytest

from bengal.content_layer.loaders import local_loader


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
        # This test will pass if aiohttp IS installed (loader works)
        # or if aiohttp is NOT installed (ImportError is raised)
        try:
            from bengal.content_layer.loaders import github_loader

            # If we get here, aiohttp is installed - test the loader works
            loader = github_loader(repo="owner/repo")
            assert loader.source_type == "github"
        except ImportError as e:
            assert "aiohttp" in str(e).lower() or "github" in str(e).lower()

    def test_rest_loader_import_error(self) -> None:
        """Test rest_loader raises ImportError if aiohttp not installed."""
        try:
            from bengal.content_layer.loaders import rest_loader

            loader = rest_loader(url="https://api.example.com")
            assert loader.source_type == "rest"
        except ImportError as e:
            assert "aiohttp" in str(e).lower() or "rest" in str(e).lower()

    def test_notion_loader_import_error(self) -> None:
        """Test notion_loader raises ImportError if aiohttp not installed."""
        try:
            from bengal.content_layer.loaders import notion_loader

            # Note: Will fail without token, but tests import works
            with pytest.raises(ValueError, match="requires a token"):
                notion_loader(database_id="abc123")
        except ImportError as e:
            assert "aiohttp" in str(e).lower() or "notion" in str(e).lower()

