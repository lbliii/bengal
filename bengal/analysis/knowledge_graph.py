"""
Knowledge Graph Analysis for Bengal SSG.

Analyzes page connectivity, identifies hubs and leaves, finds orphaned pages,
and provides insights for optimization and content strategy.
"""

from typing import TYPE_CHECKING, Dict, List, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page

logger = get_logger(__name__)


@dataclass
class GraphMetrics:
    """
    Metrics about the knowledge graph structure.
    
    Attributes:
        total_pages: Total number of pages analyzed
        total_links: Total number of links between pages
        avg_connectivity: Average connectivity score per page
        hub_count: Number of hub pages (highly connected)
        leaf_count: Number of leaf pages (low connectivity)
        orphan_count: Number of orphaned pages (no incoming links)
    """
    total_pages: int
    total_links: int
    avg_connectivity: float
    hub_count: int
    leaf_count: int
    orphan_count: int


@dataclass
class PageConnectivity:
    """
    Connectivity information for a single page.
    
    Attributes:
        page: The page object
        incoming_refs: Number of incoming references
        outgoing_refs: Number of outgoing references
        connectivity_score: Total connectivity (incoming + outgoing)
        is_hub: True if page has many incoming references
        is_leaf: True if page has few connections
        is_orphan: True if page has no incoming references
    """
    page: 'Page'
    incoming_refs: int
    outgoing_refs: int
    connectivity_score: int
    is_hub: bool
    is_leaf: bool
    is_orphan: bool


class KnowledgeGraph:
    """
    Analyzes the connectivity structure of a Bengal site.
    
    Builds a graph of all pages and their connections through:
    - Internal links (cross-references)
    - Taxonomies (tags, categories)
    - Related posts
    - Menu items
    
    Provides insights for:
    - Content strategy (find orphaned pages)
    - Performance optimization (hub-first streaming)
    - Navigation design (understand structure)
    - SEO improvements (link structure)
    
    Example:
        >>> graph = KnowledgeGraph(site)
        >>> graph.build()
        >>> hubs = graph.get_hubs(threshold=10)
        >>> orphans = graph.get_orphans()
        >>> print(f"Found {len(orphans)} orphaned pages")
    """
    
    def __init__(self, site: 'Site', hub_threshold: int = 10, leaf_threshold: int = 2):
        """
        Initialize knowledge graph analyzer.
        
        Args:
            site: Site instance to analyze
            hub_threshold: Minimum incoming refs to be considered a hub
            leaf_threshold: Maximum connectivity to be considered a leaf
        """
        self.site = site
        self.hub_threshold = hub_threshold
        self.leaf_threshold = leaf_threshold
        
        # Graph data structures - now using pages directly as keys (hashable!)
        self.incoming_refs: Dict['Page', int] = defaultdict(int)  # page -> count
        self.outgoing_refs: Dict['Page', Set['Page']] = defaultdict(set)  # page -> target pages
        # Note: page_by_id no longer needed - pages are directly hashable
        
        # Analysis results
        self.metrics: GraphMetrics = None
        self._built = False
    
    def build(self) -> None:
        """
        Build the knowledge graph by analyzing all page connections.
        
        This analyzes:
        1. Cross-references (internal links between pages)
        2. Taxonomy references (pages grouped by tags/categories)
        3. Related posts (pre-computed relationships)
        4. Menu items (navigation references)
        
        Call this before using any analysis methods.
        """
        if self._built:
            logger.debug("knowledge_graph_already_built", action="skipping")
            return
        
        logger.info("knowledge_graph_build_start", total_pages=len(self.site.pages))
        
        # No need to build page ID mapping - pages are directly hashable!
        
        # Count references from different sources
        self._analyze_cross_references()
        self._analyze_taxonomies()
        self._analyze_related_posts()
        self._analyze_menus()
        
        # Compute metrics
        self.metrics = self._compute_metrics()
        
        self._built = True
        
        logger.info(
            "knowledge_graph_build_complete",
            total_pages=self.metrics.total_pages,
            total_links=self.metrics.total_links,
            hubs=self.metrics.hub_count,
            leaves=self.metrics.leaf_count,
            orphans=self.metrics.orphan_count
        )
    
    def _analyze_cross_references(self) -> None:
        """
        Analyze cross-references (internal links between pages).
        
        Uses the site's xref_index to find all internal links.
        """
        if not hasattr(self.site, 'xref_index') or not self.site.xref_index:
            logger.debug("knowledge_graph_no_xref_index", action="skipping cross-ref analysis")
            return
        
        # The xref_index maps paths/slugs/IDs to pages
        # We need to analyze which pages link to which
        for page in self.site.pages:
            # Analyze outgoing links from this page
            for link in getattr(page, 'links', []):
                # Try to resolve the link to a target page
                target = self._resolve_link(link)
                if target and target != page:
                    self.incoming_refs[target] += 1  # Direct page reference
                    self.outgoing_refs[page].add(target)  # Direct page reference
    
    def _resolve_link(self, link: str) -> 'Page':
        """
        Resolve a link string to a target page.
        
        Args:
            link: Link string (path, slug, or ID)
        
        Returns:
            Target page or None if not found
        """
        if not hasattr(self.site, 'xref_index') or not self.site.xref_index:
            return None
        
        # Try different lookup strategies
        xref = self.site.xref_index
        
        # Try by ID
        if link.startswith('id:'):
            return xref.get('by_id', {}).get(link[3:])
        
        # Try by path
        if '/' in link or link.endswith('.md'):
            clean_link = link.replace('.md', '').strip('/')
            return xref.get('by_path', {}).get(clean_link)
        
        # Try by slug
        pages = xref.get('by_slug', {}).get(link, [])
        return pages[0] if pages else None
    
    def _analyze_taxonomies(self) -> None:
        """
        Analyze taxonomy references (pages grouped by tags/categories).
        
        Pages in the same taxonomy group reference each other implicitly.
        """
        if not hasattr(self.site, 'taxonomies') or not self.site.taxonomies:
            logger.debug("knowledge_graph_no_taxonomies", action="skipping taxonomy analysis")
            return
        
        # For each taxonomy (tags, categories, etc.)
        for taxonomy_name, taxonomy_dict in self.site.taxonomies.items():
            # For each term in the taxonomy (e.g., 'python', 'tutorial')
            for term_slug, term_data in taxonomy_dict.items():
                # Get pages with this term
                pages = term_data.get('pages', [])
                
                # Each page in the group has incoming refs from the taxonomy
                for page in pages:
                    # Each page in a taxonomy gets a small boost
                    # (exists in this conceptual grouping)
                    self.incoming_refs[page] += 1  # Direct page reference
    
    def _analyze_related_posts(self) -> None:
        """
        Analyze related posts (pre-computed relationships).
        
        Related posts are pages that share tags or other criteria.
        """
        for page in self.site.pages:
            if not hasattr(page, 'related_posts') or not page.related_posts:
                continue
            
            # Each related post is an outgoing reference
            for related in page.related_posts:
                if related != page:
                    self.incoming_refs[related] += 1  # Direct page reference
                    self.outgoing_refs[page].add(related)  # Direct page reference
    
    def _analyze_menus(self) -> None:
        """
        Analyze menu items (navigation references).
        
        Pages in menus get a significant boost in importance.
        """
        if not hasattr(self.site, 'menu') or not self.site.menu:
            logger.debug("knowledge_graph_no_menus", action="skipping menu analysis")
            return
        
        # For each menu (main, footer, etc.)
        for menu_name, menu_items in self.site.menu.items():
            for item in menu_items:
                # Check if menu item has a page reference
                if hasattr(item, 'page') and item.page:
                    # Menu items get a significant boost (10 points)
                    self.incoming_refs[item.page] += 10  # Direct page reference
    
    def _compute_metrics(self) -> GraphMetrics:
        """
        Compute overall graph metrics.
        
        Returns:
            GraphMetrics with summary statistics
        """
        total_pages = len(self.site.pages)
        total_links = sum(len(targets) for targets in self.outgoing_refs.values())
        
        # Count hubs, leaves, orphans
        hub_count = 0
        leaf_count = 0
        orphan_count = 0
        total_connectivity = 0
        
        for page in self.site.pages:
            incoming = self.incoming_refs[page]  # Direct page lookup
            outgoing = len(self.outgoing_refs[page])  # Direct page lookup
            connectivity = incoming + outgoing
            
            total_connectivity += connectivity
            
            if incoming >= self.hub_threshold:
                hub_count += 1
            
            if connectivity <= self.leaf_threshold:
                leaf_count += 1
            
            if incoming == 0:
                orphan_count += 1
        
        avg_connectivity = total_connectivity / total_pages if total_pages > 0 else 0
        
        return GraphMetrics(
            total_pages=total_pages,
            total_links=total_links,
            avg_connectivity=avg_connectivity,
            hub_count=hub_count,
            leaf_count=leaf_count,
            orphan_count=orphan_count
        )
    
    def get_connectivity(self, page: 'Page') -> PageConnectivity:
        """
        Get connectivity information for a specific page.
        
        Args:
            page: Page to analyze
        
        Returns:
            PageConnectivity with detailed metrics
        
        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting connectivity")
        
        incoming = self.incoming_refs[page]  # Direct page lookup
        outgoing = len(self.outgoing_refs[page])  # Direct page lookup
        connectivity = incoming + outgoing
        
        return PageConnectivity(
            page=page,
            incoming_refs=incoming,
            outgoing_refs=outgoing,
            connectivity_score=connectivity,
            is_hub=incoming >= self.hub_threshold,
            is_leaf=connectivity <= self.leaf_threshold,
            is_orphan=incoming == 0
        )
    
    def get_hubs(self, threshold: int = None) -> List['Page']:
        """
        Get hub pages (highly connected pages).
        
        Hubs are pages with many incoming references. These are typically:
        - Index pages
        - Popular articles
        - Core documentation
        
        Args:
            threshold: Minimum incoming refs (defaults to self.hub_threshold)
        
        Returns:
            List of hub pages sorted by incoming references (descending)
        
        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting hubs")
        
        threshold = threshold if threshold is not None else self.hub_threshold
        
        hubs = [
            page for page in self.site.pages
            if self.incoming_refs[id(page)] >= threshold
        ]
        
        # Sort by incoming refs (descending)
        hubs.sort(key=lambda p: self.incoming_refs[id(p)], reverse=True)
        
        return hubs
    
    def get_leaves(self, threshold: int = None) -> List['Page']:
        """
        Get leaf pages (low connectivity pages).
        
        Leaves are pages with few connections. These are typically:
        - One-off blog posts
        - Changelog entries
        - Niche content
        
        Args:
            threshold: Maximum connectivity (defaults to self.leaf_threshold)
        
        Returns:
            List of leaf pages sorted by connectivity (ascending)
        
        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting leaves")
        
        threshold = threshold if threshold is not None else self.leaf_threshold
        
        leaves = [
            page for page in self.site.pages
            if self.get_connectivity_score(page) <= threshold
        ]
        
        # Sort by connectivity (ascending)
        leaves.sort(key=lambda p: self.get_connectivity_score(p))
        
        return leaves
    
    def get_orphans(self) -> List['Page']:
        """
        Get orphaned pages (no incoming references).
        
        Orphans are pages that no other page links to. These might be:
        - Forgotten content
        - Draft pages
        - Pages that should be linked from navigation
        
        Returns:
            List of orphaned pages sorted by slug
        
        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting orphans")
        
        orphans = [
            page for page in self.site.pages
            if self.incoming_refs[id(page)] == 0
            and not page.metadata.get('_generated')  # Exclude generated pages
        ]
        
        # Sort by slug for consistent ordering
        orphans.sort(key=lambda p: p.slug)
        
        return orphans
    
    def get_connectivity_score(self, page: 'Page') -> int:
        """
        Get total connectivity score for a page.
        
        Connectivity = incoming_refs + outgoing_refs
        
        Args:
            page: Page to analyze
        
        Returns:
            Connectivity score (higher = more connected)
        
        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting connectivity score")
        
        return self.incoming_refs[page] + len(self.outgoing_refs[page])  # Direct page lookup
    
    def get_layers(self) -> Tuple[List['Page'], List['Page'], List['Page']]:
        """
        Partition pages into three layers by connectivity.
        
        Layers enable hub-first streaming builds:
        - Layer 0 (Hubs): High connectivity, process first, keep in memory
        - Layer 1 (Mid-tier): Medium connectivity, batch processing
        - Layer 2 (Leaves): Low connectivity, stream and release
        
        Returns:
            Tuple of (hubs, mid_tier, leaves)
        
        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting layers")
        
        # Sort all pages by connectivity (descending)
        sorted_pages = sorted(
            self.site.pages,
            key=lambda p: self.get_connectivity_score(p),
            reverse=True
        )
        
        total = len(sorted_pages)
        
        # Layer thresholds (configurable)
        hub_cutoff = int(total * 0.10)  # Top 10%
        mid_cutoff = int(total * 0.40)  # Next 30%
        
        hubs = sorted_pages[:hub_cutoff]
        mid_tier = sorted_pages[hub_cutoff:mid_cutoff]
        leaves = sorted_pages[mid_cutoff:]
        
        return hubs, mid_tier, leaves
    
    def get_metrics(self) -> GraphMetrics:
        """
        Get overall graph metrics.
        
        Returns:
            GraphMetrics with summary statistics
        
        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting metrics")
        
        return self.metrics
    
    def format_stats(self) -> str:
        """
        Format graph statistics as a human-readable string.
        
        Returns:
            Formatted statistics string
        
        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before formatting stats")
        
        m = self.metrics
        hubs = self.get_hubs()
        orphans = self.get_orphans()
        
        output = []
        output.append("\n📊 Knowledge Graph Statistics")
        output.append("=" * 60)
        output.append(f"Total pages:        {m.total_pages}")
        output.append(f"Total links:        {m.total_links}")
        output.append(f"Average links:      {m.avg_connectivity:.1f} per page")
        output.append("")
        output.append("Connectivity Distribution:")
        output.append(f"  Hubs (>{self.hub_threshold} refs):  {m.hub_count} pages ({m.hub_count/m.total_pages*100:.1f}%)")
        mid_count = m.total_pages - m.hub_count - m.leaf_count
        output.append(f"  Mid-tier (3-{self.hub_threshold}):  {mid_count} pages ({mid_count/m.total_pages*100:.1f}%)")
        output.append(f"  Leaves (≤{self.leaf_threshold}):    {m.leaf_count} pages ({m.leaf_count/m.total_pages*100:.1f}%)")
        output.append("")
        
        # Show top hubs
        output.append("Top Hubs:")
        for i, page in enumerate(hubs[:5], 1):
            refs = self.incoming_refs[id(page)]
            output.append(f"  {i}. {page.title:<40} {refs} refs")
        
        if len(hubs) > 5:
            output.append(f"  ... and {len(hubs) - 5} more")
        
        # Show orphans
        output.append("")
        if orphans:
            output.append(f"Orphaned Pages ({len(orphans)} with 0 incoming refs):")
            for orphan in orphans[:5]:
                output.append(f"  • {orphan.source_path}")
            if len(orphans) > 5:
                output.append(f"  ... and {len(orphans) - 5} more")
        else:
            output.append("Orphaned Pages: None ✓")
        
        # Insights
        output.append("")
        output.append("💡 Insights:")
        leaf_pct = m.leaf_count / m.total_pages * 100 if m.total_pages > 0 else 0
        output.append(f"  • {leaf_pct:.0f}% of pages are leaves (could stream for memory savings)")
        
        if orphans:
            output.append(f"  • {len(orphans)} pages have no incoming links (consider adding navigation)")
        
        output.append("")
        
        return "\n".join(output)

