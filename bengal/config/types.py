"""
Type definitions for Bengal site configuration.

This module provides TypedDict definitions for all configuration options,
enabling IDE autocomplete, type checking, and self-documenting configuration.

Example:
    >>> from bengal.config.types import SiteConfig
    >>> config: SiteConfig = {
    ...     "title": "My Site",
    ...     "baseurl": "/docs/",
    ...     "theme": {"name": "default", "default_palette": "ocean-lynx"},
    ... }

See Also:
    - :mod:`bengal.config.defaults`: Default values using these types.
    - :mod:`bengal.config.loader`: Configuration loading and validation.
"""

from __future__ import annotations

from typing import Literal, TypedDict

# =============================================================================
# Build Settings
# =============================================================================


class StaticConfig(TypedDict, total=False):
    """Static files configuration."""

    enabled: bool
    dir: str


class HtmlOutputConfig(TypedDict, total=False):
    """HTML output formatting configuration."""

    mode: Literal["minify", "pretty", "raw"]
    remove_comments: bool
    collapse_blank_lines: bool


class AssetsConfig(TypedDict, total=False):
    """Asset processing configuration."""

    minify: bool
    optimize: bool
    fingerprint: bool
    pipeline: bool


# =============================================================================
# Theme
# =============================================================================


class ThemeConfig(TypedDict, total=False):
    """Theme configuration."""

    name: str
    default_appearance: Literal["light", "dark", "system"]
    default_palette: str
    features: list[str]
    show_reading_time: bool
    show_author: bool
    show_prev_next: bool
    show_children_default: bool
    show_excerpts_default: bool
    max_tags_display: int
    popular_tags_count: int


# =============================================================================
# Content Processing
# =============================================================================


class ContentConfig(TypedDict, total=False):
    """Content processing configuration."""

    default_type: str
    excerpt_length: int
    summary_length: int
    reading_speed: int
    related_count: int
    related_threshold: float
    toc_depth: int
    toc_min_headings: int
    toc_style: Literal["nested", "flat"]
    sort_pages_by: Literal["weight", "date", "title", "modified"]
    sort_order: Literal["asc", "desc"]
    strict_contracts: bool
    """If True, raise errors on directive contract violations. Defaults to False (warnings only)."""


# =============================================================================
# Search
# =============================================================================


class LunrConfig(TypedDict, total=False):
    """Lunr search engine configuration."""

    prebuilt: bool
    min_query_length: int
    max_results: int
    preload: Literal["immediate", "smart", "lazy"]


class SearchUIConfig(TypedDict, total=False):
    """Search UI configuration."""

    modal: bool
    recent_searches: int
    placeholder: str


class SearchAnalyticsConfig(TypedDict, total=False):
    """Search analytics configuration."""

    enabled: bool
    event_endpoint: str | None


class SearchConfig(TypedDict, total=False):
    """Search configuration."""

    enabled: bool
    lunr: LunrConfig
    ui: SearchUIConfig
    analytics: SearchAnalyticsConfig


# =============================================================================
# Pagination
# =============================================================================


class PaginationConfig(TypedDict, total=False):
    """Pagination configuration."""

    per_page: int


# =============================================================================
# Health Check
# =============================================================================


class ConnectivityThresholds(TypedDict, total=False):
    """Connectivity scoring thresholds."""

    well_connected: float
    adequately_linked: float
    lightly_linked: float


class LinkWeights(TypedDict, total=False):
    """Link type weights for connectivity scoring."""

    explicit: float
    menu: float
    taxonomy: float
    related: float
    topical: float
    sequential: float


class HealthCheckConfig(TypedDict, total=False):
    """Health check configuration."""

    enabled: bool
    verbose: bool
    strict_mode: bool
    orphan_threshold: int
    super_hub_threshold: int
    isolated_threshold: int
    lightly_linked_threshold: int
    connectivity_thresholds: ConnectivityThresholds
    link_weights: LinkWeights
    build_validators: list[str]
    full_validators: list[str]
    ci_validators: list[str]


# =============================================================================
# Features
# =============================================================================


class FeaturesConfig(TypedDict, total=False):
    """Feature toggles for output generation."""

    rss: bool
    sitemap: bool
    search: bool
    json: bool
    llm_txt: bool
    syntax_highlighting: bool


# =============================================================================
# Graph
# =============================================================================


class GraphConfig(TypedDict, total=False):
    """Knowledge graph configuration."""

    enabled: bool
    path: str


# =============================================================================
# i18n
# =============================================================================


class I18nConfig(TypedDict, total=False):
    """Internationalization configuration."""

    strategy: str | None
    default_language: str
    default_in_subdir: bool


# =============================================================================
# Output Formats
# =============================================================================


class OutputFormatOptions(TypedDict, total=False):
    """Output format options."""

    excerpt_length: int
    json_indent: int | None
    llm_separator_width: int
    include_full_content_in_index: bool
    exclude_sections: list[str]
    exclude_patterns: list[str]


class OutputFormatsConfig(TypedDict, total=False):
    """Output formats configuration."""

    enabled: bool
    per_page: list[str]
    site_wide: list[str]
    options: OutputFormatOptions


# =============================================================================
# Markdown
# =============================================================================


class ASTCacheConfig(TypedDict, total=False):
    """AST cache configuration."""

    persist_tokens: bool


class MarkdownConfig(TypedDict, total=False):
    """Markdown parser configuration."""

    parser: Literal["mistune"]
    toc_depth: str
    ast_cache: ASTCacheConfig


# =============================================================================
# Link Previews
# =============================================================================


class LinkPreviewsConfig(TypedDict, total=False):
    """Link preview (hover card) configuration."""

    enabled: bool
    hover_delay: int
    hide_delay: int
    show_section: bool
    show_reading_time: bool
    show_word_count: bool
    show_date: bool
    show_tags: bool
    max_tags: int
    include_selectors: list[str]
    exclude_selectors: list[str]


# =============================================================================
# Document Application
# =============================================================================


class NavigationConfig(TypedDict, total=False):
    """Document application navigation configuration."""

    view_transitions: bool
    transition_style: Literal["crossfade", "fade-slide", "slide", "none"]
    scroll_restoration: bool


class PrerenderConfig(TypedDict, total=False):
    """Prerender speculation configuration."""

    eagerness: Literal["conservative", "moderate", "eager"]
    patterns: list[str]


class PrefetchConfig(TypedDict, total=False):
    """Prefetch speculation configuration."""

    eagerness: Literal["conservative", "moderate", "eager"]
    patterns: list[str]


class SpeculationConfig(TypedDict, total=False):
    """Speculation Rules configuration."""

    enabled: bool
    prerender: PrerenderConfig
    prefetch: PrefetchConfig
    auto_generate: bool
    exclude_patterns: list[str]


class InteractivityConfig(TypedDict, total=False):
    """Interactive component configuration."""

    tabs: Literal["css_state_machine", "enhanced"]
    accordions: Literal["native_details"]
    modals: Literal["native_dialog"]
    tooltips: Literal["popover"]
    dropdowns: Literal["popover"]
    code_copy: Literal["enhanced"]


class DocumentApplicationConfig(TypedDict, total=False):
    """Document application configuration."""

    enabled: bool
    navigation: NavigationConfig
    speculation: SpeculationConfig
    interactivity: InteractivityConfig


# =============================================================================
# External References (Cross-Project Documentation Links)
# =============================================================================


class ExternalRefIndexConfig(TypedDict, total=False):
    """Configuration for an external Bengal site index."""

    name: str
    url: str
    cache_days: int
    auth_header: str | None


class ExternalRefsConfig(TypedDict, total=False):
    """External references configuration for cross-project linking.

    Enables linking to external documentation using [[ext:project:target]] syntax.

    Example:
        >>> config: ExternalRefsConfig = {
        ...     "enabled": True,
        ...     "export_index": True,  # Generate xref.json
        ...     "templates": {
        ...         "python": "https://docs.python.org/3/library/{module}.html#{name}",
        ...     },
        ...     "indexes": [
        ...         {"name": "kida", "url": "https://kida.dev/xref.json"},
        ...     ],
        ... }

    See: plan/rfc-external-references.md
    """

    enabled: bool
    export_index: bool
    cache_dir: str
    default_cache_days: int
    templates: dict[str, str]
    indexes: list[ExternalRefIndexConfig]


# =============================================================================
# RSS / Sitemap / Search Feature Configs (for bool | dict patterns)
# =============================================================================


class RSSConfig(TypedDict, total=False):
    """RSS feed configuration (when not just bool)."""

    enabled: bool
    title: str
    description: str
    max_items: int


class SitemapConfig(TypedDict, total=False):
    """Sitemap configuration (when not just bool)."""

    enabled: bool
    changefreq: Literal["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"]
    priority: float


# =============================================================================
# Complete Site Configuration
# =============================================================================


class SiteConfig(TypedDict, total=False):
    """Complete site configuration schema.

    This TypedDict provides full type information for Bengal site configuration.
    All fields are optional (total=False) to support partial configuration with
    defaults applied by :func:`bengal.config.defaults.get_default`.

    Categories:
        - Site Metadata: title, baseurl, description, author, language
        - Build Settings: output_dir, parallel, incremental, etc.
        - Static Files: static directory configuration
        - HTML Output: minification and formatting
        - Assets: CSS/JS processing options
        - Theme: appearance and display options
        - Content: processing and display settings
        - Search: Lunr search configuration
        - Pagination: items per page
        - Health Check: validation configuration
        - Features: output generation toggles
        - Graph: knowledge graph settings
        - i18n: internationalization
        - Output Formats: JSON, LLM.txt output
        - Markdown: parser configuration
        - Link Previews: hover card settings
        - Document Application: modern browser features

    Example:
        >>> config: SiteConfig = {
        ...     "title": "My Documentation",
        ...     "baseurl": "/docs/",
        ...     "theme": {"name": "default"},
        ...     "content": {"excerpt_length": 300},
        ... }
    """

    # -------------------------------------------------------------------------
    # Site Metadata
    # -------------------------------------------------------------------------
    title: str
    baseurl: str
    description: str
    author: str
    language: str

    # -------------------------------------------------------------------------
    # Build Settings
    # -------------------------------------------------------------------------
    output_dir: str
    content_dir: str
    assets_dir: str
    templates_dir: str
    parallel: bool
    incremental: bool
    max_workers: int | None
    parallel_graph: bool
    parallel_autodoc: bool
    pretty_urls: bool
    minify_html: bool
    strict_mode: bool
    debug: bool
    validate_build: bool
    validate_templates: bool
    validate_links: bool
    transform_links: bool
    cache_templates: bool
    fast_writes: bool
    fast_mode: bool
    stable_section_references: bool
    min_page_size: int

    # -------------------------------------------------------------------------
    # Nested Configurations
    # -------------------------------------------------------------------------
    static: StaticConfig
    html_output: HtmlOutputConfig
    assets: AssetsConfig
    theme: ThemeConfig
    content: ContentConfig
    search: SearchConfig | bool
    pagination: PaginationConfig
    health_check: HealthCheckConfig | bool
    features: FeaturesConfig
    graph: GraphConfig | bool
    i18n: I18nConfig
    output_formats: OutputFormatsConfig | bool
    markdown: MarkdownConfig
    link_previews: LinkPreviewsConfig | bool
    document_application: DocumentApplicationConfig
    external_refs: ExternalRefsConfig | bool


# =============================================================================
# Type Aliases for Common Patterns
# =============================================================================

# Config value that can be bool (enable/disable) or dict (with options)
type BoolOrDictConfig = bool | dict[str, object]

# Normalized config with guaranteed 'enabled' key
type NormalizedFeatureConfig = dict[str, object]


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Top-level config
    "SiteConfig",
    # Build settings
    "StaticConfig",
    "HtmlOutputConfig",
    "AssetsConfig",
    # Theme
    "ThemeConfig",
    # Content
    "ContentConfig",
    # Search
    "SearchConfig",
    "LunrConfig",
    "SearchUIConfig",
    "SearchAnalyticsConfig",
    # Pagination
    "PaginationConfig",
    # Health check
    "HealthCheckConfig",
    "ConnectivityThresholds",
    "LinkWeights",
    # Features
    "FeaturesConfig",
    # Graph
    "GraphConfig",
    # i18n
    "I18nConfig",
    # Output formats
    "OutputFormatsConfig",
    "OutputFormatOptions",
    # Markdown
    "MarkdownConfig",
    "ASTCacheConfig",
    # Link previews
    "LinkPreviewsConfig",
    # Document application
    "DocumentApplicationConfig",
    "NavigationConfig",
    "SpeculationConfig",
    "PrerenderConfig",
    "PrefetchConfig",
    "InteractivityConfig",
    # RSS/Sitemap
    "RSSConfig",
    "SitemapConfig",
    # External references
    "ExternalRefsConfig",
    "ExternalRefIndexConfig",
    # Type aliases
    "BoolOrDictConfig",
    "NormalizedFeatureConfig",
]
