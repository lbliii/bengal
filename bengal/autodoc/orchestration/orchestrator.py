"""
Virtual page orchestrator for autodoc.

Generates API documentation as virtual Page and Section objects
that integrate directly into the build pipeline without intermediate
markdown files.

This is the new architecture that replaces markdown-based autodoc generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from jinja2 import Environment

from bengal.autodoc.base import DocElement
from bengal.autodoc.orchestration.extractors import (
    extract_cli,
    extract_openapi,
    extract_python,
)
from bengal.autodoc.orchestration.index_pages import create_index_pages
from bengal.autodoc.orchestration.page_builders import (
    create_pages,
    find_parent_section,
    get_element_metadata,
)
from bengal.autodoc.orchestration.result import AutodocRunResult
from bengal.autodoc.orchestration.section_builders import (
    create_aggregating_parent_sections,
    create_cli_sections,
    create_openapi_sections,
    create_python_sections,
)
from bengal.autodoc.orchestration.template_env import create_template_environment
from bengal.autodoc.orchestration.utils import normalize_autodoc_config, slugify
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.utils.hashing import hash_dict
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


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
        self.normalized_config = normalize_autodoc_config(site.config)
        self.python_config = self.config.get("python", {})
        self.cli_config = self.config.get("cli", {})
        self.openapi_config = self.config.get("openapi", {})
        # Performance: do not build a Jinja environment unless we actually
        # generate autodoc pages. Content discovery may probe autodoc enablement
        # even when autodoc is disabled, and environment setup is expensive.
        self.template_env: Environment | None = None
        # Performance: these values are used in tight loops during generation.
        # Cache them per orchestrator instance (one per build).
        self._output_prefix_cache: dict[str, str] = {}
        self._openapi_prefix_cache: str | None = None
        # Ephemeral: used by the build cache integration to persist extracted elements
        # for incremental builds (rebuild virtual pages without re-parsing sources).
        self._last_extracted_elements: dict[str, list[DocElement]] = {}

    def get_cache_payload(self) -> dict[str, Any]:
        """
        Return a JSON-serializable payload representing the latest extracted elements.

        Intended for BuildCache persistence. Only valid after generate().
        """
        autodoc_cfg = self.site.config.get("autodoc", {})
        cfg_hash = hash_dict(autodoc_cfg) if isinstance(autodoc_cfg, dict) else ""
        return {
            "version": 2,  # Bumped: v2 uses dict format for ParameterInfo/RaisesInfo
            "autodoc_config_hash": cfg_hash,
            "elements": {
                k: [e.to_dict() for e in v]
                for k, v in (self._last_extracted_elements or {}).items()
            },
        }

    def generate_from_cache_payload(
        self, payload: dict[str, Any]
    ) -> tuple[list[Page], list[Section], AutodocRunResult]:
        """
        Rebuild autodoc virtual pages/sections from a cached extraction payload.

        This avoids expensive re-extraction (AST parsing, import/inspect) when sources
        are unchanged, while still creating the in-memory Page/Section objects needed
        for rendering.
        """
        result = AutodocRunResult()

        elements_section = payload.get("elements") if isinstance(payload, dict) else None
        if not isinstance(elements_section, dict):
            return [], [], result

        python_elements = [
            DocElement.from_dict(e)
            for e in (elements_section.get("python") or [])
            if isinstance(e, dict)
        ]
        cli_elements = [
            DocElement.from_dict(e)
            for e in (elements_section.get("cli") or [])
            if isinstance(e, dict)
        ]
        openapi_elements = [
            DocElement.from_dict(e)
            for e in (elements_section.get("openapi") or [])
            if isinstance(e, dict)
        ]

        # Reuse the normal generation pipeline, but skip extraction.
        all_elements: list[DocElement] = []
        all_sections: dict[str, Section] = {}
        all_pages: list[Page] = []

        if (
            python_elements
            and self.python_config.get("virtual_pages", True)
            and self.python_config.get("enabled", True)
        ):
            all_elements.extend(python_elements)
            result.extracted += len(python_elements)
            python_sections = create_python_sections(
                python_elements, self.site, self._resolve_output_prefix
            )
            all_sections.update(python_sections)
            python_pages, _ = create_pages(
                python_elements,
                python_sections,
                self.site,
                "python",
                self._resolve_output_prefix,
                lambda e, dt: get_element_metadata(e, dt, self._resolve_output_prefix),
                lambda e, s, dt: find_parent_section(e, s, dt, self._resolve_output_prefix),
                result,
            )
            all_pages.extend(python_pages)
            result.rendered += len(python_pages)

        if (
            cli_elements
            and self.cli_config.get("virtual_pages", True)
            and self.cli_config.get("enabled", True)
        ):
            all_elements.extend(cli_elements)
            result.extracted += len(cli_elements)
            cli_sections = create_cli_sections(cli_elements, self.site, self._resolve_output_prefix)
            all_sections.update(cli_sections)
            cli_pages, _ = create_pages(
                cli_elements,
                cli_sections,
                self.site,
                "cli",
                self._resolve_output_prefix,
                lambda e, dt: get_element_metadata(e, dt, self._resolve_output_prefix),
                lambda e, s, dt: find_parent_section(e, s, dt, self._resolve_output_prefix),
                result,
            )
            all_pages.extend(cli_pages)
            result.rendered += len(cli_pages)

        if (
            openapi_elements
            and self.openapi_config.get("virtual_pages", True)
            and self.openapi_config.get("enabled", True)
        ):
            all_elements.extend(openapi_elements)
            result.extracted += len(openapi_elements)
            openapi_sections = create_openapi_sections(
                openapi_elements, self.site, self._resolve_output_prefix, all_sections
            )
            all_sections.update(openapi_sections)
            openapi_pages, _ = create_pages(
                openapi_elements,
                openapi_sections,
                self.site,
                "openapi",
                self._resolve_output_prefix,
                lambda e, dt: get_element_metadata(e, dt, self._resolve_output_prefix),
                lambda e, s, dt: find_parent_section(e, s, dt, self._resolve_output_prefix),
                result,
            )
            all_pages.extend(openapi_pages)
            result.rendered += len(openapi_pages)

        if not all_elements:
            return [], [], result

        parent_sections = create_aggregating_parent_sections(all_sections)
        all_sections.update(parent_sections)

        index_pages = create_index_pages(all_sections, self.site)
        all_pages.extend(index_pages)

        root_sections = [section for section in all_sections.values() if section.parent is None]
        return all_pages, root_sections, result

    def _ensure_template_env(self) -> Environment:
        """Create the autodoc Jinja environment lazily (only when needed)."""
        if self.template_env is None:
            self.template_env = create_template_environment(self.site)
        return self.template_env

    def _derive_python_prefix(self) -> str:
        """
        Derive output prefix from Python source directory.

        If source_dirs has exactly one entry, derives prefix from the package
        name (e.g., source_dirs: ["bengal"] → "api/bengal").

        Returns:
            Derived prefix (e.g., "api/bengal") or "api/python" as fallback
        """
        source_dirs = self.python_config.get("source_dirs", [])

        # If exactly one source directory, derive from its name
        if len(source_dirs) == 1:
            source_dir = source_dirs[0]
            # Extract package name from path (last component)
            package_name = Path(source_dir).name
            if package_name and package_name != ".":
                return f"api/{slugify(package_name)}"

        # Fallback for multiple dirs or edge cases
        return "api/python"

    def _derive_openapi_prefix(self) -> str:
        """
        Derive output prefix from OpenAPI spec title.

        Loads the OpenAPI spec file (if exists), extracts info.title,
        slugifies it, and prepends "api/".

        Returns:
            Derived prefix (e.g., "api/commerce") or "api/rest" as fallback
        """
        if self._openapi_prefix_cache is not None:
            return self._openapi_prefix_cache

        spec_file = self.openapi_config.get("spec_file")
        if not spec_file:
            self._openapi_prefix_cache = "api/rest"
            return self._openapi_prefix_cache

        spec_path = self.site.root_path / spec_file
        if not spec_path.exists():
            logger.debug("autodoc_openapi_spec_not_found_for_prefix", path=str(spec_path))
            self._openapi_prefix_cache = "api/rest"
            return self._openapi_prefix_cache

        try:
            with open(spec_path, encoding="utf-8") as f:
                spec = yaml.safe_load(f)

            title = spec.get("info", {}).get("title", "")
            if not title:
                self._openapi_prefix_cache = "api/rest"
                return self._openapi_prefix_cache

            slug = slugify(title)
            self._openapi_prefix_cache = f"api/{slug}"
            return self._openapi_prefix_cache
        except Exception as e:
            logger.debug(
                "autodoc_openapi_prefix_derivation_failed",
                path=str(spec_path),
                error=str(e),
            )
            self._openapi_prefix_cache = "api/rest"
            return self._openapi_prefix_cache

    def _resolve_output_prefix(self, doc_type: str) -> str:
        """
        Resolve output prefix for a documentation type.

        Checks explicit config value first, then applies type-specific defaults:
        - python: auto-derived from source_dirs (e.g., "api/bengal"), or "api/python"
        - openapi: auto-derived from spec title, or "api/rest"
        - cli: "cli"

        Args:
            doc_type: Documentation type ("python", "openapi", "cli")

        Returns:
            Resolved output prefix (e.g., "api/bengal", "api/commerce", "cli")
        """
        cached = self._output_prefix_cache.get(doc_type)
        if cached is not None:
            return cached

        if doc_type == "python":
            explicit = self.python_config.get("output_prefix")
            resolved = explicit.strip("/") if explicit else self._derive_python_prefix()

        elif doc_type == "openapi":
            explicit = self.openapi_config.get("output_prefix")
            resolved = explicit.strip("/") if explicit else self._derive_openapi_prefix()

        elif doc_type == "cli":
            explicit = self.cli_config.get("output_prefix")
            resolved = explicit.strip("/") if explicit else "cli"

        else:
            resolved = f"api/{doc_type}"

        self._output_prefix_cache[doc_type] = resolved
        return resolved

    def is_enabled(self) -> bool:
        """Check if virtual autodoc is enabled for any type."""
        # Performance + ergonomics: treat autodoc as opt-in.
        # If the site does not define an `autodoc` section, do not run autodoc.
        if not isinstance(self.config, dict) or not self.config:
            return False

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
        self._last_extracted_elements = {}

        # 1. Extract Python documentation
        # Virtual pages are now the default (and only) option
        if self.python_config.get("virtual_pages", True) and self.python_config.get(
            "enabled", True
        ):
            try:
                python_elements = extract_python(self.site, self.python_config)
                if python_elements:
                    self._last_extracted_elements["python"] = python_elements
                    all_elements.extend(python_elements)
                    result.extracted += len(python_elements)
                    python_sections = create_python_sections(
                        python_elements, self.site, self._resolve_output_prefix
                    )
                    all_sections.update(python_sections)
                    python_pages, page_result = create_pages(
                        python_elements,
                        python_sections,
                        self.site,
                        "python",
                        self._resolve_output_prefix,
                        lambda e, dt: get_element_metadata(e, dt, self._resolve_output_prefix),
                        lambda e, s, dt: find_parent_section(e, s, dt, self._resolve_output_prefix),
                        result,
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
                    from bengal.errors import BengalDiscoveryError

                    raise BengalDiscoveryError(
                        f"Python extraction failed in strict mode: {e}",
                        suggestion="Fix Python source code issues or disable strict mode",
                        original_error=e,
                    ) from e

        # 2. Extract CLI documentation
        # Virtual pages are now the default (and only) option
        if self.cli_config.get("virtual_pages", True) and self.cli_config.get("enabled", True):
            try:
                cli_elements = extract_cli(self.site, self.cli_config)
                if cli_elements:
                    self._last_extracted_elements["cli"] = cli_elements
                    all_elements.extend(cli_elements)
                    result.extracted += len(cli_elements)
                    cli_sections = create_cli_sections(
                        cli_elements, self.site, self._resolve_output_prefix
                    )
                    all_sections.update(cli_sections)
                    cli_pages, _ = create_pages(
                        cli_elements,
                        cli_sections,
                        self.site,
                        "cli",
                        self._resolve_output_prefix,
                        lambda e, dt: get_element_metadata(e, dt, self._resolve_output_prefix),
                        lambda e, s, dt: find_parent_section(e, s, dt, self._resolve_output_prefix),
                        result,
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
                    from bengal.errors import BengalDiscoveryError

                    raise BengalDiscoveryError(
                        f"CLI extraction failed in strict mode: {e}",
                        suggestion="Fix CLI source code issues or disable strict mode",
                        original_error=e,
                    ) from e

        # 3. Extract OpenAPI documentation
        # Pass existing sections so OpenAPI can reuse "api" section if Python already created it
        # Virtual pages are now the default (and only) option
        if self.openapi_config.get("virtual_pages", True) and self.openapi_config.get(
            "enabled", True
        ):
            try:
                openapi_elements = extract_openapi(self.site, self.openapi_config)
                if openapi_elements:
                    self._last_extracted_elements["openapi"] = openapi_elements
                    all_elements.extend(openapi_elements)
                    result.extracted += len(openapi_elements)
                    openapi_sections = create_openapi_sections(
                        openapi_elements, self.site, self._resolve_output_prefix, all_sections
                    )
                    all_sections.update(openapi_sections)
                    openapi_pages, _ = create_pages(
                        openapi_elements,
                        openapi_sections,
                        self.site,
                        "openapi",
                        self._resolve_output_prefix,
                        lambda e, dt: get_element_metadata(e, dt, self._resolve_output_prefix),
                        lambda e, s, dt: find_parent_section(e, s, dt, self._resolve_output_prefix),
                        result,
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
                    from bengal.errors import BengalDiscoveryError

                    raise BengalDiscoveryError(
                        f"OpenAPI extraction failed in strict mode: {e}",
                        suggestion="Fix OpenAPI specification issues or disable strict mode",
                        original_error=e,
                    ) from e

        if not all_elements:
            logger.info("autodoc_no_elements_found")
            if strict_mode and result.failed_extract > 0:
                from bengal.errors import BengalDiscoveryError

                raise BengalDiscoveryError(
                    f"Autodoc strict mode: {result.failed_extract} extraction failures, "
                    f"no elements produced",
                    suggestion="Fix extraction errors above or disable strict mode",
                )
            return [], [], result

        # 4. Create aggregating parent sections for shared prefixes
        # (e.g., /api/ for /api/python/ and /api/openapi/)
        parent_sections = create_aggregating_parent_sections(all_sections)
        all_sections.update(parent_sections)

        # 5. Create index pages for all sections
        index_pages = create_index_pages(all_sections, self.site)
        all_pages.extend(index_pages)

        # Check strict mode after all processing
        if strict_mode and result.has_failures():
            from bengal.errors import BengalDiscoveryError

            raise BengalDiscoveryError(
                f"Autodoc strict mode: {result.failed_extract} extraction failures, "
                f"{result.failed_render} rendering failures",
                suggestion="Fix extraction/rendering errors above or disable strict mode",
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
        # NOTE: Use default=True to match the generation logic above
        for doc_type, config in [
            ("python", self.python_config),
            ("openapi", self.openapi_config),
            ("cli", self.cli_config),
        ]:
            if not config.get("enabled", True):
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
