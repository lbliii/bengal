# RFC: Output Cache Architecture

**Status**: Draft  
**Created**: 2026-01-14  
**Author**: AI Assistant  
**Related**: `rfc-incremental-build-observability.md`, `rfc-rebuild-decision-hardening.md`

---

## Executive Summary

This RFC proposes a comprehensive output caching architecture that enables:
- **Sub-second validation builds** by caching generated page output
- **Accurate change detection** via content hashes instead of mtimes
- **Smarter hot reload** that only triggers on meaningful content changes
- **Clear output categorization** distinguishing pages, aggregates, and assets

**Target**: Reduce validation build time from ~14s to <2s for unchanged content.

---

## Problem Statement

### Current State

When running `bengal serve`, the validation build exhibits several inefficiencies:

1. **Generated pages always rebuild** (~838 pages, ~12s)
   - Tag pages, section archives, API docs
   - No source file → no fingerprint → always "changed"
   - Even when underlying content hasn't changed

2. **Mtime-based change detection is noisy**
   - Regenerated files have new mtimes even with identical content
   - ReloadController reports 2744 "changed files" when 0 content changed
   - Triggers unnecessary hot reloads

3. **Aggregate files inflate change counts**
   - `sitemap.xml`, `index.json`, `llm-full.txt` always regenerate
   - Mixed with actual page changes in reporting
   - No way to distinguish "always changes" from "content changed"

4. **No output-level cache validation**
   - Cache validates source files, not output content
   - Can't determine if regenerated output differs from previous

### Impact

| Metric | Current | Target |
|--------|---------|--------|
| Validation build time | ~14s | <2s |
| Files reported changed | 2744 | ~20 (actual changes) |
| Unnecessary hot reloads | Frequent | Rare |
| Generated page render time | 12s | <500ms |

---

## Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Output Cache Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Source     │    │   Render     │    │   Output     │      │
│  │   Cache      │───▶│   Cache      │───▶│   Cache      │      │
│  │              │    │              │    │              │      │
│  │ file hashes  │    │ parsed AST   │    │ content hash │      │
│  │ dependencies │    │ metadata     │    │ output type  │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Content Hash Registry                    │      │
│  │  page_path → {content_hash, output_type, deps}       │      │
│  └──────────────────────────────────────────────────────┘      │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              ReloadController                         │      │
│  │  Compares content hashes, not mtimes                 │      │
│  │  Filters aggregate files from change reports         │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Output Type Classification

Categorize all output files for appropriate caching strategies:

```python
from enum import Enum, auto

class OutputType(Enum):
    """Classification of output files for caching strategy."""
    
    # Content pages - can be fully cached
    CONTENT_PAGE = auto()      # HTML from .md source files
    GENERATED_PAGE = auto()    # Tag pages, section archives, API docs
    
    # Aggregate outputs - always regenerated, but content-hashable
    AGGREGATE_INDEX = auto()   # index.json, search index
    AGGREGATE_FEED = auto()    # rss.xml, atom.xml, sitemap.xml
    AGGREGATE_TEXT = auto()    # llm-full.txt, index.txt
    
    # Static assets - fingerprinted separately
    ASSET = auto()             # CSS, JS, images
    
    # Passthrough - copied verbatim
    STATIC = auto()            # favicon, robots.txt


# File patterns for classification
OUTPUT_PATTERNS: dict[str, OutputType] = {
    # Aggregates (always regenerate, but hash content)
    "sitemap.xml": OutputType.AGGREGATE_FEED,
    "rss.xml": OutputType.AGGREGATE_FEED,
    "atom.xml": OutputType.AGGREGATE_FEED,
    "index.json": OutputType.AGGREGATE_INDEX,
    "index.json.hash": OutputType.AGGREGATE_INDEX,
    "llm-full.txt": OutputType.AGGREGATE_TEXT,
    "index.txt": OutputType.AGGREGATE_TEXT,
    
    # Static assets
    "asset-manifest.json": OutputType.ASSET,
}


def classify_output(path: Path, metadata: dict | None = None) -> OutputType:
    """Classify an output file by type."""
    name = path.name
    
    # Check explicit patterns first
    if name in OUTPUT_PATTERNS:
        return OUTPUT_PATTERNS[name]
    
    # Check metadata for generated pages
    if metadata and metadata.get("_generated"):
        return OutputType.GENERATED_PAGE
    
    # HTML files are content pages by default
    if path.suffix == ".html":
        return OutputType.CONTENT_PAGE
    
    # Assets in /assets/ directory
    if "assets" in path.parts:
        return OutputType.ASSET
    
    return OutputType.STATIC
```

#### 2. Content Hash Embedding

Embed content hashes in HTML output for validation:

```python
import hashlib
from typing import NamedTuple

class ContentHash(NamedTuple):
    """Content hash with metadata."""
    hash: str           # SHA-256 truncated to 16 chars
    output_type: OutputType
    dependencies: tuple[str, ...]  # Paths this output depends on


def compute_content_hash(content: str, truncate: int = 16) -> str:
    """Compute deterministic hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()[:truncate]


def embed_content_hash(html: str, content_hash: str) -> str:
    """Embed content hash in HTML meta tag.
    
    Inserts after <head> tag:
    <meta name="bengal:content-hash" content="a1b2c3d4e5f6g7h8">
    
    This enables:
    - Fast validation without reading full file
    - ReloadController to detect actual content changes
    - Cache validation at output level
    """
    meta_tag = f'<meta name="bengal:content-hash" content="{content_hash}">'
    
    # Insert after <head> tag
    if "<head>" in html:
        return html.replace("<head>", f"<head>\n    {meta_tag}", 1)
    elif "<head " in html:
        # Handle <head lang="en"> etc.
        idx = html.find("<head ")
        end_idx = html.find(">", idx)
        return html[:end_idx+1] + f"\n    {meta_tag}" + html[end_idx+1:]
    
    return html  # No <head> tag, return unchanged


def extract_content_hash(html: str) -> str | None:
    """Extract content hash from HTML meta tag.
    
    Returns None if no hash found (old/external content).
    """
    import re
    match = re.search(
        r'<meta\s+name="bengal:content-hash"\s+content="([a-f0-9]+)"',
        html
    )
    return match.group(1) if match else None
```

#### 3. Generated Page Output Cache

Cache rendered output for generated pages based on their computed content:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class GeneratedPageCacheEntry:
    """Cache entry for a generated page."""
    
    # Identity
    page_type: str              # "tag", "section-archive", "api-doc"
    page_id: str                # "python", "docs/reference", "Site.build"
    
    # Content hash (computed from rendered HTML, excluding timestamps)
    content_hash: str
    
    # Dependencies (pages that affect this generated page's content)
    # For tag page: all pages with this tag
    # For section archive: all pages in section
    member_hashes: dict[str, str]  # source_path → content_hash
    
    # Cached output (optional, for fast regeneration)
    cached_html: str | None = None
    
    # Metadata
    last_generated: str = ""    # ISO timestamp
    generation_time_ms: int = 0


class GeneratedPageCache:
    """Cache for generated page output.
    
    Generated pages (tag pages, section archives, API docs) are expensive
    to render but their content is deterministic based on member pages.
    
    Cache Strategy:
    1. Compute hash of all member page content hashes
    2. If combined hash matches cached entry, skip regeneration
    3. Otherwise, regenerate and update cache
    
    This converts O(n) rendering to O(1) hash comparison for unchanged content.
    """
    
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.entries: dict[str, GeneratedPageCacheEntry] = {}
        self._load()
    
    def _load(self) -> None:
        """Load cache from disk."""
        if not self.cache_path.exists():
            return
        # Implementation: Load from JSON/msgpack
    
    def _save(self) -> None:
        """Persist cache to disk."""
        # Implementation: Save to JSON/msgpack with compression
    
    def get_cache_key(self, page_type: str, page_id: str) -> str:
        """Generate cache key for generated page."""
        return f"{page_type}:{page_id}"
    
    def compute_member_hash(
        self,
        member_pages: list[Any],  # List of Page objects
        content_cache: dict[str, str],  # source_path → content_hash
    ) -> str:
        """Compute combined hash of all member page content.
        
        This is the key optimization: instead of rendering the generated
        page to check if it changed, we compare the combined hash of
        member content hashes.
        
        If member content is unchanged, generated output is unchanged.
        """
        # Sort for deterministic ordering
        member_hashes = sorted(
            content_cache.get(str(p.source_path), "")
            for p in member_pages
        )
        combined = "|".join(member_hashes)
        return compute_content_hash(combined)
    
    def should_regenerate(
        self,
        page_type: str,
        page_id: str,
        member_pages: list[Any],
        content_cache: dict[str, str],
    ) -> bool:
        """Check if generated page needs regeneration.
        
        Returns True if:
        - No cache entry exists
        - Member content has changed
        - Cache entry is corrupted
        """
        key = self.get_cache_key(page_type, page_id)
        entry = self.entries.get(key)
        
        if entry is None:
            return True
        
        current_hash = self.compute_member_hash(member_pages, content_cache)
        return current_hash != entry.content_hash
    
    def update(
        self,
        page_type: str,
        page_id: str,
        member_pages: list[Any],
        content_cache: dict[str, str],
        rendered_html: str,
        generation_time_ms: int,
    ) -> None:
        """Update cache after regeneration."""
        from datetime import datetime
        
        key = self.get_cache_key(page_type, page_id)
        member_hash = self.compute_member_hash(member_pages, content_cache)
        
        self.entries[key] = GeneratedPageCacheEntry(
            page_type=page_type,
            page_id=page_id,
            content_hash=member_hash,
            member_hashes={
                str(p.source_path): content_cache.get(str(p.source_path), "")
                for p in member_pages
            },
            cached_html=rendered_html if len(rendered_html) < 100_000 else None,
            last_generated=datetime.now().isoformat(),
            generation_time_ms=generation_time_ms,
        )
    
    def get_cached_html(self, page_type: str, page_id: str) -> str | None:
        """Get cached HTML if available and valid."""
        key = self.get_cache_key(page_type, page_id)
        entry = self.entries.get(key)
        return entry.cached_html if entry else None
```

#### 4. Enhanced ReloadController

Smarter reload decisions based on content hashes:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass
class ReloadDecision:
    """Result of reload analysis."""
    
    action: Literal["none", "reload", "css"]
    reason: str
    
    # Detailed change breakdown
    content_changes: list[Path] = field(default_factory=list)
    aggregate_changes: list[Path] = field(default_factory=list)
    asset_changes: list[Path] = field(default_factory=list)
    
    @property
    def meaningful_change_count(self) -> int:
        """Count of changes that affect user-visible content."""
        return len(self.content_changes) + len(self.asset_changes)


class ContentHashReloadController:
    """ReloadController that uses content hashes for change detection.
    
    Instead of comparing file mtimes (noisy, always different after regen),
    compares content hashes embedded in HTML files.
    
    Benefits:
    - Detects actual content changes, not just regeneration
    - Ignores timestamp-only changes
    - Provides accurate change reporting
    - Enables smarter hot reload decisions
    """
    
    def __init__(self):
        self.baseline_hashes: dict[str, str] = {}  # path → content_hash
        self.output_types: dict[str, OutputType] = {}  # path → type
    
    def capture_baseline(self, output_dir: Path) -> None:
        """Capture content hashes before build for comparison."""
        self.baseline_hashes.clear()
        self.output_types.clear()
        
        for html_file in output_dir.rglob("*.html"):
            rel_path = str(html_file.relative_to(output_dir))
            content = html_file.read_text(errors="ignore")
            
            # Extract embedded hash (fast) or compute (slower)
            hash_val = extract_content_hash(content)
            if hash_val is None:
                hash_val = compute_content_hash(content)
            
            self.baseline_hashes[rel_path] = hash_val
            self.output_types[rel_path] = classify_output(html_file)
    
    def analyze_changes(self, output_dir: Path) -> ReloadDecision:
        """Analyze changes after build and decide reload action.
        
        Compares content hashes instead of mtimes for accurate detection.
        Categorizes changes by output type for clear reporting.
        """
        content_changes: list[Path] = []
        aggregate_changes: list[Path] = []
        asset_changes: list[Path] = []
        
        # Check all HTML files
        for html_file in output_dir.rglob("*.html"):
            rel_path = str(html_file.relative_to(output_dir))
            content = html_file.read_text(errors="ignore")
            
            current_hash = extract_content_hash(content)
            if current_hash is None:
                current_hash = compute_content_hash(content)
            
            baseline_hash = self.baseline_hashes.get(rel_path)
            
            # New file or changed content
            if baseline_hash is None or current_hash != baseline_hash:
                output_type = self.output_types.get(
                    rel_path, 
                    classify_output(html_file)
                )
                
                if output_type in (OutputType.CONTENT_PAGE, OutputType.GENERATED_PAGE):
                    content_changes.append(html_file)
                elif output_type in (OutputType.AGGREGATE_INDEX, OutputType.AGGREGATE_FEED, OutputType.AGGREGATE_TEXT):
                    aggregate_changes.append(html_file)
                elif output_type == OutputType.ASSET:
                    asset_changes.append(html_file)
        
        # Check for CSS changes (CSS-only hot reload)
        css_only = (
            len(content_changes) == 0 and
            len(aggregate_changes) == 0 and
            self._check_css_changes(output_dir)
        )
        
        # Decide action
        if css_only:
            return ReloadDecision(
                action="css",
                reason="css-only-change",
                asset_changes=asset_changes,
            )
        
        if content_changes:
            return ReloadDecision(
                action="reload",
                reason="content-changed",
                content_changes=content_changes,
                aggregate_changes=aggregate_changes,
                asset_changes=asset_changes,
            )
        
        # Only aggregate files changed - no reload needed
        # (sitemap, feeds, etc. don't affect visible page content)
        if aggregate_changes and not content_changes:
            return ReloadDecision(
                action="none",
                reason="aggregate-only-changes",
                aggregate_changes=aggregate_changes,
            )
        
        return ReloadDecision(
            action="none",
            reason="no-changes",
        )
    
    def _check_css_changes(self, output_dir: Path) -> bool:
        """Check if CSS files changed."""
        # Implementation: Compare CSS file hashes
        return False
```

#### 5. Content Hash Registry

Central registry for all content hashes:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

@dataclass
class ContentHashRegistry:
    """Central registry mapping outputs to their content hashes.
    
    Provides O(1) lookup for:
    - Validating if output changed
    - Finding dependencies of generated pages
    - Computing aggregate hashes for cache keys
    
    Persisted to .bengal/content_hashes.json for cross-build validation.
    """
    
    # Source file → content hash (for content pages)
    source_hashes: dict[str, str] = field(default_factory=dict)
    
    # Output file → content hash (for all outputs)
    output_hashes: dict[str, str] = field(default_factory=dict)
    
    # Output file → output type classification
    output_types: dict[str, str] = field(default_factory=dict)
    
    # Generated page → member source paths
    generated_dependencies: dict[str, list[str]] = field(default_factory=dict)
    
    def update_source(self, source_path: Path, content_hash: str) -> None:
        """Update hash for a source file."""
        self.source_hashes[str(source_path)] = content_hash
    
    def update_output(
        self,
        output_path: Path,
        content_hash: str,
        output_type: OutputType,
    ) -> None:
        """Update hash for an output file."""
        key = str(output_path)
        self.output_hashes[key] = content_hash
        self.output_types[key] = output_type.name
    
    def update_generated_deps(
        self,
        generated_path: Path,
        member_sources: list[Path],
    ) -> None:
        """Track dependencies for generated page."""
        self.generated_dependencies[str(generated_path)] = [
            str(p) for p in member_sources
        ]
    
    def get_member_hashes(self, generated_path: Path) -> dict[str, str]:
        """Get content hashes for all members of generated page."""
        deps = self.generated_dependencies.get(str(generated_path), [])
        return {
            dep: self.source_hashes.get(dep, "")
            for dep in deps
        }
    
    def compute_generated_hash(self, generated_path: Path) -> str:
        """Compute combined hash for generated page validation."""
        member_hashes = self.get_member_hashes(generated_path)
        combined = "|".join(sorted(member_hashes.values()))
        return compute_content_hash(combined)
    
    def save(self, path: Path) -> None:
        """Persist registry to disk."""
        data = {
            "source_hashes": self.source_hashes,
            "output_hashes": self.output_hashes,
            "output_types": self.output_types,
            "generated_dependencies": self.generated_dependencies,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, path: Path) -> "ContentHashRegistry":
        """Load registry from disk."""
        if not path.exists():
            return cls()
        
        try:
            data = json.loads(path.read_text())
            return cls(
                source_hashes=data.get("source_hashes", {}),
                output_hashes=data.get("output_hashes", {}),
                output_types=data.get("output_types", {}),
                generated_dependencies=data.get("generated_dependencies", {}),
            )
        except Exception:
            return cls()
```

---

## Implementation Plan

### Phase 1: Content Hash Embedding (Week 1)

**Goal**: Embed content hashes in HTML output for validation.

**Tasks**:
- [ ] Add `compute_content_hash()` utility
- [ ] Add `embed_content_hash()` to HTML writer
- [ ] Add `extract_content_hash()` for fast validation
- [ ] Update `BengalRequestHandler` to preserve hash in live reload injection

**Files**:
- `bengal/utils/primitives/hashing.py` - Hash utilities
- `bengal/orchestration/build/rendering.py` - HTML output
- `bengal/server/live_reload.py` - Preserve hash during injection

**Validation**:
```bash
# Check hash is present in output
grep 'bengal:content-hash' public/docs/index.html
```

### Phase 2: Output Type Classification (Week 1)

**Goal**: Categorize outputs for appropriate caching strategies.

**Tasks**:
- [ ] Create `OutputType` enum
- [ ] Implement `classify_output()` function
- [ ] Add output type to build context
- [ ] Update stats to report by output type

**Files**:
- `bengal/orchestration/build/output_types.py` - New module
- `bengal/orchestration/stats.py` - Type-aware reporting

**Validation**:
```
✓ Built 1063 pages:
    225 content pages (cached: 225)
    526 generated pages (cached: 480)
    312 aggregate outputs (always rebuilt)
```

### Phase 3: Generated Page Cache (Week 2-3)

**Goal**: Cache generated page output based on member content hashes.

**Tasks**:
- [ ] Implement `GeneratedPageCacheEntry` dataclass
- [ ] Implement `GeneratedPageCache` class
- [ ] Integrate with taxonomy generation
- [ ] Integrate with section archive generation
- [ ] Integrate with API doc generation

**Files**:
- `bengal/cache/generated_page_cache.py` - New module
- `bengal/orchestration/taxonomy.py` - Use cache
- `bengal/orchestration/section.py` - Use cache
- `bengal/orchestration/autodoc.py` - Use cache

**Validation**:
```bash
# First run: generates all
bengal build --verbose
# ✓ Generated 526 pages in 8.2s

# Second run (no content changes): all cached
bengal build --verbose  
# ✓ Generated 526 pages in 0.3s (all cached)
```

### Phase 4: Enhanced ReloadController (Week 3)

**Goal**: Use content hashes for accurate change detection.

**Tasks**:
- [ ] Implement `ContentHashReloadController`
- [ ] Replace mtime-based detection with hash-based
- [ ] Filter aggregate files from change reports
- [ ] Update CLI output to show meaningful changes only

**Files**:
- `bengal/server/reload_controller.py` - Hash-based detection
- `bengal/server/dev_server.py` - Updated reporting

**Validation**:
```
# Before: noisy
! RELOAD TRIGGERED: 2744 files changed

# After: accurate
✓ Cache validated - 3 content pages updated
  Changed: docs/api/site.html, docs/api/page.html, docs/api/config.html
```

### Phase 5: Content Hash Registry (Week 4)

**Goal**: Central registry for fast cross-build validation.

**Tasks**:
- [ ] Implement `ContentHashRegistry` class
- [ ] Integrate with build pipeline
- [ ] Add registry persistence
- [ ] Add registry-based validation to serve-first

**Files**:
- `bengal/cache/content_hash_registry.py` - New module
- `bengal/orchestration/build/__init__.py` - Integration
- `bengal/server/dev_server.py` - Serve-first validation

**Validation**:
```bash
# Serve-first with registry validation
bengal serve
# ✓ Serving cached content (validating in background...)
# ✓ Cache validated in 0.8s - content is fresh
```

---

## Performance Analysis

### Current Performance

```
Validation Build (1063 pages):
├── Discovery:        450ms
├── Incremental:       50ms  
├── Assets:            10ms
├── Rendering:     11,700ms  ← 838 generated pages
├── Post-process:     800ms
├── Cache save:       400ms
└── Total:         ~14,000ms
```

### Target Performance

```
Validation Build (1063 pages, with output cache):
├── Discovery:        450ms
├── Incremental:       50ms
├── Hash validation:  200ms  ← Compare member hashes
├── Rendering:        300ms  ← Only changed pages
├── Post-process:     200ms  ← Skip unchanged aggregates
├── Cache save:       100ms  ← Incremental update
└── Total:         ~1,300ms
```

### Scaling Characteristics

| Site Size | Current | With Output Cache | Speedup |
|-----------|---------|-------------------|---------|
| 100 pages | 2s | 0.5s | 4x |
| 500 pages | 8s | 1s | 8x |
| 1000 pages | 14s | 1.3s | 11x |
| 5000 pages | 60s | 3s | 20x |

The speedup increases with site size because:
1. More generated pages benefit from caching
2. Hash comparison is O(1) regardless of page content size
3. Aggregate file regeneration becomes proportionally smaller

---

## API Design

### Public API

```python
# Content hash utilities
from bengal.utils.hashing import (
    compute_content_hash,
    embed_content_hash,
    extract_content_hash,
)

# Output type classification
from bengal.orchestration.output_types import (
    OutputType,
    classify_output,
)

# Generated page cache
from bengal.cache import GeneratedPageCache

cache = GeneratedPageCache(site.paths.generated_cache)
if cache.should_regenerate("tag", "python", member_pages, content_cache):
    html = render_tag_page(tag="python", pages=member_pages)
    cache.update("tag", "python", member_pages, content_cache, html, time_ms)
else:
    html = cache.get_cached_html("tag", "python")

# Content hash registry
from bengal.cache import ContentHashRegistry

registry = ContentHashRegistry.load(site.paths.content_registry)
registry.update_source(page.source_path, content_hash)
registry.update_output(output_path, output_hash, OutputType.CONTENT_PAGE)
registry.save(site.paths.content_registry)

# Enhanced reload controller
from bengal.server.reload_controller import ContentHashReloadController

controller = ContentHashReloadController()
controller.capture_baseline(output_dir)
# ... build ...
decision = controller.analyze_changes(output_dir)
if decision.action == "reload":
    print(f"Changed: {decision.meaningful_change_count} pages")
```

### Configuration

```yaml
# bengal.yaml
build:
  # Output cache settings
  cache_generated_pages: true    # Cache tag/section/API pages
  cache_aggregates: false        # Aggregates always regenerate
  content_hash_in_html: true     # Embed hash in meta tag
  
  # Validation settings
  hash_based_reload: true        # Use content hashes for reload
  ignore_aggregate_changes: true # Don't report sitemap/feed changes
```

---

## Migration Path

### Backward Compatibility

1. **Content hash embedding is additive** - Old HTML works without hash
2. **Generated page cache is optional** - Falls back to regeneration
3. **ReloadController enhancement is internal** - Same API, better behavior

### Migration Steps

1. **Phase 1-2**: Deploy with `content_hash_in_html: true`
   - All new builds include hash
   - Old cached pages work normally
   
2. **Phase 3**: Enable generated page cache
   - First build populates cache
   - Subsequent builds benefit immediately

3. **Phase 4-5**: Deploy enhanced reload controller
   - Immediate improvement in reload behavior
   - No user action required

---

## Testing Strategy

### Unit Tests

```python
def test_content_hash_deterministic():
    """Same content produces same hash."""
    content = "<html><body>Hello</body></html>"
    hash1 = compute_content_hash(content)
    hash2 = compute_content_hash(content)
    assert hash1 == hash2

def test_content_hash_different_for_different_content():
    """Different content produces different hash."""
    hash1 = compute_content_hash("<html>A</html>")
    hash2 = compute_content_hash("<html>B</html>")
    assert hash1 != hash2

def test_embed_and_extract_roundtrip():
    """Embedded hash can be extracted."""
    html = "<html><head></head><body>Test</body></html>"
    hash_val = "abc123def456"
    embedded = embed_content_hash(html, hash_val)
    extracted = extract_content_hash(embedded)
    assert extracted == hash_val

def test_generated_page_cache_skips_unchanged():
    """Cache returns True for unchanged member content."""
    cache = GeneratedPageCache(tmp_path / "cache.json")
    members = [mock_page("a.md"), mock_page("b.md")]
    hashes = {"a.md": "hash1", "b.md": "hash2"}
    
    # First time: needs regeneration
    assert cache.should_regenerate("tag", "python", members, hashes)
    
    # After update: no regeneration needed
    cache.update("tag", "python", members, hashes, "<html>...</html>", 100)
    assert not cache.should_regenerate("tag", "python", members, hashes)

def test_reload_controller_ignores_aggregate_changes():
    """ReloadController doesn't trigger reload for aggregate-only changes."""
    controller = ContentHashReloadController()
    controller.capture_baseline(output_dir)
    
    # Only modify sitemap.xml
    (output_dir / "sitemap.xml").write_text("<sitemap>new</sitemap>")
    
    decision = controller.analyze_changes(output_dir)
    assert decision.action == "none"
    assert decision.reason == "aggregate-only-changes"
```

### Integration Tests

```python
def test_serve_first_with_content_hash_validation():
    """Serve-first validates using content hashes."""
    # Build site
    site = create_test_site()
    site.build()
    
    # Start dev server in serve-first mode
    server = DevServer(site)
    
    # Validation should complete quickly with hash comparison
    start = time.time()
    server._run_validation_build()
    duration = time.time() - start
    
    assert duration < 2.0  # Target: <2s for unchanged content

def test_generated_page_cache_integration():
    """Generated pages are cached across builds."""
    site = create_test_site_with_tags()
    
    # First build: generates all tag pages
    stats1 = site.build()
    assert stats1.generated_pages_rendered == 100
    
    # Second build: all cached (no content changes)
    stats2 = site.build()
    assert stats2.generated_pages_cached == 100
    assert stats2.generated_pages_rendered == 0
```

---

## Risks and Mitigations

### Risk 1: Hash Collisions

**Risk**: Two different contents produce same hash (extremely unlikely with SHA-256).

**Mitigation**: Use 16-character truncated SHA-256 (64 bits). Collision probability is ~1 in 2^32 for a site with 65,536 pages. Acceptable for cache validation.

### Risk 2: Cache Invalidation Complexity

**Risk**: Generated page cache becomes stale due to missed dependencies.

**Mitigation**: 
- Track all member pages explicitly in cache entry
- Invalidate on ANY member change (conservative)
- Provide `bengal cache clear-generated` for manual invalidation

### Risk 3: Memory Usage

**Risk**: Storing cached HTML for generated pages uses too much memory.

**Mitigation**:
- Only cache HTML for pages under 100KB
- Use compression for cached content
- Provide config option to disable HTML caching

### Risk 4: Migration Issues

**Risk**: Old cache entries don't have content hashes, causing validation failures.

**Mitigation**:
- Fall back to full regeneration when hash missing
- Gradually populate hashes over builds
- No breaking changes to cache format

---

## Success Criteria

### Performance

- [ ] Validation build time <2s for unchanged 1000-page site
- [ ] Generated page cache hit rate >90% for unchanged content
- [ ] Memory overhead <50MB for 1000-page site

### Accuracy

- [ ] ReloadController reports only meaningful content changes
- [ ] Zero false positives (reload when no content changed)
- [ ] Zero false negatives (no reload when content changed)

### Ergonomics

- [ ] Clear CLI output showing cache utilization
- [ ] Accurate "X files changed" reporting
- [ ] Easy cache inspection with `bengal debug cache`

### Maintainability

- [ ] <500 lines of new code per phase
- [ ] >90% test coverage for new modules
- [ ] No changes to public API surface

---

## Future Enhancements

### Incremental Aggregate Generation

Instead of fully regenerating `sitemap.xml`, `index.json`, etc., incrementally update based on changed pages:

```python
def update_sitemap_incremental(
    existing_sitemap: str,
    changed_pages: list[Page],
    deleted_pages: list[Path],
) -> str:
    """Update sitemap with only changed entries."""
    # Parse existing, update changed, remove deleted, serialize
```

### Distributed Cache

For CI/CD pipelines, share generated page cache across builds:

```yaml
build:
  cache:
    remote: "s3://my-bucket/bengal-cache"
    share_generated_pages: true
```

### Content-Addressable Storage

Store generated page HTML by content hash for deduplication:

```
.bengal/cas/
├── a1b2c3d4.html.zst  # Tag page for "python"
├── e5f6g7h8.html.zst  # Tag page for "api"
└── ...
```

---

## References

- [RFC: Incremental Build Observability](rfc-incremental-build-observability.md)
- [RFC: Rebuild Decision Hardening](rfc-rebuild-decision-hardening.md)
- [Content-Addressable Storage](https://en.wikipedia.org/wiki/Content-addressable_storage)
- [HTTP ETag](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag)

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **Content Hash** | SHA-256 hash of page content, truncated to 16 chars |
| **Generated Page** | Page without source file (tag, archive, API doc) |
| **Aggregate Output** | File combining data from all pages (sitemap, index.json) |
| **Member Pages** | Content pages that contribute to a generated page |
| **Output Type** | Classification of output file for caching strategy |
| **Hash Registry** | Central mapping of paths to content hashes |
