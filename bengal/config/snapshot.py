"""
Frozen configuration snapshot types.

This module provides immutable, frozen dataclass versions of configuration
that are safe for free-threaded parallel access.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 6)

The ConfigSnapshot is created once at load time and used throughout the build.
It provides:
- Type-safe access to config values via attribute access
- Thread-safe by construction (frozen dataclasses)
- IDE autocomplete support via typed fields
- Single, unified config access pattern (always nested: config.site.title)

Usage:
    >>> snapshot = ConfigSnapshot.from_dict(loaded_config)
    >>> snapshot.site.title
    'My Site'
    >>> snapshot.build.parallel
    True
    >>> snapshot["custom_key"]  # Raw access for custom sections
    {'my_value': 42}

"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class SiteSection:
    """
    Typed accessor for site.* config section.
    
    Attributes:
        title: Site title displayed in navigation and page titles
        baseurl: Base URL prefix for all links (e.g., "/docs/")
        description: Site description for meta tags and feeds
        author: Default author for pages without explicit author
        language: Default language code (e.g., "en", "es")
    """

    title: str = "Bengal Site"
    baseurl: str = ""
    description: str = ""
    author: str = ""
    language: str = "en"


@dataclass(frozen=True, slots=True)
class BuildSection:
    """
    Typed accessor for build.* config section.
    
    Attributes:
        output_dir: Directory where generated site is written
        content_dir: Directory containing markdown content
        assets_dir: Directory containing static assets
        templates_dir: Directory containing templates (theme override)
        parallel: Enable parallel page rendering
        incremental: Enable incremental builds (None = auto-detect)
        max_workers: Maximum worker threads (None = auto-detect from CPU count)
        pretty_urls: Generate /page/ instead of /page.html
        minify_html: Minify HTML output
        strict_mode: Fail on warnings instead of just logging
        debug: Enable debug output
        validate_build: Run validators after build
        validate_templates: Proactive template syntax validation
        validate_links: Validate internal links
        transform_links: Transform markdown links to permalinks
        fast_writes: Use faster but less safe file writes
        fast_mode: Skip non-essential processing for speed
        stable_section_references: Use stable section references
        min_page_size: Minimum page size for parallel processing
    """

    output_dir: str = "public"
    content_dir: str = "content"
    assets_dir: str = "assets"
    templates_dir: str = "templates"
    parallel: bool = True
    incremental: bool | None = None
    max_workers: int | None = None
    parallel_graph: bool = True
    parallel_autodoc: bool = True
    pretty_urls: bool = True
    minify_html: bool = True
    strict_mode: bool = False
    debug: bool = False
    validate_build: bool = True
    validate_templates: bool = False
    validate_links: bool = True
    transform_links: bool = True
    fast_writes: bool = False
    fast_mode: bool = False
    stable_section_references: bool = True
    min_page_size: int = 1000


@dataclass(frozen=True, slots=True)
class DevSection:
    """
    Typed accessor for dev.* config section.
    
    Attributes:
        cache_templates: Cache compiled templates in dev server
        watch_backend: Watch for backend changes in dev server
        live_reload: Enable live reload in dev server
        port: Dev server port number
    """

    cache_templates: bool = True
    watch_backend: bool = True
    live_reload: bool = True
    port: int = 8000


@dataclass(frozen=True, slots=True)
class ThemeSection:
    """
    Typed accessor for theme.* config section.
    
    Attributes:
        name: Theme name (must exist in themes/)
        default_appearance: Default color scheme (light/dark/system)
        default_palette: Default color palette name
        features: List of enabled theme features
        show_reading_time: Show reading time on pages
        show_author: Show author on pages
        show_prev_next: Show prev/next navigation
        show_children_default: Show child pages by default
        show_excerpts_default: Show excerpts by default
        max_tags_display: Maximum tags to display on page
        popular_tags_count: Number of popular tags to show
    """

    name: str = "default"
    default_appearance: Literal["light", "dark", "system"] = "system"
    default_palette: str = "snow-lynx"
    features: tuple[str, ...] = ()
    show_reading_time: bool = True
    show_author: bool = True
    show_prev_next: bool = True
    show_children_default: bool = True
    show_excerpts_default: bool = True
    max_tags_display: int = 10
    popular_tags_count: int = 20


@dataclass(frozen=True, slots=True)
class ContentSection:
    """
    Typed accessor for content.* config section.
    
    Attributes:
        default_type: Default page type for content
        excerpt_length: Maximum excerpt length in characters
        summary_length: Maximum summary length for meta tags
        reading_speed: Words per minute for reading time calculation
        related_count: Number of related pages to show
        related_threshold: Minimum similarity score for related pages
        toc_depth: Maximum heading depth for table of contents
        toc_min_headings: Minimum headings required to show TOC
        toc_style: TOC style (nested or flat)
        sort_pages_by: Default sort field for page lists
        sort_order: Default sort order (asc/desc)
    """

    default_type: str = "doc"
    excerpt_length: int = 200
    summary_length: int = 160
    reading_speed: int = 200
    related_count: int = 5
    related_threshold: float = 0.25
    toc_depth: int = 4
    toc_min_headings: int = 2
    toc_style: Literal["nested", "flat"] = "nested"
    sort_pages_by: Literal["weight", "date", "title", "modified"] = "weight"
    sort_order: Literal["asc", "desc"] = "asc"


@dataclass(frozen=True, slots=True)
class FeaturesSection:
    """
    Typed accessor for features.* config section.
    
    Controls which output formats and features are generated.
    """

    rss: bool = True
    sitemap: bool = True
    search: bool = True
    json: bool = True
    llm_txt: bool = True


@dataclass(frozen=True, slots=True)
class AssetsSection:
    """
    Typed accessor for assets.* config section.
    
    Attributes:
        minify: Minify CSS/JS assets
        optimize: Optimize images
        fingerprint: Add content hash to asset filenames
        pipeline: Enable asset pipeline processing
    """

    minify: bool = True
    optimize: bool = True
    fingerprint: bool = True
    pipeline: bool = False


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    """
    Frozen, typed configuration snapshot.
    
    Created once at load time, used throughout build.
    Thread-safe by construction (frozen dataclass).
    
    RFC: Snapshot-Enabled v2 Opportunities (Opportunity 6)
    
    Access patterns:
        >>> config.site.title          # Typed attribute access
        'My Site'
        >>> config.build.parallel      # Boolean fields
        True
        >>> config["custom"]           # Raw access for custom sections
        {'my_key': 'my_value'}
    """

    # Typed sections
    site: SiteSection = field(default_factory=SiteSection)
    build: BuildSection = field(default_factory=BuildSection)
    dev: DevSection = field(default_factory=DevSection)
    theme: ThemeSection = field(default_factory=ThemeSection)
    content: ContentSection = field(default_factory=ContentSection)
    features: FeaturesSection = field(default_factory=FeaturesSection)
    assets: AssetsSection = field(default_factory=AssetsSection)

    # Raw access for custom/dynamic keys
    _raw: MappingProxyType[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for custom sections."""
        return self._raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Safe access for optional keys."""
        return self._raw.get(key, default)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in raw config."""
        return key in self._raw

    @property
    def params(self) -> MappingProxyType[str, Any]:
        """Site params shortcut (template compatibility)."""
        params = self._raw.get("params")
        if isinstance(params, dict):
            return MappingProxyType(params)
        if isinstance(params, MappingProxyType):
            return params
        return MappingProxyType({})

    @property
    def raw(self) -> MappingProxyType[str, Any]:
        """Raw config dict for serialization/debugging."""
        return self._raw

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfigSnapshot:
        """
        Create frozen config snapshot from loaded dict.
        
        Applies defaults and creates typed section objects.
        
        Args:
            data: Raw configuration dictionary (from UnifiedConfigLoader)
            
        Returns:
            Frozen ConfigSnapshot with typed sections
        """
        from bengal.config.defaults import DEFAULTS
        from bengal.config.merge import deep_merge

        # Merge with defaults
        merged = deep_merge({}, DEFAULTS)
        merged = deep_merge(merged, data)

        # Extract site section
        site_data = merged.get("site", {})
        if isinstance(site_data, dict):
            site = SiteSection(
                title=str(site_data.get("title", "Bengal Site")),
                baseurl=str(site_data.get("baseurl", "")),
                description=str(site_data.get("description", "")),
                author=str(site_data.get("author", "")),
                language=str(site_data.get("language", "en")),
            )
        else:
            site = SiteSection()

        # Extract build section
        build_data = merged.get("build", {})
        if isinstance(build_data, dict):
            build = BuildSection(
                output_dir=str(build_data.get("output_dir", "public")),
                content_dir=str(build_data.get("content_dir", "content")),
                assets_dir=str(build_data.get("assets_dir", "assets")),
                templates_dir=str(build_data.get("templates_dir", "templates")),
                parallel=bool(build_data.get("parallel", True)),
                incremental=build_data.get("incremental"),
                max_workers=build_data.get("max_workers"),
                parallel_graph=bool(build_data.get("parallel_graph", True)),
                parallel_autodoc=bool(build_data.get("parallel_autodoc", True)),
                pretty_urls=bool(build_data.get("pretty_urls", True)),
                minify_html=bool(build_data.get("minify_html", True)),
                strict_mode=bool(build_data.get("strict_mode", False)),
                debug=bool(build_data.get("debug", False)),
                validate_build=bool(build_data.get("validate_build", True)),
                validate_templates=bool(build_data.get("validate_templates", False)),
                validate_links=bool(build_data.get("validate_links", True)),
                transform_links=bool(build_data.get("transform_links", True)),
                fast_writes=bool(build_data.get("fast_writes", False)),
                fast_mode=bool(build_data.get("fast_mode", False)),
                stable_section_references=bool(
                    build_data.get("stable_section_references", True)
                ),
                min_page_size=int(build_data.get("min_page_size", 1000)),
            )
        else:
            build = BuildSection()

        # Extract dev section
        dev_data = merged.get("dev", {})
        if isinstance(dev_data, dict):
            dev = DevSection(
                cache_templates=bool(dev_data.get("cache_templates", True)),
                watch_backend=bool(dev_data.get("watch_backend", True)),
                live_reload=bool(dev_data.get("live_reload", True)),
                port=int(dev_data.get("port", 8000)),
            )
        else:
            dev = DevSection()

        # Extract theme section
        theme_data = merged.get("theme", {})
        if isinstance(theme_data, dict):
            features = theme_data.get("features", [])
            if isinstance(features, list):
                features_tuple = tuple(str(f) for f in features)
            else:
                features_tuple = ()

            appearance = theme_data.get("default_appearance", "system")
            if appearance not in ("light", "dark", "system"):
                appearance = "system"

            theme = ThemeSection(
                name=str(theme_data.get("name", "default")),
                default_appearance=appearance,  # type: ignore[arg-type]
                default_palette=str(theme_data.get("default_palette", "snow-lynx")),
                features=features_tuple,
                show_reading_time=bool(theme_data.get("show_reading_time", True)),
                show_author=bool(theme_data.get("show_author", True)),
                show_prev_next=bool(theme_data.get("show_prev_next", True)),
                show_children_default=bool(theme_data.get("show_children_default", True)),
                show_excerpts_default=bool(theme_data.get("show_excerpts_default", True)),
                max_tags_display=int(theme_data.get("max_tags_display", 10)),
                popular_tags_count=int(theme_data.get("popular_tags_count", 20)),
            )
        else:
            theme = ThemeSection()

        # Extract content section
        content_data = merged.get("content", {})
        if isinstance(content_data, dict):
            toc_style = content_data.get("toc_style", "nested")
            if toc_style not in ("nested", "flat"):
                toc_style = "nested"

            sort_by = content_data.get("sort_pages_by", "weight")
            if sort_by not in ("weight", "date", "title", "modified"):
                sort_by = "weight"

            sort_order = content_data.get("sort_order", "asc")
            if sort_order not in ("asc", "desc"):
                sort_order = "asc"

            content = ContentSection(
                default_type=str(content_data.get("default_type", "doc")),
                excerpt_length=int(content_data.get("excerpt_length", 200)),
                summary_length=int(content_data.get("summary_length", 160)),
                reading_speed=int(content_data.get("reading_speed", 200)),
                related_count=int(content_data.get("related_count", 5)),
                related_threshold=float(content_data.get("related_threshold", 0.25)),
                toc_depth=int(content_data.get("toc_depth", 4)),
                toc_min_headings=int(content_data.get("toc_min_headings", 2)),
                toc_style=toc_style,  # type: ignore[arg-type]
                sort_pages_by=sort_by,  # type: ignore[arg-type]
                sort_order=sort_order,  # type: ignore[arg-type]
            )
        else:
            content = ContentSection()

        # Extract features section
        features_data = merged.get("features", {})
        if isinstance(features_data, dict):
            features_section = FeaturesSection(
                rss=bool(features_data.get("rss", True)),
                sitemap=bool(features_data.get("sitemap", True)),
                search=bool(features_data.get("search", True)),
                json=bool(features_data.get("json", True)),
                llm_txt=bool(features_data.get("llm_txt", True)),
            )
        else:
            features_section = FeaturesSection()

        # Extract assets section
        assets_data = merged.get("assets", {})
        if isinstance(assets_data, dict):
            assets = AssetsSection(
                minify=bool(assets_data.get("minify", True)),
                optimize=bool(assets_data.get("optimize", True)),
                fingerprint=bool(assets_data.get("fingerprint", True)),
                pipeline=bool(assets_data.get("pipeline", False)),
            )
        else:
            assets = AssetsSection()

        return cls(
            site=site,
            build=build,
            dev=dev,
            theme=theme,
            content=content,
            features=features_section,
            assets=assets,
            _raw=MappingProxyType(merged),
        )


__all__ = [
    "ConfigSnapshot",
    "SiteSection",
    "BuildSection",
    "DevSection",
    "ThemeSection",
    "ContentSection",
    "FeaturesSection",
    "AssetsSection",
]
