"""
Per-page JSON generator for Bengal SSG.

Generates JSON files alongside each HTML page, providing machine-readable
page data for client-side features like search, previews, and navigation.

Output Format:
    Each page.html gets a corresponding page.json (or index.json for
    directory index pages) containing:

    - url: Full public URL with baseurl
    - title: Page title from frontmatter
    - description: Page description
    - date: ISO 8601 formatted date (if available)
    - plain_text: Plain text content for search
    - excerpt: Truncated preview text
    - metadata: Serializable frontmatter fields
    - section: Parent section name
    - tags: List of tags
    - word_count: Content word count
    - reading_time: Estimated reading time in minutes
    - graph: Contextual minimap connections (if graph data available)

Performance:
    - Parallel file writes using ThreadPoolExecutor (8 workers)
    - Compact JSON (no indentation) for 3x faster serialization
    - Lazy graph index building for O(1) lookups
    - Optional accumulated JSON from rendering phase to avoid double iteration

Configuration:
    Controlled via [output_formats] in bengal.toml:

    ```toml
    [output_formats]
    enabled = true
    per_page = ["json"]  # Enable per-page JSON
    options.include_html_content = false  # HTML file exists, no need to duplicate
    options.include_plain_text = true     # Include plain text for search
    ```

Example:
    >>> generator = PageJSONGenerator(site, graph_data=graph_data)
    >>> count = generator.generate(pages)
    >>> print(f"Generated {count} JSON files")

Related:
    - bengal.postprocess.output_formats: OutputFormatsGenerator facade
    - bengal.analysis.graph_visualizer: Graph data for contextual minimap
    - bengal.postprocess.output_formats.utils: URL and path utilities
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.utils import (
    generate_excerpt,
    get_page_json_path,
    get_page_url,
    normalize_url,
)
from bengal.utils.atomic_write import AtomicFile
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class PageJSONGenerator:
    """
    Generates per-page JSON files for client-side features.

    Creates a JSON file alongside each HTML page containing metadata,
    content, and graph connections. Used for search indexing, page
    previews, and contextual navigation minimaps.

    Creation:
        Direct instantiation: PageJSONGenerator(site, graph_data=...)
            - Created by OutputFormatsGenerator for JSON generation
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with pages
        graph_data: Optional pre-computed graph data for contextual minimap
        include_html: Whether to include HTML content (default: False)
        include_text: Whether to include plain text content (default: True)

    Relationships:
        - Used by: OutputFormatsGenerator facade
        - Uses: Site for page access, utils for path resolution

    Performance:
        - Parallel writes with 8-thread pool
        - Lazy graph index building (O(1) lookups vs O(n²))
        - Compact JSON serialization (no whitespace)
        - Optional accumulated JSON from rendering phase

    Example:
        >>> generator = PageJSONGenerator(site, graph_data=graph_data)
        >>> count = generator.generate(pages)
        >>> print(f"Generated {count} JSON files")
    """

    def __init__(
        self,
        site: Site,
        graph_data: dict[str, Any] | None = None,
        include_html: bool = False,
        include_text: bool = True,
    ) -> None:
        """
        Initialize the JSON generator.

        Args:
            site: Site instance
            graph_data: Optional pre-computed graph data for contextual minimap
            include_html: Whether to include HTML content in JSON (default: False, HTML file already exists)
            include_text: Whether to include plain text content in JSON (default: True)
        """
        self.site = site
        self.graph_data = graph_data
        self.include_html = include_html
        self.include_text = include_text
        # Lazily-built indexes for O(1) graph lookups (built on first use)
        self._node_url_index: dict[str, dict[str, Any]] | None = None
        self._edge_index: dict[str, list[dict[str, Any]]] | None = None

    def generate(
        self, pages: list[Page], accumulated_json: list[tuple[Any, dict[str, Any]]] | None = None
    ) -> int:
        """
        Generate JSON files for all pages.

        Args:
            pages: List of pages to generate JSON for (used if accumulated_json not provided)
            accumulated_json: Optional pre-computed JSON data from rendering phase.
                            If provided, uses this instead of iterating pages again.

        Returns:
            Number of JSON files generated
        """
        import concurrent.futures

        # OPTIMIZATION: Use accumulated JSON data if available (Phase 2 of post-processing optimization)
        # This eliminates double iteration of pages, saving ~500-700ms on large sites
        # See: plan/active/rfc-postprocess-optimization.md
        if accumulated_json:
            page_items = list(accumulated_json)
            # Update graph connections if graph_data is available (wasn't available during rendering)
            if self.graph_data and pages:
                # Need to map pages to accumulated data to update graph connections
                page_url_map = {get_page_url(page, self.site): page for page in pages}
                for _json_path, page_data in page_items:
                    page_url = page_data.get("url", "")
                    if page_url in page_url_map:
                        page = page_url_map[page_url]
                        connections = self._get_page_connections(page, self.graph_data)
                        if connections:
                            page_data["graph"] = connections
        else:
            # Fallback: Compute JSON data from pages (original behavior)
            # Prepare all page data first (can be parallelized)
            computed_page_items: list[tuple[Any, dict[str, Any]]] = []
            for page in pages:
                json_path = get_page_json_path(page)
                if not json_path:
                    continue
                page_data = self.page_to_json(
                    page, include_html=self.include_html, include_text=self.include_text
                )
                computed_page_items.append((json_path, page_data))
            page_items = computed_page_items

        if not page_items:
            return 0

        # Write files in parallel
        def write_json(item: tuple[Any, dict[str, Any]]) -> bool:
            json_path, page_data = item
            try:
                json_path.parent.mkdir(parents=True, exist_ok=True)
                # Use compact JSON (no indent) for speed - 3x faster
                with AtomicFile(json_path, "w", encoding="utf-8") as f:
                    json.dump(page_data, f, ensure_ascii=False, separators=(",", ":"))
                return True
            except Exception as e:
                logger.warning("page_json_write_failed", path=str(json_path), error=str(e))
                return False

        # Use thread pool for I/O-bound writes
        count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = executor.map(write_json, page_items)
            count = sum(1 for r in results if r)

        logger.info("page_json_generated", count=count)
        return count

    def page_to_json(
        self,
        page: Page,
        include_html: bool = True,
        include_text: bool = True,
        excerpt_length: int = 200,
    ) -> dict[str, Any]:
        """
        Convert page to JSON representation.

        Args:
            page: Page object
            include_html: Include full HTML content
            include_text: Include plain text content
            excerpt_length: Length of excerpt

        Returns:
            Dictionary suitable for JSON serialization
        """
        data = {
            "url": get_page_url(page, self.site),
            "title": page.title,
            "description": page.metadata.get("description", ""),
        }

        # Date
        if page.date:
            data["date"] = page.date.isoformat()

        # Content (HTML if available)
        if include_html and page.parsed_ast:
            data["content"] = page.parsed_ast

        # Plain text - use page.plain_text which is pre-cached during rendering
        content_text = page.plain_text
        if include_text:
            data["plain_text"] = content_text

        # Excerpt
        data["excerpt"] = generate_excerpt(content_text, excerpt_length)

        # Metadata (serialize dates and other non-JSON types)
        data["metadata"] = {}
        skipped_keys = []
        for k, v in page.metadata.items():
            if k in ["content", "parsed_ast", "rendered_html", "_generated"]:
                continue
            # Only include JSON-serializable values
            try:
                # Convert dates to ISO format strings
                if isinstance(v, datetime) or hasattr(v, "isoformat"):
                    data["metadata"][k] = v.isoformat()
                # Test if value is JSON serializable
                elif isinstance(v, str | int | float | bool | type(None)):
                    data["metadata"][k] = v
                elif isinstance(v, list | dict):
                    # Try to serialize, skip if it fails
                    json.dumps(v)
                    data["metadata"][k] = v
                # Skip complex objects that can't be serialized
            except (TypeError, ValueError) as e:
                # Skip non-serializable values
                skipped_keys.append(k)
                logger.debug(
                    "json_serialization_skipped",
                    page=str(page.source_path),
                    key=k,
                    value_type=type(v).__name__,
                    reason=str(e)[:100],
                )

        if skipped_keys:
            logger.debug(
                "metadata_keys_skipped",
                page=str(page.source_path),
                skipped_count=len(skipped_keys),
                keys=skipped_keys,
            )

        # Section
        if hasattr(page, "_section") and page._section:
            data["section"] = getattr(page._section, "name", "")

        # Tags - ensure it's a list
        if page.tags:
            tags = page.tags
            if isinstance(tags, list | tuple):
                data["tags"] = list(tags)
            else:
                # Convert to list if it's iterable but not a list/tuple
                try:
                    data["tags"] = list(tags) if tags else []
                except (TypeError, ValueError):
                    data["tags"] = []

        # Stats
        word_count = len(content_text.split())
        data["word_count"] = word_count
        data["reading_time"] = max(1, round(word_count / 200))  # 200 wpm

        # Graph connections (for contextual minimap)
        if self.graph_data:
            connections = self._get_page_connections(page, self.graph_data)
            if connections:
                data["graph"] = connections

        return data

    def _build_graph_indexes(self, graph_data: dict[str, Any]) -> None:
        """
        Build indexes for O(1) graph lookups.

        Creates:
        - node_url_index: normalized URL -> node (for finding current page)
        - edge_index: node_id -> [edges] (for finding connected edges)

        Args:
            graph_data: Full graph data with nodes and edges
        """
        # Build URL -> node index for O(1) node lookup
        self._node_url_index = {}
        for node in graph_data.get("nodes", []):
            url = normalize_url(node.get("url", ""))
            if url:
                self._node_url_index[url] = node

        # Build node_id -> edges index for O(1) edge lookup
        self._edge_index = {}
        for edge in graph_data.get("edges", []):
            source_id = (
                edge.get("source", {}).get("id")
                if isinstance(edge.get("source"), dict)
                else edge.get("source")
            )
            target_id = (
                edge.get("target", {}).get("id")
                if isinstance(edge.get("target"), dict)
                else edge.get("target")
            )

            if source_id:
                self._edge_index.setdefault(source_id, []).append(edge)
            if target_id and target_id != source_id:
                self._edge_index.setdefault(target_id, []).append(edge)

    def _get_page_connections(
        self, page: Page, graph_data: dict[str, Any], max_connections: int = 15
    ) -> dict[str, Any] | None:
        """
        Get filtered graph data showing only connections to the current page.

        Args:
            page: Page object to get connections for
            graph_data: Full graph data from GraphVisualizer.generate_graph_data()
            max_connections: Maximum number of connected nodes to include

        Returns:
            Filtered graph data with only current page and its connections,
            or None if page not in graph
        """
        if not graph_data or not graph_data.get("nodes") or not graph_data.get("edges"):
            return None

        # Build indexes on first use (lazy initialization)
        if self._node_url_index is None or self._edge_index is None:
            self._build_graph_indexes(graph_data)

        # Get page URL for matching
        page_url = get_page_url(page, self.site)
        page_url_normalized = normalize_url(page_url)

        # Find current page node: O(1) lookup instead of O(nodes)
        current_node = self._node_url_index.get(page_url_normalized)

        if not current_node:
            # Page not in graph (might be excluded from analysis)
            return None

        # Collect connected node IDs
        connected_node_ids = {current_node["id"]}

        # Find all edges connected to current page: O(1) lookup instead of O(edges)
        connected_edges = self._edge_index.get(current_node["id"], [])

        for edge in connected_edges:
            source_id = (
                edge.get("source", {}).get("id")
                if isinstance(edge.get("source"), dict)
                else edge.get("source")
            )
            target_id = (
                edge.get("target", {}).get("id")
                if isinstance(edge.get("target"), dict)
                else edge.get("target")
            )

            if source_id == current_node["id"]:
                connected_node_ids.add(target_id)
            else:
                connected_node_ids.add(source_id)

        # Get connected nodes
        connected_nodes = [node for node in graph_data["nodes"] if node["id"] in connected_node_ids]

        # Sort by connectivity and limit
        connected_nodes.sort(
            key=lambda n: (n.get("incoming_refs", 0) + n.get("outgoing_refs", 0)),
            reverse=True,
        )
        limited_nodes = connected_nodes[:max_connections]
        limited_node_ids = {n["id"] for n in limited_nodes}

        # Filter edges to only include connections between limited nodes
        filtered_edges = [
            edge
            for edge in connected_edges
            if (
                edge.get("source", {}).get("id")
                if isinstance(edge.get("source"), dict)
                else edge.get("source")
            )
            in limited_node_ids
            and (
                edge.get("target", {}).get("id")
                if isinstance(edge.get("target"), dict)
                else edge.get("target")
            )
            in limited_node_ids
        ]

        # Mark current page
        for node in limited_nodes:
            if node["id"] == current_node["id"]:
                node["isCurrent"] = True

        return {"nodes": limited_nodes, "edges": filtered_edges}
