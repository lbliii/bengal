"""
Graph Visualization Generator for Bengal SSG.

Creates interactive D3.js visualizations of the site's knowledge graph,
inspired by Obsidian's graph view. The visualizations are standalone HTML
files that can be served alongside the site or used for offline analysis.

Features:
- Force-directed graph layout with physics simulation
- Interactive node exploration (hover, click, drag)
- Search and filtering by page title, tags, or type
- Responsive design with zoom and pan
- Theme-aware styling (light/dark mode)
- Customizable node colors based on connectivity

Node Types:
- Hub: Highly connected pages (large, prominent color)
- Regular: Normal pages
- Orphan: Pages with no incoming links (warning color)
- Generated: Taxonomy and other generated pages

Classes:
GraphNode: Data structure for visualization nodes
GraphEdge: Data structure for visualization edges
GraphVisualizer: Main visualization generator

Example:
    >>> from bengal.analysis import KnowledgeGraph, GraphVisualizer
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> visualizer = GraphVisualizer(site, graph)
    >>> html = visualizer.generate_html(title="My Site Graph")
    >>> Path('public/graph.html').write_text(html)

See Also:
- bengal/analysis/knowledge_graph.py: Graph data source
- bengal/themes/*/assets/css/style.css: Theme CSS variables

"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.errors import BengalGraphError, ErrorCode
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
    from bengal.core.site import Site

logger = get_logger(__name__)

# Path to HTML template file
_TEMPLATE_PATH = Path(__file__).parent / "templates" / "graph_visualizer.html"


@dataclass
class GraphNode:
    """
    Node in the graph visualization.
    
    Attributes:
        id: Unique identifier for the node
        label: Display label (page title)
        url: URL to the page
        type: Page type (page, index, generated, etc.)
        tags: List of tags
        incoming_refs: Number of incoming references
        outgoing_refs: Number of outgoing references
        connectivity: Total connectivity score
        reading_time: Content depth (minutes to read)
        size: Visual size (based on connectivity + content depth)
        color: Node color (based on type or connectivity)
        
    """

    id: str
    label: str
    url: str
    type: str
    tags: list[str]
    incoming_refs: int
    outgoing_refs: int
    connectivity: int
    reading_time: int
    size: int
    color: str


@dataclass
class GraphEdge:
    """
    Edge in the graph visualization.
    
    Attributes:
        source: Source node ID
        target: Target node ID
        weight: Edge weight (link strength)
        
    """

    source: str
    target: str
    weight: int = 1


class GraphVisualizer:
    """
    Generate interactive D3.js visualizations of knowledge graphs.
    
    Creates standalone HTML files with:
    - Force-directed graph layout
    - Interactive node exploration
    - Search and filtering
    - Responsive design
    - Customizable styling
    
    Example:
            >>> visualizer = GraphVisualizer(site, graph)
            >>> html = visualizer.generate_html()
            >>> Path('graph.html').write_text(html)
        
    """

    def __init__(self, site: Site, graph: KnowledgeGraph):
        """
        Initialize graph visualizer.

        Args:
            site: Site instance
            graph: Built KnowledgeGraph instance
        """
        self.site = site
        self.graph = graph

        if not graph._built:
            raise BengalGraphError(
                "KnowledgeGraph must be built before visualization",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before creating a visualizer",
            )

    def _get_page_id(self, page: Any) -> str:
        """
        Get a stable ID for a page (using source_path hash).

        Args:
            page: Page object

        Returns:
            String ID for the page
        """
        # Use hash of source_path for stable IDs (pages are hashable by source_path)
        return str(hash(page.source_path))

    def generate_graph_data(self) -> dict[str, Any]:
        """
        Generate D3.js-compatible graph data.

        Returns:
            Dictionary with 'nodes' and 'edges' arrays
        """
        # Use analysis pages (excludes autodoc if configured)
        analysis_pages = self.graph.get_analysis_pages()

        # Filter out generated taxonomy pages (tag pages, category pages, etc.)
        # These are system-generated and shouldn't appear in the content graph
        # Other analysis modules (PageRank, path analysis, link suggestions) also exclude them
        content_pages = [
            p
            for p in analysis_pages
            if not p.metadata.get("_generated")
            or p.metadata.get("type") not in ("tag", "tag-index", "category", "category-index")
        ]

        logger.info(
            "graph_viz_generate_start",
            total_pages=len(content_pages),
            filtered=len(analysis_pages) - len(content_pages),
        )

        nodes = []
        edges = []
        page_id_map = {}  # Map pages to their IDs

        # Generate nodes
        for page in content_pages:
            page_id = self._get_page_id(page)
            page_id_map[page] = page_id
            connectivity = self.graph.get_connectivity(page)

            # Determine node color based on type or connectivity
            color = self._get_node_color(page, connectivity)

            # Get reading time (content depth indicator) - ensure it's an int
            reading_time_raw = getattr(page, "reading_time", 1)
            try:
                reading_time = int(reading_time_raw) if reading_time_raw else 1
            except (ValueError, TypeError):
                reading_time = 1

            # Calculate visual size based on BOTH connectivity AND content depth
            # - Connectivity: how central/important (links)
            # - Reading time: how substantial (content depth)
            # Formula: base + connectivity bonus + content depth bonus
            base_size = 8
            connectivity_bonus = min(connectivity.connectivity_score * 1.5, 20)  # max +20
            content_bonus = min(reading_time * 0.8, 15)  # max +15 (long articles get bigger)
            size = min(50, base_size + connectivity_bonus + content_bonus)

            # Get tags safely
            tags = []
            if hasattr(page, "tags") and page.tags:
                tags = list(page.tags) if isinstance(page.tags, (list, tuple, set)) else [page.tags]

            # Get page URL - use the page's url property which computes from output_path
            # The url property is a cached property that handles all the logic
            page_url = None

            # Special handling for taxonomy pages (if they somehow got through the filter)
            if page.metadata.get("type") == "tag" and page.metadata.get("_tag_slug"):
                # Build tag URL directly: /tags/{slug}/
                tag_slug = page.metadata.get("_tag_slug")
                page_url = f"/tags/{tag_slug}/"
            elif page.metadata.get("type") == "tag-index":
                page_url = "/tags/"
            elif page.metadata.get("type") == "category" and page.metadata.get("_category_slug"):
                category_slug = page.metadata.get("_category_slug")
                page_url = f"/categories/{category_slug}/"
            elif page.metadata.get("type") == "category-index":
                page_url = "/categories/"

            # Try page.href property if we don't have a taxonomy URL
            # NOTE: page.href already includes baseurl, so we DON'T add it again
            if not page_url:
                try:
                    # page.href returns URL with baseurl already applied
                    page_url = page.href
                except (AttributeError, Exception) as e:
                    # Fallback: try to compute from output_path if available
                    logger.debug(
                        "analysis_graph_page_url_access_failed",
                        page=str(getattr(page, "source_path", "unknown")),
                        error=str(e),
                        error_type=type(e).__name__,
                        action="trying_output_path_fallback",
                    )
                    if hasattr(page, "output_path") and page.output_path:
                        try:
                            # Compute relative URL from output_dir
                            rel_path = page.output_path.relative_to(self.site.output_dir)
                            page_url = f"/{rel_path}".replace("\\", "/").replace("/index.html", "/")
                            if not page_url.endswith("/"):
                                page_url += "/"
                            # Apply baseurl for fallback path (since we computed it manually)
                            baseurl = (self.site.baseurl or "").rstrip("/")
                            if baseurl:
                                page_url = f"{baseurl}{page_url}"
                        except (ValueError, AttributeError):
                            # Final fallback: use slug-based URL with baseurl
                            baseurl = (self.site.baseurl or "").rstrip("/")
                            page_url = f"{baseurl}/{getattr(page, 'slug', page.source_path.stem)}/"
                    else:
                        # Final fallback: use slug-based URL with baseurl
                        baseurl = (self.site.baseurl or "").rstrip("/")
                        page_url = f"{baseurl}/{getattr(page, 'slug', page.source_path.stem)}/"
            else:
                # Taxonomy URLs need baseurl applied (they're constructed without it)
                baseurl = (self.site.baseurl or "").rstrip("/")
                if baseurl:
                    page_url = f"{baseurl}{page_url}"

            # Determine node type for filtering
            node_type = "regular"
            if connectivity.is_orphan:
                node_type = "orphan"
            elif connectivity.is_hub:
                node_type = "hub"
            elif page.metadata.get("_generated"):
                node_type = "generated"

            node = GraphNode(
                id=page_id,
                label=page.title or "Untitled",
                url=page_url,
                type=node_type,  # Use computed type for filtering
                tags=tags,
                incoming_refs=connectivity.incoming_refs,
                outgoing_refs=connectivity.outgoing_refs,
                connectivity=connectivity.connectivity_score,
                reading_time=reading_time,
                size=size,
                color=color,
            )

            nodes.append(asdict(node))

        # Generate edges with bidirectional weight detection
        # If A→B and B→A both exist, that's a stronger relationship (weight=2)
        edge_set = set()  # Track (source, target) pairs to detect bidirectionality

        # First pass: collect all edges
        raw_edges = []
        for page in content_pages:
            source_id = page_id_map[page]
            targets = self.graph.outgoing_refs.get(page, set())
            for target in targets:
                if target in page_id_map:
                    target_id = page_id_map[target]
                    raw_edges.append((source_id, target_id))
                    edge_set.add((source_id, target_id))

        # Second pass: create edges with weight based on bidirectionality
        seen_pairs = set()  # Avoid duplicate edges for bidirectional links
        for source_id, target_id in raw_edges:
            # Normalize pair to avoid duplicates (smaller id first)
            pair = tuple(sorted([source_id, target_id]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # Check if reverse edge exists (bidirectional)
            is_bidirectional = (target_id, source_id) in edge_set
            weight = 2 if is_bidirectional else 1

            edges.append(asdict(GraphEdge(source=source_id, target=target_id, weight=weight)))

        logger.info("graph_viz_generate_complete", nodes=len(nodes), edges=len(edges))

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_pages": len(nodes),
                "total_links": len(edges),
                "hubs": self.graph.metrics.hub_count,
                "orphans": self.graph.metrics.orphan_count,
            },
        }

    def _get_node_color(self, page: Any, connectivity: Any) -> str:
        """
        Determine node color based on page properties.

        Returns CSS variable name that will be resolved in JavaScript.
        JavaScript will read the computed value from CSS custom properties.

        Args:
            page: Page object
            connectivity: PageConnectivity object

        Returns:
            CSS variable name (e.g., "var(--graph-node-hub)")
        """
        # Return CSS variable names - JavaScript will resolve actual colors
        if connectivity.is_orphan:
            return "var(--graph-node-orphan)"
        elif connectivity.is_hub:
            return "var(--graph-node-hub)"
        elif page.metadata.get("_generated"):
            return "var(--graph-node-generated)"
        else:
            return "var(--graph-node-regular)"

    def generate_html(self, title: str | None = None) -> str:
        """
        Generate complete standalone HTML visualization.

        Uses external template file for separation of concerns.
        See RFC: rfc-code-smell-remediation.md §1.3

        Args:
            title: Page title (defaults to site title)

        Returns:
            Complete HTML document as string
        """
        context = self._build_template_context(title)
        return self._render_template(context)

    def _build_template_context(self, title: str | None = None) -> dict[str, Any]:
        """Build context dictionary for template rendering.

        Args:
            title: Page title (defaults to site title)

        Returns:
            Dictionary with all template variables
        """
        graph_data = self.generate_graph_data()

        if title is None:
            title = f"Knowledge Graph - {self.site.config.get('title', 'Site')}"

        # Get theme config for initialization
        theme_config = getattr(self.site, "theme", None)
        default_appearance = "system"
        default_palette = ""
        if theme_config:
            default_appearance = getattr(theme_config, "default_appearance", "system")
            default_palette = getattr(theme_config, "default_palette", "")

        # Get baseurl for asset paths (handles GitHub Pages /bengal subpath)
        baseurl = (self.site.baseurl or "").rstrip("/")

        # Resolve CSS path from manifest
        css_path = self._resolve_css_path(baseurl)

        return {
            "title": title,
            "css_path": css_path,
            "default_appearance": default_appearance,
            "default_palette": default_palette,
            "stats": graph_data["stats"],
            "graph_data_json": json.dumps(graph_data, indent=2, sort_keys=True),
        }

    def _resolve_css_path(self, baseurl: str) -> str:
        """Resolve fingerprinted CSS path from asset manifest.

        Args:
            baseurl: Base URL prefix for asset paths

        Returns:
            CSS path with baseurl prefix
        """
        css_path = "/assets/css/style.css"

        try:
            from bengal.assets.manifest import AssetManifest

            # Try output_dir first (where manifest is written during build)
            manifest_path = self.site.output_dir / "asset-manifest.json"
            if not manifest_path.exists():
                # Fallback to .bengal cache location
                manifest_path = self.site.paths.asset_manifest

            if manifest_path.exists():
                manifest = AssetManifest.load(manifest_path)
                if manifest:
                    css_entry = manifest.get("css/style.css")
                    if css_entry:
                        css_path = f"/{css_entry.output_path}"
        except Exception as e:
            # If manifest lookup fails, use non-fingerprinted paths
            logger.debug(
                "graph_visualizer_manifest_lookup_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="using_non_fingerprinted_paths",
            )

        # Apply baseurl prefix
        if baseurl:
            css_path = f"{baseurl}{css_path}"

        return css_path

    def _render_template(self, context: dict[str, Any]) -> str:
        """Render the HTML template with the given context.

        Uses a simple mustache-style replacement for {{ variable }} patterns.
        This avoids introducing a full template engine dependency for a
        single standalone HTML file.

        Args:
            context: Dictionary of template variables

        Returns:
            Rendered HTML string
        """
        # Read template file
        template = _TEMPLATE_PATH.read_text(encoding="utf-8")

        # Simple mustache-style replacement
        # Handle nested dict access like {{ stats.total_pages }}
        def replace_var(match: re.Match[str]) -> str:
            var_path = match.group(1).strip()
            parts = var_path.split(".")

            value = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    return ""

            return str(value)

        # Replace {{ variable }} patterns
        result = re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace_var, template)
        return result
