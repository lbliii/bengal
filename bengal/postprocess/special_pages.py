"""
Special pages generation for Bengal SSG.

Generates utility pages that don't originate from markdown content but require
site styling and navigation. These pages are rendered using theme templates
and integrate with the site's design system.

Special Pages:
    - 404.html: Custom error page with site styling and navigation
    - search.html: Client-side search interface with Lunr.js integration
    - graph.html: Interactive knowledge graph visualization (D3.js)

How It Works:
    Each special page:
    1. Checks if the corresponding template exists in the theme
    2. Creates a synthetic page context with minimal metadata
    3. Renders the template with full site context (navigation, config)
    4. Writes to output directory with URL registry conflict detection

    Special pages have priority 10 (utility pages), meaning user-authored
    content at the same path takes precedence.

Configuration:
    Special pages are configured in bengal.toml:

    ```toml
    [search]
    enabled = true
    path = "/search/"
    template = "search.html"

    [graph]
    enabled = true
    path = "/graph/"
    ```

Example:
    >>> from bengal.postprocess.special_pages import SpecialPagesGenerator
    >>>
    >>> generator = SpecialPagesGenerator(site)
    >>> generator.generate(build_context=context)

Related:
    - bengal.orchestration.postprocess: Coordinates special page generation
    - bengal.rendering.engines: Template engine for rendering
    - bengal.analysis.graph_visualizer: Knowledge graph visualization
    - bengal.core.page.utils.create_synthetic_page: Synthetic page factory
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.core.page.utils import create_synthetic_page
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class SpecialPagesGenerator:
    """
    Generates special utility pages with site styling.

    These pages use templates from the theme but don't have corresponding
    markdown source files. They are rendered during the build process to
    ensure proper styling, navigation, and integration with site features.

    Creation:
        Direct instantiation: SpecialPagesGenerator(site)
            - Created by PostprocessOrchestrator for special page generation
            - Requires Site instance with template engine

    Attributes:
        site: Site instance with configuration and template engine

    Relationships:
        - Used by: PostprocessOrchestrator for special page generation
        - Uses: Site for config, TemplateEngine for rendering
        - Uses: GraphVisualizer for knowledge graph page

    Currently Generates:
        - 404.html: Custom error page with site styling and navigation
        - search.html: Client-side search with Lunr.js integration
        - graph.html: Interactive D3.js knowledge graph visualization

    Graceful Degradation:
        - Missing templates are silently skipped (not errors)
        - User content at same path takes precedence (priority system)
        - Generation failures are logged but don't stop the build

    Example:
        >>> generator = SpecialPagesGenerator(site)
        >>> generator.generate(build_context=context)
    """

    def __init__(self, site: Site) -> None:
        """
        Initialize special pages generator.

        Args:
            site: Site instance with configuration and template engine
        """
        self.site = site

    def generate(self, build_context: BuildContext | Any | None = None) -> None:
        """
        Generate all special pages that are enabled.

        Currently generates:
        - 404 page if 404.html template exists in theme
        - search page if enabled and template exists (and no user content overrides)
        - graph visualization if enabled (and no user content overrides)
        Failures are logged but don't stop the build process.

        Args:
            build_context: Optional BuildContext with cached knowledge graph
        """
        pages_generated = []

        # Always generate 404 page
        if self._generate_404():
            pages_generated.append("404")

        # Generate search page when enabled
        if self._generate_search():
            pages_generated.append("search")

        # Generate graph visualization when enabled
        if self._generate_graph(build_context=build_context):
            pages_generated.append("graph")

        # Log what was generated for debugging (especially important in CI)
        if pages_generated:
            logger.info(
                "special_pages_generated",
                pages=pages_generated,
                count=len(pages_generated),
            )
        else:
            logger.warning(
                "no_special_pages_generated",
                reason="all_pages_disabled_or_failed",
            )

    def _generate_404(self) -> bool:
        """
        Generate 404 error page with site styling.

        Uses 404.html template from theme if it exists. Creates a minimal
        page context and renders the template with site navigation and styling.

        Returns:
            True if generated successfully, False if template missing or error occurred

        Note:
            Errors are logged but don't fail the build - a missing 404 page
            is not critical for site functionality
        """
        try:
            from bengal.rendering.engines import create_engine

            # Get template engine (reuse site's if available)
            if hasattr(self.site, "template_engine"):
                template_engine = self.site.template_engine
            else:
                # Create new template engine for rendering
                template_engine = create_engine(self.site)

            # Check if 404.html template exists
            try:
                template_engine.env.get_template("404.html")
            except Exception as e:
                # No 404 template in theme, skip generation
                logger.debug(
                    "custom_404_template_missing",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="skipping_404_generation",
                )
                return False

            # Create context for 404 page using factory
            page_context = create_synthetic_page(
                title="Page Not Found",
                description="The page you're looking for doesn't exist.",
                url="/404.html",
                kind="page",
                type="special",
            )

            context = {
                "site": self.site,
                "page": page_context,
                "config": self.site.config,
                # Add pre-computed properties that templates expect
                "meta_desc": page_context.description,
                "reading_time": 0,
                "excerpt": "",
                "content": "",
                "toc": "",
                "toc_items": [],
            }

            # Render 404 page (template functions are already registered in TemplateEngine.__init__)
            rendered_html = template_engine.render("404.html", context)

            # Write to output directory only if content changed (avoid churn)
            output_path = self.site.output_dir / "404.html"

            # Claim URL in registry before writing (claim-before-write pattern)
            # Priority 10 = special pages (fallback utility pages)
            if hasattr(self.site, "url_registry") and self.site.url_registry:
                try:
                    self.site.url_registry.claim_output_path(
                        output_path=output_path,
                        site=self.site,
                        owner="special_pages",
                        source="404.html",
                        priority=10,  # Special pages
                    )
                except Exception as e:
                    # Registry rejected claim (higher priority content exists)
                    logger.debug(
                        "special_page_conflict",
                        page="404",
                        reason=f"URL already claimed by higher priority content: {e}",
                        action="skipping_generation",
                    )
                    return False

            output_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                existing = ""
                if output_path.exists():
                    with open(output_path, encoding="utf-8") as f:
                        existing = f.read()
                if existing != rendered_html:
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(rendered_html)
            except Exception as e:
                # Best-effort diff; on any error just write
                logger.debug(
                    "special_page_diff_failed",
                    output_path=str(output_path),
                    error=str(e),
                    error_type=type(e).__name__,
                    action="writing_without_diff",
                )
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(rendered_html)

            return True

        except Exception as e:
            logger.error("404_page_generation_failed", error=str(e), error_type=type(e).__name__)
            return False

    def _generate_search(self) -> bool:
        """
        Generate client-side search page using theme/site template.

        Behavior:
        - Respects [search] config: enabled, path, template
        - Skips if a user-authored content page exists that would handle /search/
        - Skips if template is missing
        - Writes to /search/index.html by default
        """
        try:
            from bengal.config.defaults import get_feature_config

            # Get normalized search config (handles both bool and dict)
            search_cfg = get_feature_config(self.site.config, "search")
            if not search_cfg.get("enabled", True):
                return False

            # Extract config options with defaults
            path_cfg = search_cfg.get("path", "/search/") or "/search/"
            template_name = search_cfg.get("template", "search.html") or "search.html"

            # Path normalization: default '/search/'
            raw_path = path_cfg
            if not raw_path.startswith("/"):
                raw_path = "/" + raw_path
            if not raw_path.endswith("/"):
                raw_path = raw_path + "/"

            from bengal.rendering.engines import create_engine

            # Get template engine (reuse site's if available)
            if hasattr(self.site, "template_engine"):
                template_engine = self.site.template_engine
            else:
                template_engine = create_engine(self.site)

            try:
                template_engine.env.get_template(template_name)
            except Exception as e:
                # Template missing → skip
                logger.debug(
                    "special_page_template_missing",
                    template=template_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="skipping_generation",
                )
                return False

            # Build context using factory
            page_context = create_synthetic_page(
                title="Search",
                description="Search this site for content.",
                url=raw_path,
                kind="page",
                type="special",
                metadata={"search_exclude": True},  # never index the search page
            )

            context = {
                "site": self.site,
                "page": page_context,
                "config": self.site.config,
                # Add pre-computed properties that templates expect
                "meta_desc": page_context.description,
                "reading_time": 0,
                "excerpt": "",
                "content": "",
                "toc": "",
                "toc_items": [],
            }

            # Render search page
            rendered_html = template_engine.render(template_name, context)

            # Determine output path: /search/index.html by default
            # raw_path always ends with '/'
            output_path = self.site.output_dir / raw_path.strip("/") / "index.html"

            # Claim URL in registry before writing (claim-before-write pattern)
            # Priority 10 = special pages (fallback utility pages)
            if hasattr(self.site, "url_registry") and self.site.url_registry:
                try:
                    self.site.url_registry.claim_output_path(
                        output_path=output_path,
                        site=self.site,
                        owner="special_pages",
                        source="search.html",
                        priority=10,  # Special pages
                    )
                except Exception as e:
                    # Registry rejected claim (higher priority content exists, e.g., user content)
                    logger.debug(
                        "special_page_conflict",
                        page="search",
                        reason=f"URL already claimed by higher priority content: {e}",
                        action="skipping_generation",
                    )
                    return False

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_html)

            return True
        except Exception as e:
            logger.error(
                "search_page_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def _generate_graph(self, build_context: BuildContext | Any | None = None) -> bool:
        """
        Generate interactive knowledge graph visualization.

        Behavior:
        - Respects [graph] config: enabled, path
        - Skips if a user-authored content page exists that would handle /graph/
        - Uses cached knowledge graph from build_context if available
        - Writes to /graph/index.html by default

        Args:
            build_context: Optional BuildContext with cached knowledge graph

        Returns:
            True if generated successfully, False if disabled or error occurred
        """
        try:
            from bengal.config.defaults import get_feature_config

            # Get normalized graph config (handles both bool and dict)
            graph_cfg = get_feature_config(self.site.config, "graph")
            if not graph_cfg.get("enabled", True):
                return False

            # Extract config options with defaults
            path_cfg = graph_cfg.get("path", "/graph/") or "/graph/"

            # Path normalization: default '/graph/'
            raw_path = path_cfg
            if not raw_path.startswith("/"):
                raw_path = "/" + raw_path
            if not raw_path.endswith("/"):
                raw_path = raw_path + "/"

            # Try to get cached graph from build context first
            from bengal.analysis.graph_visualizer import GraphVisualizer

            graph = None
            if build_context is not None:
                graph = getattr(build_context, "knowledge_graph", None)

            # Fallback: build our own (for standalone usage)
            if graph is None:
                from bengal.analysis.knowledge_graph import KnowledgeGraph

                logger.debug("building_knowledge_graph_for_visualization")
                graph = KnowledgeGraph(self.site)
                graph.build()
            else:
                logger.debug("using_cached_knowledge_graph_for_visualization")

            # Generate visualization HTML
            visualizer = GraphVisualizer(self.site, graph)
            title = f"Knowledge Graph - {self.site.config.get('title', 'Site')}"
            html = visualizer.generate_html(title=title)

            # Determine output path: /graph/index.html by default
            # raw_path always ends with '/'
            output_path = self.site.output_dir / raw_path.strip("/") / "index.html"

            # Claim URL in registry before writing (claim-before-write pattern)
            # Priority 10 = special pages (fallback utility pages)
            if hasattr(self.site, "url_registry") and self.site.url_registry:
                try:
                    self.site.url_registry.claim_output_path(
                        output_path=output_path,
                        site=self.site,
                        owner="special_pages",
                        source="graph.html",
                        priority=10,  # Special pages
                    )
                except Exception as e:
                    # Registry rejected claim (higher priority content exists, e.g., user content)
                    logger.debug(
                        "special_page_conflict",
                        page="graph",
                        reason=f"URL already claimed by higher priority content: {e}",
                        action="skipping_generation",
                    )
                    return False

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding="utf-8")

            # Also generate JSON data file for minimap/embedding in other pages
            import json

            graph_data = visualizer.generate_graph_data()
            json_path = self.site.output_dir / raw_path.strip("/") / "graph.json"
            # sort_keys=True ensures deterministic output for cache invalidation
            json_path.write_text(json.dumps(graph_data, indent=2, sort_keys=True), encoding="utf-8")

            return True
        except Exception as e:
            logger.error(
                "graph_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
