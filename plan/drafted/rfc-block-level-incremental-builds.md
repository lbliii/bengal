# RFC: Block-Level Incremental Builds

**Status**: Draft  
**Created**: 2025-12-26  
**Priority**: High  
**Effort**: ~18 hours (~2.5 days)  
**Impact**: High — 90%+ reduction in template-triggered rebuilds  
**Category**: Orchestration / Incremental Builds / Performance  
**Scope**: `bengal/orchestration/incremental/`, `bengal/rendering/block_cache.py`  
**Dependencies**: RFC kida-template-introspection (implemented)  
**Reviewed**: 2025-12-26 — Added implementation details, thread safety, inheritance handling

---

## Executive Summary

This RFC proposes **block-level change detection** for incremental builds, leveraging Kida's template introspection API to dramatically reduce unnecessary page rebuilds when templates change.

**Current behavior**: Edit `base.html` → ALL pages using it rebuild  
**Proposed behavior**: Edit `base.html:footer` (site-scoped) → Just re-cache footer, skip page rebuilds

**Key Insight**: Most template edits (nav, footer, header) are to site-scoped blocks that don't require page-level rebuilds. The introspection API already tells us which blocks are site-scoped—we just need to use that information during change detection.

---

## Motivation

### The Problem

Consider a documentation site with 1,000 pages using `base.html`. When a developer edits the footer:

```
# Current behavior
Edit base.html (change footer text)
  └─ TemplateChangeDetector: "base.html changed"
  └─ get_affected_pages(): Returns ALL 1000 pages
  └─ Rebuild 1000 pages
  └─ Time: 30-60 seconds

# Desired behavior  
Edit base.html (change footer text)
  └─ BlockChangeDetector: "base.html:site_footer changed"
  └─ Introspection: "site_footer is site-scoped"
  └─ Re-warm footer block only (1 render)
  └─ Time: <1 second
```

### Why This Matters

| Scenario | Current | With Block-Level |
|----------|---------|------------------|
| Edit footer text | 1000 pages rebuild | 1 block re-cache |
| Edit nav link | 1000 pages rebuild | 1 block re-cache |
| Edit page title block | 1000 pages rebuild | ~10 pages rebuild (those overriding it) |
| Edit content block | 1000 pages rebuild | 0 pages rebuild (never overridden in base) |

For dev server workflows, this is the difference between **waiting 30+ seconds** and **instant feedback**.

### Prerequisites Already Met

The infrastructure for this optimization already exists:

1. ✅ **Template Introspection API** — `template.block_metadata()` returns cache scope per block
2. ✅ **Block Cache** — `BlockCache` stores pre-rendered site-scoped blocks
3. ✅ **Cache Warming** — `warm_site_blocks()` pre-renders site-scoped blocks
4. ✅ **Cached Block Injection** — `_cached_blocks` injects cached HTML during rendering
5. ✅ **Dependency Tracker** — `DependencyTracker` tracks template→page dependencies

We just need to connect these systems with block-level granularity.

---

## Design

### Architecture Overview

```
Template Change Detected
        │
        ▼
┌───────────────────────────────────────┐
│    BlockChangeDetector (NEW)          │
│  ├── Parse template into blocks       │
│  ├── Hash each block's content        │
│  ├── Compare to cached block hashes   │
│  └── Return: {block_name: changed}    │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│    BlockScopeAnalyzer (uses existing) │
│  ├── Get block metadata via introspection │
│  ├── Classify changed blocks by scope │
│  └── Return: {site: [...], page: [...]} │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│    RebuildDecisionEngine (NEW)        │
│  ├── Site-scoped only? → Re-warm blocks, skip rebuilds │
│  ├── Page-scoped changes? → Find affected pages │
│  └── Return: (blocks_to_warm, pages_to_rebuild) │
└───────────────────────────────────────┘
```

### Component 1: Block Content Hashing

Store a hash of each block's content to detect fine-grained changes:

```python
# bengal/rendering/block_cache.py

class BlockCache:
    """Extended with block content hashing."""

    __slots__ = (
        "_site_blocks",
        "_cacheable_blocks",
        "_stats",
        "_enabled",
        "_block_hashes",  # NEW: {template:block -> content_hash}
    )

    def __init__(self, enabled: bool = True) -> None:
        # ... existing init ...
        self._block_hashes: dict[str, str] = {}

    def compute_block_hashes(
        self,
        engine: KidaTemplateEngine,
        template_name: str,
    ) -> dict[str, str]:
        """Compute content hashes for each block in a template.

        Uses the template's optimized AST to extract block content
        and compute stable hashes for change detection.

        Args:
            engine: KidaTemplateEngine instance
            template_name: Template to hash blocks for

        Returns:
            Dict of block_name → content_hash
        """
        template = engine.env.get_template(template_name)
        ast = template._optimized_ast

        if ast is None:
            return {}

        hashes = {}
        for block_name, block_node in self._extract_blocks(ast):
            content = self._serialize_block_ast(block_node)
            hashes[block_name] = hashlib.sha256(content.encode()).hexdigest()[:16]

        return hashes

    def detect_changed_blocks(
        self,
        engine: KidaTemplateEngine,
        template_name: str,
    ) -> set[str]:
        """Detect which blocks changed since last build.

        Compares current block hashes to cached hashes.

        Returns:
            Set of block names that changed
        """
        current_hashes = self.compute_block_hashes(engine, template_name)
        changed = set()

        for block_name, current_hash in current_hashes.items():
            key = f"{template_name}:{block_name}"
            cached_hash = self._block_hashes.get(key)

            if cached_hash != current_hash:
                changed.add(block_name)
                self._block_hashes[key] = current_hash

        return changed
```

### Component 2: Block Change Classifier

Classify changed blocks by their cache scope:

```python
# bengal/orchestration/incremental/block_detector.py

from typing import NamedTuple, Literal

class BlockChangeSet(NamedTuple):
    """Classification of changed blocks by scope."""
    site_scoped: set[str]    # Blocks that only need re-caching
    page_scoped: set[str]    # Blocks that may require page rebuilds
    unknown_scoped: set[str] # Blocks we can't classify (conservative rebuild)


class BlockChangeDetector:
    """Detects and classifies block-level template changes.

    Uses Kida's introspection API to determine which blocks changed
    and what scope they have, enabling smart rebuild decisions.
    """

    def __init__(
        self,
        engine: KidaTemplateEngine,
        block_cache: BlockCache,
    ) -> None:
        self.engine = engine
        self.block_cache = block_cache

    def detect_and_classify(
        self,
        template_name: str,
    ) -> BlockChangeSet:
        """Detect changed blocks and classify by scope.

        Args:
            template_name: Template to analyze

        Returns:
            BlockChangeSet with blocks grouped by scope
        """
        # Get changed blocks
        changed_blocks = self.block_cache.detect_changed_blocks(
            self.engine, template_name
        )

        if not changed_blocks:
            return BlockChangeSet(set(), set(), set())

        # Get block metadata from introspection
        cacheable = self.engine.get_cacheable_blocks(template_name)

        # Classify by scope
        site_scoped = set()
        page_scoped = set()
        unknown_scoped = set()

        for block_name in changed_blocks:
            scope = cacheable.get(block_name, "unknown")

            if scope == "site":
                site_scoped.add(block_name)
            elif scope == "page":
                page_scoped.add(block_name)
            else:
                unknown_scoped.add(block_name)

        return BlockChangeSet(site_scoped, page_scoped, unknown_scoped)
```

### Component 3: Smart Rebuild Decision Engine

Make rebuild decisions based on block classification:

```python
# bengal/orchestration/incremental/rebuild_decision.py

from dataclasses import dataclass
from pathlib import Path

@dataclass
class RebuildDecision:
    """Rebuild decision for a template change."""
    blocks_to_rewarm: set[str]     # Site-scoped blocks to re-cache
    pages_to_rebuild: set[Path]    # Pages that need full rebuild
    skip_all_pages: bool           # True if only site-scoped blocks changed
    reason: str                    # Human-readable explanation


class RebuildDecisionEngine:
    """Makes smart rebuild decisions based on block-level changes.

    Key insight: If only site-scoped blocks changed, we can skip
    page rebuilds entirely and just re-warm those blocks.
    """

    def __init__(
        self,
        block_detector: BlockChangeDetector,
        block_cache: BlockCache,
        dependency_tracker: DependencyTracker,
    ) -> None:
        self.block_detector = block_detector
        self.block_cache = block_cache
        self.tracker = dependency_tracker

    def decide(
        self,
        template_name: str,
        template_path: Path,
    ) -> RebuildDecision:
        """Decide what to rebuild for a template change.

        Args:
            template_name: Template that changed
            template_path: Path to template file

        Returns:
            RebuildDecision with blocks to re-warm and pages to rebuild
        """
        # Classify changed blocks
        changes = self.block_detector.detect_and_classify(template_name)

        # Case 1: No blocks changed (file touched but content identical)
        if not (changes.site_scoped or changes.page_scoped or changes.unknown_scoped):
            return RebuildDecision(
                blocks_to_rewarm=set(),
                pages_to_rebuild=set(),
                skip_all_pages=True,
                reason="No block content changed",
            )

        # Case 2: Only site-scoped blocks changed
        if changes.site_scoped and not (changes.page_scoped or changes.unknown_scoped):
            return RebuildDecision(
                blocks_to_rewarm=changes.site_scoped,
                pages_to_rebuild=set(),
                skip_all_pages=True,
                reason=f"Only site-scoped blocks changed: {changes.site_scoped}",
            )

        # Case 3: Page-scoped or unknown blocks changed
        # Need to rebuild affected pages
        affected_pages = self._get_affected_pages(
            template_path,
            changes.page_scoped | changes.unknown_scoped
        )

        return RebuildDecision(
            blocks_to_rewarm=changes.site_scoped,  # Still re-warm site blocks
            pages_to_rebuild=affected_pages,
            skip_all_pages=False,
            reason=f"Page-scoped blocks changed: {changes.page_scoped | changes.unknown_scoped}",
        )

    def _get_affected_pages(
        self,
        template_path: Path,
        changed_blocks: set[str],
    ) -> set[Path]:
        """Get pages affected by page-scoped block changes.

        For now, returns all pages using this template.
        Future: Could track which pages override which blocks
        for even finer granularity.
        """
        # Use existing dependency tracking
        affected = self.tracker.cache.get_affected_pages(template_path)
        return {Path(p) for p in affected}
```

### Component 4: Integration with TemplateChangeDetector

Modify the existing template detector to use block-level detection:

```python
# bengal/orchestration/incremental/template_detector.py

class TemplateChangeDetector:
    """Extended with block-level change detection."""

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
        block_cache: BlockCache | None = None,  # NEW
    ) -> None:
        self.site = site
        self.cache = cache
        self.block_cache = block_cache
        self._rebuild_engine: RebuildDecisionEngine | None = None

    def check_templates(
        self,
        *,
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check templates with block-level detection.

        If block cache is available and template engine is Kida,
        uses block-level detection for smarter rebuild decisions.
        """
        # ... collect template files ...

        for template_file in template_files:
            if not self.cache.is_changed(template_file):
                self.cache.update_file(template_file)
                continue

            # Try block-level detection first
            if self._can_use_block_detection(template_file):
                decision = self._decide_block_level(template_file)

                if decision.skip_all_pages:
                    # Just re-warm blocks, skip page rebuilds!
                    self._rewarm_blocks(template_file, decision.blocks_to_rewarm)
                    logger.info(
                        "template_change_block_level",
                        template=template_file.name,
                        blocks_rewarmed=list(decision.blocks_to_rewarm),
                        pages_skipped=True,
                        reason=decision.reason,
                    )
                    continue

                # Add only affected pages
                pages_to_rebuild.update(decision.pages_to_rebuild)
                if decision.blocks_to_rewarm:
                    self._rewarm_blocks(template_file, decision.blocks_to_rewarm)
            else:
                # Fallback to file-level (current behavior)
                affected = self.cache.get_affected_pages(template_file)
                for page_path_str in affected:
                    pages_to_rebuild.add(Path(page_path_str))

            if verbose:
                change_summary.modified_templates.append(template_file)

    def _can_use_block_detection(self, template_file: Path) -> bool:
        """Check if block-level detection is available for this template."""
        if self.block_cache is None:
            return False
        if self.site.config.get("template_engine") != "kida":
            return False
        return True

    def _rewarm_blocks(self, template_file: Path, blocks: set[str]) -> None:
        """Re-warm specific blocks after changes."""
        if not self.block_cache:
            return

        template_name = self._path_to_template_name(template_file)
        if not template_name:
            return

        # Clear old cached blocks
        for block_name in blocks:
            key = f"{template_name}:{block_name}"
            self.block_cache._site_blocks.pop(key, None)

        # Re-warm from engine
        from bengal.rendering.context import get_engine_globals
        from bengal.rendering.engines import create_engine

        engine = create_engine(self.site)
        site_context = get_engine_globals(self.site)

        for block_name in blocks:
            try:
                template = engine.env.get_template(template_name)
                html = template.render_block(block_name, site_context)
                self.block_cache.set(template_name, block_name, html, scope="site")
            except Exception:
                pass  # Block may not be renderable standalone
```

---

## Performance Impact

### Benchmarks (Projected)

| Scenario | Current | With Block-Level | Improvement |
|----------|---------|------------------|-------------|
| 1000 pages, edit footer | 30-60s | <1s | 60x faster |
| 1000 pages, edit nav | 30-60s | <1s | 60x faster |
| 1000 pages, edit page title | 30-60s | 5-10s | 3-6x faster |
| 1000 pages, edit content block | 30-60s | 0s | ∞ |

### Memory Overhead

- Block hashes: ~100 bytes per block × ~20 blocks × ~100 templates = ~200 KB
- Block AST serialization: Temporary, GC'd after hashing
- **Net impact**: Negligible (<1 MB)

---

## Rollout Plan

### Phase 1: Block Hashing (~2 hours)
- [ ] Add `_block_hashes` to `BlockCache`
- [ ] Implement `compute_block_hashes()` using AST serialization
- [ ] Implement `detect_changed_blocks()` with hash comparison
- [ ] Unit tests for block hashing

### Phase 2: Block Change Classifier (~3 hours)
- [ ] Create `BlockChangeDetector` class
- [ ] Implement `detect_and_classify()` using introspection
- [ ] Unit tests for classification

### Phase 3: Rebuild Decision Engine (~4 hours)
- [ ] Create `RebuildDecisionEngine` class
- [ ] Implement site-scoped optimization (skip page rebuilds)
- [ ] Implement page-scoped fallback (existing behavior)
- [ ] Unit tests for decision logic

### Phase 4: Integration (~3 hours)
- [ ] Modify `TemplateChangeDetector` to use block detection
- [ ] Add configuration option: `incremental.block_level: true`
- [ ] Integration tests with real templates

### Phase 5: Metrics & Logging (~2 hours)
- [ ] Add block-level change metrics to build stats
- [ ] Add logging for block-level decisions
- [ ] Update CLI output to show block-level savings

---

## Configuration

```yaml
# bengal.yaml
incremental:
  enabled: true
  block_level: true  # NEW: Enable block-level change detection
```

```yaml
# Disable for debugging
incremental:
  block_level: false  # Falls back to file-level detection
```

---

## Backward Compatibility

- **Default**: Block-level detection enabled for Kida engine
- **Fallback**: If introspection unavailable (bytecode cache, preserve_ast=False), uses file-level
- **Jinja2**: Not affected (file-level detection continues)
- **No breaking changes**: All existing behavior preserved

---

## Future Enhancements

These are explicitly **not** in scope but enabled by this RFC:

1. **Block override tracking** — Track which pages override which blocks for even finer page-level filtering
2. **Partial template rebuild** — Re-render only changed blocks within a page's cached output
3. **Block dependency graph** — Visualize which blocks depend on which variables
4. **Hot module replacement** — Live-inject updated block HTML without full page reload

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Dev server feedback time | <2s for site-scoped changes |
| Pages skipped | 90%+ for nav/footer/header edits |
| Memory overhead | <1 MB |
| False negatives | 0 (never skip a page that needs rebuild) |
| Backward compatibility | 100% (existing behavior preserved) |

---

## References

- `bengal/rendering/block_cache.py` — Block cache implementation
- `bengal/rendering/kida/analysis/` — Template introspection API
- `bengal/orchestration/incremental/template_detector.py` — Current template detection
- `plan/drafted/rfc-kida-template-introspection.md` — Introspection RFC (implemented)
- `tests/rendering/kida/test_automatic_block_caching.py` — Block caching tests
