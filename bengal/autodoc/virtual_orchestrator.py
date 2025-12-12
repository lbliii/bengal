"""
Virtual page orchestrator for autodoc.

Generates API documentation as virtual Page and Section objects
that integrate directly into the build pipeline without intermediate
markdown files.

This is the new architecture that replaces markdown-based autodoc generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.runtime import Context

from bengal.autodoc.base import DocElement
from bengal.autodoc.utils import get_openapi_method, get_openapi_path, get_openapi_tags
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


def _normalize_autodoc_config(site_config: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize github repo/branch for autodoc template consumption.

    Mirrors RenderingPipeline._normalize_config for the subset we need
    inside the autodoc orchestrator (owner/repo → https URL, default branch).
    """
    base = {}
    if isinstance(site_config, dict):
        base.update(site_config)
    autodoc_cfg = base.get("autodoc", {}) or {}

    github_repo = base.get("github_repo") or autodoc_cfg.get("github_repo", "")
    if github_repo and not github_repo.startswith(("http://", "https://")):
        github_repo = f"https://github.com/{github_repo}"

    github_branch = base.get("github_branch") or autodoc_cfg.get("github_branch", "main")

    normalized = dict(autodoc_cfg)
    normalized["github_repo"] = github_repo
    normalized["github_branch"] = github_branch
    return normalized


def _format_source_file_for_display(source_file: Path | str | None, root_path: Path) -> str | None:
    """
    Normalize source_file paths for GitHub links.

    Converts source file paths to repository-relative POSIX paths suitable
    for constructing GitHub blob URLs.

    Strategy:
        1. If path is relative, keep as-is (already repo-relative)
        2. If absolute, try to make relative to repo root (root_path.parent)
        3. Fall back to site root (root_path)
        4. If neither works, return POSIX-ified absolute path

    Args:
        source_file: Path to source file (absolute or relative)
        root_path: Site root path (typically the site/ directory within a repo)

    Returns:
        Repository-relative POSIX path, or None if source_file is None

    Example:
        >>> # Site root: /home/user/myproject/site
        >>> # Source: /home/user/myproject/mypackage/core/module.py
        >>> _format_source_file_for_display(source, site_root)
        'mypackage/core/module.py'
    """
    if not source_file:
        return None

    source_path = Path(source_file)

    # If already relative, assume it's repo-relative and return as POSIX
    if not source_path.is_absolute():
        return source_path.as_posix()

    # Resolve to handle any symlinks or relative components
    source_path = source_path.resolve()

    # Try repo root first (parent of site root), then site root
    # This handles typical layouts where site/ is inside the repo
    for base in (root_path.parent.resolve(), root_path.resolve()):
        try:
            return source_path.relative_to(base).as_posix()
        except ValueError:
            continue

    # Fallback: return absolute POSIX path
    # This shouldn't happen in normal use but handles edge cases
    return source_path.as_posix()


@dataclass
class AutodocRunResult:
    """
    Summary of an autodoc generation run.

    Tracks successes, failures, and warnings for observability and strict mode enforcement.
    """

    extracted: int = 0
    """Number of elements successfully extracted."""
    rendered: int = 0
    """Number of pages successfully rendered."""
    failed_extract: int = 0
    """Number of extraction failures."""
    failed_render: int = 0
    """Number of rendering failures."""
    warnings: int = 0
    """Number of warnings emitted."""
    failed_extract_identifiers: list[str] = field(default_factory=list)
    """Qualified names of elements that failed extraction."""
    failed_render_identifiers: list[str] = field(default_factory=list)
    """Qualified names of elements that failed rendering."""
    fallback_pages: list[str] = field(default_factory=list)
    """URL paths of pages rendered via fallback template."""
    autodoc_dependencies: dict[str, set[str]] = field(default_factory=dict)
    """Mapping of source file paths to the autodoc page paths they produce.
    Used by IncrementalOrchestrator for selective autodoc rebuilds."""

    def has_failures(self) -> bool:
        """Check if any failures occurred."""
        return self.failed_extract > 0 or self.failed_render > 0

    def has_warnings(self) -> bool:
        """Check if any warnings occurred."""
        return self.warnings > 0

    def add_dependency(self, source_file: str, page_path: str) -> None:
        """
        Register a dependency between a source file and an autodoc page.

        Args:
            source_file: Path to the Python/OpenAPI source file
            page_path: Path to the generated autodoc page (source_path)
        """
        if source_file not in self.autodoc_dependencies:
            self.autodoc_dependencies[source_file] = set()
        self.autodoc_dependencies[source_file].add(page_path)


class _PageContext:
    """
    Lightweight page-like context for autodoc template rendering.

    Templates extend base.html and include partials that expect a 'page' variable
    with attributes like metadata, tags, title, and relative_url. This class provides
    those attributes without requiring a full Page object (which doesn't exist yet
    during the initial render phase).

    The navigation attributes (prev, next, prev_in_section, next_in_section) are
    set to None since autodoc virtual pages don't participate in linear navigation.
    """

    def __init__(
        self,
        title: str,
        metadata: dict[str, Any],
        tags: list[str] | None = None,
        relative_url: str = "/",
        variant: str | None = None,
        source_path: str | None = None,
        section: Section | None = None,
    ) -> None:
        self.title = title
        self.metadata = metadata
        self.tags = tags or []
        self.relative_url = relative_url
        self.variant = variant
        self.source_path = source_path

        # Navigation attributes (None = autodoc pages don't have linear navigation)
        self.prev: _PageContext | None = None
        self.next: _PageContext | None = None
        self.prev_in_section: _PageContext | None = None
        self.next_in_section: _PageContext | None = None

        # Section reference (used by docs-nav.html for sidebar navigation)
        # Templates check page._section, so we need both aliases
        self._section = section
        self.section = section

    def __repr__(self) -> str:
        return f"_PageContext(title={self.title!r}, relative_url={self.relative_url!r})"


class VirtualAutodocOrchestrator:
    """
    Orchestrate API documentation generation as virtual pages.

    This orchestrator creates virtual Page and Section objects that integrate
    directly into the site's build pipeline, rendered via theme templates
    without intermediate markdown files.

    Architecture:
        1. Extract DocElements from source (Python, CLI, or OpenAPI)
        2. Create virtual Section hierarchy based on element type
        3. Create virtual Pages for each documentable element
        4. Return (pages, sections) tuple for integration into site

    Supports:
        - Python API docs (modules, classes, functions)
        - CLI docs (commands, command groups)
        - OpenAPI docs (endpoints, schemas)

    Benefits over markdown-based approach:
        - No intermediate markdown files to manage
        - Direct HTML rendering (bypass markdown parsing)
        - Better layout control (card-based API Explorer)
        - Faster builds (no parse → render → parse cycle)
    """

    def __init__(self, site: Site):
        """
        Initialize virtual autodoc orchestrator.

        Args:
            site: Site instance for configuration and context

        Note:
            Uses the site's already-loaded config, which supports both
            YAML (config/_default/autodoc.yaml) and TOML (bengal.toml) formats.
        """
        self.site = site
        # Use site's config directly (supports both YAML and TOML)
        self.config = site.config.get("autodoc", {})
        self.normalized_config = _normalize_autodoc_config(site.config)
        self.python_config = self.config.get("python", {})
        self.cli_config = self.config.get("cli", {})
        self.openapi_config = self.config.get("openapi", {})
        self.template_env = self._create_template_environment()

    def _relativize_paths(self, message: str) -> str:
        """
        Convert absolute paths in error messages to project-relative paths.

        Makes error messages less noisy by showing paths relative to the
        project root (e.g., /bengal/themes/... instead of /Users/name/.../bengal/themes/...).

        Args:
            message: Error message that may contain absolute paths

        Returns:
            Message with absolute paths converted to project-relative paths
        """
        import re

        root_path = str(self.site.root_path)
        # Also handle bengal package paths
        import bengal

        bengal_path = str(Path(bengal.__file__).parent.parent)

        # Replace project root path with project name
        project_name = self.site.root_path.name
        message = message.replace(root_path, f"/{project_name}")

        # Replace bengal package path with /bengal (for theme paths, etc.)
        message = message.replace(bengal_path, "")

        # Clean up any double slashes
        message = re.sub(r"//+", "/", message)

        return message

    def _create_template_environment(self) -> Environment:
        """Create Jinja2 environment for HTML templates."""

        # Import icon function from main template system
        # Icons are already preloaded during main template engine initialization
        from bengal.rendering.template_functions.icons import icon

        # Template directories in priority order
        template_dirs = []

        # User templates (highest priority) - check all reference types
        for ref_type in ["api-reference", "cli-reference", "openapi-reference"]:
            user_templates = self.site.root_path / "templates" / ref_type
            if user_templates.exists():
                template_dirs.append(str(user_templates))

        # Theme templates (for inheriting theme styles) - prefer theme templates
        if self.site.theme:
            theme_templates = self._get_theme_templates_dir()
            if theme_templates:
                template_dirs.append(str(theme_templates))

        # Built-in fallback templates (lowest priority)
        import bengal

        builtin_templates = Path(bengal.__file__).parent / "autodoc" / "fallback"
        if builtin_templates.exists():
            template_dirs.append(str(builtin_templates))

        if not template_dirs:
            logger.warning("autodoc_no_template_dirs", fallback="inline_templates")
            # Use a minimal fallback
            return Environment(autoescape=select_autoescape())

        env = Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=select_autoescape(["html", "htm", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add icon function from main template system
        env.globals["icon"] = icon

        # Register ALL template functions (strings, collections, dates, urls, i18n, navigation, seo, etc.)
        # This ensures autodoc templates have access to the same functions as regular templates
        from bengal.rendering.template_functions import register_all

        register_all(env, self.site)

        # Add global variables that base.html templates expect
        env.globals["site"] = self.site
        env.globals["config"] = self.site.config
        env.globals["theme"] = self.site.theme_config

        # Add bengal metadata (used by base.html for generator meta tag)
        from bengal.utils.metadata import build_template_metadata

        try:
            env.globals["bengal"] = build_template_metadata(self.site)
        except Exception as e:
            logger.debug(
                "autodoc_template_metadata_build_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            env.globals["bengal"] = {"engine": {"name": "Bengal SSG", "version": "unknown"}}

        # Register dateformat filter (from url_helpers for legacy compatibility)
        from bengal.rendering.template_engine.url_helpers import filter_dateformat

        env.filters["dateformat"] = filter_dateformat

        # Register menu functions (required by base.html templates)
        # These are simplified versions that work without TemplateEngine instance
        def get_menu(menu_name: str = "main") -> list[dict[str, Any]]:
            """Get menu items by name."""
            menu = self.site.menu.get(menu_name, [])
            return [item.to_dict() for item in menu]

        def get_menu_lang(menu_name: str = "main", lang: str = "") -> list[dict[str, Any]]:
            """Get menu items for a specific language."""
            if not lang:
                return get_menu(menu_name)
            localized = self.site.menu_localized.get(menu_name, {}).get(lang)
            if localized is None:
                return get_menu(menu_name)
            return [item.to_dict() for item in localized]

        env.globals["get_menu"] = get_menu
        env.globals["get_menu_lang"] = get_menu_lang

        # Register asset_url function (required by base templates)
        # This is a simplified version that works without full TemplateEngine
        from jinja2 import pass_context

        from bengal.rendering.template_engine.url_helpers import with_baseurl

        @pass_context
        def asset_url(ctx: Context, asset_path: str) -> str:
            """Generate URL for an asset with baseurl handling."""
            # Normalize path
            safe_path = (asset_path or "").replace("\\", "/").strip()
            while safe_path.startswith("/"):
                safe_path = safe_path[1:]
            if not safe_path:
                return "/assets/"

            # In dev server mode, return simple path
            if self.site.config.get("dev_server", False):
                return with_baseurl(f"/assets/{safe_path}", self.site)

            # Otherwise, return path with baseurl
            return with_baseurl(f"/assets/{safe_path}", self.site)

        env.globals["asset_url"] = asset_url

        # Register url_for function (required by base templates)
        def url_for(page_path: str) -> str:
            """Generate URL for a page path."""
            if not page_path:
                return "/"
            # Normalize and add baseurl
            path = page_path.strip()
            if not path.startswith("/"):
                path = "/" + path
            return with_baseurl(path, self.site)

        env.globals["url_for"] = url_for

        # Note: Custom tests (match) and filters (first_sentence) are now
        # registered via register_all() from bengal.rendering.template_functions

        return env

    def _get_theme_templates_dir(self) -> Path | None:
        """Get theme templates directory if available."""
        if not self.site.theme:
            return None

        import bengal

        bengal_dir = Path(bengal.__file__).parent
        theme_dir = bengal_dir / "themes" / self.site.theme / "templates"
        return theme_dir if theme_dir.exists() else None

    def _slugify(self, text: str) -> str:
        """
        Convert text to URL-friendly slug.

        Strips common suffixes (API, Reference, Documentation), converts to lowercase,
        replaces non-alphanumeric characters with hyphens, and collapses multiple hyphens.

        Args:
            text: Text to slugify (e.g., "Commerce API Reference")

        Returns:
            URL-friendly slug (e.g., "commerce"), or "rest" as fallback for empty results
        """
        import re

        if not text or not text.strip():
            return "rest"

        slug = text.strip().lower()

        # Strip common suffixes (case-insensitive, already lowercased)
        for suffix in ["api", "reference", "documentation", "docs", "service"]:
            if slug.endswith(f" {suffix}"):
                slug = slug[: -(len(suffix) + 1)]
            elif slug == suffix:
                slug = ""

        # Replace non-alphanumeric characters with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", slug)

        # Collapse multiple hyphens and strip leading/trailing hyphens
        slug = re.sub(r"-+", "-", slug).strip("-")

        return slug if slug else "rest"

    def _derive_openapi_prefix(self) -> str:
        """
        Derive output prefix from OpenAPI spec title.

        Loads the OpenAPI spec file (if exists), extracts info.title,
        slugifies it, and prepends "api/".

        Returns:
            Derived prefix (e.g., "api/commerce") or "api/rest" as fallback
        """
        import yaml

        spec_file = self.openapi_config.get("spec_file")
        if not spec_file:
            return "api/rest"

        spec_path = self.site.root_path / spec_file
        if not spec_path.exists():
            logger.debug("autodoc_openapi_spec_not_found_for_prefix", path=str(spec_path))
            return "api/rest"

        try:
            with open(spec_path, encoding="utf-8") as f:
                spec = yaml.safe_load(f)

            title = spec.get("info", {}).get("title", "")
            if not title:
                return "api/rest"

            slug = self._slugify(title)
            return f"api/{slug}"
        except Exception as e:
            logger.debug(
                "autodoc_openapi_prefix_derivation_failed",
                path=str(spec_path),
                error=str(e),
            )
            return "api/rest"

    def _resolve_output_prefix(self, doc_type: str) -> str:
        """
        Resolve output prefix for a documentation type.

        Checks explicit config value first, then applies type-specific defaults:
        - python: "api/python"
        - openapi: auto-derived from spec title, or "api/rest"
        - cli: "cli"

        Args:
            doc_type: Documentation type ("python", "openapi", "cli")

        Returns:
            Resolved output prefix (e.g., "api/python", "api/commerce", "cli")
        """
        if doc_type == "python":
            explicit = self.python_config.get("output_prefix")
            if explicit:
                return explicit.strip("/")
            return "api/python"

        elif doc_type == "openapi":
            explicit = self.openapi_config.get("output_prefix")
            if explicit:
                return explicit.strip("/")
            # Empty string means auto-derive
            if explicit == "":
                return self._derive_openapi_prefix()
            # None or not set - use default auto-derive
            return self._derive_openapi_prefix()

        elif doc_type == "cli":
            explicit = self.cli_config.get("output_prefix")
            if explicit:
                return explicit.strip("/")
            return "cli"

        return f"api/{doc_type}"

    def is_enabled(self) -> bool:
        """Check if virtual autodoc is enabled for any type."""
        # Virtual pages are now the default (and only) option
        # Only check if explicitly disabled via virtual_pages: false
        # Check Python
        python_enabled = (
            self.python_config.get("virtual_pages", True)  # Default to True
            and self.python_config.get("enabled", True)
        )

        # Check CLI
        cli_enabled = (
            self.cli_config.get("virtual_pages", True)  # Default to True
            and self.cli_config.get("enabled", True)
        )

        # Check OpenAPI
        openapi_enabled = (
            self.openapi_config.get("virtual_pages", True)  # Default to True
            and self.openapi_config.get("enabled", True)
        )

        return bool(python_enabled or cli_enabled or openapi_enabled)

    def _check_prefix_overlaps(self) -> None:
        """
        Check for and warn about overlapping output prefixes.

        Emits a warning when multiple autodoc types share the same or overlapping
        prefixes, which could cause navigation conflicts.
        """
        enabled_prefixes: dict[str, str] = {}  # prefix -> doc_type

        # Collect prefixes for enabled doc types
        if self.python_config.get("enabled", False):
            enabled_prefixes[self._resolve_output_prefix("python")] = "python"

        if self.openapi_config.get("enabled", False):
            enabled_prefixes[self._resolve_output_prefix("openapi")] = "openapi"

        if self.cli_config.get("enabled", False):
            enabled_prefixes[self._resolve_output_prefix("cli")] = "cli"

        # Check for exact matches (multiple types with same prefix)
        prefix_counts: dict[str, list[str]] = {}
        for prefix, doc_type in enabled_prefixes.items():
            if prefix not in prefix_counts:
                prefix_counts[prefix] = []
            prefix_counts[prefix].append(doc_type)

        for prefix, doc_types in prefix_counts.items():
            if len(doc_types) > 1:
                logger.warning(
                    "autodoc_prefix_overlap",
                    prefix=prefix,
                    doc_types=doc_types,
                    hint=f"Multiple autodoc types share prefix '{prefix}': {', '.join(doc_types)}. "
                    f"Consider distinct output_prefix values to avoid navigation conflicts.",
                )

        # Check for hierarchical overlaps (e.g., "api" and "api/python")
        prefixes = list(enabled_prefixes.keys())
        for i, p1 in enumerate(prefixes):
            for p2 in prefixes[i + 1 :]:
                # Check if one is a prefix of the other
                if p1.startswith(f"{p2}/") or p2.startswith(f"{p1}/"):
                    logger.warning(
                        "autodoc_prefix_hierarchy_overlap",
                        prefix1=p1,
                        prefix2=p2,
                        doc_type1=enabled_prefixes[p1],
                        doc_type2=enabled_prefixes[p2],
                        hint=f"Autodoc prefixes overlap: '{p1}' ({enabled_prefixes[p1]}) and "
                        f"'{p2}' ({enabled_prefixes[p2]}). This may cause navigation issues.",
                    )

    def generate(self) -> tuple[list[Page], list[Section], AutodocRunResult]:
        """
        Generate documentation as virtual pages and sections for all enabled types.

        Returns:
            Tuple of (pages, sections, result) to add to site

        Raises:
            ValueError: If autodoc configuration is invalid
            RuntimeError: If strict mode is enabled and failures occurred
        """
        result = AutodocRunResult()
        strict_mode = self.config.get("strict", False)

        if not self.is_enabled():
            logger.debug("virtual_autodoc_disabled")
            return [], [], result

        # Check for prefix overlaps before generating
        self._check_prefix_overlaps()

        all_elements: list[DocElement] = []
        all_sections: dict[str, Section] = {}
        all_pages: list[Page] = []

        # 1. Extract Python documentation
        # Virtual pages are now the default (and only) option
        if self.python_config.get("virtual_pages", True) and self.python_config.get(
            "enabled", True
        ):
            try:
                python_elements = self._extract_python()
                if python_elements:
                    all_elements.extend(python_elements)
                    result.extracted += len(python_elements)
                    python_sections = self._create_python_sections(python_elements)
                    all_sections.update(python_sections)
                    python_pages, page_result = self._create_pages(
                        python_elements, python_sections, doc_type="python", result=result
                    )
                    all_pages.extend(python_pages)
                    result.rendered += len(python_pages)
            except Exception as e:
                result.failed_extract += 1
                result.failed_extract_identifiers.append("python")
                result.warnings += 1
                logger.warning(
                    "autodoc_python_extraction_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                if strict_mode:
                    raise RuntimeError(f"Python extraction failed in strict mode: {e}") from e

        # 2. Extract CLI documentation
        # Virtual pages are now the default (and only) option
        if self.cli_config.get("virtual_pages", True) and self.cli_config.get("enabled", True):
            try:
                cli_elements = self._extract_cli()
                if cli_elements:
                    all_elements.extend(cli_elements)
                    result.extracted += len(cli_elements)
                    cli_sections = self._create_cli_sections(cli_elements)
                    all_sections.update(cli_sections)
                    cli_pages, _ = self._create_pages(
                        cli_elements, cli_sections, doc_type="cli", result=result
                    )
                    all_pages.extend(cli_pages)
                    result.rendered += len(cli_pages)
            except Exception as e:
                result.failed_extract += 1
                result.failed_extract_identifiers.append("cli")
                result.warnings += 1
                logger.warning(
                    "autodoc_cli_extraction_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                if strict_mode:
                    raise RuntimeError(f"CLI extraction failed in strict mode: {e}") from e

        # 3. Extract OpenAPI documentation
        # Pass existing sections so OpenAPI can reuse "api" section if Python already created it
        # Virtual pages are now the default (and only) option
        if self.openapi_config.get("virtual_pages", True) and self.openapi_config.get(
            "enabled", True
        ):
            try:
                openapi_elements = self._extract_openapi()
                if openapi_elements:
                    all_elements.extend(openapi_elements)
                    result.extracted += len(openapi_elements)
                    openapi_sections = self._create_openapi_sections(openapi_elements, all_sections)
                    all_sections.update(openapi_sections)
                    openapi_pages, _ = self._create_pages(
                        openapi_elements, openapi_sections, doc_type="openapi", result=result
                    )
                    all_pages.extend(openapi_pages)
                    result.rendered += len(openapi_pages)
            except Exception as e:
                result.failed_extract += 1
                result.failed_extract_identifiers.append("openapi")
                result.warnings += 1
                logger.warning(
                    "autodoc_openapi_extraction_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                if strict_mode:
                    raise RuntimeError(f"OpenAPI extraction failed in strict mode: {e}") from e

        if not all_elements:
            logger.info("autodoc_no_elements_found")
            if strict_mode and result.failed_extract > 0:
                raise RuntimeError(
                    f"Autodoc strict mode: {result.failed_extract} extraction failures, "
                    f"no elements produced"
                )
            return [], [], result

        # 4. Create aggregating parent sections for shared prefixes (e.g., /api/ for /api/python/ and /api/openapi/)
        parent_sections = self._create_aggregating_parent_sections(all_sections)
        all_sections.update(parent_sections)

        # 5. Create index pages for all sections
        index_pages = self._create_index_pages(all_sections)
        all_pages.extend(index_pages)

        # Check strict mode after all processing
        if strict_mode and result.has_failures():
            raise RuntimeError(
                f"Autodoc strict mode: {result.failed_extract} extraction failures, "
                f"{result.failed_render} rendering failures"
            )

        logger.info(
            "virtual_autodoc_complete",
            pages=len(all_pages),
            sections=len(all_sections),
            extracted=result.extracted,
            rendered=result.rendered,
            failed_extract=result.failed_extract,
            failed_render=result.failed_render,
        )

        # Return root-level sections for navigation menu
        # Priority: aggregating parent sections > individual type sections
        # e.g., if "api" aggregates "api/python" and "api/openapi", return only "api"
        root_section_keys = set()

        # First, add aggregating parent sections (they take priority)
        aggregating_keys = {
            key for key, s in all_sections.items() if s.metadata.get("is_aggregating_section")
        }
        root_section_keys.update(aggregating_keys)

        # Then add individual type sections that aren't children of aggregating sections
        for doc_type, config in [
            ("python", self.python_config),
            ("openapi", self.openapi_config),
            ("cli", self.cli_config),
        ]:
            if not config.get("enabled", False):
                continue
            prefix = self._resolve_output_prefix(doc_type)
            if prefix not in all_sections:
                continue
            # Skip if this prefix is a child of an aggregating section
            parent = prefix.split("/")[0] if "/" in prefix else None
            if parent and parent in aggregating_keys:
                continue
            root_section_keys.add(prefix)

        root_sections = [s for key, s in all_sections.items() if key in root_section_keys]

        logger.debug(
            "virtual_autodoc_root_sections",
            count=len(root_sections),
            names=[s.name for s in root_sections],
            keys=list(root_section_keys),
            aggregating=list(aggregating_keys),
        )

        return all_pages, root_sections, result

    def _create_python_sections(self, elements: list[DocElement]) -> dict[str, Section]:
        """
        Create virtual section hierarchy from doc elements.

        Creates sections for:
        - /{prefix}/ (root Python API section, e.g., /api/python/)
        - /{prefix}/<package>/ (for each top-level package)
        - /{prefix}/<package>/<subpackage>/ (nested packages)

        Args:
            elements: List of DocElements (modules) to process

        Returns:
            Dictionary mapping section path to Section object
        """
        sections: dict[str, Section] = {}

        # Resolve output prefix for Python docs
        prefix = self._resolve_output_prefix("python")
        prefix_parts = prefix.split("/") if prefix else []
        root_name = prefix_parts[-1] if prefix_parts else "python"

        # Build lookup of package descriptions from __init__.py modules
        # Key: qualified_name (e.g., "bengal.core"), Value: description
        package_descriptions: dict[str, str] = {}
        for element in elements:
            if element.element_type == "module" and element.description:
                # This module's description can describe its package
                package_descriptions[element.qualified_name] = element.description

        # Create root Python API section
        from bengal.utils.url_normalization import join_url_paths

        api_section = Section.create_virtual(
            name=root_name,
            relative_url=join_url_paths(prefix),
            title="Python API Reference",
            metadata={
                "type": "api-reference",
                "weight": 100,
                "icon": "book",
                "description": "Browse Python API documentation by package.",
            },
        )
        sections[prefix] = api_section

        # Track package hierarchy
        for element in elements:
            if element.element_type != "module":
                continue

            # Parse module qualified name (e.g., "bengal.core.page")
            parts = element.qualified_name.split(".")

            # Create sections for package hierarchy
            current_section = api_section
            section_path = prefix

            for i, part in enumerate(parts[:-1]):  # Skip the final module
                section_path = f"{section_path}/{part}"

                if section_path not in sections:
                    # Create new package section
                    # Use join_url_paths to ensure proper normalization
                    from bengal.utils.url_normalization import join_url_paths

                    relative_url = join_url_paths(prefix, *parts[: i + 1])
                    qualified_name = ".".join(parts[: i + 1])

                    # Try to find description from the package's __init__.py
                    description = package_descriptions.get(qualified_name, "")

                    package_section = Section.create_virtual(
                        name=part,
                        relative_url=relative_url,
                        title=part.replace("_", " ").title(),
                        metadata={
                            "type": "api-reference",
                            "qualified_name": qualified_name,
                            "description": description,
                        },
                    )
                    current_section.add_subsection(package_section)
                    sections[section_path] = package_section
                    current_section = package_section
                else:
                    current_section = sections[section_path]

        logger.debug(
            "autodoc_sections_created",
            count=len(sections),
            paths=list(sections.keys()),
        )

        return sections

    def _create_cli_sections(self, elements: list[DocElement]) -> dict[str, Section]:
        """Create CLI section hierarchy."""
        sections: dict[str, Section] = {}

        # Resolve output prefix for CLI docs
        prefix = self._resolve_output_prefix("cli")
        prefix_parts = prefix.split("/") if prefix else []
        root_name = prefix_parts[-1] if prefix_parts else "cli"

        # Create root CLI section
        from bengal.utils.url_normalization import join_url_paths

        cli_section = Section.create_virtual(
            name=root_name,
            relative_url=join_url_paths(prefix),
            title="CLI Reference",
            metadata={
                "type": "cli-reference",
                "weight": 100,
                "icon": "terminal",
                "description": "Command-line interface documentation.",
            },
        )
        sections[prefix] = cli_section

        # Group commands by command-group
        command_groups: dict[str, list[DocElement]] = {}
        standalone_commands: list[DocElement] = []

        for element in elements:
            if element.element_type == "command-group":
                command_groups[element.qualified_name] = []
            elif element.element_type == "command":
                # Check if command has a parent group
                parts = element.qualified_name.split(".")
                if len(parts) > 1:
                    parent_group = ".".join(parts[:-1])
                    if parent_group not in command_groups:
                        command_groups[parent_group] = []
                    command_groups[parent_group].append(element)
                else:
                    standalone_commands.append(element)

        # Create sections for command groups
        for group_name, commands in command_groups.items():
            if not commands:
                continue

            # Build URL path components
            group_parts = group_name.split(".")
            section_path = f"{prefix}/{group_name.replace('.', '/')}"
            group_section = Section.create_virtual(
                name=group_parts[-1],
                relative_url=join_url_paths(prefix, *group_parts),
                title=group_parts[-1].replace("_", " ").title(),
                metadata={
                    "type": "cli-reference",
                    "qualified_name": group_name,
                },
            )
            cli_section.add_subsection(group_section)
            sections[section_path] = group_section

        logger.debug("autodoc_sections_created", count=len(sections), type="cli")
        return sections

    def _create_openapi_sections(
        self, elements: list[DocElement], existing_sections: dict[str, Section] | None = None
    ) -> dict[str, Section]:
        """Create OpenAPI section hierarchy."""
        sections: dict[str, Section] = {}
        # Note: existing_sections parameter kept for API compatibility but no longer used
        # Each autodoc type now creates its own distinct section tree

        # Resolve output prefix for OpenAPI docs
        prefix = self._resolve_output_prefix("openapi")
        prefix_parts = prefix.split("/") if prefix else []
        root_name = prefix_parts[-1] if prefix_parts else "rest"

        # Create root OpenAPI section (always new, never reuse)
        from bengal.utils.url_normalization import join_url_paths

        api_section = Section.create_virtual(
            name=root_name,
            relative_url=join_url_paths(prefix),
            title="REST API Reference",
            metadata={
                "type": "api-reference",
                "weight": 100,
                "icon": "book",
                "description": "REST API documentation.",
            },
        )
        sections[prefix] = api_section

        # Group endpoints by tags
        tagged_endpoints: dict[str, list[DocElement]] = {}
        untagged_endpoints: list[DocElement] = []

        for element in elements:
            if element.element_type == "openapi_endpoint":
                tags = get_openapi_tags(element)
                if tags:
                    for tag in tags:
                        if tag not in tagged_endpoints:
                            tagged_endpoints[tag] = []
                        tagged_endpoints[tag].append(element)
                else:
                    untagged_endpoints.append(element)
            elif element.element_type == "openapi_overview":
                # Overview goes at root
                pass
            elif element.element_type == "openapi_schema":
                # Schemas go in a schemas section
                schemas_key = f"{prefix}/schemas"
                if schemas_key not in sections:
                    schemas_section = Section.create_virtual(
                        name="schemas",
                        relative_url=join_url_paths(prefix, "schemas"),
                        title="Schemas",
                        metadata={
                            "type": "api-reference",
                            "description": "API data schemas and models.",
                        },
                    )
                    api_section.add_subsection(schemas_section)
                    sections[schemas_key] = schemas_section

        # Create sections for tags
        for tag, _endpoints in tagged_endpoints.items():
            tag_section = Section.create_virtual(
                name=tag,
                relative_url=join_url_paths(prefix, "tags", tag),
                title=tag.replace("-", " ").title(),
                metadata={
                    "type": "api-reference",
                    "tag": tag,
                },
            )
            api_section.add_subsection(tag_section)
            sections[f"{prefix}/tags/{tag}"] = tag_section

        logger.debug("autodoc_sections_created", count=len(sections), type="openapi")
        return sections

    def _create_pages(
        self,
        elements: list[DocElement],
        sections: dict[str, Section],
        doc_type: str = "python",
        result: AutodocRunResult | None = None,
    ) -> tuple[list[Page], AutodocRunResult]:
        """
        Create virtual pages for documentation elements.

        This uses a two-pass approach to ensure navigation works correctly:
        1. First pass: Create all Page objects and add them to sections
        2. Second pass: Render HTML (now sections have all their pages)

        Args:
            elements: DocElements to create pages for
            sections: Section hierarchy for page placement
            doc_type: Type of documentation ("python", "cli", "openapi")
            result: AutodocRunResult to track failures and warnings

        Returns:
            Tuple of (list of virtual Page objects, updated result)
        """
        if result is None:
            result = AutodocRunResult()

        # First pass: Create pages without HTML and add to sections
        page_data: list[Page] = []

        for element in elements:
            display_source_file = _format_source_file_for_display(
                element.source_file, self.site.root_path
            )
            element.display_source_file = display_source_file
            source_file_for_tracking = element.source_file
            # Determine which elements get pages based on type
            if (
                doc_type == "python"
                and element.element_type != "module"
                or doc_type == "cli"
                and element.element_type not in ("command", "command-group")
                or doc_type == "openapi"
                and element.element_type
                not in (
                    "openapi_endpoint",
                    "openapi_schema",
                    "openapi_overview",
                )
            ):
                continue

            # Determine section for this element
            parent_section = self._find_parent_section(element, sections, doc_type)

            # Create page metadata without rendering HTML yet
            template_name, url_path, page_type = self._get_element_metadata(element, doc_type)
            source_id = f"{doc_type}/{url_path}.md"
            output_path = self.site.output_dir / f"{url_path}/index.html"

            # Create page with deferred rendering - HTML rendered in rendering phase
            page = Page.create_virtual(
                source_id=source_id,
                title=element.name,
                metadata={
                    "type": page_type,
                    "qualified_name": element.qualified_name,
                    "element_type": element.element_type,
                    "description": element.description or f"Documentation for {element.name}",
                    "source_file": display_source_file,
                    "line_number": getattr(element, "line_number", None),
                    "is_autodoc": True,
                    "autodoc_element": element,
                    # Rendering metadata - used by RenderingPipeline to render with full context
                    "_autodoc_template": template_name,
                    "_autodoc_url_path": url_path,
                    "_autodoc_page_type": page_type,
                },
                rendered_html=None,  # Deferred - rendered in rendering phase with full context
                template_name=template_name,
                output_path=output_path,
            )
            page._site = self.site
            # Set section reference via setter (handles virtual sections with URL-based lookup)
            page._section = parent_section

            # Check if this element corresponds to an existing section (e.g. it's a package)
            # If so, this page should be the index page of that section
            target_section = None

            # Get the prefix for this doc type to construct correct section paths
            prefix = self._resolve_output_prefix(doc_type)

            if doc_type == "python" and element.element_type == "module":
                # Check if we have a section for this module (i.e., it is a package)
                # Section path format from _create_python_sections: {prefix}/part1/part2
                section_path = f"{prefix}/{element.qualified_name.replace('.', '/')}"
                target_section = sections.get(section_path)

            elif doc_type == "cli" and element.element_type == "command-group":
                # Section path format from _create_cli_sections: {prefix}/part1/part2
                section_path = f"{prefix}/{element.qualified_name.replace('.', '/')}"
                target_section = sections.get(section_path)

            # Add to section
            if target_section:
                # This page is the index for target_section
                # Set section reference to the target section (it belongs TO the section as its index)
                page._section = target_section

                # Set as index page manually
                # We don't use add_page() because it relies on filename stem for index detection
                target_section.index_page = page
                target_section.pages.append(page)
            else:
                # Regular page - add to parent section
                parent_section.add_page(page)

            # Track source file → autodoc page dependency for incremental builds
            if source_file_for_tracking:
                result.add_dependency(str(source_file_for_tracking), source_id)

            # Store page for return (no HTML rendering yet - deferred to rendering phase)
            page_data.append(page)

        # Note: HTML rendering is now DEFERRED to the rendering phase
        # This ensures menus and full template context are available.
        # See: RenderingPipeline._process_virtual_page() and _render_autodoc_page()
        logger.debug("autodoc_pages_created", count=len(page_data), type=doc_type)

        return page_data, result

    def _find_parent_section(
        self, element: DocElement, sections: dict[str, Section], doc_type: str
    ) -> Section:
        """Find the appropriate parent section for an element."""
        prefix = self._resolve_output_prefix(doc_type)

        # Get the first section from sections dict as fallback
        default_section = next(iter(sections.values()), None)
        if default_section is None:
            # Create a fallback section if none exists
            from bengal.utils.url_normalization import join_url_paths

            default_section = Section.create_virtual(
                name="api",
                relative_url=join_url_paths(prefix),
                title="API Reference",
                metadata={},
            )

        if doc_type == "python":
            parts = element.qualified_name.split(".")
            section_path = f"{prefix}/" + "/".join(parts[:-1]) if len(parts) > 1 else prefix
            return sections.get(section_path) or sections.get(prefix) or default_section
        elif doc_type == "cli":
            if element.element_type == "command-group":
                return sections.get(prefix) or default_section
            parts = element.qualified_name.split(".")
            if len(parts) > 1:
                section_path = f"{prefix}/{'.'.join(parts[:-1]).replace('.', '/')}"
                return sections.get(section_path) or sections.get(prefix) or default_section
            return sections.get(prefix) or default_section
        elif doc_type == "openapi":
            if element.element_type == "openapi_overview":
                return sections.get(prefix) or default_section
            elif element.element_type == "openapi_schema":
                return sections.get(f"{prefix}/schemas") or sections.get(prefix) or default_section
            elif element.element_type == "openapi_endpoint":
                tags = get_openapi_tags(element)
                if tags:
                    tag_section = sections.get(f"{prefix}/tags/{tags[0]}")
                    if tag_section:
                        return tag_section
                return sections.get(prefix) or default_section
        return sections.get(prefix) or default_section

    def _create_element_page(
        self,
        element: DocElement,
        section: Section,
        doc_type: str,
    ) -> Page:
        """
        Create a virtual page for any element type.

        Args:
            element: DocElement to create page for
            section: Parent section for this page
            doc_type: Type of documentation ("python", "cli", "openapi")

        Returns:
            Virtual Page object
        """
        # Determine URL path and template based on element type
        template_name, url_path, page_type = self._get_element_metadata(element, doc_type)

        display_source_file = _format_source_file_for_display(
            element.source_file, self.site.root_path
        )
        element.display_source_file = display_source_file

        # Build source ID (synthetic path)
        source_id = f"{doc_type}/{url_path}.md"

        # Generate HTML content using appropriate template
        html_content = self._render_element(element, template_name, url_path, page_type, section)

        # Create virtual page with absolute output path
        output_path = self.site.output_dir / f"{url_path}/index.html"

        page = Page.create_virtual(
            source_id=source_id,
            title=element.name,
            metadata={
                "type": page_type,
                "qualified_name": element.qualified_name,
                "element_type": element.element_type,
                "description": element.description or f"Documentation for {element.name}",
                "source_file": display_source_file,
                "line_number": getattr(element, "line_number", None),
                "is_autodoc": True,
                "autodoc_element": element,
            },
            rendered_html=html_content,
            template_name=template_name,
            output_path=output_path,
        )

        # Set site reference for URL computation
        page._site = self.site
        # Set section reference via setter (handles virtual sections with URL-based lookup)
        page._section = section

        return page

    def _get_element_metadata(self, element: DocElement, doc_type: str) -> tuple[str, str, str]:
        """Get template name, URL path, and page type for an element."""
        prefix = self._resolve_output_prefix(doc_type)

        if doc_type == "python":
            url_path = f"{prefix}/{element.qualified_name.replace('.', '/')}"
            return "api-reference/module", url_path, "api-reference"
        elif doc_type == "cli":
            if element.element_type == "command-group":
                url_path = f"{prefix}/{element.qualified_name.replace('.', '/')}"
                return "cli-reference/command-group", url_path, "cli-reference"
            else:
                url_path = f"{prefix}/{element.qualified_name.replace('.', '/')}"
                return "cli-reference/command", url_path, "cli-reference"
        elif doc_type == "openapi":
            if element.element_type == "openapi_overview":
                return "openapi-reference/overview", f"{prefix}/overview", "api-reference"
            elif element.element_type == "openapi_schema":
                schema_name = element.name
                return (
                    "openapi-reference/schema",
                    f"{prefix}/schemas/{schema_name}",
                    "api-reference",
                )
            elif element.element_type == "openapi_endpoint":
                method = get_openapi_method(element).lower()
                path = get_openapi_path(element).strip("/").replace("/", "-")
                return (
                    "openapi-reference/endpoint",
                    f"{prefix}/endpoints/{method}-{path}",
                    "api-reference",
                )
        # Fallback
        return "api-reference/module", f"{prefix}/{element.name}", "api-reference"

    def _render_element(
        self,
        element: DocElement,
        template_name: str,
        url_path: str,
        page_type: str,
        section: Section | None = None,
    ) -> str:
        """
        Render element documentation to HTML.

        Args:
            element: DocElement to render
            template_name: Template name (e.g., "api-reference/module")
            url_path: URL path for this element (e.g., "cli/bengal/serve")
            page_type: Page type (e.g., "cli-reference", "api-reference")
            section: Parent section (for sidebar navigation)

        Returns:
            Rendered HTML string
        """
        # Create a page-like context for templates that expect a 'page' variable.
        # Templates extend base.html and include partials (page-hero, docs-nav, etc.)
        # that require page.metadata, page.tags, page.title, etc.
        # Get tags: use typed helper for OpenAPI, fall back to metadata dict for others
        if element.element_type == "openapi_endpoint":
            element_tags = list(get_openapi_tags(element))
        else:
            element_tags = element.metadata.get("tags", []) if element.metadata else []

        display_source_file = getattr(
            element,
            "display_source_file",
            _format_source_file_for_display(element.source_file, self.site.root_path),
        )

        page_context = _PageContext(
            title=element.name,
            metadata={
                "type": page_type,
                "qualified_name": element.qualified_name,
                "element_type": element.element_type,
                "description": element.description or f"Documentation for {element.name}",
                "source_file": display_source_file,
                "line_number": getattr(element, "line_number", None),
                "is_autodoc": True,
            },
            tags=element_tags,
            relative_url=f"/{url_path}/",
            source_path=display_source_file,
            section=section,
        )

        # Try theme template first
        try:
            template = self.template_env.get_template(f"{template_name}.html")
            return template.render(
                element=element,
                page=page_context,
                config=self.normalized_config,
                site=self.site,
            )
        except Exception as e:
            # Fall back to generic template or legacy path
            try:
                # Try without .html extension
                template = self.template_env.get_template(template_name)
                return template.render(
                    element=element,
                    page=page_context,
                    config=self.normalized_config,
                    site=self.site,
                )
            except Exception as fallback_error:
                logger.warning(
                    "autodoc_template_render_failed",
                    element=element.qualified_name,
                    template=template_name,
                    error=self._relativize_paths(str(e)),
                    fallback_error=self._relativize_paths(str(fallback_error)),
                )
                # Return minimal fallback HTML
                # Note: In deferred rendering path, fallback tagging happens in RenderingPipeline
                return self._render_fallback(element)

    def _render_fallback(self, element: DocElement) -> str:
        """Render minimal fallback HTML when template fails."""
        classes = [c for c in element.children if c.element_type == "class"]
        functions = [f for f in element.children if f.element_type == "function"]

        return f"""
<div class="api-explorer">
    <div class="api-module">
        <h1 class="api-module__title">{element.name}</h1>
        <p class="api-module__description">{element.description or "No description available."}</p>

        <div class="api-module__stats">
            <span class="api-stat">Classes: {len(classes)}</span>
            <span class="api-stat">Functions: {len(functions)}</span>
        </div>

        <div class="api-classes">
            {"".join(self._render_fallback_class(c) for c in classes)}
        </div>

        <div class="api-functions">
            {"".join(self._render_fallback_function(f) for f in functions)}
        </div>
    </div>
</div>
"""

    def _render_fallback_class(self, element: DocElement) -> str:
        """Render minimal class HTML."""
        return f"""
<div class="api-card api-card--class">
    <h2 class="api-card__title">{element.name}</h2>
    <p class="api-card__description">{element.description or ""}</p>
</div>
"""

    def _render_fallback_function(self, element: DocElement) -> str:
        """Render minimal function HTML."""
        return f"""
<div class="api-card api-card--function">
    <h3 class="api-card__title">{element.name}</h3>
    <p class="api-card__description">{element.description or ""}</p>
</div>
"""

    def _create_aggregating_parent_sections(
        self, sections: dict[str, Section]
    ) -> dict[str, Section]:
        """
        Create aggregating parent sections for shared prefixes.

        When multiple autodoc types share a common prefix (e.g., api/python and
        api/openapi), this creates a parent section (e.g., api/) that aggregates
        them. This enables:
        - A navigable /api/ page showing all API documentation types
        - Correct Dev dropdown detection (finds 'api' section)

        Args:
            sections: Existing section dictionary

        Returns:
            Dictionary of newly created parent sections
        """
        from bengal.utils.url_normalization import join_url_paths

        parent_sections: dict[str, Section] = {}

        # Find all unique parent paths that have multiple IMMEDIATE children
        # e.g., "api" is parent of "api/python" and "api/bengal-demo-commerce"
        # but NOT "api/python/analysis" (that's a grandchild, child of "api/python")
        parent_counts: dict[str, list[str]] = {}
        for section_path in sections:
            parts = section_path.split("/")
            # Only count IMMEDIATE children (exactly one level deep from top-level)
            # "api/python" → 2 parts, parent "api" ✓
            # "api/python/analysis" → 3 parts (skip for top-level parent aggregation)
            if len(parts) == 2:
                parent = parts[0]
                parent_counts.setdefault(parent, []).append(section_path)

        # Create parent sections for paths with 2+ immediate children
        for parent_path, child_paths in parent_counts.items():
            # Skip if parent already exists or only one immediate child
            if parent_path in sections or len(child_paths) < 2:
                continue

            # Determine type based on children (prefer api-reference)
            child_types = [sections[cp].metadata.get("type", "api-reference") for cp in child_paths]
            section_type = "api-reference" if "api-reference" in child_types else child_types[0]

            # Create the parent section
            parent_section = Section.create_virtual(
                name=parent_path,
                relative_url=join_url_paths(parent_path),
                title=f"{parent_path.replace('-', ' ').title()} Reference",
                metadata={
                    "type": section_type,
                    "weight": 50,
                    "icon": "book-open",
                    "description": f"Browse all {parent_path} documentation.",
                    "is_aggregating_section": True,
                },
            )

            # Link only immediate child sections as subsections
            # (nested sections like api/python/analysis are already children of api/python)
            for child_path in child_paths:
                child_section = sections[child_path]
                parent_section.add_subsection(child_section)

            parent_sections[parent_path] = parent_section
            logger.debug(
                "autodoc_aggregating_section_created",
                parent=parent_path,
                children=child_paths,
            )

        return parent_sections

    def _create_index_pages(self, sections: dict[str, Section]) -> list[Page]:
        """
        Create index pages for sections that need them.

        Args:
            sections: Section dictionary to process

        Returns:
            List of created index pages (to add to main pages list)
        """
        created_pages: list[Page] = []

        for section_path, section in sections.items():
            if section.index_page is not None:
                continue

            # output_path must be absolute for correct URL generation
            output_path = self.site.output_dir / f"{section_path}/index.html"

            # Determine template and page type based on section metadata
            section_type = section.metadata.get("type", "api-reference")
            template_name = f"{section_type}/section-index"

            # Create page with deferred rendering - HTML rendered in rendering phase
            # NOTE: We pass autodoc_element=None for section-index pages because:
            # - Templates expect 'element' to be a DocElement with properties like
            #   element_type, qualified_name, children, description, etc.
            # - Section objects don't have these properties and would cause StrictUndefined errors
            # - The section data is already available via the 'section' template variable
            index_page = Page.create_virtual(
                source_id=f"__virtual__/{section_path}/section-index.md",
                title=section.title,
                metadata={
                    "type": section_type,
                    "is_section_index": True,
                    "description": section.metadata.get("description", ""),
                    # Autodoc deferred rendering metadata
                    "is_autodoc": True,
                    "autodoc_element": None,  # Section data available via 'section' variable
                    "_autodoc_template": template_name,
                },
                rendered_html=None,  # Deferred - rendered in rendering phase with full context
                template_name=template_name,
                output_path=output_path,
            )

            # Set site reference for URL computation
            index_page._site = self.site
            # Set section reference via setter (handles virtual sections with URL-based lookup)
            index_page._section = section

            # Set as section index directly (don't use add_page which would
            # trigger index collision detection)
            section.index_page = index_page
            section.pages.append(index_page)
            created_pages.append(index_page)

        return created_pages

    def _render_section_index(self, section: Section) -> str:
        """Render section index page HTML."""
        section_type = section.metadata.get("type", "api-reference")
        template_name = f"{section_type}/section-index"

        # Create a page-like context for templates that expect a 'page' variable
        page_context = _PageContext(
            title=section.title,
            metadata={
                "type": section_type,
                "is_section_index": True,
                "description": section.metadata.get("description", ""),
            },
            tags=[],
            relative_url=section.relative_url,
            section=section,
        )

        # Try theme template first
        try:
            template = self.template_env.get_template(f"{template_name}.html")
            return template.render(
                section=section,
                page=page_context,
                config=self.config,
                site=self.site,
            )
        except Exception as e:
            # Fall back to generic section-index or legacy path
            try:
                template = self.template_env.get_template("api-reference/section-index.html")
                return template.render(
                    section=section,
                    page=page_context,
                    config=self.config,
                    site=self.site,
                )
            except Exception as e2:
                try:
                    template = self.template_env.get_template("section-index.html")
                    return template.render(
                        section=section,
                        page=page_context,
                        config=self.config,
                        site=self.site,
                    )
                except Exception as e3:
                    logger.warning(
                        "autodoc_template_fallback",
                        template=template_name,
                        section=section.name,
                        error=self._relativize_paths(str(e)),
                        secondary_error=self._relativize_paths(str(e2)),
                        tertiary_error=self._relativize_paths(str(e3)),
                    )
                    # Fallback rendering with cards
                    return self._render_section_index_fallback(section)

    def _render_section_index_fallback(self, section: Section) -> str:
        """Fallback card-based rendering when template fails."""
        from bengal.rendering.template_functions.icons import icon

        # SVG icons for cards (already preloaded during site build)
        folder_icon = icon("folder", size=20, css_class="icon-muted")
        code_icon = icon("code", size=16, css_class="icon-muted")

        subsections_cards = []
        for s in section.sorted_subsections:
            desc = s.metadata.get("description", "")
            desc_preview = (desc[:80] + "..." if len(desc) > 80 else desc) if desc else ""
            child_count = len(s.subsections) + len(s.pages)
            subsections_cards.append(f'''
      <a href="{s.relative_url}" class="api-package-card">
        <span class="api-package-card__icon">{folder_icon}</span>
        <span class="api-package-card__name">{s.name}</span>
        {f'<span class="api-package-card__description">{desc_preview}</span>' if desc_preview else ""}
        <span class="api-package-card__meta">
          {child_count} item{"s" if child_count != 1 else ""}
        </span>
      </a>''')

        module_cards = []
        for p in section.sorted_pages:
            if p == section.index_page:
                continue
            desc = p.metadata.get("description", "")
            desc_preview = (desc[:80] + "..." if len(desc) > 80 else desc) if desc else ""
            element_type = p.metadata.get("element_type", "")
            module_cards.append(f'''
      <a href="{p.relative_url}" class="api-module-card">
        <span class="api-module-card__icon">{code_icon}</span>
        <span class="api-module-card__name">{p.title}</span>
        {f'<span class="api-module-card__description">{desc_preview}</span>' if desc_preview else ""}
        {f'<span class="api-module-card__badges"><span class="api-badge--mini">{element_type}</span></span>' if element_type else ""}
      </a>''')

        subsections_section = ""
        if subsections_cards:
            subsections_section = f"""
  <section class="api-section api-section--packages">
    <h2 class="api-section__title">Packages</h2>
    <div class="api-grid api-grid--packages">
      {"".join(subsections_cards)}
    </div>
  </section>"""

        modules_section = ""
        if module_cards:
            modules_section = f"""
  <section class="api-section api-section--modules">
    <h2 class="api-section__title">Modules</h2>
    <div class="api-grid api-grid--modules">
      {"".join(module_cards)}
    </div>
  </section>"""

        desc_html = ""
        section_desc = section.metadata.get("description", "")
        if section_desc:
            desc_html = f'<p class="api-section-header__description">{section_desc}</p>'

        return f"""
<div class="api-explorer api-explorer--index">
  <header class="api-section-header">
    <h1 class="api-section-header__title">{section.title}</h1>
    {desc_html}
  </header>
  {subsections_section}
  {modules_section}
</div>
"""

    def _extract_python(self) -> list[DocElement]:
        """Extract Python API documentation."""
        from bengal.autodoc.extractors.python import PythonExtractor

        source_dirs = self.python_config.get("source_dirs", [])
        exclude_patterns = self.python_config.get("exclude", [])

        extractor = PythonExtractor(exclude_patterns=exclude_patterns, config=self.python_config)
        all_elements = []

        for source_dir in source_dirs:
            source_path = Path(source_dir)
            if not source_path.exists():
                logger.warning(
                    "autodoc_source_dir_not_found",
                    path=str(source_path),
                    type="python",
                )
                continue

            elements = extractor.extract(source_path)
            all_elements.extend(elements)

        logger.debug("autodoc_python_extracted", count=len(all_elements))
        return all_elements

    def _extract_cli(self) -> list[DocElement]:
        """Extract CLI documentation."""
        import importlib

        from bengal.autodoc.extractors.cli import CLIExtractor

        app_module = self.cli_config.get("app_module")
        if not app_module:
            logger.warning("autodoc_cli_no_app_module")
            return []

        framework = self.cli_config.get("framework", "click")
        include_hidden = self.cli_config.get("include_hidden", False)

        # Load CLI app from module path (e.g., "bengal.cli:main")
        try:
            module_path, attr_name = app_module.split(":")
            module = importlib.import_module(module_path)
            cli_app = getattr(module, attr_name)
        except (ValueError, ImportError, AttributeError) as e:
            logger.warning("autodoc_cli_load_failed", app_module=app_module, error=str(e))
            return []

        # Extract documentation
        extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
        elements = extractor.extract(cli_app)

        logger.debug("autodoc_cli_extracted", count=len(elements))
        return elements

    def _extract_openapi(self) -> list[DocElement]:
        """Extract OpenAPI documentation."""
        from bengal.autodoc.extractors.openapi import OpenAPIExtractor

        spec_file = self.openapi_config.get("spec_file")
        if not spec_file:
            logger.warning("autodoc_openapi_no_spec_file")
            return []

        spec_path = Path(spec_file)
        if not spec_path.exists():
            logger.warning("autodoc_openapi_spec_not_found", path=str(spec_path))
            return []

        # Extract documentation
        extractor = OpenAPIExtractor()
        elements = extractor.extract(spec_path)

        logger.debug("autodoc_openapi_extracted", count=len(elements))
        return elements
