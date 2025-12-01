# RFC: Edge Case Hardening for Bengal Core Features

**Status**: Draft  
**Author**: Edge Case Audit  
**Date**: 2025-11-26  
**Priority**: P0/P1 for public release readiness

---

## Executive Summary

Systematic review of Bengal's core features against its product promises revealed **12 high-priority edge cases** that could undermine user trust. This RFC proposes fixes organized into 3 phases, prioritizing issues that affect data integrity, security, and the "it just works" promise.

**Key Findings**:
- Link validation is a no-op (promises validation but doesn't deliver)
- Graph analysis commands are broken (0 links detected)
- Include directives have no file size limits (OOM risk)
- Concurrent builds can corrupt cache (no locking)
- Template cycles produce cryptic errors (no detection)

---

## Motivation

Bengal's marketing promises:
1. "Incremental builds with dependency tracking (18-42x faster!)"
2. "Link validation" and "Build quality checks"
3. "Parallel processing with ThreadPoolExecutor"
4. "Health validation system with incremental checks"

Users who rely on these features and encounter edge cases will lose trust. Fixing these before wider adoption prevents reputation damage and support burden.

---

## Proposed Changes

### Phase 1: Security & Data Integrity (P0 - Before Release)

#### 1.1 Implement Actual Link Validation

**Problem**: `_is_valid_link()` always returns `True` for internal links.

**Location**: `bengal/rendering/link_validator.py:119-129`

**Solution**:

```python
def _is_valid_link(self, link: str, page: Page) -> bool:
    """Validate internal link resolves to an existing page."""
    from urllib.parse import urlparse, urljoin

    parsed = urlparse(link)

    # External links validated separately
    if parsed.scheme in ('http', 'https', 'mailto'):
        return True  # External validation is async elsewhere

    # Fragment-only links are valid
    path = parsed.path
    if not path:
        return True

    # Resolve relative to page URL
    base_url = page.url.rstrip('/') + '/'
    resolved = urljoin(base_url, path)

    # Normalize trailing slashes
    resolved_variants = [resolved, resolved.rstrip('/'), resolved.rstrip('/') + '/']

    # Check against site pages
    page_urls = {p.url for p in self._site.pages}
    page_urls.update({p.url.rstrip('/') for p in self._site.pages})
    page_urls.update({p.url.rstrip('/') + '/' for p in self._site.pages})

    return any(v in page_urls for v in resolved_variants)
```

**Tests Required**:
- `test_internal_link_validation_existing_page`
- `test_internal_link_validation_missing_page`
- `test_internal_link_validation_with_fragments`
- `test_internal_link_validation_relative_paths`

**Effort**: 4 hours

---

#### 1.2 Add Include Directive File Size Limits

**Problem**: Include directives can read arbitrary file sizes, causing OOM.

**Location**: `bengal/rendering/plugins/directives/include.py`

**Solution**:

```python
MAX_INCLUDE_SIZE = 10 * 1024 * 1024  # 10 MB

def _load_file(self, file_path: Path, state: BlockState) -> str | None:
    """Load file with size limit check."""
    try:
        file_size = file_path.stat().st_size
        if file_size > MAX_INCLUDE_SIZE:
            logger.warning(
                "include_file_too_large",
                path=str(file_path),
                size_bytes=file_size,
                limit_bytes=MAX_INCLUDE_SIZE,
            )
            return f"[File too large: {file_size:,} bytes exceeds {MAX_INCLUDE_SIZE:,} limit]"

        # Existing file reading logic...
```

**Also applies to**: `bengal/rendering/plugins/directives/literalinclude.py`

**Tests Required**:
- `test_include_rejects_large_files`
- `test_literalinclude_rejects_large_files`
- `test_include_size_limit_configurable` (optional)

**Effort**: 2 hours

---

#### 1.3 Harden Symlink Handling

**Problem**: Symlinks inside site root can escape path containment.

**Location**: `bengal/rendering/plugins/directives/include.py:181-188`

**Solution**:

```python
def _resolve_path(self, path: str, state: BlockState) -> Path | None:
    """Resolve include path with symlink safety."""
    # ... existing path construction ...

    # Check for symlinks BEFORE resolving
    if file_path.is_symlink():
        logger.warning(
            "include_symlink_rejected",
            path=str(file_path),
            reason="symlinks_not_allowed",
        )
        return None

    # Then verify resolved path is within site root
    try:
        resolved = file_path.resolve(strict=True)
        root_resolved = root_path.resolve()
        resolved.relative_to(root_resolved)
    except (ValueError, FileNotFoundError):
        logger.warning(
            "include_outside_site_root",
            path=str(file_path),
        )
        return None

    return resolved
```

**Also add to**: `bengal/discovery/content_discovery.py` for directory traversal

**Tests Required**:
- `test_include_rejects_symlinks`
- `test_discovery_rejects_symlink_loops`
- `test_include_rejects_symlink_escape`

**Effort**: 3 hours

---

### Phase 2: Feature Correctness (P1 - Soon After Release)

#### 2.1 Fix Graph Analysis Link Extraction

**Problem**: `page.links` is empty when knowledge graph builds (extraction happens during rendering, after graph construction).

**Location**: `bengal/analysis/knowledge_graph.py`, `bengal/cli/commands/graph/__main__.py`

**Solution Options**:

**Option A: Early Link Extraction (Recommended)**
Extract links during discovery, before graph construction:

```python
# In ContentDiscovery._create_page()
def _create_page(self, file_path: Path, ...) -> Page:
    page = Page(source_path=file_path, ...)

    # Extract links early (lightweight regex, not full parse)
    page.links = self._extract_links_early(page.content)

    return page

def _extract_links_early(self, content: str) -> list[str]:
    """Fast link extraction for graph analysis."""
    import re
    # Match markdown links [text](url) and wiki-style [[link]]
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    wiki_links = re.findall(r'\[\[([^\]]+)\]\]', content)
    return [url for _, url in md_links] + wiki_links
```

**Option B: Trigger Rendering Before Graph**
Build graph after a quick parse pass:

```python
# In graph/__main__.py
def _build_graph(site):
    # Parse all pages to extract links
    pipeline = RenderingPipeline(site)
    for page in site.pages:
        pipeline._extract_links(page)  # New method for link-only extraction

    # Now build graph with populated links
    return KnowledgeGraph.build(site)
```

**Recommendation**: Option A - avoids full rendering, faster for large sites.

**Tests Required**:
- `test_graph_analyze_detects_links`
- `test_graph_pagerank_with_links`
- `test_early_link_extraction_markdown`
- `test_early_link_extraction_wikilinks`

**Effort**: 6 hours

---

#### 2.2 Add Concurrent Build Safety

**Problem**: No file locking; multiple builds can corrupt cache.

**Location**: `bengal/cache/build_cache.py`

**Solution**:

```python
import fcntl
from contextlib import contextmanager

class BuildCache:
    LOCK_TIMEOUT = 30  # seconds

    @contextmanager
    def _file_lock(self, cache_path: Path, exclusive: bool = True):
        """Acquire file lock for cache operations."""
        lock_path = cache_path.with_suffix('.lock')
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock_file = open(lock_path, 'w')
        try:
            lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(lock_file.fileno(), lock_type | fcntl.LOCK_NB)
            yield
        except BlockingIOError:
            logger.warning(
                "cache_lock_contention",
                cache_path=str(cache_path),
                action="waiting_for_lock",
            )
            fcntl.flock(lock_file.fileno(), lock_type)  # Blocking wait
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

    def save(self, cache_path: Path) -> None:
        with self._file_lock(cache_path, exclusive=True):
            # Existing save logic...

    @classmethod
    def load(cls, cache_path: Path) -> BuildCache:
        with cls()._file_lock(cache_path, exclusive=False):
            # Existing load logic...
```

**Also add**: SIGINT/SIGTERM handling in `BuildOrchestrator`

**Tests Required**:
- `test_concurrent_cache_save`
- `test_cache_lock_contention`
- `test_build_interrupted_gracefully`

**Effort**: 4 hours

---

#### 2.3 Add Template Cycle Detection

**Problem**: Circular template includes cause Python stack overflow.

**Location**: `bengal/rendering/template_engine.py`

**Solution**:

```python
class CycleDetectingLoader(FileSystemLoader):
    """Custom loader that detects template include cycles."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._include_stack = threading.local()

    def get_source(self, environment, template):
        # Get or create thread-local stack
        if not hasattr(self._include_stack, 'templates'):
            self._include_stack.templates = []

        stack = self._include_stack.templates

        # Check for cycle
        if template in stack:
            cycle = ' → '.join(stack + [template])
            raise TemplateSyntaxError(
                f"Template cycle detected: {cycle}",
                lineno=1,
            )

        stack.append(template)
        try:
            return super().get_source(environment, template)
        finally:
            stack.pop()
```

**Tests Required**:
- `test_template_cycle_direct`
- `test_template_cycle_indirect`
- `test_template_cycle_error_message`

**Effort**: 3 hours

---

#### 2.4 Prevent Content Discovery Symlink Loops

**Problem**: Directory symlink loops cause infinite recursion.

**Location**: `bengal/discovery/content_discovery.py`

**Solution**:

```python
def _discover_full(self) -> tuple[list[Section], list[Page]]:
    """Full discovery with symlink loop protection."""
    visited_inodes: set[tuple[int, int]] = set()  # (device, inode) pairs

    def walk_safe(directory: Path):
        """Walk directory tree, skipping symlink loops."""
        try:
            stat = directory.stat()
            inode_key = (stat.st_dev, stat.st_ino)

            if inode_key in visited_inodes:
                logger.warning(
                    "symlink_loop_detected",
                    path=str(directory),
                    action="skipping",
                )
                return

            visited_inodes.add(inode_key)

            for entry in os.scandir(directory):
                if entry.is_dir(follow_symlinks=True):
                    yield from walk_safe(Path(entry.path))
                elif entry.is_file():
                    yield Path(entry.path)

        except PermissionError:
            logger.warning("permission_denied", path=str(directory))

    # Use walk_safe instead of rglob
    for file_path in walk_safe(self.content_dir):
        # Existing file processing...
```

**Tests Required**:
- `test_discovery_handles_symlink_loop`
- `test_discovery_handles_permission_denied`

**Effort**: 3 hours

---

### Phase 3: Developer Experience (P2 - Quality Improvements)

#### 3.1 i18n Missing Translation Warnings

**Problem**: Missing translations silently return the key.

**Location**: `bengal/rendering/template_functions/i18n.py:171-173`

**Solution**:

```python
def t(key: str, params: dict[str, Any] | None = None, lang: str | None = None) -> str:
    # ... existing resolution logic ...

    if value is None:
        # Log missing translation (once per key per build)
        if not hasattr(t, '_warned_keys'):
            t._warned_keys = set()

        warn_key = f"{use_lang}:{key}"
        if warn_key not in t._warned_keys:
            t._warned_keys.add(warn_key)
            logger.debug(
                "translation_missing",
                key=key,
                lang=use_lang,
                fallback="key_returned",
            )

        # Still return key for visibility
        value = key

    return format_params(value, params or {})
```

**Add**: `bengal validate --i18n` flag to report all missing translations

**Effort**: 2 hours

---

#### 3.2 Theme Not Found Explicit Warning

**Problem**: Missing theme silently degrades to default.

**Location**: `bengal/rendering/template_engine.py`

**Solution**:

```python
def _create_environment(self) -> Environment:
    # ... existing theme resolution ...

    if not theme_found:
        # Explicit, visible warning
        click.secho(
            f"⚠️  Theme '{theme_name}' not found. Using default theme.",
            fg="yellow",
            err=True,
        )
        logger.warning(
            "theme_not_found",
            theme=theme_name,
            searched_paths=[
                str(self.site.root_path / "themes" / theme_name),
                f"bengal-theme-{theme_name} (pip)",
                str(Path(__file__).parent.parent / "themes" / theme_name),
            ],
            action="using_default",
        )
```

**Effort**: 1 hour

---

#### 3.3 Empty RSS/Sitemap Handling

**Problem**: Sites with no pages may produce invalid XML.

**Location**: `bengal/postprocess/sitemap.py`, `bengal/postprocess/rss.py`

**Solution**:

```python
def generate_sitemap(self) -> str | None:
    """Generate sitemap, or None if no pages."""
    pages = [p for p in self.site.pages if not p.draft]

    if not pages:
        logger.info(
            "sitemap_skipped",
            reason="no_published_pages",
        )
        return None

    # Existing generation logic...
```

**Tests Required**:
- `test_sitemap_empty_site`
- `test_rss_empty_site`

**Effort**: 1 hour

---

## Implementation Plan

### Phase 1: Security & Data Integrity (Week 1) ✅ COMPLETE

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| 1.1 Link validation | 4h | AI | ✅ |
| 1.2 Include size limits | 2h | AI | ✅ |
| 1.3 Symlink hardening | 3h | AI | ✅ |
| **Phase 1 Total** | **9h** | | **DONE** |

**Commit**: `e98a19e` - core(security): implement Phase 1 edge case hardening

### Phase 2: Feature Correctness (Week 2-3) ✅ COMPLETE

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| 2.1 Graph analysis links | 6h | AI | ✅ (already fixed) |
| 2.2 Concurrent build safety | 4h | AI | ✅ |
| 2.3 Template cycle detection | 3h | AI | ✅ (Jinja2 native) |
| 2.4 Discovery symlink loops | 3h | AI | ✅ (done in P1) |
| **Phase 2 Total** | **16h** | | **DONE** |

**Notes**:
- 2.1: Already implemented via `_ensure_links_extracted()` in `KnowledgeGraph`
- 2.2: Added `file_lock` utility and integrated with `BuildCache.save()/load()`
- 2.3: Jinja2 natively handles template cycles; rich error formatting already exists
- 2.4: Inode-based loop detection added in Phase 1

### Phase 3: Developer Experience (Week 4) ✅ COMPLETE

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| 3.1 i18n warnings | 2h | AI | ✅ |
| 3.2 Theme warnings | 1h | AI | ✅ |
| 3.3 Empty feed handling | 1h | AI | ✅ |
| **Phase 3 Total** | **4h** | | **DONE** |

**Notes**:
- 3.1: Added `_warn_missing_translation()` with once-per-key-per-build tracking
- 3.2: Added visible stderr warning when theme not found (in addition to log)
- 3.3: Sitemap and RSS generators now skip gracefully when no content to include

**Grand Total**: ~29 hours of development — **ALL PHASES COMPLETE** ✅

---

## Testing Strategy

### New Test Categories

1. **Edge Case Unit Tests** (~50 tests)
   - Link validation scenarios
   - Include directive limits
   - Symlink handling
   - Template cycles

2. **Integration Tests** (~15 tests)
   - Concurrent build simulation
   - Graph analysis with real content
   - Full build with edge case content

3. **Property Tests** (~10 tests)
   - Link extraction with random content
   - File size limits with various sizes
   - Unicode handling in translations

### Test Infrastructure Additions

```python
# tests/_testing/edge_cases.py

@pytest.fixture
def symlink_content(tmp_path):
    """Create content directory with symlinks for testing."""
    # Create normal content
    content = tmp_path / "content"
    content.mkdir()
    (content / "page.md").write_text("# Test")

    # Create symlink loop
    (content / "loop").symlink_to(content)

    return content

@pytest.fixture
def large_file(tmp_path):
    """Create a file larger than MAX_INCLUDE_SIZE."""
    large = tmp_path / "large.txt"
    large.write_bytes(b"x" * (11 * 1024 * 1024))  # 11 MB
    return large
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Link validation slows builds | Medium | Medium | Cache validation results; only validate changed pages |
| File locking doesn't work on NFS | Low | High | Document limitation; suggest local cache directory |
| Symlink rejection breaks legitimate use cases | Low | Medium | Add config flag to allow symlinks |
| Early link extraction misses dynamic links | Medium | Low | Document limitation; full extraction available via graph --render |

---

## Success Criteria

1. **No false promises**: Every feature in README actually works as described
2. **Graceful degradation**: Edge cases produce helpful errors, not crashes
3. **Test coverage**: All edge cases have automated tests
4. **Documentation**: Edge case behavior documented in user docs

---

## Alternatives Considered

### Do Nothing
- **Pros**: No development effort
- **Cons**: Users discover bugs in production; support burden; reputation damage
- **Verdict**: Rejected

### Document Limitations Only
- **Pros**: Quick; sets expectations
- **Cons**: Doesn't solve the problem; looks like admitting defeat
- **Verdict**: Rejected for P0 issues; acceptable for P3

### Full Rewrite of Affected Systems
- **Pros**: Clean architecture
- **Cons**: Massive scope; delays release
- **Verdict**: Rejected; targeted fixes are sufficient

---

## Open Questions

1. **Should symlink handling be configurable?** Some users may have legitimate symlink use cases (shared content across sites).

2. **What's the right file size limit for includes?** 10MB is arbitrary; should it be configurable?

3. **Should graph analysis use full rendering or early extraction?** Trade-off between accuracy and performance.

4. **How should we handle Windows compatibility for file locking?** `fcntl` is Unix-only.

---

## References

- `plan/active/security-audit-findings.md` - Security issues identified
- `plan/implemented/rfc-test-gaps-and-resilience.md` - Test coverage gaps
- `plan/active/graph-analysis-investigation.md` - Graph analysis bug investigation
- `plan/implemented/plan-stable-section-references.md` - Cache-proxy contract issues

---

## Appendix: Edge Cases by Category

### A. Security (3 issues)
- Include file size limits
- Symlink path traversal
- Variable substitution sandboxing

### B. Data Integrity (4 issues)
- Link validation no-op
- Concurrent build corruption
- Cache-proxy field drift
- Template cycle stack overflow

### C. Feature Correctness (3 issues)
- Graph analysis 0 links
- Discovery symlink loops
- Cascade config ordering

### D. Developer Experience (5 issues)
- i18n missing translation silence
- Theme not found silence
- Empty feed handling
- GIL messaging
- Environment detection conflicts

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-26  
**Status**: Ready for Review
