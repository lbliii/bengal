"""
Shared fixtures for directive unit tests.

Provides realistic mock state objects for testing directive parsing and rendering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


class MockBlockState:
    """
    Realistic mock for Mistune's BlockState.
    
    Mimics the structure of patitas.core.BlockState with proper env handling.
    This fixture helps test directive parsing with realistic state tracking.
    """

    def __init__(
        self,
        root_path: Path | None = None,
        source_path: Path | None = None,
        env: dict[str, Any] | None = None,
    ):
        self.root_path = root_path
        self.source_path = source_path
        # env is a mutable dict for sharing state during parse
        self.env = env if env is not None else {}
        self._tokens: list[dict[str, Any]] = []
        self._cursor = 0

    def env_get(self, key: str, default: Any = None) -> Any:
        """Get value from env with default."""
        return self.env.get(key, default)

    def env_set(self, key: str, value: Any) -> None:
        """Set value in env."""
        self.env[key] = value

    def append_token(self, token: dict[str, Any]) -> None:
        """Append token to state (for directive nesting)."""
        self._tokens.append(token)

    def get_tokens(self) -> list[dict[str, Any]]:
        """Get accumulated tokens."""
        return self._tokens


@pytest.fixture
def mock_block_state(tmp_path: Path) -> MockBlockState:
    """
    Create a realistic mock BlockState for directive parsing tests.
    
    The state has:
    - root_path set to a temp directory (for file resolution)
    - env initialized as empty dict (not None!)
    - source_path set to a content file in the temp dir
    
    Usage:
        def test_directive(mock_block_state):
            directive = SomeDirective()
            result = directive.parse(block, match, mock_block_state)
            assert mock_block_state.env.get("_include_depth") == 1
    """
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    source_file = content_dir / "test.md"
    source_file.touch()

    return MockBlockState(
        root_path=tmp_path,
        source_path=source_file,
        env={},  # Always provide empty dict, not None
    )


@pytest.fixture
def mock_block_state_factory(tmp_path: Path):
    """
    Factory fixture for creating multiple isolated block states.
    
    Useful for testing state isolation between parallel parses.
    
    Usage:
        def test_parallel_parsing(mock_block_state_factory):
            state1 = mock_block_state_factory()
            state2 = mock_block_state_factory()
            # Parse with both, verify they don't share state
    """

    def _factory(
        env: dict[str, Any] | None = None,
        root_path: Path | None = None,
    ) -> MockBlockState:
        effective_root = root_path or tmp_path
        content_dir = effective_root / "content"
        content_dir.mkdir(parents=True, exist_ok=True)

        return MockBlockState(
            root_path=effective_root,
            source_path=content_dir / "test.md",
            env=env if env is not None else {},
        )

    return _factory


@pytest.fixture
def mock_renderer():
    """
    Create a mock renderer for directive rendering tests.
    
    The renderer has:
    - _site with default config
    - __call__ method that returns rendered HTML
    - render_children for nested content
    
    Usage:
        def test_render(mock_renderer):
            directive = SomeDirective()
            html = directive.render(mock_renderer, text="content")
    """
    renderer = MagicMock()
    renderer._site = MagicMock()
    renderer._site.config = {
        "document_application": {
            "interactivity": {
                "tabs": "enhanced",
            }
        }
    }

    # render_children returns the input by default
    renderer.render_children = MagicMock(side_effect=lambda tokens: tokens)

    return renderer


@pytest.fixture
def mock_renderer_factory():
    """
    Factory for creating renderers with specific configs.
    
    Usage:
        def test_different_configs(mock_renderer_factory):
            css_renderer = mock_renderer_factory(tabs_mode="css_state_machine")
            enhanced_renderer = mock_renderer_factory(tabs_mode="enhanced")
    """

    def _factory(
        tabs_mode: str = "enhanced",
        extra_config: dict[str, Any] | None = None,
    ) -> MagicMock:
        renderer = MagicMock()
        renderer._site = MagicMock()

        config = {
            "document_application": {
                "interactivity": {
                    "tabs": tabs_mode,
                }
            }
        }

        if extra_config:
            config.update(extra_config)

        renderer._site.config = config
        renderer.render_children = MagicMock(side_effect=lambda tokens: tokens)

        return renderer

    return _factory


@pytest.fixture
def temp_content_tree(tmp_path: Path):
    """
    Create a temporary content tree for include directive tests.
    
    Returns a helper to create files within the content directory.
    
    Usage:
        def test_includes(temp_content_tree):
            temp_content_tree.create("snippets/code.md", "```python\ncode\n```")
            temp_content_tree.create("components/header.md", "# Header")
    """

    class ContentTreeHelper:
        def __init__(self, root: Path):
            self.root = root
            self.content_dir = root / "content"
            self.content_dir.mkdir(parents=True, exist_ok=True)

        def create(self, relative_path: str, content: str) -> Path:
            """Create a file at the relative path with given content."""
            file_path = self.content_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return file_path

        def get_state(self, env: dict[str, Any] | None = None) -> MockBlockState:
            """Get a block state rooted at this content tree."""
            return MockBlockState(
                root_path=self.root,
                source_path=self.content_dir / "_index.md",
                env=env if env is not None else {},
            )

    return ContentTreeHelper(tmp_path)
