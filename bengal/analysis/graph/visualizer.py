"""
Graph Visualization Generator for Bengal SSG.

Builds the data (nodes, edges, stats) and standalone HTML page for the site's
knowledge graph, inspired by Obsidian's graph view. Node positions are baked at
build time (see ``layout.py``) and the page is rendered by a dependency-free
canvas explorer (``bengal-graph-explorer.js``) — no D3, no runtime simulation.

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

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.analysis.utils.pages import get_content_pages
from bengal.errors import BengalGraphError, ErrorCode
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.normalize import to_posix

if TYPE_CHECKING:
    from bengal.analysis.graph.knowledge_graph import KnowledgeGraph
    from bengal.protocols import SiteConfig

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
    Generate interactive visualizations of knowledge graphs.

    Creates standalone HTML files with:
    - Build-time baked force-directed layout (rendered to canvas, no D3)
    - Interactive node exploration
    - Search and filtering
    - Responsive design
    - Customizable styling

    Example:
            >>> visualizer = GraphVisualizer(site, graph)
            >>> html = visualizer.generate_html()
            >>> Path('graph.html').write_text(html)

    """

    def __init__(self, site: SiteConfig, graph: KnowledgeGraph):
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
        Get a stable, build-reproducible ID for a page.

        Thin wrapper over :func:`bengal.analysis.utils.pages.stable_page_id` —
        the single source of truth for the page id, shared with the canonical
        page-ordering key in ``GraphBuilder.get_analysis_pages`` so nodes are
        emitted in id order and every analysis iterates a build-stable order.

        Args:
            page: Page object

        Returns:
            Stable string ID for the page
        """
        from bengal.analysis.utils.pages import stable_page_id

        return stable_page_id(self.site, page)

    def generate_graph_data(self) -> dict[str, Any]:
        """
        Generate graph data with build-time baked node positions.

        Returns:
            Dictionary with 'nodes' (each carrying normalized x/y), 'edges',
            and 'stats'.
        """
        # Use content pages (excludes autodoc and generated pages like taxonomy pages)
        # This is consistent with other analysis modules (PageRank, path analysis, link suggestions)
        analysis_pages = self.graph.get_analysis_pages()
        content_pages = get_content_pages(self.graph)

        logger.info(
            "graph_viz_generate_start",
            total_pages=len(content_pages),
            filtered=len(analysis_pages) - len(content_pages),
        )

        # --- Surface the analysis we already compute: topic communities
        # (Louvain) + importance (PageRank). Both are cached on the graph and
        # computed once. Communities color the graph as a topic map; PageRank
        # drives node size. Determinism is guarded upstream (sorted page order +
        # Louvain local seeded PRNG); we round the PageRank float before baking.
        community_by_page: dict[Any, int] = {}
        communities_summary: list[dict[str, Any]] = []
        community_results = None
        pr_scores: dict[Any, float] = {}
        pr_max = 0.0
        try:
            pr_results = self.graph.compute_pagerank()
            pr_scores = pr_results.scores or {}
            pr_max = max(pr_scores.values()) if pr_scores else 0.0
        except Exception as e:
            logger.debug("graph_viz_pagerank_failed", error=str(e), error_type=type(e).__name__)

        try:
            community_results = self.graph.detect_communities()
            for community in community_results.communities:
                for p in community.pages:
                    community_by_page[p] = community.id
            # Rank-ordered (0 = largest) summary for the cluster legend.
            communities_summary = [
                {
                    "id": community.id,
                    "label": self._community_label(community, pr_scores),
                    "size": community.size,
                }
                for community in community_results.communities[:12]
            ]
        except Exception as e:
            logger.debug("graph_viz_community_failed", error=str(e), error_type=type(e).__name__)

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
            except ValueError, TypeError:
                reading_time = 1

            # Calculate visual size from PageRank importance (dominant) blended
            # with content depth — so genuinely authoritative pages read as large
            # and luminous, not merely well-connected ones. Falls back to
            # connectivity when PageRank is unavailable.
            pr_score = float(pr_scores.get(page, 0.0))
            pr_norm = (pr_score / pr_max) if pr_max > 0 else 0.0
            base_size = 8
            if pr_max > 0:
                importance_bonus = pr_norm * 28  # PageRank drives prominence
            else:
                importance_bonus = min(connectivity.connectivity_score * 1.5, 20)
            content_bonus = min(reading_time * 0.6, 12)
            size = int(min(50, base_size + importance_bonus + content_bonus))

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
                            # Type narrowing: output_path should be a Path
                            from pathlib import Path

                            output_path = page.output_path
                            if isinstance(output_path, Path) and isinstance(
                                self.site.output_dir, Path
                            ):
                                # Compute relative URL from output_dir
                                rel_path = output_path.relative_to(self.site.output_dir)
                                page_url = f"/{to_posix(rel_path)}".replace("/index.html", "/")
                            else:
                                raise TypeError("output_path or output_dir is not a Path")
                            if not page_url.endswith("/"):
                                page_url += "/"
                            # Apply baseurl for fallback path (since we computed it manually)
                            baseurl = (self.site.baseurl or "").rstrip("/")
                            if baseurl:
                                page_url = f"{baseurl}{page_url}"
                        except ValueError, AttributeError:
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

            # Bake the surfaced analysis onto the node dict (the dataclass stays
            # a stable shim; new fields ride alongside x/y). ``community`` is a
            # stable rank-ordered id (-1 = unclustered) the client maps to a
            # color token; ``pagerank`` is rounded for byte-parity.
            node_dict = asdict(node)
            node_dict["community"] = int(community_by_page.get(page, -1))
            node_dict["pagerank"] = round(pr_score, 6)
            nodes.append(node_dict)

        # Generate edges with bidirectional weight detection
        # If A→B and B→A both exist, that's a stronger relationship (weight=2)
        edge_set = set()  # Track (source, target) pairs to detect bidirectionality

        # First pass: collect all edges
        raw_edges = []
        for page in content_pages:
            source_id = page_id_map[page]
            targets = self.graph.outgoing_refs.get(page, set())
            # Iterate targets in a stable order: ``outgoing_refs`` is a set of
            # Page objects whose iteration order varies per process/instance,
            # which would make the emitted edge order (and thus graph.json)
            # nondeterministic. Sort by the target's stable node id.
            for target_id in sorted(
                page_id_map[target] for target in targets if target in page_id_map
            ):
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

        # Bake deterministic layout coordinates onto each node so the client
        # renders *static* positions with no runtime force simulation (this is
        # what lets the explorer drop D3 and stop choking at scale). The layout
        # is seeded + reproducible: coordinates ship in graph.json and the build
        # guards warm==cold byte parity.
        from bengal.analysis.graph.layout import (
            compute_community_bounds,
            compute_force_layout,
            compute_hierarchical_layout,
        )

        # Community-aware layout: cluster nodes into separated topical lobes
        # (not one center-piled hairball) and pull strongly-linked pairs closer.
        node_community = {n["id"]: n["community"] for n in nodes}
        edge_weights = {(e["source"], e["target"]): e["weight"] for e in edges}
        node_sizes = {n["id"]: float(n["size"]) for n in nodes}
        unique_communities = len({c for c in node_community.values() if c >= 0})

        node_id_list = [n["id"] for n in nodes]
        edge_list = [(e["source"], e["target"]) for e in edges]
        if unique_communities > 1:
            coords = compute_hierarchical_layout(
                node_id_list,
                edge_list,
                communities=node_community,
                weights=edge_weights,
                node_sizes=node_sizes,
            )
        else:
            coords = compute_force_layout(
                node_id_list,
                edge_list,
                communities=node_community,
                weights=edge_weights,
                node_sizes=node_sizes,
            )
        for n in nodes:
            x, y = coords.get(n["id"], (0.5, 0.5))
            n["x"] = x
            n["y"] = y

        bounds_by_community = compute_community_bounds(coords, node_community)
        community_regions: list[dict[str, Any]] = []
        if community_results is not None:
            for community in community_results.communities:
                region = {
                    "id": community.id,
                    "label": self._community_label(community, pr_scores),
                    "size": community.size,
                }
                region.update(bounds_by_community.get(community.id, {}))
                community_regions.append(region)
            for entry in communities_summary:
                entry.update(bounds_by_community.get(entry["id"], {}))
        else:
            for cid, bounds in sorted(bounds_by_community.items()):
                community_regions.append(
                    {"id": cid, "label": f"Cluster {cid}", "size": 0, **bounds}
                )

        logger.info(
            "graph_viz_generate_complete",
            nodes=len(nodes),
            edges=len(edges),
            communities=len(communities_summary),
        )

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_pages": len(nodes),
                "total_links": len(edges),
                "hubs": self.graph.metrics.hub_count if self.graph.metrics else 0,
                "orphans": self.graph.metrics.orphan_count if self.graph.metrics else 0,
                "communities": communities_summary,
                "community_regions": community_regions,
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
        if connectivity.is_hub:
            return "var(--graph-node-hub)"
        if page.metadata.get("_generated"):
            return "var(--graph-node-generated)"
        return "var(--graph-node-regular)"

    def _community_label(self, community: Any, pr_scores: dict[Any, float]) -> str:
        """
        Derive a human label for a topic community, deterministically.

        Prefers the most frequent tag shared across the community's pages (ties
        broken alphabetically); falls back to the title of the highest-PageRank
        member (ties broken by stable page id) so the choice is reproducible.

        Args:
            community: A detected Community (has ``.id`` and ``.pages``).
            pr_scores: PageRank scores by page, for the fallback ranking.

        Returns:
            A short display label for the community.
        """
        from collections import Counter

        from bengal.analysis.utils.pages import stable_page_id

        tag_counts: Counter[str] = Counter()
        for p in community.pages:
            tags = getattr(p, "tags", None) or []
            if isinstance(tags, (list, tuple, set)):
                for t in tags:
                    if t:
                        tag_counts[str(t)] += 1
        if tag_counts:
            best = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            if best:
                return best.replace("-", " ").replace("_", " ").title()

        # Fallback: highest-PageRank member title (tie-break by stable page id).
        members = sorted(
            community.pages,
            key=lambda p: (-float(pr_scores.get(p, 0.0)), stable_page_id(self.site, p)),
        )
        for p in members:
            title = getattr(p, "title", None)
            if title:
                return str(title)
        return f"Cluster {community.id}"

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

        # Resolve fingerprinted asset paths from the manifest.
        css_path = self._resolve_asset_path(baseurl, "css/style.css", "/assets/css/style.css")
        explorer_js_path = self._resolve_asset_path(
            baseurl,
            "js/bengal-graph-explorer.js",
            "/assets/js/bengal-graph-explorer.js",
        )

        return {
            "title": title,
            "css_path": css_path,
            "explorer_js_path": explorer_js_path,
            "default_appearance": default_appearance,
            "default_palette": default_palette,
            "stats": graph_data["stats"],
            "graph_json_url": "graph.json",
        }

    def _resolve_asset_path(self, baseurl: str, manifest_key: str, default_path: str) -> str:
        """Resolve a fingerprinted asset path from the asset manifest.

        Args:
            baseurl: Base URL prefix for asset paths
            manifest_key: Manifest source key (e.g. ``"css/style.css"``)
            default_path: Non-fingerprinted fallback path if the manifest
                lookup is unavailable

        Returns:
            Resolved path with baseurl prefix
        """
        resolved = default_path

        try:
            from bengal.assets.manifest import AssetManifest

            # Try output_dir first (where manifest is written during build)
            manifest_path = self.site.output_dir / "asset-manifest.json"
            if not manifest_path.exists():
                # Fallback to .bengal cache location
                # Type narrowing: paths may not be on SiteLike protocol
                if hasattr(self.site, "config_service") and self.site.config_service.paths:
                    paths = self.site.config_service.paths
                    manifest_path = getattr(paths, "asset_manifest", None)
                else:
                    manifest_path = None

            if manifest_path and manifest_path.exists():
                manifest = AssetManifest.load(manifest_path)
                if manifest:
                    entry = manifest.get(manifest_key)
                    if entry:
                        resolved = f"/{entry.output_path}"
        except Exception as e:
            # If manifest lookup fails, use non-fingerprinted paths
            logger.debug(
                "graph_visualizer_manifest_lookup_failed",
                error=str(e),
                error_type=type(e).__name__,
                manifest_key=manifest_key,
                action="using_non_fingerprinted_paths",
            )

        # Apply baseurl prefix
        if baseurl:
            resolved = f"{baseurl}{resolved}"

        return resolved

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
