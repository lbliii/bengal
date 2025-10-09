# Memory Optimization Strategies - Implementation Roadmap

**Date:** October 9, 2025  
**Status:** Planning  
**Prerequisites:** ✅ Hashable Pages (completed)  
**Estimated Effort:** 8-10 hours  

---

## 🎯 Executive Summary

With hashable pages enabling efficient set operations, we can implement sophisticated memory management for large-scale builds (5K-50K+ pages).

**Strategies:**
1. **Streaming Builds** - Process and release pages incrementally
2. **Lazy Loading** - Load page content on demand
3. **Selective Caching** - Keep only important pages in memory
4. **Memory Pooling** - Reuse page objects efficiently

**Business Value:**
- 📉 Build 50K pages on 4GB RAM (currently needs 16GB+)
- ⚡ Enable massive documentation sites
- 💰 Reduce server costs for CI/CD
- 🌍 Support resource-constrained environments

---

## 📊 Current Memory Profile

### Baseline (4K pages)

```
Component                  Memory      Percentage
─────────────────────────────────────────────────
Page objects              ~800 MB     65%
  - content strings       400 MB      32%
  - rendered_html        250 MB      20%
  - metadata             100 MB      8%
  - other fields          50 MB       5%

Site collections          ~200 MB     16%
  - taxonomies           100 MB      8%
  - xref_index            50 MB       4%
  - related_posts         50 MB       4%

Caches & indices          ~150 MB     12%
Knowledge graph            ~50 MB     4%
Other                      ~50 MB     3%
─────────────────────────────────────────────────
Total                   ~1,250 MB    100%
```

### Scaling Projection

| Pages | Current Memory | Optimized Memory | Savings |
|-------|----------------|------------------|---------|
| 1K    | 312 MB         | 150 MB           | 52%     |
| 4K    | 1.25 GB        | 400 MB           | 68%     |
| 10K   | 3.12 GB        | 800 MB           | 74%     |
| 50K   | 15.6 GB        | 2.5 GB           | 84%     |

---

## 🏗️ Architecture Design

### Strategy 1: Streaming Builds

**Concept:** Process pages in batches, releasing memory between batches.

```
┌─────────────────────────────────────────────────────┐
│ Traditional Build (Current)                          │
│ ═══════════════════════════════════════════════════ │
│  1. Load ALL 50K pages into memory                  │
│  2. Build taxonomies (references all pages)         │
│  3. Compute related posts (O(n²))                   │
│  4. Render ALL pages                                │
│  5. Write outputs                                   │
│  MEMORY: 50K pages × 300KB = 15GB                   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Streaming Build (Proposed)                          │
│ ═══════════════════════════════════════════════════ │
│  Phase 1: Build indices (lightweight)               │
│    - Load metadata only (no content/html)           │
│    - Build taxonomies with page references          │
│    - Compute PageRank scores                        │
│    - Identify hub pages (keep in memory)            │
│    MEMORY: 50K × 10KB = 500MB                       │
│                                                      │
│  Phase 2: Stream render in batches                  │
│    Batch 1: Hubs (1000 pages)                       │
│      - Load full content                            │
│      - Render with full site context                │
│      - Write & release                              │
│      MEMORY: 1K × 300KB = 300MB                     │
│                                                      │
│    Batch 2-N: Remaining pages (49K pages)           │
│      - Process in chunks of 1000                    │
│      - Load → Render → Write → Release              │
│      MEMORY: 1K × 300KB = 300MB (per batch)         │
│                                                      │
│  PEAK MEMORY: 500MB + 300MB = 800MB                 │
│  SAVINGS: 94% less memory!                          │
└─────────────────────────────────────────────────────┘
```

### Strategy 2: Lazy Content Loading

**Concept:** Separate metadata from content, load content only when needed.

```python
@dataclass
class Page:
    source_path: Path
    metadata: Dict[str, Any]
    
    # Lazy-loaded fields
    _content: Optional[str] = None
    _rendered_html: Optional[str] = None
    
    @property
    def content(self) -> str:
        """Load content on first access."""
        if self._content is None:
            self._content = self._load_content()
        return self._content
    
    def release_content(self):
        """Release content from memory (keep metadata)."""
        self._content = None
        self._rendered_html = None
```

### Strategy 3: Selective Caching

**Concept:** Keep important pages in memory, stream unimportant ones.

```python
class MemoryManager:
    """
    Manage page memory based on importance.
    
    Strategy:
    - Keep top 10% (by PageRank) in memory always
    - Middle 60% in LRU cache (size-limited)
    - Bottom 30% stream-only (never cache)
    """
    
    def __init__(self, site: Site, cache_size_mb: int = 500):
        self.site = site
        self.cache_size = cache_size_mb * 1024 * 1024
        
        # Categorize pages by importance
        graph = KnowledgeGraph(site)
        page_ranks = graph.compute_page_rank()
        
        sorted_pages = sorted(page_ranks.items(), key=lambda x: x[1], reverse=True)
        n = len(sorted_pages)
        
        # Top 10% - always in memory
        self.hot_pages: Set[Page] = set(p for p, _ in sorted_pages[:n//10])
        
        # Middle 60% - LRU cache
        self.warm_pages: Set[Page] = set(p for p, _ in sorted_pages[n//10:7*n//10])
        self.cache: LRUCache = LRUCache(maxsize=len(self.warm_pages) // 2)
        
        # Bottom 30% - stream only
        self.cold_pages: Set[Page] = set(p for p, _ in sorted_pages[7*n//10:])
    
    def get_page(self, page: Page) -> Page:
        """Get page, loading if necessary."""
        if page in self.hot_pages:
            return page  # Already in memory
        
        if page in self.warm_pages:
            return self.cache.get(page, self._load_page)
        
        # Cold page - load, use, don't cache
        return self._load_page(page)
```

---

## 📋 Implementation Plan

### Phase 1: Lightweight Page Objects (3 hours)

**Goal:** Separate metadata from content for selective loading.

#### 1.1: Page Metadata Extraction (1.5 hours)

**New File:** `bengal/core/page_metadata.py`

```python
"""
Lightweight page metadata for memory-efficient builds.

PageMetadata contains only essential fields needed for:
- Taxonomies
- Navigation
- Graph algorithms
- Link resolution

Full Page objects are loaded on-demand.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional


@dataclass
class PageMetadata:
    """
    Lightweight page metadata (~10KB vs ~300KB for full Page).
    
    Used during:
    - Initial site discovery
    - Index building
    - Graph analysis
    - Streaming builds
    """
    
    # Identity
    source_path: Path
    output_path: Optional[Path] = None
    
    # Metadata (from frontmatter)
    title: str = ""
    slug: str = ""
    tags: List[str] = field(default_factory=list)
    date: Optional[datetime] = None
    draft: bool = False
    
    # Relationships (references only)
    section_path: Optional[Path] = None
    related_slugs: List[str] = field(default_factory=list)  # Slugs, not full pages
    
    # Statistics
    word_count: int = 0
    link_count: int = 0
    
    def __hash__(self) -> int:
        """Hashable based on source_path."""
        return hash(self.source_path)
    
    def __eq__(self, other: Any) -> bool:
        """Equal if same source_path."""
        if not isinstance(other, PageMetadata):
            return NotImplemented
        return self.source_path == other.source_path
    
    @classmethod
    def from_page(cls, page: 'Page') -> 'PageMetadata':
        """Extract metadata from full Page object."""
        return cls(
            source_path=page.source_path,
            output_path=page.output_path,
            title=page.title,
            slug=page.slug,
            tags=page.tags,
            date=page.date,
            draft=page.draft,
            word_count=len(page.content.split()) if page.content else 0,
            link_count=len(page.links)
        )
    
    def to_page(self) -> 'Page':
        """Convert to full Page object (loads content from disk)."""
        from bengal.core.page import Page
        from bengal.utils.file_io import read_file
        
        # Load content from source file
        if self.source_path.exists():
            raw_content = read_file(self.source_path)
            # Parse frontmatter + content
            content, metadata = parse_frontmatter(raw_content)
        else:
            content, metadata = "", {}
        
        return Page(
            source_path=self.source_path,
            content=content,
            metadata=metadata,
            output_path=self.output_path,
            tags=self.tags
        )
```

#### 1.2: Metadata-Only Discovery (1.5 hours)

**Update:** `bengal/discovery/content_discovery.py`

```python
class ContentDiscovery:
    def __init__(self, content_dir: Path, metadata_only: bool = False):
        """
        Args:
            metadata_only: If True, load only metadata (not full content)
        """
        self.metadata_only = metadata_only
        # ...
    
    def discover(self) -> Tuple[List[Section], List[Union[Page, PageMetadata]]]:
        """
        Discover content, optionally in metadata-only mode.
        
        Returns:
            Sections and pages (or PageMetadata if metadata_only=True)
        """
        for md_file in md_files:
            if self.metadata_only:
                # Load only frontmatter, skip content
                metadata = self._load_metadata_only(md_file)
                self.pages.append(PageMetadata.from_dict(metadata, md_file))
            else:
                # Load full page
                page = self._load_page(md_file)
                self.pages.append(page)
```

---

### Phase 2: Streaming Orchestrator (3 hours)

**Goal:** Implement streaming build pipeline.

**New File:** `bengal/orchestration/streaming.py`

```python
"""
Streaming build orchestrator for memory-efficient large builds.

Strategy:
1. Build lightweight indices (metadata only)
2. Identify important pages (keep in memory)
3. Stream-render remaining pages in batches
4. Release memory between batches
"""

from typing import List, Set, Iterator
from pathlib import Path

from bengal.core.page import Page
from bengal.core.page_metadata import PageMetadata
from bengal.core.site import Site
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class StreamingBuildOrchestrator:
    """
    Memory-efficient build for large sites.
    
    Reduces memory usage by 70-90% for large builds (5K+ pages).
    """
    
    def __init__(self, 
                 site: Site,
                 batch_size: int = 1000,
                 keep_top_percent: int = 10):
        """
        Initialize streaming orchestrator.
        
        Args:
            site: Site instance
            batch_size: Pages per batch
            keep_top_percent: Percentage of top pages to keep in memory
        """
        self.site = site
        self.batch_size = batch_size
        self.keep_top_percent = keep_top_percent
        
        self.metadata_pages: List[PageMetadata] = []
        self.important_pages: Set[Page] = set()
    
    def build(self) -> BuildStats:
        """
        Execute streaming build.
        
        Phases:
        1. Lightweight discovery (metadata only)
        2. Build indices and identify important pages
        3. Render important pages (keep in memory)
        4. Stream-render remaining pages in batches
        """
        stats = BuildStats()
        
        # Phase 1: Metadata-only discovery
        logger.info("streaming_discovery_start")
        self._discover_metadata()
        logger.info("streaming_discovery_complete", 
                   total_pages=len(self.metadata_pages),
                   memory_mb=self._estimate_memory())
        
        # Phase 2: Build indices
        logger.info("streaming_indices_start")
        self._build_indices()
        self._identify_important_pages()
        logger.info("streaming_indices_complete",
                   important_pages=len(self.important_pages))
        
        # Phase 3: Render important pages
        logger.info("streaming_render_important_start")
        self._render_important_pages(stats)
        
        # Phase 4: Stream-render remaining pages
        logger.info("streaming_render_remaining_start")
        self._stream_render_remaining(stats)
        
        return stats
    
    def _discover_metadata(self):
        """Discover pages in metadata-only mode."""
        from bengal.discovery.content_discovery import ContentDiscovery
        
        discovery = ContentDiscovery(
            self.site.root_path / "content",
            metadata_only=True
        )
        self.site.sections, self.metadata_pages = discovery.discover()
    
    def _build_indices(self):
        """Build taxonomies and indices from metadata."""
        # Build taxonomy index (slug → page paths)
        self.site.taxonomies = defaultdict(lambda: defaultdict(list))
        
        for meta in self.metadata_pages:
            for tag in meta.tags:
                tag_slug = tag.lower().replace(' ', '-')
                self.site.taxonomies['tags'][tag_slug]['pages'].append(meta.source_path)
    
    def _identify_important_pages(self):
        """
        Identify pages to keep in memory.
        
        Criteria:
        - Top N% by PageRank
        - Hub pages (many incoming links)
        - Navigation pages (in menus)
        """
        # Build lightweight graph from metadata
        graph = self._build_metadata_graph()
        
        # Compute PageRank on metadata
        page_ranks = graph.compute_page_rank()
        
        # Select top N%
        n = len(self.metadata_pages)
        threshold_idx = n * self.keep_top_percent // 100
        
        sorted_pages = sorted(page_ranks.items(), key=lambda x: x[1], reverse=True)
        important_metadata = [meta for meta, _ in sorted_pages[:threshold_idx]]
        
        # Convert important metadata to full pages
        for meta in important_metadata:
            page = meta.to_page()
            self.important_pages.add(page)
    
    def _render_important_pages(self, stats: BuildStats):
        """Render and keep important pages in memory."""
        from bengal.orchestration.render import RenderOrchestrator
        
        render = RenderOrchestrator(self.site)
        render.process(list(self.important_pages))
        
        stats.important_pages_rendered = len(self.important_pages)
    
    def _stream_render_remaining(self, stats: BuildStats):
        """Stream-render remaining pages in batches."""
        remaining_metadata = [
            meta for meta in self.metadata_pages
            if meta not in {m.source_path: m for m in self.important_pages}
        ]
        
        batches = self._batch_pages(remaining_metadata, self.batch_size)
        
        for batch_idx, batch_metadata in enumerate(batches):
            logger.debug("streaming_batch_start", 
                        batch=batch_idx,
                        size=len(batch_metadata))
            
            # Load batch into full pages
            batch_pages = [meta.to_page() for meta in batch_metadata]
            
            # Render batch
            from bengal.orchestration.render import RenderOrchestrator
            render = RenderOrchestrator(self.site)
            render.process(batch_pages)
            
            # Release batch from memory
            del batch_pages
            import gc
            gc.collect()
            
            stats.batches_processed += 1
            logger.debug("streaming_batch_complete",
                        batch=batch_idx,
                        memory_mb=self._estimate_memory())
    
    def _batch_pages(self, pages: List[PageMetadata], size: int) -> Iterator[List[PageMetadata]]:
        """Split pages into batches."""
        for i in range(0, len(pages), size):
            yield pages[i:i + size]
    
    def _estimate_memory(self) -> int:
        """Estimate current memory usage in MB."""
        import sys
        import gc
        
        gc.collect()
        
        # Rough estimation
        page_count = len(self.important_pages)
        metadata_count = len(self.metadata_pages)
        
        # Full pages: ~300KB each
        # Metadata: ~10KB each
        estimated_mb = (page_count * 300 + metadata_count * 10) // 1024
        
        return estimated_mb
```

---

### Phase 3: CLI Integration (1 hour)

**Update:** `bengal/cli.py`

```python
@app.command()
def build(
    # ... existing args ...
    memory_optimized: bool = typer.Option(
        False,
        "--memory-optimized",
        help="Use streaming build for large sites (5K+ pages)"
    ),
    batch_size: int = typer.Option(
        1000,
        help="Pages per batch in streaming mode"
    )
):
    """
    Build the static site.
    
    For large sites (5K+ pages), use --memory-optimized to reduce memory usage by 70-90%.
    """
    if memory_optimized:
        print("🌊 Streaming build enabled (memory-optimized)")
        orchestrator = StreamingBuildOrchestrator(site, batch_size=batch_size)
    else:
        orchestrator = BuildOrchestrator(site)
    
    stats = orchestrator.build(...)
```

---

### Phase 4: Memory Profiling Tools (1 hour)

**New File:** `bengal/utils/memory_profiler.py`

```python
"""
Memory profiling utilities for Bengal builds.

Track memory usage throughout the build process.
"""

import gc
import psutil
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time."""
    timestamp: datetime
    phase: str
    total_mb: float
    rss_mb: float  # Resident set size
    page_count: int
    metadata_count: int


class MemoryProfiler:
    """Track memory usage during build."""
    
    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.process = psutil.Process()
    
    def snapshot(self, phase: str, page_count: int = 0, metadata_count: int = 0):
        """Take a memory snapshot."""
        gc.collect()
        
        mem_info = self.process.memory_info()
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            phase=phase,
            total_mb=mem_info.vms / 1024 / 1024,
            rss_mb=mem_info.rss / 1024 / 1024,
            page_count=page_count,
            metadata_count=metadata_count
        )
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def report(self) -> str:
        """Generate memory usage report."""
        if not self.snapshots:
            return "No snapshots taken"
        
        lines = ["Memory Profile Report", "=" * 80]
        
        for i, snapshot in enumerate(self.snapshots):
            delta = ""
            if i > 0:
                prev = self.snapshots[i-1]
                delta_mb = snapshot.rss_mb - prev.rss_mb
                delta = f" ({delta_mb:+.1f} MB)"
            
            lines.append(
                f"{snapshot.phase:<30} {snapshot.rss_mb:>8.1f} MB{delta}"
            )
        
        lines.append("=" * 80)
        lines.append(f"Peak memory: {max(s.rss_mb for s in self.snapshots):.1f} MB")
        
        return "\n".join(lines)
```

---

### Phase 5: Testing & Validation (2 hours)

#### 5.1: Memory Usage Tests

```python
def test_streaming_memory_usage(tmp_path):
    """Test that streaming build uses less memory."""
    import psutil
    import gc
    
    # Create large site
    site = create_test_site(tmp_path, page_count=5000)
    
    # Traditional build
    gc.collect()
    mem_before = psutil.Process().memory_info().rss
    
    traditional = BuildOrchestrator(site)
    traditional.build()
    
    mem_traditional = psutil.Process().memory_info().rss - mem_before
    
    # Streaming build
    gc.collect()
    mem_before = psutil.Process().memory_info().rss
    
    streaming = StreamingBuildOrchestrator(site, batch_size=500)
    streaming.build()
    
    mem_streaming = psutil.Process().memory_info().rss - mem_before
    
    # Streaming should use significantly less memory
    assert mem_streaming < mem_traditional * 0.5, \
        f"Streaming ({mem_streaming/1024/1024:.1f}MB) should use < 50% of traditional ({mem_traditional/1024/1024:.1f}MB)"
```

#### 5.2: Correctness Tests

Ensure streaming builds produce identical output to traditional builds.

---

## 📈 Success Metrics

**Memory Reduction:**
- 1K pages: 50%+ reduction
- 4K pages: 70%+ reduction
- 10K+ pages: 80%+ reduction

**Performance:**
- Streaming overhead: < 10% slower
- Peak memory stays under 2GB for 50K pages

**Correctness:**
- Bit-identical output to traditional builds
- All tests pass in streaming mode

---

## 🚀 Future Enhancements

- **Memory-mapped files**: Even less memory for huge sites
- **Distributed builds**: Split work across multiple machines
- **Progressive builds**: Incremental + streaming combined
- **Smart batching**: Batch related pages together
- **Compression**: Compress cached data

---

## 📚 References

- Python `gc` module: Garbage collection
- `psutil`: Memory profiling
- Generator patterns for streaming
- LRU cache implementations

