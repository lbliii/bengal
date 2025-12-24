"""
CSS Manifest for Bengal Default Theme.

Defines categorized CSS files for content-aware tree shaking.
The CSSOptimizer uses this manifest to generate minimal style.css
bundles based on what content types and features are actually used.

Categories:
    CSS_CORE: Always included (site won't render without these)
    CSS_SHARED: Common components used across most content types
    CSS_TYPE_MAP: Content-type-specific CSS
    CSS_FEATURE_MAP: Feature-specific CSS (enabled by content or config)
    CSS_PALETTES: Color theme presets

Usage:
    from bengal.themes.default.css_manifest import (
        CSS_CORE,
        CSS_SHARED,
        CSS_TYPE_MAP,
        CSS_FEATURE_MAP,
        CSS_PALETTES,
    )

See Also:
    - bengal/orchestration/css_optimizer.py: CSSOptimizer that consumes this
    - plan/drafted/rfc-css-tree-shaking.md: Design rationale
"""

from __future__ import annotations

# ============================================================================
# CSS_CORE: Always included (site won't render correctly without these)
# ============================================================================
CSS_CORE: list[str] = [
    # Design tokens (CSS variables)
    "tokens/foundation.css",
    "tokens/typography.css",
    "tokens/semantic.css",
    # Base styles
    "base/reset.css",
    "base/typography.css",
    "base/utilities.css",
    "base/interactive-patterns.css",
    "base/accessibility.css",
    "base/print.css",
    # Composition layouts
    "composition/layouts.css",
    # Core layout components
    "layouts/grid.css",
    "layouts/header.css",
    "layouts/footer.css",
    "layouts/page-header.css",
]

# ============================================================================
# CSS_PALETTES: Color theme presets (optional, but usually all included)
# ============================================================================
CSS_PALETTES: list[str] = [
    "tokens/palettes/snow-lynx.css",
    "tokens/palettes/brown-bengal.css",
    "tokens/palettes/silver-bengal.css",
    "tokens/palettes/charcoal-bengal.css",
    "tokens/palettes/blue-bengal.css",
]

# ============================================================================
# CSS_SHARED: Common components used across most content types
# ============================================================================
CSS_SHARED: list[str] = [
    # UI components
    "components/buttons.css",
    "components/forms.css",
    "components/cards.css",
    "components/badges.css",
    "components/labels.css",
    "components/icons.css",
    "components/alerts.css",
    "components/admonitions.css",
    "components/tabs.css",
    "components/dropdowns.css",
    "components/code.css",
    "components/target-anchor.css",
    # Navigation components
    "components/navigation.css",
    "components/pagination.css",
    "components/toc.css",
    # States
    "components/empty-state.css",
    # Utilities
    "utilities/motion.css",
    "utilities/scroll-animations.css",
    "utilities/gradient-borders.css",
    "utilities/fluid-blobs.css",
]

# ============================================================================
# CSS_TYPE_MAP: Content-type-specific CSS
# ============================================================================
CSS_TYPE_MAP: dict[str, list[str]] = {
    # Blog content type
    "blog": [
        "components/blog.css",
        "components/archive.css",
        "components/author.css",
        "components/author-page.css",
        "components/related-posts.css",
        "components/share.css",
        "components/meta.css",
        "components/tags.css",
        "components/category-browser.css",
    ],
    # Documentation content type
    "doc": [
        "components/docs-nav.css",
        "components/action-bar.css",
        "components/nav-action-buttons.css",
        "components/versioning.css",
        "components/steps.css",
        "components/checklist.css",
    ],
    # Tutorial content type
    "tutorial": [
        "components/tutorial.css",
        "components/steps.css",
    ],
    # Learning tracks
    "track": [
        "components/tracks.css",
        "components/hub-cards.css",
    ],
    # API documentation
    "autodoc": [
        "components/autodoc.css",
        "components/reference-docs.css",
        "components/api-hub.css",
    ],
    "autodoc-python": [
        "components/autodoc.css",
        "components/reference-docs.css",
        "components/api-hub.css",
    ],
    "autodoc-cli": [
        "components/autodoc.css",
        "components/reference-docs.css",
    ],
    "api-reference": [
        "components/autodoc.css",
        "components/reference-docs.css",
        "components/api-hub.css",
    ],
    # Changelog
    "changelog": [
        "layouts/changelog.css",
    ],
    # Resume
    "resume": [
        "layouts/resume.css",
    ],
    # Landing pages
    "landing": [
        "pages/landing.css",
        "components/hero.css",
        "components/page-hero.css",
    ],
    "home": [
        "pages/landing.css",
        "components/hero.css",
        "components/page-hero.css",
    ],
    # Hub pages
    "hub": [
        "components/hub-cards.css",
    ],
    "api-hub": [
        "components/api-hub.css",
        "components/hub-cards.css",
    ],
}

# ============================================================================
# CSS_FEATURE_MAP: Feature-specific CSS (detected from content or config)
# ============================================================================
CSS_FEATURE_MAP: dict[str, list[str]] = {
    # Graph visualization
    "graph": [
        "components/graph.css",
        "components/graph-minimap.css",
        "components/graph-contextual.css",
    ],
    # Search functionality
    "search": [
        "components/search.css",
        "components/search-modal.css",
    ],
    # Mermaid diagrams
    "mermaid": [
        "components/mermaid.css",
    ],
    # Data tables (tabulator)
    "data_tables": [
        "components/data-table.css",
        "tabulator.min.css",
    ],
    # Interactive widgets
    "interactive": [
        "components/interactive.css",
        "components/widgets.css",
    ],
    # Experimental holographic effects
    "holo_cards": [
        "experimental/holo-cards-advanced.css",
    ],
}

# ============================================================================
# CSS_EXPERIMENTAL: Opt-in experimental CSS (requires explicit config)
# ============================================================================
CSS_EXPERIMENTAL: list[str] = [
    "experimental/holo-cards-advanced.css",
    "experimental/holo-tcg-admonitions.css",
    "experimental/border-gradient-theme-aware.css",
    "experimental/border-styles-demo.css",
]

# ============================================================================
# Manifest version for cache invalidation
# ============================================================================
MANIFEST_VERSION: int = 1
