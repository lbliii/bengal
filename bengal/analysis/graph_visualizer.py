"""
Graph Visualization Generator for Bengal SSG.

Generates interactive D3.js visualizations of the site's knowledge graph.
Inspired by Obsidian's graph view.
"""

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

    def __init__(self, site: 'Site', graph: 'KnowledgeGraph'):
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

    def generate_graph_data(self) -> dict[str, Any]:
        """
        Generate D3.js-compatible graph data.

        Returns:
            Dictionary with 'nodes' and 'edges' arrays
        """
        logger.info("graph_viz_generate_start", total_pages=len(self.site.pages))

        nodes = []
        edges = []

        # Generate nodes
        for page in self.site.pages:
            page_id = str(id(page))
            connectivity = self.graph.get_connectivity(page)

            # Determine node color based on type or connectivity
            color = self._get_node_color(page, connectivity)

            # Calculate visual size (min 10, max 50)
            size = min(50, 10 + connectivity.connectivity_score * 2)

            node = GraphNode(
                id=page_id,
                label=page.title or "Untitled",
                url=page.url if hasattr(page, 'url') else "#",
                type=page.metadata.get('type', 'page'),
                tags=list(page.tags) if hasattr(page, 'tags') else [],
                incoming_refs=connectivity.incoming_refs,
                outgoing_refs=connectivity.outgoing_refs,
                connectivity=connectivity.connectivity_score,
                size=size,
                color=color
            )

            nodes.append(asdict(node))

        # Generate edges
        for page in self.site.pages:
            source_id = str(id(page))

            # Get outgoing references
            target_ids = self.graph.outgoing_refs.get(id(page), set())
            for target_id in target_ids:
                edges.append(asdict(GraphEdge(
                    source=source_id,
                    target=str(target_id),
                    weight=1
                )))

        logger.info(
            "graph_viz_generate_complete",
            nodes=len(nodes),
            edges=len(edges)
        )

        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_pages': len(nodes),
                'total_links': len(edges),
                'hubs': self.graph.metrics.hub_count,
                'orphans': self.graph.metrics.orphan_count,
            }
        }

    def _get_node_color(self, page: Any, connectivity: Any) -> str:
        """
        Determine node color based on page properties.

        Args:
            page: Page object
            connectivity: PageConnectivity object

        Returns:
            Hex color code
        """
        # Color by connectivity level
        if connectivity.is_orphan:
            return '#ef4444'  # Red for orphans
        elif connectivity.is_hub:
            return '#3b82f6'  # Blue for hubs
        elif page.metadata.get('_generated'):
            return '#8b5cf6'  # Purple for generated pages
        else:
            return '#6b7280'  # Gray for regular pages

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

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow: hidden;
            background: #0a0a0a;
            color: #e5e7eb;
        }}

        #container {{
            width: 100vw;
            height: 100vh;
            position: relative;
        }}

        #graph {{
            width: 100%;
            height: 100%;
        }}

        .controls {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(17, 24, 39, 0.95);
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 16px;
            max-width: 300px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}

        .controls h2 {{
            font-size: 18px;
            margin-bottom: 12px;
            color: #f3f4f6;
        }}

        .controls input {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #4b5563;
            border-radius: 4px;
            background: #1f2937;
            color: #e5e7eb;
            font-size: 14px;
            margin-bottom: 12px;
        }}

        .controls input:focus {{
            outline: none;
            border-color: #3b82f6;
        }}

        .stats {{
            font-size: 13px;
            color: #9ca3af;
            line-height: 1.6;
        }}

        .stats strong {{
            color: #e5e7eb;
        }}

        .legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(17, 24, 39, 0.95);
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}

        .legend h3 {{
            font-size: 14px;
            margin-bottom: 8px;
            color: #f3f4f6;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            margin: 6px 0;
            font-size: 12px;
            color: #9ca3af;
        }}

        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 8px;
        }}

        .node {{
            cursor: pointer;
            stroke: rgba(255, 255, 255, 0.3);
            stroke-width: 1.5px;
        }}

        .node:hover {{
            stroke: #fff;
            stroke-width: 3px;
        }}

        .node.highlighted {{
            stroke: #fbbf24;
            stroke-width: 3px;
        }}

        .link {{
            stroke: rgba(156, 163, 175, 0.3);
            stroke-width: 1px;
        }}

        .link.highlighted {{
            stroke: rgba(251, 191, 36, 0.8);
            stroke-width: 2px;
        }}

        .label {{
            font-size: 11px;
            fill: #d1d5db;
            pointer-events: none;
            text-anchor: middle;
        }}

        .tooltip {{
            position: absolute;
            background: rgba(17, 24, 39, 0.98);
            border: 1px solid #374151;
            border-radius: 6px;
            padding: 12px;
            pointer-events: none;
            font-size: 13px;
            max-width: 250px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            display: none;
            z-index: 1000;
        }}

        .tooltip h4 {{
            margin-bottom: 6px;
            color: #f3f4f6;
            font-size: 14px;
        }}

        .tooltip p {{
            margin: 4px 0;
            color: #9ca3af;
            line-height: 1.4;
        }}

        .tooltip .tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 6px;
        }}

        .tooltip .tag {{
            background: #374151;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            color: #d1d5db;
        }}
    </style>
</head>
<body>
    <div id="container">
        <div class="controls">
            <h2>🗺️ Knowledge Graph</h2>
            <input
                type="text"
                id="search"
                placeholder="Search pages..."
                autocomplete="off"
            />
            <div class="stats">
                <p><strong>Pages:</strong> {graph_data['stats']['total_pages']}</p>
                <p><strong>Links:</strong> {graph_data['stats']['total_links']}</p>
                <p><strong>Hubs:</strong> {graph_data['stats']['hubs']}</p>
                <p><strong>Orphans:</strong> {graph_data['stats']['orphans']}</p>
            </div>
        </div>

        <div class="legend">
            <h3>Legend</h3>
            <div class="legend-item">
                <div class="legend-color" style="background: #3b82f6;"></div>
                <span>Hub (highly connected)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #6b7280;"></div>
                <span>Regular page</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ef4444;"></div>
                <span>Orphan (no incoming links)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #8b5cf6;"></div>
                <span>Generated page</span>
            </div>
        </div>

        <div id="graph"></div>
        <div class="tooltip" id="tooltip"></div>
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

        // Create force simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.edges)
                .id(d => d.id)
                .distance(50))
            .force("charge", d3.forceManyBody()
                .strength(-200))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide()
                .radius(d => d.size + 5));

        // Render links
        const link = g.append("g")
            .selectAll("line")
            .data(graphData.edges)
            .enter().append("line")
            .attr("class", "link");

        // Render nodes
        const node = g.append("g")
            .selectAll("circle")
            .data(graphData.nodes)
            .enter().append("circle")
            .attr("class", "node")
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

        // Search functionality
        const searchInput = document.getElementById('search');
        searchInput.addEventListener('input', (e) => {{
            const query = e.target.value.toLowerCase();

            if (query) {{
                node.style("opacity", d => {{
                    return d.label.toLowerCase().includes(query) ||
                           d.tags.some(t => t.toLowerCase().includes(query))
                        ? 1 : 0.2;
                }});

                link.style("opacity", 0.1);
            }} else {{
                node.style("opacity", 1);
                link.style("opacity", 1);
            }}
        }});

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.key === '/' || (e.metaKey && e.key === 'k')) {{
                e.preventDefault();
                searchInput.focus();
            }}
            if (e.key === 'Escape') {{
                searchInput.value = '';
                searchInput.blur();
                node.style("opacity", 1);
                link.style("opacity", 1);
            }}
        }});
    </script>
</body>
</html>
"""

        return html

