"""
Page metadata visibility mixin - visibility settings and inclusion checks.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

from bengal.core.page.types import VisibilitySettings


class PageMetadataVisibilityMixin:
    """Visibility settings and in_listings, in_sitemap, in_search, etc."""

    metadata: object
    _site: object

    def _get_content_signal_defaults(self) -> dict[str, Any]:
        """Get site-level content signal defaults from config."""
        site = getattr(self, "_site", None)
        if site is None:
            return {}
        config = getattr(site, "config", None)
        if config is None:
            return {}
        try:
            cs = config.get("content_signals", {})
            return cs if isinstance(cs, dict) else {}
        except Exception:
            return {}

    @cached_property
    def visibility(self) -> VisibilitySettings:
        """Get visibility settings with defaults (frozen for thread-safety).

        Cost: O(1) cached — computed once, then attribute access for 8 sub-properties.
        """
        if self.metadata.get("hidden", False):
            return VisibilitySettings(
                menu=False,
                listings=False,
                sitemap=False,
                robots="noindex, nofollow",
                render="always",
                search=False,
                rss=False,
                ai_train=False,
                ai_input=False,
            )

        vis = self.metadata.get("visibility", {})
        cs = self._get_content_signal_defaults()
        return VisibilitySettings(
            menu=vis.get("menu", True),
            listings=vis.get("listings", True),
            sitemap=vis.get("sitemap", True),
            robots=vis.get("robots", "index, follow"),
            render=vis.get("render", "always"),
            search=vis.get("search", cs.get("search", True)),
            rss=vis.get("rss", True),
            ai_train=vis.get("ai_train", cs.get("ai_train", False)),
            ai_input=vis.get("ai_input", cs.get("ai_input", True)),
        )

    @property
    def in_listings(self) -> bool:
        """Check if page should appear in listings/queries."""
        return self.visibility.listings and not self.draft

    @property
    def in_sitemap(self) -> bool:
        """Check if page should appear in sitemap."""
        return self.visibility.sitemap and not self.draft

    @property
    def in_search(self) -> bool:
        """Check if page should appear in search index."""
        return self.visibility.search and not self.draft

    @property
    def in_rss(self) -> bool:
        """Check if page should appear in RSS feeds."""
        return self.visibility.rss and not self.draft

    @property
    def in_ai_train(self) -> bool:
        """Check if page content may be used for AI training."""
        return self.visibility.ai_train and not self.draft

    @property
    def in_ai_input(self) -> bool:
        """Check if page content may be used for AI input (RAG, grounding)."""
        return self.visibility.ai_input and not self.draft

    @property
    def robots_meta(self) -> str:
        """Get robots meta content for this page."""
        return str(self.visibility.robots)

    @property
    def should_render(self) -> bool:
        """Check if page should be rendered based on visibility.render setting."""
        return bool(self.visibility.render != "never")

    def should_render_in_environment(self, is_production: bool = False) -> bool:
        """
        Check if page should be rendered in the given environment.

        Args:
            is_production: True if building for production

        Returns:
            True if page should be rendered in this environment
        """
        render = self.visibility.render
        if render == "never":
            return False
        return not (render == "local" and is_production)
