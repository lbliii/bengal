"""
Graph Visualization Generator for Bengal SSG.

Generates interactive D3.js visualizations of the site's knowledge graph.
Inspired by Obsidian's graph view.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
    from bengal.core.site import Site

logger = get_logger(__name__)


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
        size: Visual size (based on connectivity)
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
            raise ValueError("KnowledgeGraph must be built before visualization")

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

            # Calculate visual size (min 10, max 50)
            size = min(50, 10 + connectivity.connectivity_score * 2)

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

            # Try page.url property if we don't have a taxonomy URL
            if not page_url:
                try:
                    page_url = page.url
                except (AttributeError, Exception):
                    # Fallback: try to compute from output_path if available
                    if hasattr(page, "output_path") and page.output_path:
                        try:
                            # Compute relative URL from output_dir
                            rel_path = page.output_path.relative_to(self.site.output_dir)
                            page_url = f"/{rel_path}".replace("\\", "/").replace("/index.html", "/")
                            if not page_url.endswith("/"):
                                page_url += "/"
                        except (ValueError, AttributeError):
                            # Final fallback: use slug-based URL
                            page_url = f"/{getattr(page, 'slug', page.source_path.stem)}/"
                    else:
                        # Final fallback: use slug-based URL
                        page_url = f"/{getattr(page, 'slug', page.source_path.stem)}/"

            # Apply baseurl to URL (like templates do with permalink)
            baseurl = self.site.config.get("baseurl", "").rstrip("/")
            if baseurl:
                # Ensure page_url starts with /
                if not page_url.startswith("/"):
                    page_url = "/" + page_url
                # Handle absolute vs path-only base URLs
                if baseurl.startswith(("http://", "https://", "file://")):
                    page_url = f"{baseurl}{page_url}"
                else:
                    # Path-only baseurl (e.g., /bengal)
                    base_path = "/" + baseurl.lstrip("/")
                    page_url = f"{base_path}{page_url}"

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
                size=size,
                color=color,
            )

            nodes.append(asdict(node))

        # Generate edges (using pages directly as keys, matching graph structure)
        for page in content_pages:
            source_id = page_id_map[page]

            # Get outgoing references (graph uses pages directly as keys)
            targets = self.graph.outgoing_refs.get(page, set())
            for target in targets:
                # Only include edges to pages we're visualizing
                if target in page_id_map:
                    target_id = page_id_map[target]
                    edges.append(asdict(GraphEdge(source=source_id, target=target_id, weight=1)))

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

        Args:
            title: Page title (defaults to site title)

        Returns:
            Complete HTML document as string
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

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>

    <!-- Include theme CSS - relative path from /graph/index.html to /assets/css/style.css -->
    <link rel="stylesheet" href="../assets/css/style.css">

    <!-- Theme configuration defaults -->
    <script>
        window.BENGAL_THEME_DEFAULTS = {{
            appearance: '{default_appearance}',
            palette: '{default_palette}'
        }};
    </script>

    <!-- Theme initialization script -->
    <script src="../assets/js/theme-init.js"></script>

    <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body class="graph-body">
    <div id="container" class="graph-container">
        <div class="graph-controls">
            <h2>🗺️ Knowledge Graph</h2>
            <input
                type="text"
                id="search"
                placeholder="Search pages or tags..."
                autocomplete="off"
            />
            <div class="graph-filter-group">
                <label>Filter by Type:</label>
                <select id="filter-type">
                    <option value="all">All Pages</option>
                    <option value="hub">Hubs Only</option>
                    <option value="orphan">Orphans Only</option>
                    <option value="regular">Regular Pages</option>
                </select>
            </div>
            <div class="graph-stats">
                <p><strong>Pages:</strong> {graph_data["stats"]["total_pages"]}</p>
                <p><strong>Links:</strong> {graph_data["stats"]["total_links"]}</p>
                <p><strong>Hubs:</strong> {graph_data["stats"]["hubs"]}</p>
                <p><strong>Orphans:</strong> {graph_data["stats"]["orphans"]}</p>
            </div>
        </div>

        <div class="graph-legend">
            <h3>Legend</h3>
            <div class="graph-legend-item">
                <div class="graph-legend-color" style="background: var(--graph-node-hub);"></div>
                <span>Hub (highly connected)</span>
            </div>
            <div class="graph-legend-item">
                <div class="graph-legend-color" style="background: var(--graph-node-regular);"></div>
                <span>Regular page</span>
            </div>
            <div class="graph-legend-item">
                <div class="graph-legend-color" style="background: var(--graph-node-orphan);"></div>
                <span>Orphan (no incoming links)</span>
            </div>
            <div class="graph-legend-item">
                <div class="graph-legend-color" style="background: var(--graph-node-generated);"></div>
                <span>Generated page</span>
            </div>
        </div>

        <div id="graph" class="graph-svg"></div>
        <div class="graph-tooltip" id="tooltip"></div>
    </div>

    <script>
        // Graph data
        const graphData = {json.dumps(graph_data, indent=2)};

        // Dimensions
        const width = window.innerWidth;
        const height = window.innerHeight;

        // Create SVG
        const svg = d3.select("#graph")
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        // Add zoom behavior
        const g = svg.append("g");

        svg.call(d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }})
        );

        // Create force simulation with link force
        // D3's forceLink will convert edge source/target IDs to node references
        const linkForce = d3.forceLink(graphData.edges)
            .id(d => d.id)
            .distance(50);

        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", linkForce)
            .force("charge", d3.forceManyBody()
                .strength(-200))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide()
                .radius(d => d.size + 5));

        // Render links - use the same edges array, D3 will convert IDs to node refs
        const link = g.append("g")
            .attr("class", "graph-links")
            .selectAll("line")
            .data(graphData.edges)
            .enter().append("line")
            .attr("class", "graph-link")
            .attr("stroke", "var(--color-border-light, rgba(0, 0, 0, 0.1))")
            .attr("stroke-width", 1);

        // Helper function to resolve CSS variables to actual colors
        function resolveCSSVariable(varName) {{
            // Remove 'var(' and ')' if present
            const cleanVar = varName.replace(/var\\(|\\s|\\)/g, '');
            // Get computed value from root element
            const root = document.documentElement;
            const value = getComputedStyle(root).getPropertyValue(cleanVar).trim();
            return value || '#9e9e9e'; // Fallback color
        }}

        // Resolve CSS variables in node colors
        graphData.nodes.forEach(node => {{
            if (node.color && node.color.startsWith('var(')) {{
                // Extract variable name and resolve
                const varMatch = node.color.match(/var\\(([^)]+)\\)/);
                if (varMatch) {{
                    const varName = varMatch[1].trim();
                    node.color = resolveCSSVariable(varName);
                }}
            }}
        }});

        // Helper function to resolve CSS variables to actual colors
        function resolveCSSVariable(varName) {{
            // Remove 'var(' and ')' if present
            const cleanVar = varName.replace(/var\\(|\\s|\\)/g, '');
            // Get computed value from root element
            const root = document.documentElement;
            const value = getComputedStyle(root).getPropertyValue(cleanVar).trim();
            return value || '#9e9e9e'; // Fallback color
        }}

        // Resolve CSS variables in node colors
        graphData.nodes.forEach(node => {{
            if (node.color && node.color.startsWith('var(')) {{
                // Extract variable name and resolve
                const varMatch = node.color.match(/var\\(([^)]+)\\)/);
                if (varMatch) {{
                    const varName = varMatch[1].trim();
                    node.color = resolveCSSVariable(varName);
                }}
            }}
        }});

        // Render nodes
        const node = g.append("g")
            .attr("class", "graph-nodes")
            .selectAll("circle")
            .data(graphData.nodes)
            .enter().append("circle")
            .attr("class", "graph-node")
            .attr("r", d => d.size)
            .attr("fill", d => d.color)
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended))
            .on("click", (event, d) => {{
                window.location.href = d.url;
            }})
            .on("mouseover", (event, d) => {{
                showTooltip(event, d);
                highlightConnections(d);
            }})
            .on("mouseout", () => {{
                hideTooltip();
                clearHighlights();
            }});

        // Update positions on simulation tick
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
        }});

        // Drag functions
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}

        // Tooltip functions
        const tooltip = d3.select("#tooltip");

        function showTooltip(event, d) {{
            const tags = d.tags.length > 0
                ? `<div class="tags">${{d.tags.map(t => `<span class="tag">${{t}}</span>`).join('')}}</div>`
                : '';

            tooltip
                .style("display", "block")
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY + 10) + "px")
                .html(`
                    <h4>${{d.label}}</h4>
                    <p>Type: ${{d.type}}</p>
                    <p>Incoming: ${{d.incoming_refs}} | Outgoing: ${{d.outgoing_refs}}</p>
                    ${{tags}}
                `);
        }}

        function hideTooltip() {{
            tooltip.style("display", "none");
        }}

        // Highlight connections
        function highlightConnections(d) {{
            // Highlight connected nodes
            const connectedNodeIds = new Set();
            connectedNodeIds.add(d.id);

            graphData.edges.forEach(e => {{
                if (e.source.id === d.id || e.source === d.id) {{
                    connectedNodeIds.add(typeof e.target === 'object' ? e.target.id : e.target);
                }}
                if (e.target.id === d.id || e.target === d.id) {{
                    connectedNodeIds.add(typeof e.source === 'object' ? e.source.id : e.source);
                }}
            }});

            node.classed("highlighted", n => connectedNodeIds.has(n.id));

            // Highlight connected links
            link.classed("highlighted", e => {{
                const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
                const targetId = typeof e.target === 'object' ? e.target.id : e.target;
                return sourceId === d.id || targetId === d.id;
            }});
        }}

        function clearHighlights() {{
            node.classed("highlighted", false);
            link.classed("highlighted", false);
        }}

        // Search and filter functionality
        const searchInput = document.getElementById('search');
        const filterType = document.getElementById('filter-type');

        function updateVisibility() {{
            const query = searchInput.value.toLowerCase();
            const filter = filterType.value;

            node.style("opacity", d => {{
                // Apply search filter
                const matchesSearch = !query ||
                    d.label.toLowerCase().includes(query) ||
                    d.tags.some(t => t.toLowerCase().includes(query));

                // Apply type filter (use node.type property)
                let matchesType = true;
                if (filter !== 'all') {{
                    matchesType = d.type === filter;
                }}

                return matchesSearch && matchesType ? 1 : 0.2;
            }});

            // Hide links to filtered nodes
            link.style("opacity", d => {{
                const sourceVisible = node.filter(n => n.id === (typeof d.source === 'object' ? d.source.id : d.source)).style("opacity") === "1";
                const targetVisible = node.filter(n => n.id === (typeof d.target === 'object' ? d.target.id : d.target)).style("opacity") === "1";
                return sourceVisible && targetVisible ? 1 : 0.1;
            }});
        }}

        searchInput.addEventListener('input', updateVisibility);
        filterType.addEventListener('change', updateVisibility);

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.key === '/' || (e.metaKey && e.key === 'k')) {{
                e.preventDefault();
                searchInput.focus();
            }}
            if (e.key === 'Escape') {{
                searchInput.value = '';
                filterType.value = 'all';
                searchInput.blur();
                updateVisibility();
            }}
        }});
    </script>
</body>
</html>
"""

        return html
