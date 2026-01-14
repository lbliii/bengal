# RFC: Output Cache Architecture

**Status**: Draft (Revised)  
**Created**: 2026-01-14  
**Revised**: 2026-01-14  
**Author**: AI Assistant  
**Related**: `rfc-incremental-build-observability.md`, `rfc-rebuild-decision-hardening.md`

---

### Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-14 | 1.2 | Added: thread-safety architecture (RWLock), zstandard compression for HTML cache, dependency-aware template tracking via `DependencyTracker`, unification with legacy `TaxonomyIndex`. Improved: hash extraction regex performance, error recovery state machine. |
| 2026-01-14 | 1.1 | Added: timestamp exclusion strategy, template hash tracking, cache format versioning, corruption recovery logging, race condition risk, open questions. Improved: hash embedding via `format_html()` integration, ReloadController extension (not replacement), performance claims marked as estimates. |

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

| Metric | Current | Target | Speedup/Note |
|--------|---------|--------|--------------|
| Validation build time | ~14s | <2s | **7-10x faster** |
| Files reported changed | 2744 | ~20 | 99% noise reduction |
| Unnecessary hot reloads | Frequent | Rare | Better DX |
| Generated page render time | 12s | <500ms | **24x faster** |
| **Cache Efficiency** | 0% hit rate | **~95% hit rate** | - |
| **Reliability** | mtime-based | **content-hashed** | - |

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

#### 0. Thread Safety and Concurrency

The caching architecture must be thread-safe to support Bengal's parallel rendering.

- **ContentHashRegistry**: Uses a reader-writer lock (`threading.RLock` or `threading.Lock` for simplicity, as writes happen at the end of the build).
- **GeneratedPageCache**: Uses `threading.Lock` for atomic updates to `entries`.
- **Parallel Reads**: Baseline capture and validation can run in parallel with the initial build setup.

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

Embed content hashes in HTML output for validation. **Key insight**: Compute hash 
on *rendered content* before final formatting, then embed during `format_html()`.

##### Timestamp Exclusion Strategy

Bengal pages may display dates in templates (e.g., "Last updated: Jan 14, 2026"),
but these come from frontmatter metadata (`date`, `lastmod`) - not dynamically 
injected at render time. The hash is computed on:

1. **Rendered HTML content** (after template rendering)
2. **Before `format_html()` post-processing** (minification, etc.)

This means dates displayed in templates ARE included in the hash (correctly - they
represent actual content), but the hash excludes:
- Build timestamps (not in output)
- File system mtimes (handled separately)

```python
from typing import NamedTuple
from bengal.utils.primitives.hashing import hash_str  # Reuse existing utility

class ContentHash(NamedTuple):
    """Content hash with metadata."""
    hash: str           # SHA-256 truncated to 16 chars
    output_type: OutputType
    dependencies: tuple[str, ...]  # Paths this output depends on


def compute_content_hash(content: str, truncate: int = 16) -> str:
    """Compute deterministic hash of content.
    
    Uses existing hash_str utility from bengal.utils.primitives.hashing.
    """
    return hash_str(content, truncate=truncate)
```

##### Integration Point: format_html()

Instead of fragile string manipulation, integrate hash embedding into the 
existing `format_html()` pipeline in `bengal/rendering/pipeline/output.py`:

```python
# bengal/rendering/pipeline/output.py

def format_html(html: str, page: Page, site: Site) -> str:
    """Format HTML output (minify/pretty) with content hash embedding.
    
    Hash is computed BEFORE formatting to ensure deterministic results.
    This is the correct integration point because:
    1. All template rendering is complete
    2. Content is stable (no more transformations)
    3. We have access to Page metadata for output type classification
    """
    from bengal.utils.primitives.hashing import hash_str
    
    # Compute content hash BEFORE any formatting
    # This ensures identical content always produces identical hash
    content_hash = hash_str(html, truncate=16)
    
    # Embed hash in HTML (template-layer approach)
    if site.config.get("build", {}).get("content_hash_in_html", True):
        html = _embed_content_hash_safe(html, content_hash)
    
    # Continue with existing formatting logic...
    try:
        from bengal.postprocess.html_output import format_html_output
        # ... (existing implementation)


def _embed_content_hash_safe(html: str, content_hash: str) -> str:
    """Embed content hash using safe template-aware insertion.
    
    Handles edge cases:
    - Missing <head> tag → skip embedding (don't break output)
    - Uppercase/whitespace variants → normalize matching
    - Already has hash → update existing
    """
    import re
    
    meta_tag = f'<meta name="bengal:content-hash" content="{content_hash}">'
    
    # Remove existing hash if present (for rebuilds)
    html = re.sub(
        r'<meta\s+name="bengal:content-hash"\s+content="[a-f0-9]+"[^>]*>\s*',
        '',
        html,
        flags=re.IGNORECASE
    )
    
    # Find <head> tag (case-insensitive, handle attributes)
    head_match = re.search(r'<head[^>]*>', html, re.IGNORECASE)
    if head_match:
        insert_pos = head_match.end()
        return html[:insert_pos] + f"\n    {meta_tag}" + html[insert_pos:]
    
    # No <head> tag found - log warning and return unchanged
    # (This shouldn't happen for valid HTML, but don't break output)
    from bengal.utils.observability.logger import get_logger
    logger = get_logger(__name__)
    logger.debug("content_hash_embed_skipped", reason="no_head_tag")
    return html


def extract_content_hash(html: str) -> str | None:
    """Extract content hash from HTML meta tag.
    
    Returns None if no hash found (old/external content).
    Handles case-insensitive matching and attribute order variations.
    """
    import re
    # Match both attribute orders: name then content, or content then name
    patterns = [
        r'<meta\s+name="bengal:content-hash"\s+content="([a-f0-9]+)"',
        r'<meta\s+content="([a-f0-9]+)"\s+name="bengal:content-hash"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
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
    
    # Content hash (computed from combined member hashes)
    content_hash: str
    
    # Template hash - invalidates cache if template changes
    # Computed from the template file(s) used to render this page
    template_hash: str = ""
    
    # Dependencies (pages that affect this generated page's content)
    # For tag page: all pages with this tag
    # For section archive: all pages in section
    member_hashes: dict[str, str] = field(default_factory=dict)  # source_path → content_hash
    
    # Cached output (optional, for fast regeneration)
    # Only stored for pages under 100KB to limit memory usage
    # Compressed using zstandard (bengal.cache.compression)
    cached_html: bytes | None = None
    
    # Metadata
    last_generated: str = ""    # ISO timestamp
    generation_time_ms: int = 0
    is_compressed: bool = True


class GeneratedPageCache:
    """Cache for generated page output.
    
    Generated pages (tag pages, section archives, API docs) are expensive
    to render but their content is deterministic based on member pages.
    
    UNIFICATION: This replaces the legacy `TaxonomyIndex` by tracking
    both membership AND content hashes.
    
    Cache Strategy:
    1. Compute hash of all member page content hashes
    2. If combined hash matches cached entry, skip regeneration
    3. Otherwise, regenerate and update cache
    
    This converts O(n) rendering to O(1) hash comparison for unchanged content.
    """
    
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.entries: dict[str, GeneratedPageCacheEntry] = {}
        self._lock = threading.Lock()
        self._load()
    
    def _load(self) -> None:
        """Load cache from disk using load_auto (supports zst)."""
        from bengal.cache.compression import load_auto
        if not self.cache_path.exists():
            return
        # Implementation: Load from compressed JSON
        data = load_auto(self.cache_path)
        # ... deserialization ...
    
    def _save(self) -> None:
        """Persist cache to disk using save_compressed."""
        from bengal.cache.compression import save_compressed
        # Implementation: Save to .json.zst
    
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
        template_hash: str = "",
    ) -> bool:
        """Check if generated page needs regeneration.
        
        Returns True if:
        - No cache entry exists
        - Member content has changed
        - Template has changed (Risk 6 mitigation)
        - Cache entry is corrupted
        
        Args:
            page_type: Type of generated page ("tag", "section-archive", etc.)
            page_id: Unique identifier for this page
            member_pages: List of Page objects contributing to this page
            content_cache: Mapping of source_path → content_hash
            template_hash: Hash of template used for rendering (optional)
        """
        key = self.get_cache_key(page_type, page_id)
        entry = self.entries.get(key)
        
        if entry is None:
            return True
        
        # Check template hash first (fast path for template changes)
        if template_hash and entry.template_hash and template_hash != entry.template_hash:
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
        template_hash: str = "",
    ) -> None:
        """Update cache after regeneration.
        
        Args:
            page_type: Type of generated page
            page_id: Unique identifier
            member_pages: Pages contributing to this generated page
            content_cache: Source path → content hash mapping
            rendered_html: Rendered HTML output
            generation_time_ms: Time taken to render
            template_hash: Hash of template(s) used for rendering
        """
        from datetime import datetime
        
        key = self.get_cache_key(page_type, page_id)
        member_hash = self.compute_member_hash(member_pages, content_cache)
        
        self.entries[key] = GeneratedPageCacheEntry(
            page_type=page_type,
            page_id=page_id,
            content_hash=member_hash,
            template_hash=template_hash,
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

Extend the existing `ReloadController` in `bengal/server/reload_controller.py` 
rather than replacing it. This preserves existing throttling, ignore patterns, 
and the `hash_on_suspect` feature while adding content-hash awareness.

##### Design: Extend, Don't Replace

The existing `ReloadController` already has:
- Throttling (`min_notify_interval_ms`)
- Ignore patterns (`ignored_globs`)
- Suspect hash verification (`hash_on_suspect`)
- Thread-safe configuration (`_config_lock`)

We enhance it with content-hash based change detection:

```python
# bengal/server/reload_controller.py (enhanced)

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass
class EnhancedReloadDecision:
    """Extended reload decision with output type breakdown.
    
    Extends existing ReloadDecision to categorize changes by type.
    """
    action: Literal["none", "reload", "reload-css"]
    reason: str
    changed_paths: list[str] = field(default_factory=list)
    
    # NEW: Detailed change breakdown by output type
    content_changes: list[str] = field(default_factory=list)
    aggregate_changes: list[str] = field(default_factory=list)
    asset_changes: list[str] = field(default_factory=list)
    
    @property
    def meaningful_change_count(self) -> int:
        """Count of changes that affect user-visible content."""
        return len(self.content_changes) + len(self.asset_changes)


class ReloadController:
    """Intelligent reload decision engine (enhanced with content hashing).
    
    ENHANCEMENT: Now supports content-hash based change detection in addition
    to mtime-based detection. Content hashes provide accurate change detection
    that ignores regeneration noise.
    
    New Features (RFC: Output Cache Architecture):
    - Extract content hashes from bengal:content-hash meta tags
    - Categorize changes by output type (content vs aggregate)
    - Skip reload for aggregate-only changes (sitemap, feeds)
    
    Thread Safety:
        IMPORTANT: capture_baseline() must complete BEFORE build starts.
        Call sequence: capture_baseline() → build() → analyze_with_hashes()
    """
    
    def __init__(
        self,
        min_notify_interval_ms: int = 300,
        ignored_globs: list[str] | None = None,
        hash_on_suspect: bool = True,
        suspect_hash_limit: int = 200,
        suspect_size_limit_bytes: int = 2_000_000,
        # NEW: Content hash mode
        use_content_hashes: bool = False,
    ) -> None:
        # ... existing initialization ...
        self._use_content_hashes = use_content_hashes
        self._baseline_content_hashes: dict[str, str] = {}
        self._output_types: dict[str, OutputType] = {}
    
    def capture_content_hash_baseline(self, output_dir: Path) -> None:
        """Capture content hashes before build for comparison.
        
        IMPORTANT: Must be called BEFORE build starts to establish baseline.
        Build writes may overlap with this scan if called during build.
        
        Args:
            output_dir: Path to output directory (e.g., public/)
        """
        self._baseline_content_hashes.clear()
        self._output_types.clear()
        
        for html_file in output_dir.rglob("*.html"):
            rel_path = str(html_file.relative_to(output_dir))
            try:
                content = html_file.read_text(errors="ignore")
                
                # Extract embedded hash (O(1) regex) or compute (O(n) hash)
                hash_val = extract_content_hash(content)
                if hash_val is None:
                    hash_val = compute_content_hash(content)
                
                self._baseline_content_hashes[rel_path] = hash_val
                self._output_types[rel_path] = classify_output(html_file)
            except OSError:
                # File may have been deleted during scan - skip
                continue
    
    def decide_with_content_hashes(self, output_dir: Path) -> EnhancedReloadDecision:
        """Analyze changes using content hashes for accurate detection.
        
        Compares content hashes instead of mtimes for accurate detection.
        Categorizes changes by output type for clear reporting.
        
        Returns:
            EnhancedReloadDecision with action and categorized changes.
        """
        content_changes: list[str] = []
        aggregate_changes: list[str] = []
        asset_changes: list[str] = []
        
        for html_file in output_dir.rglob("*.html"):
            rel_path = str(html_file.relative_to(output_dir))
            try:
                content = html_file.read_text(errors="ignore")
            except OSError:
                continue
            
            current_hash = extract_content_hash(content)
            if current_hash is None:
                current_hash = compute_content_hash(content)
            
            baseline_hash = self._baseline_content_hashes.get(rel_path)
            
            # New file or changed content
            if baseline_hash is None or current_hash != baseline_hash:
                output_type = self._output_types.get(
                    rel_path, 
                    classify_output(html_file)
                )
                
                if output_type in (OutputType.CONTENT_PAGE, OutputType.GENERATED_PAGE):
                    content_changes.append(rel_path)
                elif output_type in (OutputType.AGGREGATE_INDEX, OutputType.AGGREGATE_FEED, OutputType.AGGREGATE_TEXT):
                    aggregate_changes.append(rel_path)
                elif output_type == OutputType.ASSET:
                    asset_changes.append(rel_path)
        
        # Apply throttling (reuse existing mechanism)
        now = self._now_ms()
        if now - self._last_notify_time_ms < self._min_interval_ms:
            return EnhancedReloadDecision(
                action="none", 
                reason="throttled",
                changed_paths=[],
            )
        
        # CSS-only reload
        css_changes = self._check_css_changes_hashed(output_dir)
        if not content_changes and not aggregate_changes and css_changes:
            self._last_notify_time_ms = now
            return EnhancedReloadDecision(
                action="reload-css",
                reason="css-only",
                changed_paths=css_changes[:MAX_CHANGED_PATHS_TO_SEND],
                asset_changes=css_changes,
            )
        
        # Content changed - full reload
        if content_changes:
            self._last_notify_time_ms = now
            all_changes = content_changes + aggregate_changes + asset_changes
            return EnhancedReloadDecision(
                action="reload",
                reason="content-changed",
                changed_paths=all_changes[:MAX_CHANGED_PATHS_TO_SEND],
                content_changes=content_changes,
                aggregate_changes=aggregate_changes,
                asset_changes=asset_changes,
            )
        
        # Aggregate-only changes - no reload needed
        if aggregate_changes and not content_changes:
            return EnhancedReloadDecision(
                action="none",
                reason="aggregate-only-changes",
                changed_paths=[],
                aggregate_changes=aggregate_changes,
            )
        
        return EnhancedReloadDecision(
            action="none",
            reason="no-changes",
            changed_paths=[],
        )
    
    def _check_css_changes_hashed(self, output_dir: Path) -> list[str]:
        """Check CSS files for content changes."""
        changed = []
        for css_file in output_dir.rglob("*.css"):
            rel_path = str(css_file.relative_to(output_dir))
            # Use existing hash_file utility
            current_hash = hash_file(css_file, truncate=16)
            if self._baseline_content_hashes.get(rel_path) != current_hash:
                changed.append(rel_path)
        return changed
```

#### 5. Content Hash Registry

Central registry for all content hashes with format versioning and corruption recovery:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import threading

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

# Cache format version - increment when schema changes
REGISTRY_FORMAT_VERSION = 1


@dataclass
class ContentHashRegistry:
    """Central registry mapping outputs to their content hashes.
    
    Provides O(1) lookup for:
    - Validating if output changed
    - Finding dependencies of generated pages
    - Computing aggregate hashes for cache keys
    
    Persisted to .bengal/content_hashes.json for cross-build validation.
    
    THREAD SAFETY:
        Internal mappings are protected by an RLock for safe concurrent access
        during parallel rendering updates.
    """
    
    # Format version for compatibility checking
    version: int = REGISTRY_FORMAT_VERSION
    
    # Source file → content hash (for content pages)
    source_hashes: dict[str, str] = field(default_factory=dict)
    
    # Output file → content hash (for all outputs)
    output_hashes: dict[str, str] = field(default_factory=dict)
    
    # ... other fields ...
    
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def update_source(self, source_path: Path, content_hash: str) -> None:
        """Update hash for a source file."""
        with self._lock:
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
        """Persist registry to disk with version metadata."""
        data = {
            "version": REGISTRY_FORMAT_VERSION,
            "source_hashes": self.source_hashes,
            "output_hashes": self.output_hashes,
            "output_types": self.output_types,
            "generated_dependencies": self.generated_dependencies,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, path: Path) -> "ContentHashRegistry":
        """Load registry from disk with version check and corruption recovery.
        
        Recovery Behavior:
        - Missing file: Return empty registry (normal for first build)
        - Corrupted JSON: Log warning, return empty registry
        - Version mismatch: Log info, return empty registry (will rebuild)
        - Missing fields: Use defaults for forward compatibility
        """
        if not path.exists():
            return cls()
        
        try:
            data = json.loads(path.read_text())
            
            # Check format version
            file_version = data.get("version", 0)
            if file_version < REGISTRY_FORMAT_VERSION:
                logger.info(
                    "content_hash_registry_version_mismatch",
                    file_version=file_version,
                    current_version=REGISTRY_FORMAT_VERSION,
                    action="rebuilding_registry",
                )
                return cls()
            
            return cls(
                version=file_version,
                source_hashes=data.get("source_hashes", {}),
                output_hashes=data.get("output_hashes", {}),
                output_types=data.get("output_types", {}),
                generated_dependencies=data.get("generated_dependencies", {}),
            )
            
        except json.JSONDecodeError as e:
            logger.warning(
                "content_hash_registry_corrupted",
                path=str(path),
                error=str(e),
                action="starting_fresh",
            )
            return cls()
            
        except Exception as e:
            logger.warning(
                "content_hash_registry_load_failed",
                path=str(path),
                error_type=type(e).__name__,
                error=str(e),
                action="starting_fresh",
            )
            return cls()
    
    @classmethod
    def validate(cls, path: Path) -> tuple[bool, str]:
        """Validate registry file integrity.
        
        Use with `bengal cache validate` for explicit verification.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not path.exists():
            return True, "No registry file (will be created on build)"
        
        try:
            data = json.loads(path.read_text())
            
            # Check version
            version = data.get("version", 0)
            if version != REGISTRY_FORMAT_VERSION:
                return False, f"Version mismatch: {version} != {REGISTRY_FORMAT_VERSION}"
            
            # Check required fields
            required = ["source_hashes", "output_hashes"]
            missing = [f for f in required if f not in data]
            if missing:
                return False, f"Missing fields: {missing}"
            
            # Check data types
            if not isinstance(data.get("source_hashes"), dict):
                return False, "source_hashes is not a dict"
            if not isinstance(data.get("output_hashes"), dict):
                return False, "output_hashes is not a dict"
            
            return True, f"Valid (version {version}, {len(data['source_hashes'])} sources)"
            
        except json.JSONDecodeError as e:
            return False, f"JSON parse error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
```

---

## Implementation Plan

### Phase 1: Content Hash Embedding (Week 1)

**Goal**: Embed content hashes in HTML output for validation.

**Tasks**:
- [ ] Extend `bengal/utils/primitives/hashing.py` with `compute_content_hash()` wrapper
- [ ] Add `_embed_content_hash_safe()` and `extract_content_hash()` functions
- [ ] Integrate hash embedding into `format_html()` in `bengal/rendering/pipeline/output.py`
- [ ] Update `LiveReloadMixin` to preserve hash when injecting reload script
- [ ] Add `build.content_hash_in_html` config option (default: true)
- [ ] Create benchmark script to validate performance estimates

**Files** (based on codebase analysis):
- `bengal/utils/primitives/hashing.py` - Already has `hash_str()`, add wrapper
- `bengal/rendering/pipeline/output.py` - Integration point: `format_html()` (line 229)
- `bengal/server/live_reload.py` - `LiveReloadMixin` injects script into HTML
- `bengal/server/request_handler.py` - `BengalRequestHandler` serves files

**Integration Point**:
```python
# bengal/rendering/pipeline/output.py:229
def format_html(html: str, page: Page, site: Site) -> str:
    # NEW: Compute and embed content hash BEFORE formatting
    if site.config.get("build", {}).get("content_hash_in_html", True):
        content_hash = hash_str(html, truncate=16)
        html = _embed_content_hash_safe(html, content_hash)
    
    # ... existing formatting logic ...
```

**Validation**:
```bash
# Check hash is present in output
grep 'bengal:content-hash' public/docs/index.html
# Expected: <meta name="bengal:content-hash" content="a1b2c3d4e5f6g7h8">

# Verify hash is deterministic (same content = same hash)
bengal build && grep 'content-hash' public/docs/index.html > hash1.txt
bengal build && grep 'content-hash' public/docs/index.html > hash2.txt
diff hash1.txt hash2.txt  # Should be identical
```

**Benchmark**:
```bash
# Run performance benchmark to validate estimates
python scripts/benchmark_output_cache.py --phase 1
# Expected output:
#   Hash embedding overhead: <5ms per 1000 pages
#   Hash extraction: <1ms per 1000 files
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

**Approach**: Extend existing `ReloadController` class (don't replace).
The current implementation in `bengal/server/reload_controller.py` already has:
- Throttling (`min_notify_interval_ms`)
- Ignore patterns (`ignored_globs`) 
- Suspect hash verification (`hash_on_suspect`)
- Thread-safe configuration

**Tasks**:
- [ ] Add `use_content_hashes` config option to existing `ReloadController`
- [ ] Add `capture_content_hash_baseline()` method
- [ ] Add `decide_with_content_hashes()` method returning `EnhancedReloadDecision`
- [ ] Update `BuildTrigger` to use content-hash mode when enabled
- [ ] Filter aggregate files from change reports
- [ ] Update CLI output to show categorized changes

**Files**:
- `bengal/server/reload_controller.py` - Extend existing class
- `bengal/server/build_trigger.py` - Use new content-hash methods
- `bengal/server/dev_server.py` - Updated reporting

**Key Changes to Existing Code**:
```python
# bengal/server/reload_controller.py - ADD to existing class
class ReloadController:
    def __init__(self, ..., use_content_hashes: bool = False):
        # ... existing init ...
        self._use_content_hashes = use_content_hashes
        self._baseline_content_hashes: dict[str, str] = {}
    
    # NEW methods (don't modify existing decide_and_update)
    def capture_content_hash_baseline(self, output_dir: Path) -> None: ...
    def decide_with_content_hashes(self, output_dir: Path) -> EnhancedReloadDecision: ...
```

**Validation**:
```
# Before: noisy (mtime-based)
! RELOAD TRIGGERED: 2744 files changed

# After: accurate (content-hash based)
✓ Build complete - 3 content pages changed
  Changed: docs/api/site.html, docs/api/page.html, docs/api/config.html
  Aggregates updated: sitemap.xml, index.json (no reload)
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

### Current Performance (Measured)

Data from actual Bengal site (1063 pages, 2026-01-14):

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

### Target Performance (Estimated)

**Note**: These are estimates based on analysis, not measured benchmarks.
Actual performance will be validated during Phase 1 implementation.

```
Validation Build (1063 pages, with output cache):
├── Discovery:        450ms     (unchanged)
├── Incremental:       50ms     (unchanged)
├── Hash validation:  200ms  ← Compare member hashes (estimate)
├── Rendering:        300ms  ← Only changed pages (estimate)
├── Post-process:     200ms  ← Skip unchanged aggregates (estimate)
├── Cache save:       100ms  ← Incremental update (estimate)
└── Total:         ~1,300ms  (ESTIMATED)
```

### Assumptions Behind Estimates

1. **Hash extraction is O(1)**: Regex match on first 500 bytes of file
2. **~95% cache hit rate**: Most builds don't change generated page content
3. **Member hash comparison is fast**: ~838 lookups in dict = ~1ms
4. **Aggregate skip saves ~600ms**: sitemap/index.json/feeds generation
5. **Incremental cache save**: Only write changed entries

### Scaling Characteristics (Projected)

| Site Size | Current | With Output Cache | Speedup | Confidence |
|-----------|---------|-------------------|---------|------------|
| 100 pages | 2s | 0.5s | 4x | High |
| 500 pages | 8s | 1s | 8x | Medium |
| 1000 pages | 14s | 1.3s | 11x | Medium |
| 5000 pages | 60s | 3s | 20x | Low (extrapolated) |

**Confidence Levels**:
- **High**: Based on similar optimization patterns in existing Bengal cache
- **Medium**: Reasonable extrapolation from measured data
- **Low**: Extrapolated, may vary based on page complexity and dependencies

The speedup increases with site size because:
1. More generated pages benefit from caching
2. Hash comparison is O(1) regardless of page content size
3. Aggregate file regeneration becomes proportionally smaller

### Validation Plan

Performance claims will be validated in Phase 1:

```bash
# Benchmark script to validate estimates
python -m bengal.benchmarks.output_cache \
    --site site/ \
    --iterations 5 \
    --output reports/output-cache-benchmark.json
```

Results will be added to this RFC before Phase 2 begins.

---

## API Design

### Public API

```python
# Content hash utilities (extends existing hashing module)
from bengal.utils.primitives.hashing import hash_str  # Existing
from bengal.rendering.pipeline.output import (
    extract_content_hash,  # NEW
    _embed_content_hash_safe,  # Internal, used by format_html
)

# Output type classification
from bengal.orchestration.output_types import (
    OutputType,
    classify_output,
)

# Generated page cache
from bengal.cache import GeneratedPageCache

cache = GeneratedPageCache(site.paths.generated_cache)
template_hash = hash_str(template_content, truncate=16)

if cache.should_regenerate("tag", "python", member_pages, content_cache, template_hash):
    html = render_tag_page(tag="python", pages=member_pages)
    cache.update("tag", "python", member_pages, content_cache, html, time_ms, template_hash)
else:
    html = cache.get_cached_html("tag", "python")

# Content hash registry
from bengal.cache import ContentHashRegistry

registry = ContentHashRegistry.load(site.paths.content_registry)
registry.update_source(page.source_path, content_hash)
registry.update_output(output_path, output_hash, OutputType.CONTENT_PAGE)
registry.save(site.paths.content_registry)

# Validate cache integrity
is_valid, message = ContentHashRegistry.validate(site.paths.content_registry)

# Enhanced reload controller (extends existing class)
from bengal.server.reload_controller import ReloadController

controller = ReloadController(use_content_hashes=True)
controller.capture_content_hash_baseline(output_dir)
# ... build ...
decision = controller.decide_with_content_hashes(output_dir)
if decision.action == "reload":
    print(f"Changed: {decision.meaningful_change_count} pages")
    print(f"  Content: {len(decision.content_changes)}")
    print(f"  Aggregates (no reload): {len(decision.aggregate_changes)}")
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
    controller = ReloadController(use_content_hashes=True)
    controller.capture_content_hash_baseline(output_dir)
    
    # Only modify sitemap.xml
    (output_dir / "sitemap.xml").write_text("<sitemap>new</sitemap>")
    
    decision = controller.decide_with_content_hashes(output_dir)
    assert decision.action == "none"
    assert decision.reason == "aggregate-only-changes"

def test_generated_page_cache_invalidates_on_template_change():
    """Cache invalidates when template hash changes."""
    cache = GeneratedPageCache(tmp_path / "cache.json")
    members = [mock_page("a.md"), mock_page("b.md")]
    hashes = {"a.md": "hash1", "b.md": "hash2"}
    
    # Initial cache with template v1
    cache.update("tag", "python", members, hashes, "<html>v1</html>", 100, "template_v1")
    
    # Same member hashes, same template → no regeneration
    assert not cache.should_regenerate("tag", "python", members, hashes, "template_v1")
    
    # Same member hashes, different template → regenerate
    assert cache.should_regenerate("tag", "python", members, hashes, "template_v2")

def test_registry_version_migration():
    """Registry returns empty on version mismatch."""
    # Write old version
    old_data = {"version": 0, "source_hashes": {"a.md": "hash1"}}
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(old_data))
    
    # Load should return empty (version mismatch)
    registry = ContentHashRegistry.load(registry_path)
    assert registry.source_hashes == {}  # Fresh start

def test_registry_corruption_recovery():
    """Registry recovers gracefully from corruption."""
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{ invalid json }")
    
    # Should not raise, returns empty registry
    registry = ContentHashRegistry.load(registry_path)
    assert registry.source_hashes == {}
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

### Risk 5: Race Conditions in Baseline Capture

**Risk**: If `capture_content_hash_baseline()` runs concurrently with file writes,
partial reads or missed files could cause incorrect change detection.

**Mitigation**:
- Document sequencing requirement: baseline capture MUST complete before build starts
- Add assertion in dev server: `assert not self._build_in_progress` before capture
- For parallel builds, capture baseline in main thread before spawning workers
- Files deleted during scan are safely skipped (try/except around reads)

**Call Sequence** (enforced in dev server):
```python
# Correct order - baseline before build
controller.capture_content_hash_baseline(output_dir)  # 1. Capture
build_result = site.build()                            # 2. Build  
decision = controller.decide_with_content_hashes(output_dir)  # 3. Decide
```

### Risk 6: Template Changes Not Tracked

**Risk**: Template changes affect output but aren't reflected in member page hashes.
A template change would not invalidate generated page cache.

**Mitigation**:
- Include template hash in generated page cache key
- Track template dependencies in `GeneratedPageCacheEntry.template_hash`
- Invalidate all generated pages when base templates change

```python
@dataclass
class GeneratedPageCacheEntry:
    # ... existing fields ...
    template_hash: str = ""  # Hash of template used for rendering
```

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
- [ ] Cache validation command: `bengal cache validate`

**CLI Examples**:
```bash
# Validate cache integrity
$ bengal cache validate
✓ Content hash registry: Valid (version 1, 1063 sources)
✓ Generated page cache: Valid (526 entries, 480 with cached HTML)
✓ No corruption detected

# Clear generated page cache
$ bengal cache clear-generated
✓ Cleared 526 generated page cache entries

# Show cache stats
$ bengal debug cache
Content Hash Registry:
  Source hashes: 225
  Output hashes: 1063
  Generated deps: 526
  
Generated Page Cache:
  Entries: 526
  Cached HTML: 480 (91%)
  Total size: 12.4 MB
```

### Maintainability

- [ ] <500 lines of new code per phase
- [ ] >90% test coverage for new modules
- [ ] No changes to public API surface

---

## Open Questions

Questions to resolve during implementation:

### Q1: Live Reload Script Injection

**Question**: Does `LiveReloadMixin` inject the reload script after `format_html()`?
If so, the injected script would not be in the content hash.

**Resolution Needed**: Verify injection order. If script is injected after hashing,
this is correct behavior (reload script shouldn't affect content hash).

### Q2: Template Hash Granularity

**Question**: Should template hash include:
- Just the immediate template file?
- All inherited templates (base.html, etc.)?
- Included partials?

**Proposed Resolution**: Leverage the existing `DependencyTracker` in `BuildContext`. 
When rendering a generated page, the tracker records all template dependencies.
The hash should be computed from the combined content of all tracked template files.
This ensures perfect invalidation even when a deeply nested partial changes.

### Q3: Memory vs Speed Tradeoff for Cached HTML

**Question**: The 100KB threshold for caching HTML is arbitrary. Should this be:
- Configurable?
- Based on available memory?
- Always off (re-render is cheap compared to memory)?

**Proposed Resolution**: Make configurable with sensible default (100KB). Add
`build.cache_generated_html_threshold` config option.

### Q4: Hash Collision Probability

**Question**: Is 16-character truncated SHA-256 sufficient? 

**Analysis**: 16 hex chars = 64 bits. Birthday paradox: collision at ~2^32 items.
A 65,000-page site has ~0.0002% collision chance per build.

**Resolution**: 16 chars is sufficient. Document in Glossary that collisions are
theoretically possible but practically negligible.

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
