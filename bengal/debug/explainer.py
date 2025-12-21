"""
Page explainer - generates explanations for how pages are built.

Provides complete traceability for any page: source file, template chain,
dependencies, shortcodes, cache status, output location, and diagnostics.

Key Concepts:
    - Read-only introspection: No side effects, pure analysis
    - Template chain resolution: Shows full inheritance
    - Dependency tracking: Content, templates, data, assets
    - Cache status: HIT/MISS/STALE with reasons

Related Modules:
    - bengal.debug.models: Data models for explanation components
    - bengal.debug.reporter: Rich terminal output formatting
    - bengal.rendering.template_engine: Template resolution
    - bengal.cache.build_cache: Cache status introspection

See Also:
    - plan/active/rfc-explain-page.md: Design RFC
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.debug.models import (
    CacheInfo,
    DependencyInfo,
    Issue,
    OutputInfo,
    PageExplanation,
    ShortcodeUsage,
    SourceInfo,
    TemplateInfo,
)
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEngineProtocol

logger = get_logger(__name__)

# Pattern to match shortcode/directive usage in content
# Matches MyST directives like ```{name} and :::name
DIRECTIVE_PATTERN = re.compile(
    r"(?:```\{(\w+)\}|:::(\w+))",
    re.MULTILINE,
)


class PageExplainer:
    """
    Generate explanations for how pages are built.

    Provides complete traceability for any page including source info,
    template chain, dependencies, cache status, and diagnostics.

    Creation:
        Direct instantiation: PageExplainer(site, cache=None, template_engine=None)
            - Created by CLI explain command
            - Requires Site instance with discovered content

    Attributes:
        site: Site instance with pages and configuration
        cache: Optional BuildCache for cache status
        template_engine: Optional TemplateEngineProtocol for template resolution

    Thread Safety:
        Thread-safe. Read-only operations only.

    Examples:
        explainer = PageExplainer(site)
        explanation = explainer.explain("docs/guide.md")
        print(explanation.source.size_human)
    """

    def __init__(
        self,
        site: Site,
        cache: BuildCache | None = None,
        template_engine: TemplateEngineProtocol | None = None,
    ) -> None:
        """
        Initialize the page explainer.

        Args:
            site: Site instance with pages and configuration
            cache: Optional BuildCache for cache status introspection
            template_engine: Optional TemplateEngineProtocol for template resolution
        """
        self.site = site
        self.cache = cache
        self.template_engine = template_engine

    def explain(
        self,
        page_path: str,
        verbose: bool = False,
        diagnose: bool = False,
    ) -> PageExplanation:
        """
        Generate complete explanation for a page.

        Args:
            page_path: Path to the page (relative to content dir or source_path)
            verbose: Include additional details (timing, template variables)
            diagnose: Check for issues (broken links, missing assets)

        Returns:
            PageExplanation with all available information

        Raises:
            ValueError: If page not found
        """
        page = self._find_page(page_path)
        if page is None:
            from bengal.utils.exceptions import BengalContentError

            raise BengalContentError(
                f"Page not found: {page_path}\n"
                f"Searched in {len(self.site.pages)} pages\n"
                f"Tip: Run 'bengal site build' first to discover content",
                suggestion="Run 'bengal site build' first to discover content, or check the page path",
            )

        explanation = PageExplanation(
            source=self._get_source_info(page),
            frontmatter=dict(page.metadata) if page.metadata else {},
            template_chain=self._resolve_template_chain(page),
            dependencies=self._get_dependencies(page),
            shortcodes=self._get_shortcode_usage(page),
            cache=self._get_cache_status(page),
            output=self._get_output_info(page),
        )

        if diagnose:
            explanation.issues = self._diagnose_issues(page)

        return explanation

    def _find_page(self, page_path: str) -> Page | None:
        """
        Find a page by path.

        Searches by:
        1. Exact source_path match
        2. Relative path match (without content/ prefix)
        3. Partial path match (filename or partial path)

        Args:
            page_path: Path to search for

        Returns:
            Page if found, None otherwise
        """
        search_path = Path(page_path)

        for page in self.site.pages:
            # Exact match
            if page.source_path == search_path:
                return page

            # Match without content/ prefix
            try:
                content_dir = self.site.root_path / "content"
                rel_path = page.source_path.relative_to(content_dir)
                if rel_path == search_path:
                    return page
            except ValueError:
                pass

            # Partial match (ends with search path)
            if str(page.source_path).endswith(str(search_path)):
                return page

        return None

    def _get_source_info(self, page: Page) -> SourceInfo:
        """Get source file information."""
        source_path = page.source_path

        # Handle virtual pages
        if page.is_virtual:
            return SourceInfo(
                path=source_path,
                size_bytes=len(page.content.encode()) if page.content else 0,
                line_count=page.content.count("\n") + 1 if page.content else 0,
                modified=None,
                encoding="UTF-8",
            )

        # Regular file
        try:
            # Try to get absolute path
            if source_path.is_absolute():
                abs_path = source_path
            else:
                abs_path = self.site.root_path / source_path

            if abs_path.exists():
                stat = abs_path.stat()
                content = abs_path.read_text(encoding="utf-8")
                return SourceInfo(
                    path=source_path,
                    size_bytes=stat.st_size,
                    line_count=content.count("\n") + 1,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    encoding="UTF-8",
                )
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("source_info_error", path=str(source_path), error=str(e))

        # Fallback: use content from page object
        return SourceInfo(
            path=source_path,
            size_bytes=len(page.content.encode()) if page.content else 0,
            line_count=page.content.count("\n") + 1 if page.content else 0,
            modified=None,
            encoding="UTF-8",
        )

    def _resolve_template_chain(self, page: Page) -> list[TemplateInfo]:
        """
        Resolve the complete template inheritance chain.

        Args:
            page: Page to resolve templates for

        Returns:
            List of TemplateInfo in inheritance order (child first)
        """
        chain: list[TemplateInfo] = []

        # Get the template name for this page
        template_name = self._get_template_name(page)
        if not template_name:
            return chain

        # If we have a template engine, use it for resolution
        if self.template_engine:
            try:
                return self._resolve_chain_from_engine(template_name)
            except Exception as e:
                logger.debug("template_chain_resolution_failed", error=str(e))

        # Fallback: basic info without full chain
        chain.append(
            TemplateInfo(
                name=template_name,
                source_path=None,
                theme=self.site.theme,
                extends=None,
                includes=[],
            )
        )

        return chain

    def _get_template_name(self, page: Page) -> str | None:
        """Get the template name for a page."""
        # Check for explicit template in metadata
        if page.metadata.get("template"):
            return str(page.metadata["template"])

        # Check for template override on virtual pages
        if page.is_virtual and page.template_name:
            return page.template_name

        # Check page type for template inference
        page_core = page.core if hasattr(page, "core") and page.core else None
        page_type = page.metadata.get("type") or (page_core.type if page_core else None)
        if page_type:
            return f"{page_type}.html"

        # Default template
        return "page.html"

    def _resolve_chain_from_engine(self, template_name: str) -> list[TemplateInfo]:
        """Resolve template chain using the template engine."""
        chain: list[TemplateInfo] = []

        # Find the template file
        if self.template_engine is None:
            return chain
        template_path = self.template_engine._find_template_path(template_name)

        info = TemplateInfo(
            name=template_name,
            source_path=template_path,
            theme=self._get_theme_from_path(template_path) if template_path else None,
            extends=None,
            includes=[],
        )

        # Try to parse template for extends and includes
        if template_path and template_path.exists():
            try:
                content = template_path.read_text()
                info.extends = self._extract_extends(content)
                info.includes = self._extract_includes(content)
            except (OSError, UnicodeDecodeError):
                pass

        chain.append(info)

        # Follow extends chain
        if info.extends:
            parent_chain = self._resolve_chain_from_engine(info.extends)
            chain.extend(parent_chain)

        return chain

    def _get_theme_from_path(self, template_path: Path | None) -> str | None:
        """Extract theme name from template path."""
        if not template_path:
            return None

        path_str = str(template_path)

        # Check for theme in path (e.g., themes/default/templates/...)
        if "themes/" in path_str:
            parts = path_str.split("themes/")
            if len(parts) > 1:
                theme_part = parts[1].split("/")[0]
                return theme_part

        return None

    def _extract_extends(self, content: str) -> str | None:
        """Extract extends directive from Jinja2 template."""
        # Match {% extends "base.html" %} or {% extends 'base.html' %}
        match = re.search(r'{%\s*extends\s*["\']([^"\']+)["\']\s*%}', content)
        return match.group(1) if match else None

    def _extract_includes(self, content: str) -> list[str]:
        """Extract include directives from Jinja2 template."""
        # Match {% include "partial.html" %} patterns
        matches = re.findall(r'{%\s*include\s*["\']([^"\']+)["\']\s*%}', content)
        return matches

    def _get_dependencies(self, page: Page) -> DependencyInfo:
        """Get all dependencies for a page."""
        deps = DependencyInfo()

        # Content dependencies
        if page._section:
            section = page._section
            if hasattr(section, "index_page") and section.index_page:
                deps.content.append(str(section.index_page.source_path))

        # Template dependencies (from chain)
        for tpl in self._resolve_template_chain(page):
            if tpl.source_path:
                deps.templates.append(str(tpl.source_path))
            for include in tpl.includes:
                deps.templates.append(include)

        # Data file dependencies
        if page.metadata.get("data"):
            data_refs = page.metadata["data"]
            if isinstance(data_refs, str):
                deps.data.append(data_refs)
            elif isinstance(data_refs, list):
                deps.data.extend(data_refs)

        # Asset references from content
        if page.content:
            deps.assets = self._extract_asset_refs(page.content)

        # Include dependencies from shortcodes
        for shortcode in self._get_shortcode_usage(page):
            if shortcode.name == "include" and "file" in shortcode.args:
                deps.includes.append(shortcode.args["file"])

        # Cache-tracked dependencies
        if self.cache:
            page_key = str(page.source_path)
            cached_deps = self.cache.dependencies.get(page_key, set())
            for dep in cached_deps:
                if dep not in deps.templates and dep not in deps.data:
                    # Add to appropriate category based on extension
                    if dep.endswith((".html", ".jinja2", ".jinja")):
                        if dep not in deps.templates:
                            deps.templates.append(dep)
                    elif dep.endswith((".yaml", ".yml", ".json", ".toml")) and dep not in deps.data:
                        deps.data.append(dep)

        return deps

    def _extract_asset_refs(self, content: str) -> list[str]:
        """Extract asset references from content."""
        assets: list[str] = []

        # Match markdown images: ![alt](path)
        img_pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
        for match in img_pattern.finditer(content):
            src = match.group(1)
            # Skip external URLs
            if not src.startswith(("http://", "https://", "data:")):
                assets.append(src)

        # Match HTML img tags
        html_img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']')
        for match in html_img_pattern.finditer(content):
            src = match.group(1)
            if not src.startswith(("http://", "https://", "data:")):
                assets.append(src)

        return assets

    def _get_shortcode_usage(self, page: Page) -> list[ShortcodeUsage]:
        """Extract shortcode/directive usage from page content."""
        if not page.content:
            return []

        usages: dict[str, ShortcodeUsage] = {}

        for match in DIRECTIVE_PATTERN.finditer(page.content):
            # Get name from either capture group
            name = match.group(1) or match.group(2)
            line = page.content[: match.start()].count("\n") + 1

            if name not in usages:
                usages[name] = ShortcodeUsage(name=name, count=0, lines=[])

            usages[name].count += 1
            usages[name].lines.append(line)

        return sorted(usages.values(), key=lambda x: -x.count)

    def _get_cache_status(self, page: Page) -> CacheInfo:
        """Get cache status for a page."""
        page_key = str(page.source_path)

        # No cache available
        if not self.cache:
            return CacheInfo(
                status="UNKNOWN",
                reason="No cache available",
                cache_key=None,
            )

        # Check if page is in cache
        content_cached = page_key in self.cache.parsed_content
        rendered_cached = page_key in self.cache.rendered_output

        if not content_cached and not rendered_cached:
            return CacheInfo(
                status="MISS",
                reason="Not in cache",
                cache_key=page_key,
                content_cached=False,
                rendered_cached=False,
            )

        # Check if file has changed
        if self.cache.is_changed(page.source_path):
            return CacheInfo(
                status="STALE",
                reason="Source file modified",
                cache_key=page_key,
                content_cached=content_cached,
                rendered_cached=rendered_cached,
            )

        # Check dependencies
        deps = self.cache.dependencies.get(page_key, set())
        for dep in deps:
            dep_path = Path(dep)
            if dep_path.exists() and self.cache.is_changed(dep_path):
                return CacheInfo(
                    status="STALE",
                    reason=f"Dependency changed: {dep}",
                    cache_key=page_key,
                    content_cached=content_cached,
                    rendered_cached=rendered_cached,
                )

        # Cache hit
        return CacheInfo(
            status="HIT",
            reason=None,
            cache_key=page_key,
            content_cached=content_cached,
            rendered_cached=rendered_cached,
        )

    def _get_output_info(self, page: Page) -> OutputInfo:
        """Get output information for a page."""
        # Get URL
        url = page.url if hasattr(page, "url") else "/"

        # Get output path
        output_path = page.output_path

        # Check if output exists and get size
        size_bytes = None
        if output_path:
            full_path = self.site.output_dir / output_path
            if full_path.exists():
                size_bytes = full_path.stat().st_size

        return OutputInfo(
            path=output_path,
            url=url,
            size_bytes=size_bytes,
        )

    def _diagnose_issues(self, page: Page) -> list[Issue]:
        """Diagnose potential issues with a page."""
        issues: list[Issue] = []

        # Check template exists
        template_name = self._get_template_name(page)
        if template_name and self.template_engine:
            template_path = self.template_engine._find_template_path(template_name)
            if not template_path:
                issues.append(
                    Issue(
                        severity="error",
                        issue_type="template_not_found",
                        message=f"Template '{template_name}' not found",
                        details={
                            "specified_in": "frontmatter"
                            if page.metadata.get("template")
                            else "default",
                            "searched_dirs": [str(d) for d in self.template_engine.template_dirs],
                        },
                        suggestion=f"Create {template_name} or use an existing template",
                    )
                )

        # Check internal links
        if page.content:
            link_pattern = re.compile(r"\[([^\]]+)\]\((/[^)]+)\)")
            for match in link_pattern.finditer(page.content):
                link_text, link_target = match.groups()
                line = page.content[: match.start()].count("\n") + 1

                # Check if target page exists
                target_exists = any(
                    p.url == link_target or p.url == link_target.rstrip("/")
                    for p in self.site.pages
                )
                if not target_exists and not link_target.startswith(("#", "http")):
                    issues.append(
                        Issue(
                            severity="warning",
                            issue_type="broken_link",
                            message=f"Link to '{link_target}' may not exist",
                            details={"link_text": link_text, "line": line},
                            suggestion="Check if page exists or update link",
                            line=line,
                        )
                    )

        # Check for missing images
        if page.content:
            for asset_ref in self._extract_asset_refs(page.content):
                # Skip external and data URLs
                if asset_ref.startswith(("http", "data:", "#")):
                    continue

                # Check if asset exists
                asset_path = self.site.root_path / asset_ref.lstrip("/")
                content_asset = (
                    page.source_path.parent / asset_ref if not asset_ref.startswith("/") else None
                )

                if not asset_path.exists() and (not content_asset or not content_asset.exists()):
                    issues.append(
                        Issue(
                            severity="warning",
                            issue_type="missing_asset",
                            message=f"Asset '{asset_ref}' not found",
                            details={"searched_paths": [str(asset_path)]},
                            suggestion="Add the asset or fix the path",
                        )
                    )

        return issues
