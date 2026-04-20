"""
Site package for Bengal SSG.

Provides the Site class — the central container for all content (pages,
sections, assets) and coordinator of the build process.

Public API:
Site: Main site dataclass with discovery, build, and serve capabilities

Creation:
Site.from_config(path): Load from bengal.toml (recommended)
Site.for_testing(): Minimal instance for unit tests
Site(root_path, config): Direct instantiation (advanced)

Package Structure:
- factory.py:    Factory functions (from_config, for_testing)
- versioning.py: VersionService (composed)
- context.py:    SiteContext Protocol — read-only surface for Page/Section

Example:
    from bengal.core import Site

    site = Site.from_config(Path('/path/to/site'))
    site.build(parallel=True, incremental=True)

Related Packages:
- bengal.orchestration.site_runner: Build/serve/clean lifecycle (canonical)
- bengal.orchestration.build:       Build orchestration
- bengal.rendering.template_engine: Template rendering
- bengal.cache.build_cache:         Build state persistence

"""

from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Self, cast

from bengal.config.hash import compute_config_hash
from bengal.config.utils import unwrap_config
from bengal.core.cascade_snapshot import CascadeSnapshot, build_cascade_from_content
from bengal.core.diagnostics import DiagnosticsSink
from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.page_cache import PageCacheManager
from bengal.core.registry import ContentRegistry
from bengal.core.theme import Theme
from bengal.core.url_ownership import URLRegistry
from bengal.core.version import Version, VersionConfig
from bengal.icons import resolver as icon_resolver
from bengal.services.config import ConfigService

from .factory import for_testing, from_config
from .versioning import VersionService

if TYPE_CHECKING:
    from datetime import datetime

    from bengal.assets.manifest import AssetManifest
    from bengal.cache.paths import BengalPaths
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.config.accessor import Config
    from bengal.core.asset import Asset
    from bengal.core.menu import MenuBuilder, MenuItem
    from bengal.orchestration.build.inputs import BuildInput
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.build_state import BuildState
    from bengal.orchestration.stats.models import BuildStats
    from bengal.parsing.base import BaseMarkdownParser
    from bengal.protocols.core import PageLike, SectionLike, SiteLike
    from bengal.utils.primitives.dotdict import DotDict


# Thread-safe output lock for parallel processing.
_print_lock = Lock()


@dataclass
class Site:
    """
    Represents the entire website and orchestrates the build process.

    Prefer ``Site.from_config(root_path)`` for production/CLI use; direct
    instantiation (``Site(root_path=..., config=...)``) is for tests and
    programmatic config manipulation. ``Site.for_testing()`` builds a
    minimal instance suitable for unit tests.
    """

    root_path: Path
    config: Config | dict[str, Any] = field(default_factory=dict)
    pages: list[PageLike] = field(default_factory=list)
    sections: list[SectionLike] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    theme: str | None = None
    output_dir: Path = field(default_factory=lambda: Path("public"))
    build_time: datetime | None = None
    taxonomies: dict[str, dict[str, Any]] = field(default_factory=dict)
    xref_index: dict[str, Any] = field(default_factory=dict)
    menu: dict[str, list[MenuItem]] = field(default_factory=dict)
    menu_builders: dict[str, MenuBuilder] = field(default_factory=dict)
    menu_localized: dict[str, dict[str, list[MenuItem]]] = field(default_factory=dict)
    menu_builders_localized: dict[str, dict[str, MenuBuilder]] = field(default_factory=dict)
    current_language: str | None = None
    data: DotDict = field(default_factory=dict)
    dev_mode: bool = False

    version_config: VersionConfig = field(default_factory=VersionConfig)
    current_version: Version | None = None

    _version_service: VersionService | None = field(default=None, repr=False, init=False)
    page_cache: PageCacheManager = field(default=None, repr=False, init=False)  # type: ignore[assignment]
    _theme_obj: Theme | None = field(default=None, repr=False, init=False)
    _query_registry: QueryIndexRegistry | None = field(default=None, repr=False, init=False)
    url_registry: URLRegistry = field(default_factory=URLRegistry, init=False)
    _registry: ContentRegistry | None = field(default=None, repr=False, init=False)
    _current_build_state: BuildState | None = field(default=None, repr=False, init=False)
    _config_hash: str | None = field(default=None, repr=False, init=False)
    _paths: BengalPaths | None = field(default=None, repr=False, init=False)
    _description_override: str | None = field(default=None, repr=False, init=False)
    config_service: ConfigService = field(default=None, repr=False, init=False)  # type: ignore[assignment]
    link_registry: Any | None = field(default=None, repr=False, init=False)

    # Dynamic runtime attributes (set by various orchestrators)
    diagnostics: DiagnosticsSink | None = field(default=None, repr=False, init=False)
    _dev_menu_metadata: dict[str, Any] | None = field(default=None, repr=False, init=False)
    _page_lookup_maps: dict[str, dict[str, PageLike]] | None = field(
        default=None, repr=False, init=False
    )
    _last_build_stats: dict[str, Any] | None = field(default=None, repr=False, init=False)
    _template_parser: BaseMarkdownParser | None = field(default=None, repr=False, init=False)

    # Runtime caches — legacy fallback fields. Primary path is BuildState
    # (fresh each build); these fall back when running outside a build context
    # (tests, CLI health checks). Consumers check BuildState first via getattr.
    _asset_manifest_previous: AssetManifest | None = field(default=None, repr=False, init=False)
    _asset_manifest_fallbacks_global: set[str] = field(default_factory=set, repr=False, init=False)
    _asset_manifest_fallbacks_lock: Lock | None = field(default=None, repr=False, init=False)
    _init_lock: Lock = field(default_factory=Lock, repr=False, init=False)
    _bengal_theme_chain_cache: dict[str, Any] | None = field(default=None, repr=False, init=False)
    _bengal_template_dirs_cache: dict[str, Any] | None = field(default=None, repr=False, init=False)
    _bengal_template_metadata_cache: dict[str, Any] | None = field(
        default=None, repr=False, init=False
    )
    _discovery_breakdown_ms: dict[str, float] | None = field(default=None, repr=False, init=False)
    features_detected: set[str] = field(default_factory=set, repr=False, init=False)
    _cascade_snapshot: CascadeSnapshot | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        """Initialize site from configuration."""
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)

        # Ensure root_path is always absolute to eliminate CWD-dependent behavior.
        if not self.root_path.is_absolute():
            self.root_path = self.root_path.resolve()

        # Theme name resolution priority:
        # 1. [site] section with theme key
        # 2. Top-level theme string (legacy)
        # 3. Default to "default"
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and site_section.get("theme"):
            self.theme = site_section.get("theme")
        elif hasattr(site_section, "theme") and site_section.theme:
            self.theme = site_section.theme
        else:
            theme_value = self.config.get("theme")
            if isinstance(theme_value, str):
                self.theme = theme_value
            elif (isinstance(theme_value, dict) and theme_value.get("name")) or (
                hasattr(theme_value, "get") and theme_value.get("name")
            ):
                self.theme = str(theme_value.get("name"))
            elif hasattr(theme_value, "name") and theme_value.name:
                self.theme = str(theme_value.name)
            else:
                self.theme = "default"

        config_dict = unwrap_config(self.config)
        self._theme_obj = Theme.from_config(
            config_dict,
            root_path=self.root_path,
            diagnostics_site=self,
        )

        icon_resolver.initialize(cast("SiteLike", self))

        # Resolve output_dir from build section
        output_dir_str: str | None = None
        if hasattr(self.config, "build"):
            build_attr = self.config.build
            output_dir_str = getattr(build_attr, "output_dir", "public")
        else:
            build_section = self.config.get("build", {})
            if isinstance(build_section, dict):
                output_dir_str = build_section.get("output_dir", "public")
            else:
                output_dir_str = self.config.get("output_dir", "public")

        if output_dir_str:
            self.output_dir = Path(output_dir_str)

        if not self.output_dir.is_absolute():
            self.output_dir = self.root_path / self.output_dir

        from bengal.services.data import scan_data_directory
        from bengal.utils.primitives.dotdict import DotDict, wrap_data

        data_dict, _source_files = scan_data_directory(self.root_path)
        self.data = wrap_data(data_dict) if data_dict else DotDict()
        self._compute_config_hash()

        self.config_service = ConfigService.from_config(self.config, self.root_path)

        self.page_cache = PageCacheManager(lambda: self.pages)

        self.version_config = VersionConfig.from_config(config_dict)
        self._version_service = VersionService(self.version_config)
        if self.version_config.enabled:
            emit_diagnostic(
                self,
                "debug",
                "versioning_enabled",
                versions=[v.id for v in self.version_config.versions],
                latest=self.version_config.latest_version.id
                if self.version_config.latest_version
                else None,
            )

        if self._asset_manifest_fallbacks_lock is None:
            self._asset_manifest_fallbacks_lock = Lock()

        if not hasattr(self, "url_registry") or self.url_registry is None:
            self.url_registry = URLRegistry()

        if self._registry is None:
            self._registry = ContentRegistry()
            self._registry.set_root_path(self.root_path)
            self._registry.url_ownership = self.url_registry

    # =========================================================================
    # SECTION REGISTRY
    # =========================================================================

    @property
    def registry(self) -> ContentRegistry:
        """
        Content registry for O(1) page/section lookups.

        Initialized lazily on first access.
        """
        if self._registry is None:
            with self._init_lock:
                if self._registry is None:
                    _reg = ContentRegistry()
                    _reg.set_root_path(self.root_path)
                    _reg.url_ownership = self.url_registry
                    self._registry = _reg
        return self._registry

    def get_section_by_path(self, path: Path | str) -> SectionLike | None:
        """Look up a section by its path (O(1) operation)."""
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            content_relative = self.root_path / "content" / path
            if content_relative.exists():
                path = content_relative
            else:
                root_relative = self.root_path / path
                if root_relative.exists():
                    path = root_relative

        section = self.registry.get_section(path)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_registry",
                path=str(path),
                registry_size=self.registry.section_count,
            )

        return section

    def get_section_by_url(self, url: str) -> SectionLike | None:
        """Look up a section by its relative URL (O(1) operation)."""
        section = self.registry.get_section_by_url(url)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_url_registry",
                url=url,
                registry_size=self.registry.section_count,
            )

        return section

    def register_sections(self) -> None:
        """
        Build the section registry for path-based and URL-based lookups.

        Populates ContentRegistry with all sections (recursive). Must be called
        after discover_content().
        """
        start = time.time()

        self.registry._sections_by_path.clear()
        self.registry._sections_by_url.clear()

        for section in self.sections:
            self.registry.register_sections_recursive(section)

        self.registry.increment_epoch()

        elapsed_ms = (time.time() - start) * 1000

        emit_diagnostic(
            self,
            "debug",
            "section_registry_built",
            sections=self.registry.section_count,
            elapsed_ms=f"{elapsed_ms:.2f}",
            avg_us_per_section=f"{(elapsed_ms * 1000 / self.registry.section_count):.2f}"
            if self.registry.section_count
            else "0",
        )

    # =========================================================================
    # CONTENT DISCOVERY
    # =========================================================================

    def discover_content(self, content_dir: Path | None = None) -> None:
        """
        Discover all content (pages, sections) in the content directory.

        Scans the content directory recursively, creating Page and Section
        objects for all markdown files and organizing them into a hierarchy.
        """
        if content_dir is None:
            content_dir = self.root_path / "content"

        if not content_dir.exists():
            build_cfg = self.config.get("build", {}) if isinstance(self.config, dict) else {}
            if build_cfg.get("strict_mode", False):
                from bengal.errors import BengalConfigError, ErrorCode

                raise BengalConfigError(
                    f"Content directory not found: {content_dir}\n"
                    f"Strict mode is enabled — missing content directory is an error.",
                    code=ErrorCode.C003,
                    suggestion=f"Create the directory at '{content_dir}', or check "
                    f"'build.content_dir' in your config",
                )
            emit_diagnostic(self, "warning", "content_dir_not_found", path=str(content_dir))
            import warnings

            warnings.warn(
                f"Content directory not found: {content_dir} — "
                f"site will have zero pages. Check 'build.content_dir' in your config.",
                stacklevel=2,
            )
            return

        from bengal.collections import load_collections
        from bengal.content.discovery.content_discovery import ContentDiscovery

        collections = load_collections(self.root_path)

        build_config = self.config.get("build", {}) if isinstance(self.config, dict) else {}
        strict_validation = build_config.get("strict_collections", False)

        discovery = ContentDiscovery(
            content_dir,
            site=self,
            collections=collections,
            strict_validation=strict_validation,
        )
        self.sections, self.pages = discovery.discover()

        self.register_sections()
        self._setup_page_references()
        self._validate_page_section_references()
        self._apply_cascades()
        self._set_output_paths()
        self._detect_features()

    def _set_output_paths(self) -> None:
        """Set output paths for all discovered pages."""
        from bengal.utils.paths.url_strategy import URLStrategy

        for page in self.pages:
            if page.output_path:
                continue

            page.output_path = URLStrategy.compute_regular_page_output_path(
                page, cast("SiteLike", self)
            )

            if hasattr(self, "url_registry") and self.url_registry:
                try:
                    url = URLStrategy.url_from_output_path(page.output_path, cast("SiteLike", self))
                    source = str(getattr(page, "source_path", page.title))
                    version = getattr(page, "version", None)
                    lang = getattr(page, "lang", None)
                    self.url_registry.claim(
                        url=url,
                        owner="content",
                        source=source,
                        priority=100,
                        version=version,
                        lang=lang,
                    )
                except Exception:  # noqa: S110
                    pass

    def _detect_features(self) -> None:
        """Detect CSS-requiring features in page content (mermaid, tables, etc.)."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()

        for page in self.pages:
            features = detector.detect_features_in_page(page)
            _bs = getattr(self, "_current_build_state", None)
            target = _bs.features_detected if _bs is not None else self.features_detected
            target.update(features)

        config = self.config
        _bs = getattr(self, "_current_build_state", None)
        target = _bs.features_detected if _bs is not None else self.features_detected

        if config.get("search", {}).get("enabled", False):
            target.add("search")

        if config.get("graph", {}).get("enabled", False):
            target.add("graph")

    # =========================================================================
    # ASSET DISCOVERY
    # =========================================================================

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.

        Theme assets are discovered first (lower priority), then site assets
        (higher priority, can override theme assets).
        """
        from bengal.content.discovery.asset_discovery import AssetDiscovery
        from bengal.services.theme import get_theme_assets_chain

        self.assets = []

        if self.theme:
            for theme_dir in get_theme_assets_chain(self.root_path, self.theme):
                if theme_dir and theme_dir.exists():
                    theme_discovery = AssetDiscovery(theme_dir)
                    self.assets.extend(theme_discovery.discover())

        self._discover_provider_assets()

        if assets_dir is None:
            assets_dir = self.root_path / "assets"

        if assets_dir.exists():
            emit_diagnostic(self, "debug", "discovering_site_assets", path=str(assets_dir))
            site_discovery = AssetDiscovery(assets_dir)
            self.assets.extend(site_discovery.discover())
        elif not self.assets:
            emit_diagnostic(self, "warning", "assets_dir_not_found", path=str(assets_dir))

        if self.assets:
            dedup: dict[str, Asset] = {}
            order: list[str] = []
            for asset in self.assets:
                key = str(asset.output_path) if asset.output_path else str(asset.source_path.name)
                if key in dedup:
                    dedup[key] = asset
                else:
                    dedup[key] = asset
                    order.append(key)
            self.assets = [dedup[k] for k in order]

    def _discover_provider_assets(self) -> None:
        """Discover assets from theme library providers, namespaced by prefix."""
        from bengal.content.discovery.asset_discovery import AssetDiscovery
        from bengal.core.theme.providers import get_provider_asset_dirs, resolve_theme_providers
        from bengal.core.theme.resolution import resolve_theme_chain

        if not self.theme:
            return

        theme_chain = resolve_theme_chain(self.root_path, self.theme)
        providers = resolve_theme_providers(self.root_path, theme_chain)
        if not providers:
            return

        for prefix, asset_root in get_provider_asset_dirs(providers):
            discovery = AssetDiscovery(asset_root)
            for asset in discovery.discover():
                if asset.output_path:
                    asset.output_path = Path(prefix) / asset.output_path
                self.assets.append(asset)

    # =========================================================================
    # PAGE / SECTION REFERENCES
    # =========================================================================

    def _setup_page_references(self) -> None:
        """
        Set up page references for navigation (next, prev, parent, etc.).

        Sets _site and _section references on all pages. Must be called after
        content discovery and section registry building, but before cascade
        application.
        """
        for page in self.pages:
            page._site = self

        for section in self.sections:
            section._site = self

            if section.index_page:
                section.index_page._section = section

            for page in section.pages:
                page._section = section

            self._setup_section_references(section)

    def _setup_section_references(self, section: SectionLike) -> None:
        """Recursively set up references for a section and its subsections."""
        for subsection in section.subsections:
            subsection._site = self

            if subsection.index_page:
                subsection.index_page._section = subsection

            for page in subsection.pages:
                page._section = subsection

            self._setup_section_references(subsection)

    def _apply_cascades(self) -> None:
        """
        Build cascade snapshot for view-based resolution.

        Section _index.md files can define metadata that automatically applies to all
        descendant pages.
        """
        self.build_cascade_snapshot()

    # =========================================================================
    # CASCADE SNAPSHOT
    # =========================================================================

    @property
    def cascade(self) -> CascadeSnapshot:
        """
        Get the immutable cascade snapshot for this build.

        Resolution order:
            1. BuildState.cascade_snapshot (during builds — structurally fresh)
            2. Local _cascade_snapshot (outside builds — tests, CLI)
            3. Empty snapshot (graceful fallback)

        Returns:
            CascadeSnapshot instance (empty if not yet built)
        """
        if self._current_build_state is not None:
            snapshot = self._current_build_state.cascade_snapshot
            if snapshot is not None:
                return snapshot

        if self._cascade_snapshot is not None:
            return self._cascade_snapshot

        return CascadeSnapshot.empty()

    def build_cascade_snapshot(self) -> None:
        """
        Build the immutable cascade snapshot from all sections.

        Delegates to bengal.core.cascade_snapshot.build_cascade_from_content()
        and stores the result on BuildState (primary) and _cascade_snapshot (fallback).
        """
        snapshot = build_cascade_from_content(self.root_path, self.sections, self.pages)
        snapshot = dataclasses.replace(snapshot)  # New id for cache invalidation

        if self._current_build_state is not None:
            self._current_build_state.cascade_snapshot = snapshot

        self._cascade_snapshot = snapshot

    # =========================================================================
    # CONFIG HASH + INDEXES
    # =========================================================================

    def _compute_config_hash(self) -> None:
        """Compute and cache the configuration hash."""
        self._config_hash = compute_config_hash(self.config)
        emit_diagnostic(
            self,
            "debug",
            "config_hash_computed",
            hash=self._config_hash[:8] if self._config_hash else "none",
        )

    @property
    def indexes(self) -> QueryIndexRegistry:
        """Access to query indexes for O(1) page lookups."""
        if self._query_registry is None:
            with self._init_lock:
                if self._query_registry is None:
                    from bengal.cache.query_index_registry import QueryIndexRegistry

                    self._query_registry = QueryIndexRegistry(
                        cast("SiteLike", self), self.config_service.paths.indexes_dir
                    )
        return self._query_registry

    # =========================================================================
    # PAGE COLLECTIONS + ROOT SECTION
    # =========================================================================
    # Content slices of the site. Thin @property over PageCacheManager — these
    # are domain facets (what the site contains), not implementation details.

    @property
    def regular_pages(self) -> list[PageLike]:
        """Regular content pages (excludes generated taxonomy/archive pages)."""
        return self.page_cache.regular_pages

    @property
    def generated_pages(self) -> list[PageLike]:
        """Generated pages (taxonomy, archive, pagination)."""
        return self.page_cache.generated_pages

    @property
    def listable_pages(self) -> list[PageLike]:
        """Pages eligible for public listings (excludes hidden/draft)."""
        return self.page_cache.listable_pages

    def get_page_path_map(self) -> dict[str, PageLike]:
        """Cached string-keyed page lookup map for O(1) resolution."""
        return self.page_cache.get_page_path_map()

    @property
    def page_by_source_path(self) -> dict[Path, PageLike]:
        """O(1) page lookup by source Path (shared across orchestrators)."""
        return self.page_cache.page_by_source_path

    @property
    def root_section(self) -> SectionLike:
        """Root section of the content tree (first parentless section)."""
        for section in self.sections:
            if section.parent is None:
                return section
        child_ids = {id(sub) for s in self.sections for sub in s.subsections}
        for section in self.sections:
            if id(section) not in child_ids:
                return section
        msg = "No root section found — site has no sections"
        raise ValueError(msg)

    def invalidate_page_caches(self) -> None:
        """Clear all page caches. Call after adding/removing pages."""
        self.page_cache.invalidate()

    def invalidate_regular_pages_cache(self) -> None:
        """Clear only the regular_pages cache."""
        self.page_cache.invalidate_regular()

    # =========================================================================
    # DOMAIN FACETS (config-derived)
    # =========================================================================
    # Thin @property over ConfigService. These are user-facing site identity —
    # template authors address them directly (site.title, site.logo). They
    # pass the greenfield-design test: a Site has a title, has a logo, etc.

    @property
    def title(self) -> str | None:
        """Site title from configuration."""
        return self.config_service.title

    @property
    def description(self) -> str | None:
        """Site description, respecting runtime overrides."""
        if self._description_override is not None:
            return self._description_override
        return self.config_service.description

    @description.setter
    def description(self, value: str | None) -> None:
        """Allow runtime override of site description for generated outputs."""
        self._description_override = value

    @property
    def baseurl(self) -> str | None:
        """Site baseurl from configuration."""
        return self.config_service.baseurl

    @property
    def author(self) -> str | None:
        """Site author from configuration."""
        return self.config_service.author

    @property
    def content_dir(self) -> Path:
        """Path to the content directory."""
        return self.config_service.content_dir

    @property
    def params(self) -> dict[str, Any]:
        """Site-level custom parameters from [params] config section."""
        return self.config_service.params

    @property
    def logo(self) -> str:
        """Logo URL from config (checks multiple locations)."""
        return self.config_service.logo

    @property
    def logo_image(self) -> str | None:
        """Logo image path from site config."""
        return self.config_service.logo_image

    @property
    def logo_text(self) -> str | None:
        """Logo text from site config."""
        return self.config_service.logo_text

    @property
    def favicon(self) -> str | None:
        """Favicon path from site config."""
        return self.config_service.favicon

    @property
    def theme_config(self) -> Theme:
        """Theme configuration object (prefers in-memory override if set)."""
        if self._theme_obj is not None:
            return self._theme_obj
        return self.config_service.theme_config

    # =========================================================================
    # NORMALIZED CONFIG BLOCKS
    # =========================================================================
    # Real normalization of structured config sections. Returns frozen dicts
    # regardless of input shape (True/False/None/dict).

    @property
    def build_badge(self) -> dict[str, Any]:
        """
        Normalized build badge configuration.

        Handles all supported formats:
        - None/False: disabled
        - True: enabled with defaults
        - dict: enabled with custom settings
        """
        _defaults = {
            "dir_name": "bengal",
            "label": "built in",
            "label_color": "#555",
            "message_color": "#4c1d95",
        }
        value = self.config.get("build_badge")

        if value is None or value is False:
            return {"enabled": False, **_defaults}
        if value is True:
            return {"enabled": True, **_defaults}
        if isinstance(value, dict):
            return {
                "enabled": bool(value.get("enabled", True)),
                "dir_name": str(value.get("dir_name", _defaults["dir_name"])),
                "label": str(value.get("label", _defaults["label"])),
                "label_color": str(value.get("label_color", _defaults["label_color"])),
                "message_color": str(value.get("message_color", _defaults["message_color"])),
            }
        return {"enabled": False, **_defaults}

    @property
    def document_application(self) -> dict[str, Any]:
        """
        Normalized document application configuration.

        Enables modern browser-native features: View Transitions API,
        Speculation Rules, native dialogs, CSS state machines.
        """
        from bengal.config.defaults import DEFAULTS

        defaults = DEFAULTS["document_application"]
        value = self.config.get("document_application", {})

        if not isinstance(value, dict):
            return {
                "enabled": False,
                "navigation": dict(defaults["navigation"]),
                "speculation": dict(defaults["speculation"]),
                "interactivity": dict(defaults["interactivity"]),
                "features": {},
            }

        navigation = value.get("navigation", {})
        speculation = value.get("speculation", {})
        interactivity = value.get("interactivity", {})

        return {
            "enabled": bool(value.get("enabled", defaults["enabled"])),
            "navigation": {
                "view_transitions": navigation.get(
                    "view_transitions", defaults["navigation"]["view_transitions"]
                ),
                "transition_style": navigation.get(
                    "transition_style", defaults["navigation"]["transition_style"]
                ),
                "scroll_restoration": navigation.get(
                    "scroll_restoration", defaults["navigation"]["scroll_restoration"]
                ),
            },
            "speculation": {
                "enabled": speculation.get("enabled", defaults["speculation"]["enabled"]),
                "prerender": {
                    "eagerness": speculation.get("prerender", {}).get(
                        "eagerness", defaults["speculation"]["prerender"]["eagerness"]
                    ),
                    "patterns": speculation.get("prerender", {}).get(
                        "patterns", defaults["speculation"]["prerender"]["patterns"]
                    ),
                },
                "prefetch": {
                    "eagerness": speculation.get("prefetch", {}).get(
                        "eagerness", defaults["speculation"]["prefetch"]["eagerness"]
                    ),
                    "patterns": speculation.get("prefetch", {}).get(
                        "patterns", defaults["speculation"]["prefetch"]["patterns"]
                    ),
                },
                "auto_generate": speculation.get(
                    "auto_generate", defaults["speculation"]["auto_generate"]
                ),
                "exclude_patterns": speculation.get(
                    "exclude_patterns", defaults["speculation"]["exclude_patterns"]
                ),
            },
            "interactivity": {
                "tabs": interactivity.get("tabs", defaults["interactivity"]["tabs"]),
                "accordions": interactivity.get(
                    "accordions", defaults["interactivity"]["accordions"]
                ),
                "modals": interactivity.get("modals", defaults["interactivity"]["modals"]),
                "tooltips": interactivity.get("tooltips", defaults["interactivity"]["tooltips"]),
                "dropdowns": interactivity.get("dropdowns", defaults["interactivity"]["dropdowns"]),
                "code_copy": interactivity.get("code_copy", defaults["interactivity"]["code_copy"]),
            },
            "features": {
                "speculation_rules": True,
                "view_transitions_meta": True,
                **value.get("features", {}),
            },
        }

    @property
    def link_previews(self) -> dict[str, Any]:
        """
        Normalized link previews configuration.

        Provides Wikipedia-style hover cards for internal links.
        """
        from bengal.config.defaults import DEFAULTS

        defaults = DEFAULTS["link_previews"]
        value = self.config.get("link_previews", {})

        if not isinstance(value, dict):
            if value is False:
                return {
                    "enabled": False,
                    "hover_delay": defaults["hover_delay"],
                    "hide_delay": defaults["hide_delay"],
                    "show_section": defaults["show_section"],
                    "show_reading_time": defaults["show_reading_time"],
                    "show_word_count": defaults["show_word_count"],
                    "show_date": defaults["show_date"],
                    "show_tags": defaults["show_tags"],
                    "max_tags": defaults["max_tags"],
                    "include_selectors": defaults["include_selectors"],
                    "exclude_selectors": defaults["exclude_selectors"],
                    "allowed_hosts": defaults["allowed_hosts"],
                    "allowed_schemes": defaults["allowed_schemes"],
                    "host_failure_threshold": defaults["host_failure_threshold"],
                    "show_dead_links": defaults["show_dead_links"],
                }
            return dict(defaults)

        return {
            "enabled": bool(value.get("enabled", defaults["enabled"])),
            "hover_delay": value.get("hover_delay", defaults["hover_delay"]),
            "hide_delay": value.get("hide_delay", defaults["hide_delay"]),
            "show_section": value.get("show_section", defaults["show_section"]),
            "show_reading_time": value.get("show_reading_time", defaults["show_reading_time"]),
            "show_word_count": value.get("show_word_count", defaults["show_word_count"]),
            "show_date": value.get("show_date", defaults["show_date"]),
            "show_tags": value.get("show_tags", defaults["show_tags"]),
            "max_tags": value.get("max_tags", defaults["max_tags"]),
            "include_selectors": value.get("include_selectors", defaults["include_selectors"]),
            "exclude_selectors": value.get("exclude_selectors", defaults["exclude_selectors"]),
            "allowed_hosts": value.get("allowed_hosts", defaults["allowed_hosts"]),
            "allowed_schemes": value.get("allowed_schemes", defaults["allowed_schemes"]),
            "host_failure_threshold": value.get(
                "host_failure_threshold", defaults["host_failure_threshold"]
            ),
            "show_dead_links": value.get("show_dead_links", defaults["show_dead_links"]),
        }

    # =========================================================================
    # VALIDATION — URL collisions and reference integrity
    # =========================================================================

    def validate_no_url_collisions(self, *, strict: bool = False) -> list[str]:
        """
        Detect when multiple pages output to the same URL.

        Args:
            strict: If True, raise BengalContentError on collision instead of warning.

        Returns:
            List of collision warning messages (empty if no collisions).

        Raises:
            BengalContentError: If strict=True and collisions are detected.
        """
        collisions: list[str] = []

        if hasattr(self, "url_registry") and self.url_registry:
            urls_seen: dict[str, str] = {}

            for page in self.pages:
                url = page._path
                source = str(getattr(page, "source_path", page.title))

                if url in urls_seen:
                    claim = self.url_registry.get_claim(url)
                    owner_info = f" ({claim.owner}, priority {claim.priority})" if claim else ""

                    msg = (
                        f"URL collision detected: {url}\n"
                        f"  Already claimed by: {urls_seen[url]}{owner_info}\n"
                        f"  Also claimed by: {source}\n"
                        f"Tip: Check for duplicate slugs or conflicting autodoc output"
                    )
                    collisions.append(msg)

                    emit_diagnostic(
                        self,
                        "warning",
                        "url_collision",
                        url=url,
                        first_source=urls_seen[url],
                        second_source=source,
                    )
                else:
                    urls_seen[url] = source
        else:
            urls_seen = {}

            for page in self.pages:
                url = page._path
                source = str(getattr(page, "source_path", page.title))

                if url in urls_seen:
                    msg = (
                        f"URL collision detected: {url}\n"
                        f"  Already claimed by: {urls_seen[url]}\n"
                        f"  Also claimed by: {source}\n"
                        f"Tip: Check for duplicate slugs or conflicting autodoc output"
                    )
                    collisions.append(msg)

                    emit_diagnostic(
                        self,
                        "warning",
                        "url_collision",
                        url=url,
                        first_source=urls_seen[url],
                        second_source=source,
                    )
                else:
                    urls_seen[url] = source

        if collisions and strict:
            from bengal.errors import BengalContentError, ErrorCode

            raise BengalContentError(
                "URL collisions detected (strict mode):\n\n" + "\n\n".join(collisions),
                code=ErrorCode.D005,
                suggestion=(
                    "Check for duplicate slugs, conflicting autodoc output, "
                    "or use different URLs for conflicting pages"
                ),
            )

        return collisions

    def _validate_page_section_references(self) -> None:
        """
        Validate that pages in sections have correct _section references.

        Logs warnings for pages that are in a section's pages list but have
        _section = None, which would cause navigation to fall back to flat mode.
        """
        pages_without_section: list[tuple[PageLike, SectionLike]] = []

        for section in self.sections:
            pages_without_section.extend(
                (page, section) for page in section.pages if page._section is None
            )
            self._validate_subsection_references(section, pages_without_section)

        if pages_without_section:
            sample_pages = [(str(p.source_path), s.name) for p, s in pages_without_section[:5]]
            emit_diagnostic(
                self,
                "warning",
                "pages_missing_section_reference",
                count=len(pages_without_section),
                samples=sample_pages,
                note="These pages are in sections but have _section=None, navigation may be flat",
            )

    def _validate_subsection_references(
        self, section: SectionLike, pages_without_section: list[tuple[PageLike, SectionLike]]
    ) -> None:
        """Recursively validate page-section references in subsections."""
        for subsection in section.subsections:
            pages_without_section.extend(
                (page, subsection) for page in subsection.pages if page._section is None
            )
            self._validate_subsection_references(subsection, pages_without_section)

    # =========================================================================
    # FACTORY METHODS
    # =========================================================================

    @classmethod
    def from_config(
        cls,
        root_path: Path,
        config_path: Path | None = None,
        environment: str | None = None,
        profile: str | None = None,
    ) -> Self:
        """Create a Site from configuration (preferred constructor)."""
        return from_config(cls, root_path, config_path, environment, profile)

    @classmethod
    def for_testing(
        cls, root_path: Path | None = None, config: dict[str, Any] | None = None
    ) -> Self:
        """Create a minimal Site instance for tests (no config file required)."""
        return for_testing(cls, root_path, config)

    # =========================================================================
    # VERSIONING (delegated to VersionService)
    # =========================================================================

    @property
    def versioning_enabled(self) -> bool:
        """Whether versioned documentation is enabled."""
        return self._version_service.versioning_enabled if self._version_service else False

    @property
    def versions(self) -> list[dict[str, Any]]:
        """Available documentation versions."""
        return self._version_service.versions if self._version_service else []

    @property
    def latest_version(self) -> dict[str, Any] | None:
        """Latest documentation version."""
        return self._version_service.latest_version if self._version_service else None

    def get_version(self, version_id: str) -> Version | None:
        """Get version by ID or alias."""
        return self._version_service.get_version(version_id) if self._version_service else None

    def invalidate_version_caches(self) -> None:
        """Clear cached version data."""
        if self._version_service:
            self._version_service.invalidate_caches()

    def get_version_target_url(
        self, page: PageLike | None, target_version: dict[str, Any] | None
    ) -> str:
        """
        Get the best URL for a page in the target version.

        Computes a fallback cascade at build time:
        1. If exact equivalent page exists → return that URL
        2. If section index exists → return section index URL
        3. Otherwise → return version root URL

        Args:
            page: Current page object (may be None for edge cases)
            target_version: Target version dict with 'id', 'url_prefix', 'latest' keys

        Returns:
            Best URL to navigate to (guaranteed to exist, never 404)
        """
        from bengal.rendering.template_functions.version_url import (
            get_version_target_url as _get_version_target_url,
        )

        return _get_version_target_url(page, target_version, cast("SiteLike", self))

    def __repr__(self) -> str:
        pages = len(self.pages)
        sections = len(self.sections)
        assets = len(self.assets)
        return f"Site(pages={pages}, sections={sections}, assets={assets})"

    # =========================================================================
    # LIFECYCLE — delegating shims to SiteRunner
    # =========================================================================
    # Canonical implementation lives in `bengal.orchestration.site_runner`.
    # These shims preserve back-compat for ~100 test call sites and external
    # callers; new code should construct `SiteRunner(site)` directly. Slated
    # for removal in v0.5.0. See plan/immutable-floating-sun.md Sprint B1.
    # The single deferred import below is intentional: site_runner is upward
    # (orchestration → core), promoting to module-level would create a cycle.

    def _runner(self) -> Any:
        """Construct a SiteRunner bound to this Site (deferred to avoid cycle)."""
        from bengal.orchestration.site_runner import SiteRunner

        return SiteRunner(self)

    def prepare_for_rebuild(self) -> None:
        """Reset content state for a warm rebuild. Delegates to SiteRunner."""
        self._runner().prepare_for_rebuild()

    def build(self, options: BuildOptions | BuildInput) -> BuildStats:
        """Build the entire site. Delegates to SiteRunner."""
        return self._runner().build(options)

    def serve(
        self,
        host: str = "localhost",
        port: int = 5173,
        watch: bool = True,
        auto_port: bool = True,
        open_browser: bool = False,
        version_scope: str | None = None,
    ) -> None:
        """Start a development server. Delegates to SiteRunner."""
        self._runner().serve(
            host=host,
            port=port,
            watch=watch,
            auto_port=auto_port,
            open_browser=open_browser,
            version_scope=version_scope,
        )

    def clean(self) -> None:
        """Clean the output directory. Delegates to SiteRunner."""
        self._runner().clean()

    def reset_ephemeral_state(self) -> None:
        """Clear ephemeral/derived state between builds. Delegates to SiteRunner."""
        self._runner().reset_ephemeral_state()

    @property
    def build_state(self) -> BuildState | None:
        """Current build state (None outside build context)."""
        return self._current_build_state

    def set_build_state(self, state: BuildState | None) -> None:
        """Set current build state (called by BuildOrchestrator)."""
        self._current_build_state = state


__all__ = [
    "Site",
]
