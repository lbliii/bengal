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
    from bengal.core.url_collisions import URLCollisionRecord
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

        When to use:
            Use for low-level registry operations — bulk registration, URL
            ownership checks, epoch introspection. For typical lookups,
            prefer the wrappers: ``get_section_by_path``,
            ``get_section_by_url``, ``page_by_source_path``. Go to the
            registry directly only when those wrappers don't cover the
            access pattern.

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
        """
        Look up a section by its path (O(1) operation).

        When to use:
            Use when you have a filesystem path (absolute, ``content/``-
            relative, or root-relative) and need the matching ``Section``.
            Prefer ``get_section_by_url`` when the caller has a URL.
            Returns ``None`` if not found (logs a debug diagnostic); do not
            treat ``None`` as an error in code that runs pre-discovery.
        """
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
        """
        Look up a section by its relative URL (O(1) operation).

        When to use:
            Use for URL-driven lookups (permalink resolution, redirect
            handling, sitemap tooling). Prefer ``get_section_by_path`` when
            you have a filesystem path. Returns ``None`` if no section
            owns that URL.
        """
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

        When to use:
            Call once per build after ``discover_content()`` and before
            any ``get_section_by_*()`` call. Orchestrators already wire
            this in the standard sequence; only call directly if you are
            driving discovery manually (e.g., tests or custom pipelines).

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

    def _content_orchestrator(self) -> Any:
        """Construct a ContentOrchestrator bound to this Site (deferred to avoid cycle)."""
        from bengal.orchestration.content import ContentOrchestrator

        return ContentOrchestrator(self)

    def discover_content(self, content_dir: Path | None = None) -> None:
        """
        Discover all content (pages, sections) in the content directory.

        When to use:
            Call once early in a build, before ``register_sections`` and
            ``build_cascade_snapshot``. Orchestrators wire this in the
            standard sequence — call directly only from tests or custom
            pipelines. Passing ``content_dir=`` overrides the default
            ``root_path/content`` for mixed-source builds.

        Scans the content directory recursively, creating Page and Section
        objects for all markdown files and organizing them into a hierarchy.
        """
        self._content_orchestrator().discover_content(content_dir=content_dir, warn_missing=True)

    def _set_output_paths(self) -> None:
        """Set output paths for all discovered pages."""
        self._content_orchestrator()._set_output_paths()

    def _detect_features(self) -> None:
        """Detect CSS-requiring features in page content (mermaid, tables, etc.)."""
        self._content_orchestrator()._detect_features()

    # =========================================================================
    # ASSET DISCOVERY
    # =========================================================================

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.

        When to use:
            Call once per build after theme setup, typically alongside
            ``discover_content``. Order matters: theme assets are loaded
            first so site-level assets can override them by sharing a
            relative path. Override ``assets_dir`` only for tests or
            alternative layouts.

        Theme assets are discovered first (lower priority), then site assets
        (higher priority, can override theme assets).
        """
        self._content_orchestrator().discover_assets(assets_dir=assets_dir)

    def _discover_provider_assets(self) -> None:
        """Discover assets from theme library providers, namespaced by prefix."""
        self._content_orchestrator()._discover_provider_assets()

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
        self._content_orchestrator()._setup_page_references()

    def _setup_section_references(self, section: SectionLike) -> None:
        """Recursively set up references for a section and its subsections."""
        self._content_orchestrator()._setup_section_references(section)

    def _apply_cascades(self) -> None:
        """
        Build cascade snapshot for view-based resolution.

        Section _index.md files can define metadata that automatically applies to all
        descendant pages.
        """
        self._content_orchestrator()._apply_cascades()

    # =========================================================================
    # CASCADE SNAPSHOT
    # =========================================================================

    @property
    def cascade(self) -> CascadeSnapshot:
        """
        Immutable cascade snapshot for this build (read-only).

        When to use:
            Use to resolve cascaded metadata values outside a Page/Section
            context (e.g., build-wide queries, diagnostic dumps, cross-page
            analytics). Page code should read through ``Page.metadata``,
            which applies cascade per-page. The snapshot is rebuilt by
            ``build_cascade_snapshot()`` — never mutate it.

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

        When to use:
            Call once per build, after ``discover_content()`` and before
            any code that reads ``self.cascade`` or ``Page.metadata``.
            Cheap to skip inside tests that construct pages with fully-
            populated metadata; required for any build path that relies on
            ``_index.md`` cascade values.

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
        """
        Query index registry for O(1) page/term lookups.

        When to use:
            Use when you need to query pages by indexed fields (tags,
            categories, custom indexes) — taxonomies, "related posts"
            logic, sitemap generation. Prefer this over iterating
            ``self.pages`` with a filter; the registry is precomputed and
            disk-cached. Raw ``self.pages`` iteration is only correct when
            ordering matters or you genuinely need every page.
        """
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
        """
        Regular content pages authored on disk (excludes generated).

        When to use:
            Use when you need the set of pages a writer actually created —
            sitemaps of authored content, "recent posts" feeds, incremental
            rebuild planning. Does **not** include taxonomy/archive pages
            generated at build time; use ``generated_pages`` for those or
            ``self.pages`` for the union.
        """
        return self.page_cache.regular_pages

    @property
    def generated_pages(self) -> list[PageLike]:
        """
        Pages created by generators (taxonomy, archive, pagination).

        When to use:
            Use to introspect what the build produced beyond the authored
            files — tag pages, year archives, paginated listings. Complement
            to ``regular_pages``; the union is ``self.pages``. These pages
            have no source file, so filesystem operations must check
            ``page.virtual`` first.
        """
        return self.page_cache.generated_pages

    @property
    def listable_pages(self) -> list[PageLike]:
        """
        Pages eligible to appear in public listings (excludes hidden/draft).

        When to use:
            Use for anything that renders a user-visible page index — home
            feeds, section lists, sitemap.xml, RSS. Filters out
            ``draft: true``, ``hidden: true``, and ``_no_list: true`` pages.
            Prefer this over ``regular_pages`` whenever the output is
            reader-facing; use ``regular_pages`` only for authoring or
            build-planning code.
        """
        return self.page_cache.listable_pages

    def get_page_path_map(self) -> dict[str, PageLike]:
        """
        Cached string-keyed page lookup map for O(1) resolution.

        When to use:
            Use when you have a string path (e.g., from config, CLI args,
            URL resolution) and want O(1) page lookup. Prefer
            ``page_by_source_path`` when you already hold a ``Path`` — that
            variant avoids the stringification and is shared across
            orchestrators without re-materializing.
        """
        return self.page_cache.get_page_path_map()

    @property
    def page_by_source_path(self) -> dict[Path, PageLike]:
        """
        O(1) page lookup keyed by source ``Path`` (shared across orchestrators).

        When to use:
            Use this whenever the caller already has a ``Path`` object.
            Prefer ``get_page_path_map()`` when your key is a ``str``. The
            map is shared across the build so reads are safe and cheap; do
            not mutate it.
        """
        return self.page_cache.page_by_source_path

    @property
    def root_section(self) -> SectionLike:
        """
        Root section of the content tree (first parentless section).

        When to use:
            Use as the walk entry point when traversing the section tree.
            Raises ``ValueError`` if the site has no sections — callers that
            can run pre-discovery should check ``self.sections`` first.
        """
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
        """
        Clear all page caches (regular, generated, listable, path maps).

        When to use:
            Call after any structural change — adding, removing, or
            reclassifying pages (e.g., toggling ``draft``). Heavier than
            ``invalidate_regular_pages_cache``; prefer the narrower call
            when you only added/removed authored pages and know generated
            pages are unaffected.
        """
        self.page_cache.invalidate()

    def invalidate_regular_pages_cache(self) -> None:
        """
        Clear only the ``regular_pages`` cache (authored content only).

        When to use:
            Call after adding/removing authored pages during an
            incremental build. Cheaper than ``invalidate_page_caches``;
            use that fuller variant when generated pages or listing
            eligibility may have changed.
        """
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

    def collect_url_collisions(self) -> list[URLCollisionRecord]:
        """Return structured URL collision records for the current site graph."""
        from bengal.core.url_collisions import collect_url_collision_records

        return collect_url_collision_records(
            self.pages,
            root_path=self.root_path,
            url_registry=self.url_registry if getattr(self, "url_registry", None) else None,
        )

    def validate_no_url_collisions(self, *, strict: bool = False) -> list[str]:
        """
        Detect when multiple pages output to the same URL.

        When to use:
            Call near the end of discovery (after ``_set_output_paths``)
            whenever you need to surface conflicting permalinks. Pass
            ``strict=True`` to fail the build on collision; default is a
            warning list that callers can report at whatever severity
            fits. Typical call sites: pre-render validation, health check,
            ``bengal check``.

        Args:
            strict: If True, raise BengalContentError on collision instead of warning.

        Returns:
            List of collision warning messages (empty if no collisions).

        Raises:
            BengalContentError: If strict=True and collisions are detected.
        """
        from bengal.core.url_collisions import format_url_collision_text

        records = self.collect_url_collisions()
        collisions = [format_url_collision_text(record) for record in records]

        for record in records:
            sources = [claimant.source for claimant in record.claimants]
            emit_diagnostic(
                self,
                "warning",
                "url_collision",
                url=record.url,
                first_source=sources[0] if sources else "",
                second_source=sources[1] if len(sources) > 1 else "",
                sources=sources,
            )

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
        self._content_orchestrator()._validate_page_section_references()

    def _validate_subsection_references(
        self, section: SectionLike, pages_without_section: list[tuple[PageLike, SectionLike]]
    ) -> None:
        """Recursively validate page-section references in subsections."""
        self._content_orchestrator()._validate_subsection_references(section, pages_without_section)

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
        """
        Create a Site from on-disk configuration (preferred constructor).

        When to use:
            Use this from the CLI, dev server, and any production-shaped
            code path. Resolves ``bengal.toml`` from ``root_path`` (or
            ``config_path``), applies environment/profile overrides, and
            wires all composed services. Prefer ``for_testing`` only inside
            tests that do not need a real config file.
        """
        return from_config(cls, root_path, config_path, environment, profile)

    @classmethod
    def for_testing(
        cls, root_path: Path | None = None, config: dict[str, Any] | None = None
    ) -> Self:
        """
        Create a minimal Site for tests (no config file required).

        When to use:
            Use only in tests that exercise Site behavior without needing a
            real ``bengal.toml``. Skips config-file resolution and env/profile
            merging. Pass ``config=`` as a dict to inject specific values.
            Prefer ``from_config`` in any code path that might run outside
            ``tests/``.
        """
        return for_testing(cls, root_path, config)

    # =========================================================================
    # VERSIONING (delegated to VersionService)
    # =========================================================================

    @property
    def versioning_enabled(self) -> bool:
        """
        Whether versioned documentation is enabled.

        When to use:
            Gate any code that branches on versioning — version pickers,
            canonical-URL emission, version-aware search indexes. Returns
            ``False`` when no ``[versions]`` config is present, so it is
            safe to call unconditionally instead of probing
            ``site.config_service`` directly.
        """
        return self._version_service.versioning_enabled if self._version_service else False

    @property
    def versions(self) -> list[dict[str, Any]]:
        """
        Available documentation versions.

        When to use:
            Iterate this in templates and version-switcher widgets to render
            the full version list. Returns plain ``dict`` entries (not
            ``Version`` objects) for template-friendly access; reach for
            ``get_version(id)`` when you need typed metadata. Empty list
            when versioning is disabled.
        """
        return self._version_service.versions if self._version_service else []

    @property
    def latest_version(self) -> dict[str, Any] | None:
        """
        Latest documentation version.

        When to use:
            Use to identify the version that should receive the canonical
            URL and serve as the default redirect target from the bare
            site root. Returns ``None`` when versioning is disabled or no
            version is marked latest in config.
        """
        return self._version_service.latest_version if self._version_service else None

    def get_version(self, version_id: str) -> Version | None:
        """
        Get version by ID or alias.

        When to use:
            Prefer this over scanning ``self.versions`` — it accepts both
            the canonical ID (e.g. ``"v2.1"``) and configured aliases
            (e.g. ``"latest"``, ``"stable"``) and returns a typed
            ``Version`` object instead of a raw dict. Returns ``None``
            when the ID is unknown or versioning is disabled.
        """
        return self._version_service.get_version(version_id) if self._version_service else None

    def invalidate_version_caches(self) -> None:
        """
        Clear cached version data (resolved version list, latest, aliases).

        When to use:
            Call after modifying ``versions`` config at runtime (dev-server
            config reload, test fixtures). Narrower than
            ``invalidate_page_caches``; this touches only version metadata.
            No-op when versioning is disabled.
        """
        if self._version_service:
            self._version_service.invalidate_caches()

    def get_version_target_url(
        self, page: PageLike | None, target_version: dict[str, Any] | None
    ) -> str:
        """
        Get the best URL for a page in the target version.

        When to use:
            Use from version-switching UI to produce a guaranteed-non-404
            target URL — if the exact page doesn't exist in the target
            version, the method falls back to the nearest section index or
            the version root. Prefer this over manually building URLs when
            cross-version navigation is in play; the fallback cascade is
            non-obvious to reimplement.

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
        """
        Reset content state for a warm rebuild (keeps caches).

        When to use:
            Call between builds in a long-running process (dev server,
            watch mode) before invoking ``build()`` again. Preserves cache
            state that is still valid across rebuilds. Prefer
            ``reset_ephemeral_state`` for the narrower scope of clearing
            just per-build derived state, and only call this when content
            discovery needs to be redone.
        """
        self._runner().prepare_for_rebuild()

    def build(self, options: BuildOptions | BuildInput) -> BuildStats:
        """
        Build the entire site.

        When to use:
            Primary entry point for one-shot production builds. Dev server
            drives this indirectly via ``serve()``. For multiple builds in
            the same process, call ``prepare_for_rebuild()`` between them.
        """
        return self._runner().build(options)

    def serve(
        self,
        host: str = "localhost",
        port: int = 5173,
        watch: bool = True,
        auto_port: bool = True,
        open_browser: bool = False,
        version_scope: str | None = None,
        completion_policy: Any | None = None,
    ) -> None:
        """
        Start a development server with file watching and live reload.

        When to use:
            The preferred entry point for ``bengal serve`` and interactive
            authoring. Performs an initial ``build()`` and then reacts to
            file changes. For headless one-shot production output, use
            ``build()`` directly.
        """
        self._runner().serve(
            host=host,
            port=port,
            watch=watch,
            auto_port=auto_port,
            open_browser=open_browser,
            version_scope=version_scope,
            completion_policy=completion_policy,
        )

    def clean(self) -> None:
        """
        Remove the output directory and build artifacts.

        When to use:
            Call before a fully cold rebuild, from CI reset scripts, or when
            stale files need to be purged. Does not touch source content or
            caches — use ``invalidate_page_caches()`` alongside it for a
            scorched-earth reset.
        """
        self._runner().clean()

    def reset_ephemeral_state(self) -> None:
        """
        Clear per-build derived state (stats, timings, warnings, rendered html).

        When to use:
            Call between builds when you want a clean slate for reported
            output without re-running discovery. Narrower than
            ``prepare_for_rebuild``; use that when content may have
            changed on disk.
        """
        self._runner().reset_ephemeral_state()

    @property
    def build_state(self) -> BuildState | None:
        """
        Current ``BuildState`` while a build is running, else ``None``.

        When to use:
            Use from orchestration code that needs to emit diagnostics,
            read the current cascade snapshot, or collect stats. Outside a
            build (CLI idle, tests without a runner) this is ``None`` — do
            not dereference unguarded. Prefer reading through convenience
            properties (``self.cascade``) when they already handle the
            fallback.
        """
        return self._current_build_state

    def set_build_state(self, state: BuildState | None) -> None:
        """
        Set current build state (called by BuildOrchestrator).

        When to use:
            Orchestration-internal API. Called at build start with a fresh
            ``BuildState`` and at build end with ``None``. Do not call from
            user code — use ``SiteRunner`` to drive builds, which manages
            state lifecycle correctly.
        """
        self._current_build_state = state


__all__ = [
    "Site",
]
