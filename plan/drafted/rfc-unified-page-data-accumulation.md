# RFC: Unified Page Data Accumulation

**Status**: Implemented  
**Author**: AI Assistant  
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Subsystems**: utils/build_context, rendering/pipeline, postprocess/output_formats

---

## Executive Summary

Consolidate JSON and search index data accumulation into a single unified accumulator during rendering. This eliminates redundant page iteration in `SiteIndexGenerator` and provides a foundation for future per-page data needs.

**Impact**: ~200-400ms saved on large sites, cleaner architecture with single accumulation point.

**Pattern**: Extends existing `_accumulated_page_json` to include search-index fields.

---

## Problem Statement

### Current State

Bengal has two separate systems that compute similar per-page data:

1. **`_accumulated_page_json`** (during render) → consumed by `PageJSONGenerator`
2. **`SiteIndexGenerator.page_to_summary()`** (during post-process) → builds `index.json`

Both compute overlapping fields:

| Field | PageJSONGenerator | SiteIndexGenerator |
|-------|-------------------|-------------------|
| url | ✓ | ✓ |
| title | ✓ | ✓ |
| description | ✓ | ✓ |
| excerpt | ✓ | ✓ |
| plain_text | ✓ | ✓ (for excerpt) |
| tags | ✓ | ✓ |
| section | ✓ | ✓ |
| word_count | ✓ | ✓ |
| reading_time | ✓ | ✓ |

### The Problem

1. **Redundant computation** — Excerpt, word count, reading time computed twice
2. **Double iteration** — Pages iterated during render (JSON) and post-process (index)
3. **Scattered logic** — Per-page data computation spread across multiple modules
4. **Missed optimization** — `SiteIndexGenerator` can't use accumulated JSON because fields differ

### Performance Profile

```text
Post-processing (1134 pages)
────────────────────────────────────────────
PageJSONGenerator:     ~800ms (uses accumulated data ✓)
SiteIndexGenerator:    ~400ms (re-iterates pages ✗)
────────────────────────────────────────────

With unified accumulation:
PageJSONGenerator:     ~800ms (uses accumulated data ✓)
SiteIndexGenerator:    ~50ms  (uses accumulated data ✓)
```

---

## Goals

### Must Have

1. Single accumulation point during render for all per-page data
2. `SiteIndexGenerator` consumes accumulated data (no re-iteration)
3. Backward compatible (fallback to current behavior if no accumulated data)
4. No regression in data quality for either output
5. Support incremental builds (partial accumulation + fallback)

### Should Have

1. Clear separation between "core" fields (all consumers) and "optional" fields
2. Configurable field inclusion (don't compute unused fields)

### Non-Goals

- Changing output format of `index.json` or per-page JSON files
- Adding new fields to either output format
- Modifying sitemap/RSS generators (they use simple metadata)

---

## Design

### Architecture Overview

```text
                    ┌─────────────────────────────────┐
                    │      RenderingPipeline          │
                    │  _accumulate_unified_page_data  │
                    └─────────────┬───────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────────┐
                    │        BuildContext             │
                    │   _accumulated_page_data        │
                    │   (unified: JSON + index)       │
                    └─────────────┬───────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ PageJSONGenerator│ │SiteIndexGenerator│ │ Future Consumer │
    │  (per-page JSON) │ │   (index.json)   │ │                 │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Unified Page Data Structure

The dataclass must include ALL fields needed by both `PageJSONGenerator` and `SiteIndexGenerator`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AccumulatedPageData:
    """
    Unified per-page data accumulated during rendering.

    Contains all fields needed by:
    - PageJSONGenerator (per-page JSON files)
    - SiteIndexGenerator (index.json for search)
    """

    # =========================================================================
    # Identity (required by all consumers)
    # =========================================================================
    source_path: Path
    url: str              # Full URL with baseurl (for PageJSONGenerator)
    uri: str              # Relative path without baseurl (for SiteIndexGenerator)

    # =========================================================================
    # Core Metadata (required by all consumers)
    # =========================================================================
    title: str
    description: str
    date: str | None      # ISO format (YYYY-MM-DD for index, full ISO for JSON)
    date_iso: str | None  # Full ISO format for PageJSONGenerator

    # =========================================================================
    # Content Derivatives (computed once, used by many)
    # =========================================================================
    plain_text: str
    excerpt: str                    # Short excerpt (excerpt_length chars)
    content_preview: str            # Longer preview for search (excerpt_length * 3)
    word_count: int
    reading_time: int

    # =========================================================================
    # Classification (for search/filtering)
    # =========================================================================
    section: str
    tags: list[str]

    # =========================================================================
    # Navigation/Structure (for SiteIndexGenerator)
    # =========================================================================
    dir: str              # Directory path (e.g., "/docs/getting-started/")

    # =========================================================================
    # Enhanced Metadata (for SiteIndexGenerator)
    # These are extracted from page.metadata during accumulation
    # =========================================================================
    enhanced_metadata: dict[str, Any] = field(default_factory=dict)
    # Contains: type, layout, author, authors, category, categories, weight,
    #           draft, featured, search_keywords, search_exclude, cli_name,
    #           api_module, difficulty, level, related, lastmod, source_file,
    #           version, isAutodoc

    # =========================================================================
    # Extended Data for PageJSONGenerator
    # Only populated if per-page JSON is enabled
    # =========================================================================
    full_json_data: dict[str, Any] | None = None
    json_output_path: Path | None = None

    # =========================================================================
    # Raw Metadata (fallback for fields we didn't anticipate)
    # =========================================================================
    raw_metadata: dict[str, Any] = field(default_factory=dict)
```

### Data Flow

```text
Render Phase                          Post-Process Phase
────────────────                      ──────────────────

page.render()  
    │  
    ▼  
format_html()  
    │  
    ▼  
_accumulate_unified_page_data()  
    │  
    ├─► url, uri = compute_urls()  
    ├─► plain_text = page.plain_text  
    ├─► excerpt = generate_excerpt()  
    ├─► content_preview = excerpt*3  
    ├─► word_count = len(split())  
    ├─► reading_time = word_count/200
    ├─► enhanced_metadata = extract()
    │  
    ▼  
BuildContext._accumulated_page_data  
                                          │
                                          ├──► PageJSONGenerator
                                          │    (writes per-page .json)
                                          │    + patches graph data
                                          │
                                          └──► SiteIndexGenerator
                                               (builds index.json)
                                               (hybrid mode for incremental)
```

### Incremental Build Behavior

During incremental builds, only changed pages are rendered. The accumulator handles this with a hybrid approach:

```text
Full Build (all pages rendered):
────────────────────────────────
accumulated_data.count == pages.count
→ SiteIndexGenerator uses accumulated data only

Incremental Build (partial render):
────────────────────────────────────
accumulated_data.count < pages.count
→ SiteIndexGenerator uses hybrid mode:
  - accumulated_data for rendered pages (fast lookup by source_path)
  - page_to_summary() for non-rendered pages (fallback)
```

---

## Implementation

### Phase 1: Extend BuildContext

**File**: `bengal/utils/build_context.py`

Replace `_accumulated_page_json` with unified accumulator:

```python
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass
class AccumulatedPageData:
    """Unified per-page data for post-processing consumers."""

    # Identity
    source_path: Path
    url: str
    uri: str

    # Core metadata
    title: str
    description: str
    date: str | None
    date_iso: str | None

    # Content derivatives
    plain_text: str
    excerpt: str
    content_preview: str
    word_count: int
    reading_time: int

    # Classification
    section: str
    tags: list[str]

    # Navigation
    dir: str

    # Enhanced metadata for index
    enhanced_metadata: dict[str, Any] = field(default_factory=dict)

    # Extended data for PageJSONGenerator
    full_json_data: dict[str, Any] | None = None
    json_output_path: Path | None = None

    # Raw metadata fallback
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildContext:
    # ... existing fields ...

    # Unified page data accumulation (replaces _accumulated_page_json)
    # Populated during rendering, consumed by PageJSONGenerator and SiteIndexGenerator
    _accumulated_page_data: list[AccumulatedPageData] = field(
        default_factory=list, repr=False
    )
    _accumulated_page_data_lock: Lock = field(default_factory=Lock, repr=False)
    # Index for O(1) lookup by source_path during hybrid mode
    _accumulated_page_index: dict[Path, AccumulatedPageData] = field(
        default_factory=dict, repr=False
    )

    def accumulate_page_data(self, data: AccumulatedPageData) -> None:
        """
        Accumulate unified page data during rendering (thread-safe).

        Called once per page during render phase. Data is consumed by
        multiple post-processing generators.
        """
        with self._accumulated_page_data_lock:
            self._accumulated_page_data.append(data)
            self._accumulated_page_index[data.source_path] = data

    def get_accumulated_page_data(self) -> list[AccumulatedPageData]:
        """Get accumulated page data for post-processing."""
        with self._accumulated_page_data_lock:
            return list(self._accumulated_page_data)

    def get_accumulated_for_page(self, source_path: Path) -> AccumulatedPageData | None:
        """
        Get accumulated data for a specific page (O(1) lookup).

        Used by SiteIndexGenerator in hybrid mode during incremental builds.
        """
        with self._accumulated_page_data_lock:
            return self._accumulated_page_index.get(source_path)

    @property
    def has_accumulated_page_data(self) -> bool:
        """Check if page data was accumulated during render."""
        with self._accumulated_page_data_lock:
            return len(self._accumulated_page_data) > 0

    @property
    def accumulated_page_count(self) -> int:
        """Get count of accumulated pages (for hybrid mode detection)."""
        with self._accumulated_page_data_lock:
            return len(self._accumulated_page_data)

    def clear_accumulated_page_data(self) -> None:
        """Clear accumulated page data to free memory."""
        with self._accumulated_page_data_lock:
            self._accumulated_page_data.clear()
            self._accumulated_page_index.clear()

    # =========================================================================
    # DEPRECATED: Legacy methods for backward compatibility
    # Remove in next major version
    # =========================================================================

    @property
    def has_accumulated_json(self) -> bool:
        """Deprecated: Use has_accumulated_page_data instead."""
        return self.has_accumulated_page_data

    def get_accumulated_json(self) -> list[tuple[Any, dict[str, Any]]]:
        """
        Deprecated: Use get_accumulated_page_data instead.

        Returns data in legacy format for backward compatibility.
        """
        with self._accumulated_page_data_lock:
            return [
                (data.json_output_path, data.full_json_data)
                for data in self._accumulated_page_data
                if data.full_json_data is not None
            ]
```

### Phase 2: Unified Accumulation in Pipeline

**File**: `bengal/rendering/pipeline/core.py`

Replace `_accumulate_json_data` with unified accumulator:

```python
def _accumulate_unified_page_data(self, page: Page) -> None:
    """
    Accumulate unified page data during rendering.

    Computes all per-page derivatives once (excerpt, word_count, etc.)
    for consumption by multiple post-processing generators.

    Replaces: _accumulate_json_data()
    """
    if not self.build_context or not self.site:
        return

    from bengal.postprocess.output_formats.utils import (
        generate_excerpt,
        get_page_json_path,
        get_page_relative_url,
        get_page_url,
    )
    from bengal.utils.autodoc import is_autodoc_page
    from bengal.utils.build_context import AccumulatedPageData

    try:
        # Compute URLs
        url = get_page_url(page, self.site)  # Full URL with baseurl
        uri = get_page_relative_url(page, self.site)  # Relative path

        # Content derivatives (computed once)
        plain_text = page.plain_text
        word_count = len(plain_text.split())
        excerpt_length = 200  # Could be configurable
        excerpt = generate_excerpt(plain_text, excerpt_length)
        content_preview = generate_excerpt(plain_text, excerpt_length * 3)

        # Directory structure
        dir_path = "/"
        if uri and isinstance(uri, str):
            path_parts = uri.strip("/").split("/")
            if len(path_parts) > 1:
                dir_path = "/" + "/".join(path_parts[:-1]) + "/"

        # Extract enhanced metadata for SiteIndexGenerator
        enhanced = self._extract_enhanced_metadata(page)

        # Build unified data
        data = AccumulatedPageData(
            source_path=page.source_path,
            url=url,
            uri=uri,
            title=page.title or "",
            description=page.metadata.get("description", "") or "",
            date=page.date.strftime("%Y-%m-%d") if page.date else None,
            date_iso=page.date.isoformat() if page.date else None,
            plain_text=plain_text,
            excerpt=excerpt,
            content_preview=content_preview,
            word_count=word_count,
            reading_time=max(1, round(word_count / 200)),
            section=page._section.name if page._section else "",
            tags=list(page.tags) if page.tags else [],
            dir=dir_path,
            enhanced_metadata=enhanced,
            raw_metadata=dict(page.metadata),
        )

        # Extended JSON data (only if per-page JSON enabled)
        output_formats_config = self.site.config.get("output_formats", {})
        per_page = output_formats_config.get("per_page", [])

        if "json" in per_page:
            json_path = get_page_json_path(page)
            if json_path:
                data.json_output_path = json_path
                data.full_json_data = self._build_full_json_data(page, data)

        self.build_context.accumulate_page_data(data)

    except Exception as e:
        logger.debug(
            "unified_page_data_accumulation_failed",
            page=str(page.source_path),
            error=str(e)[:100],
        )


def _extract_enhanced_metadata(self, page: Page) -> dict[str, Any]:
    """
    Extract enhanced metadata fields for SiteIndexGenerator.

    Mirrors the fields extracted by SiteIndexGenerator._add_enhanced_metadata()
    to ensure index.json output is identical.
    """
    from bengal.utils.autodoc import is_autodoc_page

    metadata = page.metadata
    enhanced: dict[str, Any] = {}

    # Content type and layout
    if value := metadata.get("type"):
        enhanced["type"] = value
    if value := metadata.get("layout"):
        enhanced["layout"] = value

    # Authorship
    if value := metadata.get("author"):
        enhanced["author"] = value
    if value := metadata.get("authors"):
        enhanced["authors"] = value

    # Categories
    if value := metadata.get("category"):
        enhanced["category"] = value
    if value := metadata.get("categories"):
        enhanced["categories"] = value

    # Weight for sorting
    if value := metadata.get("weight"):
        enhanced["weight"] = value

    # Status flags
    if metadata.get("draft"):
        enhanced["draft"] = True
    if metadata.get("featured"):
        enhanced["featured"] = True

    # Search-specific
    if value := metadata.get("search_keywords"):
        enhanced["search_keywords"] = value
    if metadata.get("search_exclude"):
        enhanced["search_exclude"] = True

    # Visibility system integration
    visibility = metadata.get("visibility")
    if metadata.get("hidden", False) or (
        isinstance(visibility, dict) and not visibility.get("search", True)
    ):
        enhanced["search_exclude"] = True

    # API/CLI specific
    if value := metadata.get("cli_name"):
        enhanced["cli_name"] = value
    if value := metadata.get("api_module"):
        enhanced["api_module"] = value

    # Difficulty/level
    if value := metadata.get("difficulty"):
        enhanced["difficulty"] = value
    if value := metadata.get("level"):
        enhanced["level"] = value

    # Related content
    if value := metadata.get("related"):
        enhanced["related"] = value

    # Last modified
    if value := metadata.get("lastmod"):
        if hasattr(value, "isoformat"):
            enhanced["lastmod"] = value.isoformat()
        else:
            enhanced["lastmod"] = str(value)

    # Source file path
    if value := metadata.get("source_file"):
        enhanced["source_file"] = value

    # Version field
    if hasattr(page, "version") and page.version:
        enhanced["version"] = page.version

    # Autodoc flag
    if is_autodoc_page(page):
        enhanced["isAutodoc"] = True

    return enhanced


def _build_full_json_data(
    self, page: Page, base_data: AccumulatedPageData
) -> dict[str, Any]:
    """Build full JSON data for per-page JSON files."""
    from bengal.postprocess.output_formats.json_generator import PageJSONGenerator

    # Reuse per-pipeline generator instance
    if self._page_json_generator is None:
        options = self.site.config.get("output_formats", {}).get("options", {})
        self._page_json_generator = PageJSONGenerator(
            self.site,
            graph_data=None,  # Graph not available during render
            include_html=options.get("include_html_content", False),
            include_text=options.get("include_plain_text", True),
        )

    return self._page_json_generator.page_to_json(page)
```

**Integration point** — Replace the call in `_render_page()`:

```python
# In _render_page() method, around line 516
# BEFORE:
self._accumulate_json_data(page)

# AFTER:
self._accumulate_unified_page_data(page)
```

### Phase 3: Update SiteIndexGenerator

**File**: `bengal/postprocess/output_formats/index_generator.py`

```python
from bengal.utils.build_context import AccumulatedPageData


class SiteIndexGenerator:
    # ... existing __init__ ...

    def generate(
        self,
        pages: list[Page],
        accumulated_data: list[AccumulatedPageData] | None = None,
        build_context: BuildContext | None = None,
    ) -> Path | list[Path]:
        """
        Generate site-wide index.json.

        Args:
            pages: List of pages (always needed for versioning grouping)
            accumulated_data: Optional pre-computed page data from rendering.
                            If provided, uses this instead of iterating pages.
            build_context: Optional BuildContext for hybrid mode lookups.

        Modes:
            - Full: accumulated_data covers all pages → use accumulated only
            - Hybrid: partial accumulated_data → use accumulated + fallback
            - Legacy: no accumulated_data → iterate all pages
        """
        # Store for hybrid mode
        self._build_context = build_context
        self._accumulated_index = {
            data.source_path: data for data in (accumulated_data or [])
        }

        # ... existing versioning check ...

        if not versioning_enabled:
            return self._generate_single_index(pages, accumulated_data)

        # Per-version indexes
        generated = []
        by_version = self._group_by_version(pages)

        for version_id, version_pages in by_version.items():
            # Filter accumulated data for this version
            version_accumulated = None
            if accumulated_data:
                version_paths = {p.source_path for p in version_pages}
                version_accumulated = [
                    d for d in accumulated_data if d.source_path in version_paths
                ]
            path = self._generate_version_index(version_id, version_pages, version_accumulated)
            generated.append(path)

        return generated

    def _generate_single_index(
        self,
        pages: list[Page],
        accumulated_data: list[AccumulatedPageData] | None = None,
    ) -> Path:
        """Generate single index.json with hybrid mode support."""
        logger.debug("generating_site_index_json", page_count=len(pages))

        site_data = self._build_site_metadata()

        # Determine mode
        accumulated_count = len(accumulated_data) if accumulated_data else 0
        use_hybrid = 0 < accumulated_count < len(pages)
        use_accumulated_only = accumulated_count == len(pages)

        if use_accumulated_only:
            # FAST PATH: All pages have accumulated data
            logger.debug("index_generator_mode", mode="accumulated_only")
            for data in accumulated_data:
                page_summary = self._accumulated_to_summary(data)
                self._add_to_site_data(site_data, page_summary)
        elif use_hybrid:
            # HYBRID PATH: Mix of accumulated + computed
            logger.debug(
                "index_generator_mode",
                mode="hybrid",
                accumulated=accumulated_count,
                total=len(pages),
            )
            for page in pages:
                if acc_data := self._accumulated_index.get(page.source_path):
                    page_summary = self._accumulated_to_summary(acc_data)
                else:
                    page_summary = self.page_to_summary(page)
                self._add_to_site_data(site_data, page_summary)
        else:
            # LEGACY PATH: Compute from pages
            logger.debug("index_generator_mode", mode="legacy")
            for page in pages:
                page_summary = self.page_to_summary(page)
                self._add_to_site_data(site_data, page_summary)

        # ... rest of generation (sections/tags aggregation, write) ...

    def _accumulated_to_summary(self, data: AccumulatedPageData) -> dict[str, Any]:
        """
        Convert accumulated data to index summary format.

        Produces identical output to page_to_summary() for consistency.
        """
        baseurl = self.site.config.get("baseurl", "").rstrip("/")

        summary: dict[str, Any] = {
            "objectID": data.uri,
            "url": data.url,
            "href": data.url,
            "uri": data.uri,
            "title": data.title,
            "description": data.description,
            "excerpt": data.excerpt,
            "section": data.section,
            "tags": data.tags,
            "word_count": data.word_count,
            "reading_time": data.reading_time,
            "dir": data.dir,
        }

        # Optional date
        if data.date:
            summary["date"] = data.date

        # Content for full-text search
        if data.content_preview:
            if self.include_full_content:
                summary["content"] = data.plain_text
            else:
                summary["content"] = data.content_preview

        # Enhanced metadata (type, author, draft, etc.)
        for key, value in data.enhanced_metadata.items():
            summary[key] = value

        # Content type alias
        if result_type := summary.get("type"):
            summary["kind"] = result_type

        return summary

    def _add_to_site_data(
        self, site_data: dict[str, Any], page_summary: dict[str, Any]
    ) -> None:
        """Add page summary to site data and update aggregations."""
        site_data["pages"].append(page_summary)

        # Count sections
        section = page_summary.get("section", "")
        if section:
            site_data["sections"][section] = site_data["sections"].get(section, 0) + 1

        # Count tags
        for tag in page_summary.get("tags", []):
            site_data["tags"][tag] = site_data["tags"].get(tag, 0) + 1
```

### Phase 4: Update OutputFormatsGenerator

**File**: `bengal/postprocess/output_formats/__init__.py`

```python
def generate(self) -> None:
    """Generate all enabled output formats."""
    # ... existing setup ...

    # Get accumulated data once (shared by multiple generators)
    accumulated_data = None
    if self.build_context and self.build_context.has_accumulated_page_data:
        accumulated_data = self.build_context.get_accumulated_page_data()
        logger.debug(
            "using_accumulated_page_data",
            count=len(accumulated_data),
            total_pages=len(pages),
        )

    # Per-page JSON
    if "json" in per_page:
        json_gen = PageJSONGenerator(...)
        # Extract JSON-specific data from accumulated
        accumulated_json = None
        if accumulated_data:
            accumulated_json = [
                (data.json_output_path, data.full_json_data)
                for data in accumulated_data
                if data.full_json_data is not None
            ]
        count = json_gen.generate(pages, accumulated_json=accumulated_json)
        generated.append(f"JSON ({count} files)")

    # Site-wide index
    if "index_json" in site_wide:
        index_gen = SiteIndexGenerator(...)
        # Pass accumulated data and build_context for hybrid mode
        index_result = index_gen.generate(
            pages,
            accumulated_data=accumulated_data,
            build_context=self.build_context,
        )
        generated.append("index.json")
```

### Phase 5: Handle Graph Data Post-Processing

Graph data is computed after rendering, so `PageJSONGenerator` needs to patch it in:

**File**: `bengal/postprocess/output_formats/json_generator.py`

```python
def generate(
    self, pages: list[Page], accumulated_json: list[tuple[Any, dict[str, Any]]] | None = None
) -> int:
    """Generate JSON files with post-render graph patching."""

    if accumulated_json:
        page_items = list(accumulated_json)

        # GRAPH PATCHING: Graph data wasn't available during rendering
        # Patch it in now if available
        if self.graph_data:
            page_url_map = {get_page_url(page, self.site): page for page in pages}
            for _json_path, page_data in page_items:
                page_url = page_data.get("url", "")
                if page := page_url_map.get(page_url):
                    connections = self._get_page_connections(page, self.graph_data)
                    if connections:
                        page_data["graph"] = connections
    else:
        # ... existing fallback logic ...
```

---

## Migration

### Backward Compatibility

1. **Deprecated methods preserved**: `get_accumulated_json()` and `has_accumulated_json` continue to work
2. **Automatic fallback**: Generators fall back to current behavior if no accumulated data
3. **No config changes**: Works automatically when pipeline accumulates data

### Deprecation Timeline

| Version | Action |
|---------|--------|
| Current | Add unified accumulator, keep legacy methods |
| +1 minor | Log deprecation warnings for legacy methods |
| +1 major | Remove legacy methods |

### Code Changes Summary

| File | Change |
|------|--------|
| `bengal/utils/build_context.py` | Add `AccumulatedPageData` dataclass, new accumulator methods |
| `bengal/rendering/pipeline/core.py` | Replace `_accumulate_json_data` with `_accumulate_unified_page_data` |
| `bengal/postprocess/output_formats/index_generator.py` | Add hybrid mode, `_accumulated_to_summary()` |
| `bengal/postprocess/output_formats/__init__.py` | Pass accumulated data to both generators |

---

## Performance Expectations

### Before

```text
Post-processing (1134 pages)
────────────────────────────────────────
JSON generation:     ~800ms (accumulated)
Index generation:    ~400ms (re-iterates)
────────────────────────────────────────
Total:              ~1200ms
```

### After

```text
Post-processing (1134 pages)
────────────────────────────────────────
JSON generation:     ~800ms (accumulated)
Index generation:     ~50ms (accumulated)
────────────────────────────────────────
Total:               ~850ms (~30% faster)
```

### Rendering Overhead

Additional per-page computation during render:

| Operation | Time/page |
|-----------|-----------|
| `generate_excerpt()` | ~0.5ms |
| `_extract_enhanced_metadata()` | ~0.2ms |
| Field assignments | ~0.1ms |
| **Total** | ~0.8ms |

Total: ~0.8ms × 1134 pages ÷ 8 workers ≈ **113ms** wall clock

**Net savings**: ~350ms - 113ms = **~237ms**

### Incremental Build (Hybrid Mode)

When 10% of pages change:

```text
Before: 400ms (iterates all pages)
After:  ~170ms (113 accumulated + 1021 computed at 0.35ms each)
```

---

## Testing

### Unit Tests

```python
# tests/unit/utils/test_accumulated_page_data.py

def test_accumulate_page_data_thread_safe():
    """Concurrent accumulation preserves all data."""
    ctx = BuildContext()

    def accumulate(i):
        data = AccumulatedPageData(
            source_path=Path(f"page{i}.md"),
            url=f"/page{i}/",
            uri=f"/page{i}/",
            # ... other fields
        )
        ctx.accumulate_page_data(data)

    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(accumulate, range(100))

    assert ctx.accumulated_page_count == 100


def test_get_accumulated_for_page_o1_lookup():
    """Source path lookup is O(1) via index."""
    ctx = BuildContext()
    path = Path("target.md")
    data = AccumulatedPageData(source_path=path, ...)
    ctx.accumulate_page_data(data)

    result = ctx.get_accumulated_for_page(path)
    assert result is data


def test_legacy_get_accumulated_json_format():
    """Legacy method returns (path, data) tuples."""
    ctx = BuildContext()
    data = AccumulatedPageData(
        ...,
        json_output_path=Path("out.json"),
        full_json_data={"title": "Test"},
    )
    ctx.accumulate_page_data(data)

    result = ctx.get_accumulated_json()
    assert result == [(Path("out.json"), {"title": "Test"})]
```

### Integration Tests

```python
# tests/integration/test_unified_accumulation.py

def test_index_json_identical_with_accumulation():
    """index.json content matches with/without accumulation."""
    # Build with accumulation
    site1 = build_site(use_accumulation=True)
    index1 = json.loads((site1.output_dir / "index.json").read_text())

    # Build without accumulation (legacy)
    site2 = build_site(use_accumulation=False)
    index2 = json.loads((site2.output_dir / "index.json").read_text())

    # Compare (ignore build_time)
    del index1["site"]["build_time"]
    del index2["site"]["build_time"]
    assert index1 == index2


def test_per_page_json_identical_with_accumulation():
    """Per-page JSON files identical with/without accumulation."""
    # Similar comparison for per-page JSON files


def test_incremental_build_hybrid_mode():
    """Hybrid mode produces correct index during incremental builds."""
    # Initial build
    site = build_site()

    # Modify one page
    modify_page(site, "docs/quickstart.md")

    # Incremental build (partial accumulation)
    rebuild_incremental(site)

    # Verify index includes all pages with correct data
    index = json.loads((site.output_dir / "index.json").read_text())
    assert len(index["pages"]) == expected_total_pages


def test_enhanced_metadata_preserved():
    """All enhanced metadata fields appear in index.json."""
    page = create_page(metadata={
        "type": "tutorial",
        "author": "Test Author",
        "difficulty": "beginner",
        "featured": True,
    })

    site = build_site(pages=[page])
    index = json.loads((site.output_dir / "index.json").read_text())

    page_entry = index["pages"][0]
    assert page_entry["type"] == "tutorial"
    assert page_entry["author"] == "Test Author"
    assert page_entry["difficulty"] == "beginner"
    assert page_entry["featured"] is True


def test_version_scoped_indexes_use_accumulated():
    """Per-version indexes correctly consume accumulated data."""
    # Build versioned site with accumulation
    site = build_versioned_site(versions=["v1", "v2"])

    # Verify each version index has correct page count
    v1_index = json.loads((site.output_dir / "docs/v1/index.json").read_text())
    v2_index = json.loads((site.output_dir / "index.json").read_text())

    assert len(v1_index["pages"]) == expected_v1_pages
    assert len(v2_index["pages"]) == expected_v2_pages
```

### Performance Tests

```python
# benchmarks/test_unified_accumulation.py

def test_index_generation_speedup():
    """Verify ~350ms savings on 1000+ page site."""
    site = load_large_site()  # 1134 pages

    # Measure without accumulation
    start = time.perf_counter()
    SiteIndexGenerator(site).generate(site.pages, accumulated_data=None)
    legacy_time = time.perf_counter() - start

    # Measure with accumulation
    accumulated = simulate_accumulation(site.pages)
    start = time.perf_counter()
    SiteIndexGenerator(site).generate(site.pages, accumulated_data=accumulated)
    optimized_time = time.perf_counter() - start

    speedup = legacy_time - optimized_time
    assert speedup > 0.2  # At least 200ms savings
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data structure mismatch (fields missing) | Medium | High | Comprehensive field audit, integration tests |
| Memory increase (larger dataclass) | Low | Low | ~500 bytes/page × 1134 = ~560KB |
| Migration complexity | Low | Low | Backward compatible, gradual deprecation |
| Hybrid mode bugs | Medium | Medium | Extensive incremental build tests |
| Graph patching regression | Low | Medium | Existing test coverage, explicit patching |

---

## Alternatives Considered

### 1. Keep Separate Accumulators

**Rejected**: Leads to scattered, duplicated computation. Harder to add new consumers.

### 2. Lazy Shared Cache

**Rejected**: Requires locking on read, complex invalidation. Accumulator pattern simpler.

### 3. Compute Everything in Post-Process

**Rejected**: Misses opportunity to compute while page data is hot in cache.

### 4. Minimal Field Extension

Add only `uri` and `section` to existing structure.

**Rejected**: Doesn't solve the full field mismatch problem. `SiteIndexGenerator` needs many more fields.

---

## Future Extensions

This unified accumulator pattern enables future optimizations:

1. **LLM text generation**: Could use accumulated `plain_text` instead of re-accessing
2. **Search suggestions**: Could accumulate heading structure for autocomplete
3. **Related pages**: Could accumulate link graph during render
4. **Custom outputs**: Third-party generators can consume accumulated data
5. **Sitemap generation**: Could use accumulated URLs and dates

---

## References

- `bengal/utils/build_context.py`: Current `_accumulated_page_json` implementation
- `bengal/rendering/pipeline/core.py`: `_accumulate_json_data()` method (line 538)
- `bengal/postprocess/output_formats/index_generator.py`: `SiteIndexGenerator`
- `bengal/postprocess/output_formats/json_generator.py`: `PageJSONGenerator`
- Inline Asset Extraction (Implemented): Related accumulation pattern (see changelog.md)
