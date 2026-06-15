"""
Tests guarding the documented public content-type API and the published
content-type key set.

These tests pin two things the docs must not drift from:

1. The public registration API is ``bengal.content_types.register_strategy``,
   which takes a content-type name and a strategy *instance* (not a class).
2. The "Available types" list documented in
   ``site/content/docs/reference/architecture/core/content-types.md`` matches
   the actual keys in ``CONTENT_TYPE_REGISTRY`` exactly.
"""

from __future__ import annotations

import re
from pathlib import Path

from bengal.content_types import (
    CONTENT_TYPE_REGISTRY,
    ContentTypeStrategy,
    get_strategy,
    register_strategy,
)

# Repo root: tests/unit/content_types/ -> up three levels.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTENT_TYPES_DOC = (
    _REPO_ROOT
    / "site"
    / "content"
    / "docs"
    / "reference"
    / "architecture"
    / "core"
    / "content-types.md"
)


class TestDocumentedRegisterStrategyApi:
    """The docs tell users to call ``register_strategy(name, StrategyInstance())``."""

    def test_register_strategy_is_importable_from_package_root(self) -> None:
        """``from bengal.content_types import register_strategy`` must work."""
        assert callable(register_strategy)

    def test_register_strategy_accepts_an_instance_and_get_strategy_returns_it(self) -> None:
        """
        Registering a strategy *instance* (as the docs show) must make it
        retrievable via ``get_strategy`` by name.
        """

        class NewsStrategy(ContentTypeStrategy):
            default_template = "news/list.html"
            allows_pagination = True

            def detect_from_section(self, section):
                return section.name.lower() in ("news", "announcements")

        instance = NewsStrategy()
        original = CONTENT_TYPE_REGISTRY.get("news")
        try:
            register_strategy("news", instance)
            retrieved = get_strategy("news")
            assert retrieved is instance
            assert isinstance(retrieved, NewsStrategy)
        finally:
            # Keep the global registry clean for other tests.
            if original is None:
                CONTENT_TYPE_REGISTRY.pop("news", None)
            else:
                CONTENT_TYPE_REGISTRY["news"] = original


class TestPublishedContentTypeKeys:
    """The documented key set must exactly equal the live registry keys."""

    #: The single source of truth for what content-type keys Bengal publishes.
    #: Mirrors ``CONTENT_TYPE_REGISTRY`` in ``bengal/content_types/registry.py``.
    PUBLISHED_KEYS = frozenset(
        {
            "blog",
            "archive",
            "changelog",
            "doc",
            "notebook",
            "autodoc-python",
            "autodoc-cli",
            "tutorial",
            "track",
            "page",
            "list",
        }
    )

    def test_registry_keys_match_published_set_exactly(self) -> None:
        """
        The live registry keys must be exactly the published set.

        This fails loudly if a key is added/removed without updating the
        published documentation, or if the published set ever drifts to
        include phantom keys like ``api-reference`` / ``cli-reference``.
        """
        assert set(CONTENT_TYPE_REGISTRY) == set(self.PUBLISHED_KEYS), (
            "CONTENT_TYPE_REGISTRY keys diverged from the published set. "
            f"Only in registry: {set(CONTENT_TYPE_REGISTRY) - set(self.PUBLISHED_KEYS)}; "
            f"only in published set: {set(self.PUBLISHED_KEYS) - set(CONTENT_TYPE_REGISTRY)}"
        )

    def test_docs_available_types_list_matches_registry(self) -> None:
        """
        The "Available types" list in the content-types reference doc must
        enumerate exactly the real registry keys.

        RED before the fix: the doc lists ``api-reference`` / ``cli-reference``
        (which are not registry keys) and omits ``archive`` / ``notebook`` /
        ``list``, so the parsed set will not equal the registry keys.
        """
        text = _CONTENT_TYPES_DOC.read_text(encoding="utf-8")
        match = re.search(r"Available types:\s*(.+)", text)
        assert match is not None, "Could not find the 'Available types:' line in the doc"

        # The keys are written as inline code spans: `blog`, `doc`, ...
        documented = set(re.findall(r"`([a-z0-9-]+)`", match.group(1)))
        assert documented, "No `code`-quoted type keys found on the Available types line"

        assert documented == set(CONTENT_TYPE_REGISTRY), (
            "Documented 'Available types' diverged from the real registry keys. "
            f"Only in doc: {documented - set(CONTENT_TYPE_REGISTRY)}; "
            f"only in registry: {set(CONTENT_TYPE_REGISTRY) - documented}"
        )

    def test_phantom_reference_keys_are_not_documented(self) -> None:
        """The phantom ``api-reference`` / ``cli-reference`` keys must be gone."""
        text = _CONTENT_TYPES_DOC.read_text(encoding="utf-8")
        match = re.search(r"Available types:\s*(.+)", text)
        assert match is not None
        documented = set(re.findall(r"`([a-z0-9-]+)`", match.group(1)))
        assert "api-reference" not in documented
        assert "cli-reference" not in documented
