# RFC: Content Layer Algorithm Optimization

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Content Layer (ContentLayerManager, ContentSource, LocalSource, GitHubSource, RESTSource, NotionSource)  
**Priority**: P2 (Medium) — Performance, scalability for remote content sources  
**Estimated Effort**: 1-2 days  
**Verified**: All code locations verified against source (2025-12-24)

---

## Executive Summary

The `bengal/content_layer` package provides a unified content abstraction for fetching content from local files, GitHub, REST APIs, and Notion databases. Analysis identified **5 algorithmic patterns** requiring attention:

**Key findings**:

1. **LocalSource.fetch_all()** — O(n log n) sort on glob results
2. **LocalSource._should_exclude()** — O(p) fnmatch per file (p = patterns)
3. **GitHubSource.fetch_all()** — O(n) sequential API calls for n files
4. **NotionSource** — O(n × b) API calls (n = pages, b = blocks per page)
5. **ContentSource.get_cache_key()** — O(c log c) sorted config items

**Proposed optimizations**:

1. **Phase 1 (Quick Wins)**: Remove unnecessary sort, pre-compile exclude patterns → 10-20% speedup
2. **Phase 2 (GitHub)**: Batch file fetching using Git blob API → O(⌈n/100⌉) API calls
3. **Phase 3 (Notion)**: Parallel block fetching + block caching → 50-70% speedup
4. **Phase 4 (Caching)**: Cache key memoization → O(1) repeated lookups

**Current state**: The implementation is well-designed with zero-cost-unless-used philosophy. Local-only sites have negligible overhead. Remote sources have network-bound latency that can be reduced.

**Impact**: 2-5x speedup for GitHub/Notion sources; local sources remain fast

---

## Problem Statement

### Current Performance Characteristics

> ⚠️ **Performance projections are theoretical estimates.** Actual measurements required before optimization (see Step 0).

| Scenario | LocalSource | GitHubSource | NotionSource | Total (Remote) |
|----------|-------------|--------------|--------------|----------------|
| 50 files, 0 exclude patterns | <100ms | ~2-5s | ~5-10s | ~5-10s |
| 500 files, 5 exclude patterns | ~200ms | ~20-50s ⚠️ | ~50-100s ⚠️ | ~60-120s ⚠️ |
| 2K files, 10 exclude patterns | ~500ms | **~80-200s** 🔴 | **~200-400s** 🔴 | **4-7 min** 🔴 |

The network-bound sources (GitHub, Notion) are the primary bottleneck. Local sources are already fast but have minor inefficiencies.

### Bottleneck 1: LocalSource.fetch_all() — O(n log n) Sort

**Location**: `sources/local.py:117`

```python
for path in sorted(self.directory.glob(self.glob_pattern)):  # O(n log n)
    if not path.is_file():
        continue
    ...
```

**Problem**: Sorting all glob results before yielding. For 2K files, this is ~22K comparisons before returning any results.

**Impact**: Low — Sorting 2K paths takes ~5ms. But it blocks streaming.

**Optimal approach**: Remove sort (order typically doesn't matter) or use `heapq.nsmallest` for streaming.

### Bottleneck 2: LocalSource._should_exclude() — O(p) per file

**Location**: `sources/local.py:191-206`

```python
def _should_exclude(self, path: Path) -> bool:
    if not self.exclude_patterns:
        return False
    rel_path = str(path.relative_to(self.directory))
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in self.exclude_patterns)
```

**Problem**: Each file tests against ALL exclude patterns. With 10 patterns and 2K files, that's 20K fnmatch calls.

**Optimal approach**: Pre-compile patterns to regex on init, test with single combined regex.

### Bottleneck 3: GitHubSource.fetch_all() — O(n) Sequential API Calls

**Location**: `sources/github.py:116-133`

```python
# Get entire tree in one call: O(1) API call ✅
tree_url = f"{self.api_base}/repos/{self.repo}/git/trees/{self.branch}?recursive=1"
...
# But then fetch each file individually: O(n) API calls ⚠️
for item in data.get("tree", []):
    ...
    entry = await self._fetch_file(session, file_path, item["sha"])  # 1 API call per file!
```

**Problem**: After getting the tree in a single call, we fetch each file's content with a separate API call. For 500 files, that's 500 sequential HTTPS round-trips (~100-200ms each = 50-100 seconds).

**Optimal approach**: Use GitHub's Git Blob API with batch requests, or fetch raw content in parallel with concurrency limit.

### Bottleneck 4: NotionSource — O(n × ⌈b/100⌉) API Calls

**Location**: `sources/notion.py:108-147` and `sources/notion.py:213-250`

```python
# For each page in database...
for page in data.get("results", []):
    entry = await self._page_to_entry(session, page)  # Fetches blocks!
    ...

async def _get_page_content(self, session, page_id) -> str:
    # Paginated block fetch: O(⌈b/100⌉) API calls PER PAGE
    while has_more:
        async with session.get(url, params=params) as resp:
            ...
        blocks.extend(data.get("results", []))
        has_more = data.get("has_more", False)
```

**Problem**: Each Notion page requires:
1. Database query (paginated, 100 pages/request)
2. Per-page block fetch (paginated, 100 blocks/request)
3. Block-to-markdown conversion

For 100 pages with 50 blocks each: 1 + 100 = 101 API calls minimum.

**Optimal approach**: Parallel block fetching with `asyncio.gather()`, block content caching.

### Bottleneck 5: ContentSource.get_cache_key() — O(c log c)

**Location**: `source.py:96-108`

```python
def get_cache_key(self) -> str:
    config_str = f"{self.source_type}:{self.name}:{sorted(self.config.items())}"  # O(c log c)
    return hash_str(config_str, truncate=16)
```

**Problem**: Sorts config items on every call. Called multiple times during cache validation.

**Optimal approach**: Compute and cache the key on first access.

---

## Current Complexity Analysis

### What's Already Optimal ✅

| Component | Operation | Complexity | Notes |
|-----------|-----------|------------|-------|
| ContentEntry | All methods | **O(1)** or O(k) ✅ | k = frontmatter keys |
| ContentLayerManager | `register_source()` | **O(1)** ✅ | Dict insertion |
| ContentLayerManager | `fetch_all()` | O(s) parallel ✅ | Uses `asyncio.gather` |
| LocalSource | `_load_file()` | O(f) ✅ | f = file size, unavoidable |
| RESTSource | `_get_nested()` | O(d) ✅ | d = path depth |
| All sources | `fetch_one()` | O(1) network ✅ | Single item lookup |

### What Could Be Optimized ⚠️

| Component | Operation | Current | Optimal | Impact |
|-----------|-----------|---------|---------|--------|
| LocalSource | `fetch_all()` sort | O(n log n) | O(n) | Low |
| LocalSource | `_should_exclude()` | O(n × p) | O(n) | Low-Medium |
| GitHubSource | `fetch_all()` file fetch | O(n) API calls | O(⌈n/100⌉) batch | **High** |
| NotionSource | `fetch_all()` blocks | O(n × ⌈b/100⌉) API | O(n) parallel | **High** |
| ContentSource | `get_cache_key()` | O(c log c) | O(1) cached | Low |
| Manager | `_load_cache()` | O(n) deserialize | O(n) | N/A (unavoidable) |

**Variables**: n=files/pages, p=patterns, c=config items, b=blocks/page, f=file size, d=nesting depth

---

## Goals

1. **Reduce GitHub source latency** by 80%+ via batch/parallel fetching — **Phase 2**
2. **Reduce Notion source latency** by 50%+ via parallel block fetching — **Phase 3**
3. **Eliminate O(n log n) sort** in LocalSource — **Phase 1**
4. **Pre-compile exclude patterns** for O(1) matching — **Phase 1**
5. **Memoize cache keys** for repeated lookups — **Phase 4**
6. **Maintain API compatibility** — No breaking changes
7. **Preserve correctness** — Identical content output

### Non-Goals

- Caching across process restarts (separate RFC)
- Incremental/delta fetching (separate RFC)
- WebSocket-based real-time updates
- User-configurable retry policies (basic exponential backoff is in-scope)

---

## Proposed Solution

### Phase 1: Quick Wins (LocalSource) — LOW EFFORT

**Estimated effort**: 2 hours  
**Impact**: 10-20% speedup for local sources with exclude patterns  
**Priority**: Low — Local sources already fast

#### 1.1 Remove Unnecessary Sort

```python
# sources/local.py - Before
for path in sorted(self.directory.glob(self.glob_pattern)):
    ...

# After: Remove sort (or make optional via config)
for path in self.directory.glob(self.glob_pattern):
    ...
```

**Trade-off**: Entries may be yielded in filesystem-dependent order.

**Behavior change**: Code that depends on alphabetical ordering will break. Mitigations:
1. Add `sort: bool = False` config option (default False for performance)
2. Document the change in CHANGELOG
3. Update tests to use set comparison instead of list equality

#### 1.2 Pre-compile Exclude Patterns

```python
# sources/local.py - Enhanced exclusion

import re
from functools import cached_property

class LocalSource(ContentSource):
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self.directory = Path(config["directory"])
        self.glob_pattern = config.get("glob", "**/*.md")
        self._exclude_patterns: list[str] = config.get("exclude", [])

    @cached_property
    def _exclude_regex(self) -> re.Pattern[str] | None:
        """Pre-compile exclude patterns to single regex. O(p) once, O(1) per match."""
        if not self._exclude_patterns:
            return None
        # Convert fnmatch patterns to regex and combine
        regex_parts = [fnmatch.translate(p) for p in self._exclude_patterns]
        combined = "|".join(f"(?:{p})" for p in regex_parts)
        return re.compile(combined)

    def _should_exclude(self, path: Path) -> bool:
        """Check exclusion with pre-compiled regex. O(1) per file."""
        if self._exclude_regex is None:
            return False
        rel_path = str(path.relative_to(self.directory))
        # fullmatch() ensures entire path matches (fnmatch.translate adds \Z anchor)
        return bool(self._exclude_regex.fullmatch(rel_path))
```

**Complexity change**: O(n × p) → O(n)

**Fallback**: If regex compilation fails on edge-case patterns, fall back to original fnmatch loop:

```python
@cached_property
def _exclude_regex(self) -> re.Pattern[str] | None:
    if not self._exclude_patterns:
        return None
    try:
        regex_parts = [fnmatch.translate(p) for p in self._exclude_patterns]
        combined = "|".join(f"(?:{p})" for p in regex_parts)
        return re.compile(combined)
    except re.error as e:
        logger.warning(f"Failed to compile exclude patterns: {e}. Using fnmatch fallback.")
        return None  # _should_exclude will use fnmatch loop
```

---

### Phase 2: GitHub Batch Fetching — MEDIUM EFFORT

**Estimated effort**: 4 hours  
**Impact**: 80%+ speedup for GitHub sources  
**Priority**: High — Major bottleneck for remote content

#### 2.1 Parallel File Fetching with Concurrency Limit

```python
# sources/github.py - Parallel fetching with semaphore

import asyncio
from typing import Any

class GitHubSource(ContentSource):
    MAX_CONCURRENT_REQUESTS = 10  # GitHub rate limit friendly
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 1.0  # seconds

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """Fetch all files with parallel requests."""
        async with aiohttp.ClientSession(headers=self._headers) as session:
            # Get tree in one call (existing)
            tree_url = f"{self.api_base}/repos/{self.repo}/git/trees/{self.branch}?recursive=1"
            async with session.get(tree_url) as resp:
                resp.raise_for_status()
                data = await resp.json()

            # Filter to matching files
            matching_files = [
                item for item in data.get("tree", [])
                if item["type"] == "blob"
                and item["path"].endswith(".md")
                and (not self.path or item["path"].startswith(self.path + "/"))
            ]

            # Fetch files in parallel with concurrency limit
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)

            async def fetch_with_retry(item: dict[str, Any]) -> ContentEntry | None:
                """Fetch file with exponential backoff on rate limit."""
                async with semaphore:
                    for attempt in range(self.MAX_RETRIES):
                        try:
                            return await self._fetch_file(session, item["path"], item["sha"])
                        except aiohttp.ClientResponseError as e:
                            if e.status == 429 and attempt < self.MAX_RETRIES - 1:
                                # Rate limited: exponential backoff
                                delay = self.RETRY_BACKOFF_BASE * (2 ** attempt)
                                logger.warning(f"Rate limited, retrying in {delay}s: {item['path']}")
                                await asyncio.sleep(delay)
                                continue
                            elif e.status == 403 and attempt < self.MAX_RETRIES - 1:
                                # May be secondary rate limit
                                delay = self.RETRY_BACKOFF_BASE * (2 ** attempt)
                                await asyncio.sleep(delay)
                                continue
                            raise
                    return None  # All retries exhausted

            tasks = [fetch_with_retry(item) for item in matching_files]

            # Track failed files for error reporting
            failed_count = 0

            # Stream results as they complete (order not guaranteed)
            for coro in asyncio.as_completed(tasks):
                try:
                    entry = await coro
                    if entry:
                        yield entry
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to fetch file: {e}")

            if failed_count > 0:
                logger.warning(f"Failed to fetch {failed_count}/{len(matching_files)} files")
```

**Complexity change**: O(n) sequential → O(n/10) with 10 concurrent requests

**Behavior changes**:
- Results are yielded in completion order, not alphabetical order
- Individual file failures don't abort the entire fetch
- Rate limit responses trigger exponential backoff

#### 2.2 Alternative: Use Raw Content URLs (Public Repos)

```python
# For public repos, use raw.githubusercontent.com (no API rate limit)
async def _fetch_file_raw(self, session: aiohttp.ClientSession, path: str) -> ContentEntry | None:
    """Fetch via raw content URL (no API rate limit)."""
    url = f"https://raw.githubusercontent.com/{self.repo}/{self.branch}/{path}"
    async with session.get(url) as resp:
        if resp.status == 404:
            return None
        content = await resp.text()
        # ... parse frontmatter, create entry ...
```

**Trade-off**: Works for public repos only. Private repos need API with token.

---

### Phase 3: Notion Parallel Block Fetching — MEDIUM EFFORT

**Estimated effort**: 4 hours  
**Impact**: 50-70% speedup for Notion sources  
**Priority**: High — Most expensive source

#### 3.1 Parallel Page Processing

```python
# sources/notion.py - Parallel page processing

class NotionSource(ContentSource):
    MAX_CONCURRENT_PAGES = 5  # Notion API rate limit friendly

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """Fetch all pages with parallel block fetching."""
        async with aiohttp.ClientSession(headers=self._headers) as session:
            url = f"{self.api_base}/databases/{self.database_id}/query"

            # Collect all pages first (paginated)
            all_pages: list[dict[str, Any]] = []
            has_more = True
            start_cursor: str | None = None

            while has_more:
                body: dict[str, Any] = {}
                if start_cursor:
                    body["start_cursor"] = start_cursor
                if self.filter:
                    body["filter"] = self.filter
                if self.sorts:
                    body["sorts"] = self.sorts

                async with session.post(url, json=body) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                all_pages.extend(data.get("results", []))
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

            # Process pages in parallel with concurrency limit
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_PAGES)

            async def process_with_limit(page: dict[str, Any]) -> ContentEntry | None:
                async with semaphore:
                    return await self._page_to_entry(session, page)

            tasks = [process_with_limit(page) for page in all_pages]

            for coro in asyncio.as_completed(tasks):
                entry = await coro
                if entry:
                    yield entry
```

**Complexity change**: O(n) sequential → O(n/5) with 5 concurrent pages

#### 3.2 Block Content Caching (Bounded)

```python
# sources/notion.py - Block-level caching with TTL and size limit

from typing import Any

try:
    from cachetools import TTLCache
except ImportError:
    TTLCache = None  # Fallback to no caching

class NotionSource(ContentSource):
    BLOCK_CACHE_TTL = 300  # seconds
    BLOCK_CACHE_MAXSIZE = 500  # pages

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        # ... existing init ...

        # Instance-level cache (not class-level!) with TTL and size limit
        if TTLCache is not None:
            self._block_cache: TTLCache[str, str] = TTLCache(
                maxsize=self.BLOCK_CACHE_MAXSIZE,
                ttl=self.BLOCK_CACHE_TTL,
            )
        else:
            self._block_cache = None  # No caching if cachetools unavailable

    async def _get_page_content(
        self,
        session: aiohttp.ClientSession,
        page_id: str,
    ) -> str:
        """Fetch blocks with bounded caching."""
        # Check cache (TTLCache handles expiration automatically)
        if self._block_cache is not None and page_id in self._block_cache:
            logger.debug(f"Cache hit for page {page_id}")
            return self._block_cache[page_id]

        # Fetch blocks (existing logic)
        content = await self._fetch_blocks(session, page_id)

        # Cache result (TTLCache handles eviction automatically)
        if self._block_cache is not None:
            self._block_cache[page_id] = content

        return content
```

**Key improvements over original**:
1. **Instance-level cache** — Not shared across NotionSource instances (was class-level, causing cross-contamination)
2. **Bounded size** — LRU eviction when cache exceeds 500 pages (~5MB typical)
3. **TTL with automatic expiration** — No manual age checking
4. **Graceful degradation** — Works without cachetools (just no caching)

**Dependency**: Add `cachetools>=5.0` as optional dependency (`pip install bengal[notion]`)

**Trade-off**: In-memory cache only; cleared on source recreation. Could extend to disk cache for dev server.

---

### Phase 4: Cache Key Memoization — LOW EFFORT

**Estimated effort**: 30 minutes  
**Impact**: O(c log c) → O(1) for repeated cache key lookups  
**Priority**: Low — Minor improvement

```python
# source.py - Memoized cache key

from functools import cached_property

class ContentSource(ABC):
    @cached_property
    def cache_key(self) -> str:
        """
        Generate cache key for this source configuration.
        Computed once, cached for lifetime of source instance.
        """
        config_str = f"{self.source_type}:{self.name}:{sorted(self.config.items())}"
        return hash_str(config_str, truncate=16)

    def get_cache_key(self) -> str:
        """Get cache key (memoized). O(1) after first call."""
        return self.cache_key
```

**Alternative**: Keep method-based API but cache internally:

```python
def get_cache_key(self) -> str:
    if not hasattr(self, "_cache_key"):
        config_str = f"{self.source_type}:{self.name}:{sorted(self.config.items())}"
        self._cache_key = hash_str(config_str, truncate=16)
    return self._cache_key
```

---

## Implementation Plan

### Step 0: Establish Baseline Benchmarks (REQUIRED FIRST)

**Files**: `benchmarks/test_content_layer_performance.py` (new)

1. Create synthetic content files (50, 200, 1K, 5K files)
2. Mock GitHub/Notion API responses
3. Measure wall-clock time for:
   - LocalSource.fetch_all() with varying exclude patterns
   - GitHubSource.fetch_all() with varying file counts
   - NotionSource.fetch_all() with varying page/block counts
   - ContentLayerManager.fetch_all() with multiple sources
4. Record baseline metrics in `benchmarks/baseline_content_layer.json`

```python
# Example benchmark structure
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

@pytest.mark.benchmark(group="local-source")
def test_local_source_2k_files_10_patterns(benchmark, tmp_path):
    """Baseline: LocalSource with 2K files and 10 exclude patterns."""
    # Create 2K test files
    for i in range(2000):
        (tmp_path / f"file_{i}.md").write_text(f"# File {i}\n\nContent")

    source = LocalSource("test", {
        "directory": str(tmp_path),
        "glob": "**/*.md",
        "exclude": [f"**/pattern_{j}*" for j in range(10)],
    })

    async def fetch():
        return [e async for e in source.fetch_all()]

    result = benchmark(lambda: asyncio.run(fetch()))
    assert len(result) == 2000


@pytest.mark.benchmark(group="github-source")
def test_github_source_500_files(benchmark, mock_github_api):
    """Baseline: GitHubSource with 500 files."""
    source = GitHubSource("test", {
        "repo": "test/repo",
        "branch": "main",
    })

    async def fetch():
        return [e async for e in source.fetch_all()]

    result = benchmark(lambda: asyncio.run(fetch()))
    assert len(result) == 500
```

### Step 1: Implement Phase 1 (Quick Wins)

**Files**: `bengal/content_layer/sources/local.py`

1. Remove `sorted()` from `fetch_all()` (or make optional)
2. Add `@cached_property` for compiled exclude regex
3. Update `_should_exclude()` to use compiled regex
4. Add tests for:
   - Exclusion with 0, 1, 10, 50 patterns
   - Pattern matching correctness
   - Empty directory handling
5. Run benchmarks to measure improvement

### Step 2: Implement Phase 2 (GitHub Parallel)

**Files**: `bengal/content_layer/sources/github.py`

1. Add `MAX_CONCURRENT_REQUESTS` class constant
2. Refactor `fetch_all()` to collect files first, then parallel fetch
3. Add semaphore-based concurrency limiting
4. Use `asyncio.as_completed()` for streaming results
5. Add tests for:
   - Parallel fetch correctness
   - Rate limit handling (mock)
   - Error handling for individual file failures
   - Empty repo handling
6. Run benchmarks to measure improvement

### Step 3: Implement Phase 3 (Notion Parallel)

**Files**: `bengal/content_layer/sources/notion.py`

1. Add `MAX_CONCURRENT_PAGES` class constant
2. Refactor `fetch_all()` to parallel page processing
3. Add block content caching with TTL
4. Add tests for:
   - Parallel page processing correctness
   - Block cache hit/miss behavior
   - Cache expiration
   - Error handling for individual page failures
5. Run benchmarks to measure improvement

### Step 4: Implement Phase 4 (Cache Key Memoization)

**Files**: `bengal/content_layer/source.py`

1. Add `@cached_property` decorator to `get_cache_key()`
2. Or use internal `_cache_key` attribute pattern
3. Add tests for cache key stability
4. Verify no behavior change

---

## Project Plan

### Timeline Overview

| Phase | Duration | Start | Depends On | Deliverables |
|-------|----------|-------|------------|--------------|
| **Step 0: Baseline** | 2 hours | Day 1 | — | Benchmark suite, baseline metrics |
| **Phase 1: Quick Wins** | 2 hours | Day 1 | Step 0 | Optimized LocalSource |
| **Phase 2: GitHub** | 4 hours | Day 1-2 | Step 0 | Parallel GitHubSource |
| **Phase 3: Notion** | 4 hours | Day 2 | Step 0 | Parallel NotionSource + caching |
| **Phase 4: Cache Keys** | 30 min | Day 2 | — | Memoized cache keys |
| **Validation** | 2 hours | Day 2 | All phases | Benchmark comparison, docs |

**Total estimated time**: 1-2 days

---

### Milestone 1: Baseline Benchmarks (Day 1, 2h)

**Goal**: Establish measurable performance baseline before any changes.

**Tasks**:
- [ ] Create `benchmarks/test_content_layer_performance.py`
- [ ] Generate synthetic test fixtures (50, 200, 1K, 5K files)
- [ ] Create mock GitHub API responses for 50, 200, 500 files
- [ ] Create mock Notion API responses for 20, 50, 100 pages
- [ ] Implement LocalSource benchmarks with varying exclude patterns
- [ ] Implement GitHubSource benchmarks (mocked)
- [ ] Implement NotionSource benchmarks (mocked)
- [ ] Record baseline in `benchmarks/baseline_content_layer.json`
- [ ] Verify benchmarks run in CI

**Acceptance criteria**:
- Benchmark suite runs in <5 minutes
- Baseline recorded for all 3 source types
- CI integration confirmed

---

### Milestone 2: LocalSource Optimization (Day 1, 2h)

**Goal**: Remove O(n log n) sort and O(n × p) pattern matching overhead.

**Tasks**:
- [ ] **2.1**: Remove `sorted()` from `fetch_all()` glob iteration
  - File: `bengal/content_layer/sources/local.py:117`
  - Add `sort: bool = False` config option for backward compatibility
- [ ] **2.2**: Add `@cached_property _exclude_regex`
  - Convert fnmatch patterns to combined regex
  - Add fallback for regex compilation failure
- [ ] **2.3**: Update `_should_exclude()` to use compiled regex
- [ ] **2.4**: Add unit tests
  - Test exclusion with 0, 1, 10, 50 patterns
  - Test pattern matching correctness (glob edge cases)
  - Test empty directory handling
  - Test `sort: true` config option
- [ ] **2.5**: Run benchmarks, document improvement

**Acceptance criteria**:
- LocalSource 2K files + 10 patterns: <200ms (baseline ~500ms)
- All existing tests pass
- New tests cover edge cases

**Dependencies**: Milestone 1 (baseline)

---

### Milestone 3: GitHubSource Parallel Fetching (Day 1-2, 4h)

**Goal**: Reduce GitHub API latency by 80%+ via concurrent file fetching.

**Tasks**:
- [ ] **3.1**: Add class constants
  - `MAX_CONCURRENT_REQUESTS = 10`
  - `MAX_RETRIES = 3`
  - `RETRY_BACKOFF_BASE = 1.0`
- [ ] **3.2**: Refactor `fetch_all()` to collect files first
  - Get tree in single API call (existing)
  - Filter matching files into list
- [ ] **3.3**: Implement parallel fetch with semaphore
  - Add `fetch_with_retry()` inner function
  - Handle 429 rate limit with exponential backoff
  - Handle 403 secondary rate limit
- [ ] **3.4**: Use `asyncio.as_completed()` for streaming results
- [ ] **3.5**: Add error tracking and summary logging
- [ ] **3.6**: Add unit tests
  - Test parallel fetch correctness (set comparison)
  - Test rate limit handling (mock 429 responses)
  - Test individual file failure handling
  - Test empty repo handling
  - Test semaphore limit is respected
- [ ] **3.7**: Run benchmarks, document improvement

**Acceptance criteria**:
- GitHubSource 500 files: <15s (baseline ~100s) with mocked API
- Rate limit (429) triggers backoff
- Individual failures don't abort fetch
- All existing tests pass

**Dependencies**: Milestone 1 (baseline)

---

### Milestone 4: NotionSource Parallel Fetching + Caching (Day 2, 4h)

**Goal**: Reduce Notion API latency by 50%+ via parallel pages and block caching.

**Tasks**:
- [ ] **4.1**: Add class constants
  - `MAX_CONCURRENT_PAGES = 5`
  - `BLOCK_CACHE_TTL = 300`
  - `BLOCK_CACHE_MAXSIZE = 500`
- [ ] **4.2**: Add optional `cachetools` dependency
  - Add to `pyproject.toml` extras: `notion = ["cachetools>=5.0"]`
  - Add graceful import fallback
- [ ] **4.3**: Add instance-level `_block_cache: TTLCache`
  - Initialize in `__init__`
  - Set to `None` if cachetools unavailable
- [ ] **4.4**: Refactor `fetch_all()` for parallel page processing
  - Collect all pages first (paginated query)
  - Process pages with semaphore-limited concurrency
  - Use `asyncio.as_completed()` for streaming
- [ ] **4.5**: Update `_get_page_content()` to use cache
  - Check cache before fetch
  - Store in cache after fetch
  - Log cache hits for debugging
- [ ] **4.6**: Add unit tests
  - Test parallel page processing correctness
  - Test cache hit/miss behavior
  - Test cache expiration (TTL)
  - Test graceful degradation without cachetools
  - Test individual page failure handling
- [ ] **4.7**: Run benchmarks, document improvement

**Acceptance criteria**:
- NotionSource 100 pages: <40s (baseline ~100s) with mocked API
- Block cache reduces repeated fetches
- Works without cachetools (no caching, no crash)
- All existing tests pass

**Dependencies**: Milestone 1 (baseline)

---

### Milestone 5: Cache Key Memoization (Day 2, 30min)

**Goal**: Eliminate repeated O(c log c) cache key computation.

**Tasks**:
- [ ] **5.1**: Add `@cached_property cache_key` to `ContentSource`
  - File: `bengal/content_layer/source.py`
- [ ] **5.2**: Update `get_cache_key()` to return cached property
- [ ] **5.3**: Add unit tests
  - Test cache key stability across calls
  - Test cache key uniqueness for different configs
- [ ] **5.4**: Verify no behavior change in existing tests

**Acceptance criteria**:
- `get_cache_key()` O(1) after first call
- All existing tests pass

**Dependencies**: None (can run in parallel with other milestones)

---

### Milestone 6: Validation & Documentation (Day 2, 2h)

**Goal**: Confirm improvements and document changes.

**Tasks**:
- [ ] **6.1**: Run full benchmark suite with optimizations
- [ ] **6.2**: Compare against baseline, document speedup
  - Update `benchmarks/baseline_content_layer.json` with "after" metrics
  - Create comparison table
- [ ] **6.3**: Verify all unit tests pass
- [ ] **6.4**: Verify integration tests pass
- [ ] **6.5**: Update CHANGELOG.md with behavior changes
- [ ] **6.6**: Update docstrings with new parameters
- [ ] **6.7**: Mark RFC status as "Implemented"

**Acceptance criteria**:
- Benchmark improvements documented
- CHANGELOG updated
- All tests green
- RFC status updated

**Dependencies**: Milestones 2, 3, 4, 5

---

### Parallel Execution Opportunities

```
Day 1:
  ├── Step 0: Baseline (2h) ─────────────────────┐
  │                                              │
  │   (after baseline complete)                  │
  │                                              ▼
  ├── Phase 1: LocalSource (2h) ───────┐   Phase 4: Cache Keys (30min)
  │                                    │         │
  ├── Phase 2: GitHub (4h) ────────────┤         │
  │                                    │         │
Day 2:                                 │         │
  ├── Phase 3: Notion (4h) ────────────┤         │
  │                                    │         │
  │                                    ▼         ▼
  └── Milestone 6: Validation ◄────────┴─────────┘
```

**Parallelizable**:
- Phases 1, 2, 3 can run in parallel after Step 0
- Phase 4 can run independently at any time

---

### Risk Checkpoints

| After | Check | Action if Failed |
|-------|-------|------------------|
| Step 0 | Benchmarks run, baseline recorded | Fix benchmark setup before proceeding |
| Phase 1 | LocalSource <200ms @ 2K files | Investigate regex compilation; may need different approach |
| Phase 2 | GitHubSource <15s @ 500 files (mocked) | Reduce concurrency; check for blocking I/O |
| Phase 3 | NotionSource <40s @ 100 pages (mocked) | Reduce concurrency; verify cache is working |
| Phase 4 | Tests pass, no behavior change | Revert if causing issues |
| Milestone 6 | All improvements measured | Document partial success; create follow-up issues |

---

### Post-Implementation Checklist

- [ ] All benchmarks pass with target improvements
- [ ] All unit tests pass (existing + new)
- [ ] CHANGELOG updated with behavior changes
- [ ] `pyproject.toml` updated with `notion` extras
- [ ] RFC status changed from "Draft" to "Implemented"
- [ ] Performance regression test added to CI
- [ ] Follow-up issues created for Future Work items

---

## Complexity Analysis Summary

### Before Optimization

| Operation | Time Complexity | Network Calls | Notes |
|-----------|-----------------|---------------|-------|
| LocalSource.fetch_all() | O(n log n + n × p) | 0 | Sort + exclude check |
| GitHubSource.fetch_all() | O(1 + n) | 1 + n | Tree + n file fetches |
| NotionSource.fetch_all() | O(⌈n/100⌉ + n × ⌈b/100⌉) | ⌈n/100⌉ + n | Pages + blocks |
| RESTSource.fetch_all() | O(p × i) | p | p pages, i items/page |
| ContentSource.get_cache_key() | O(c log c) | 0 | Sorted config |

### After Optimization

| Operation | Time Complexity | Network Calls | Change |
|-----------|-----------------|---------------|--------|
| LocalSource.fetch_all() | **O(n)** | 0 | -log n factor, -p factor |
| GitHubSource.fetch_all() | O(1 + n/k) | 1 + n | **k concurrent** |
| NotionSource.fetch_all() | O(⌈n/100⌉ + n/k × ⌈b/100⌉) | Same | **k concurrent pages** |
| RESTSource.fetch_all() | O(p × i) | p | No change needed |
| ContentSource.get_cache_key() | **O(1)** after first | 0 | Memoized |

**Variables**: n=files/pages, p=patterns/pages, c=config items, b=blocks, k=concurrency (10 for GitHub, 5 for Notion), i=items/page

---

## Testing Strategy

### Unit Tests

1. **Correctness**: Verify optimized operations produce identical results
   - Same entries returned (set comparison, order may differ)
   - Same content and frontmatter

2. **Edge cases**:
   - 0 files/pages (empty source)
   - 1 file/page (no parallelism benefit)
   - Mixed success/failure (some files fail to fetch)
   - Rate limiting responses (429 status)
   - Network timeouts

3. **Concurrency**:
   - Verify semaphore limits are respected
   - Verify no race conditions in result aggregation
   - Verify proper cleanup on exception

### Performance Tests

1. **Benchmark suite** with synthetic/mocked data:
   - Small: 50 files, 0 patterns
   - Medium: 500 files, 5 patterns
   - Large: 2K files, 10 patterns

2. **Regression detection**: Fail if performance degrades >10%

### Integration Tests

1. **Real API tests** (optional, in CI with secrets):
   - Fetch from real GitHub public repo
   - Verify content matches expected

---

## Behavior Changes

These optimizations introduce observable behavior changes:

| Change | Affected | Impact | Migration |
|--------|----------|--------|-----------|
| **Entry order non-deterministic** | LocalSource, GitHubSource, NotionSource | `fetch_all()` may return entries in different order | Use set comparison; add `sort: true` config if order required |
| **Partial fetch on errors** | GitHubSource, NotionSource | Some entries returned even if others fail | Check logs for failure count; errors logged individually |
| **Rate limit backoff** | GitHubSource | Automatic retry with delay on 429/403 | No action needed; improves reliability |
| **Block cache hit** | NotionSource | Repeated fetches within 5min may return cached content | Clear cache or wait for TTL; cache is per-instance |

**CHANGELOG entry** (to be added on merge):
```markdown
### Changed
- `LocalSource.fetch_all()` no longer sorts entries by default. Add `sort: true` to config for alphabetical order.
- `GitHubSource.fetch_all()` fetches files in parallel (10 concurrent). Entry order is non-deterministic.
- `NotionSource.fetch_all()` fetches pages in parallel (5 concurrent). Entry order is non-deterministic.

### Added
- `GitHubSource`: Automatic retry with exponential backoff on rate limit (429) responses.
- `NotionSource`: In-memory block cache (5-minute TTL) reduces API calls on repeated fetches.
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rate limiting from parallel requests | Medium | High | Conservative concurrency limits (10 GitHub, 5 Notion), exponential backoff |
| Order change breaks downstream code | Low | Low | Add `sort` config option; document in CHANGELOG |
| Regex compilation fails on edge patterns | Low | Medium | Fallback to original fnmatch loop (implemented in Phase 1) |
| Block cache memory pressure | Low | Medium | Bounded TTLCache with LRU eviction (500 pages max) |
| Parallel fetch hides individual errors | Medium | Medium | Log all errors, continue fetching, report summary at end |
| Memory spike from parallel fetches | Low | Medium | Semaphore limits concurrent in-flight requests |
| cachetools dependency unavailable | Low | Low | Graceful degradation: caching disabled if import fails |

---

## Alternatives Considered

### 1. GraphQL for GitHub (Single Request)

**Pros**: Could fetch multiple files in one query  
**Cons**: GraphQL API has different rate limits, more complex query building

**Decision**: Parallel REST is simpler and well-understood.

### 2. Git Clone Instead of API

**Pros**: One network operation, offline access  
**Cons**: Requires git, temp storage, cleanup

**Decision**: API is more portable; clone could be separate "git" source type.

### 3. Notion Official SDK

**Pros**: Maintained, handles pagination/retries  
**Cons**: Adds dependency, may not support async natively

**Decision**: Keep direct API for now; SDK could be future enhancement.

### 4. Process Pool for Local Files

**Pros**: Could parallelize file I/O  
**Cons**: IPC overhead exceeds I/O benefit for typical file sizes

**Decision**: File I/O is already fast; not worth complexity.

---

## Success Criteria

**Performance** (validated against Step 0 baseline):

| Metric | Baseline (est.) | Target | Improvement |
|--------|-----------------|--------|-------------|
| LocalSource 2K files, 10 patterns | ~500ms | <200ms | 2.5x |
| GitHubSource 500 files | ~100s | <10s | 10x |
| NotionSource 100 pages | ~100s | <30s | 3x |

**Functional**:
1. **API compatibility**: Existing configurations work unchanged
2. **Output equivalence**: Same entries returned (set comparison)
3. **Error handling**: Individual failures don't abort entire fetch
4. **Benchmarks exist**: CI tracks performance regression

**Quality**:
1. **Test coverage**: All new code paths have unit tests
2. **Documentation**: CHANGELOG documents behavior changes

---

## Future Work

1. **Disk cache for remote sources**: Persist across builds for dev server
2. **Incremental fetching**: Only fetch changed files (using ETags, checksums)
3. **WebSocket updates**: Real-time Notion/GitHub webhook integration
4. **Git source type**: Clone repos instead of API fetching
5. **CDN caching layer**: Cache remote content at edge
6. **User-configurable retry/backoff**: Expose MAX_RETRIES and backoff settings in config

---

## Dependencies

**New optional dependency for Phase 3**:
- `cachetools>=5.0` — Added to `bengal[notion]` extras for bounded TTL caching

**No new dependencies for Phases 1, 2, 4**.

---

## References

- [GitHub REST API Rate Limits](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting) — 5000 req/hour with token
- [Notion API Rate Limits](https://developers.notion.com/reference/request-limits) — 3 req/sec average
- [asyncio.Semaphore](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore) — Concurrency limiting
- [asyncio.as_completed()](https://docs.python.org/3/library/asyncio-task.html#asyncio.as_completed) — Streaming parallel results
- [fnmatch.translate()](https://docs.python.org/3/library/fnmatch.html#fnmatch.translate) — Convert glob to regex
- [cachetools.TTLCache](https://cachetools.readthedocs.io/en/stable/#cachetools.TTLCache) — Bounded TTL cache with LRU eviction

---

## Appendix: Current Implementation Locations

| Component | File | Key Functions |
|-----------|------|---------------|
| ContentEntry | `entry.py` | `to_dict()`, `from_dict()` |
| ContentSource | `source.py` | `fetch_all()`, `get_cache_key()` |
| ContentLayerManager | `manager.py` | `fetch_all()`, `_fetch_source()`, cache methods |
| LocalSource | `sources/local.py` | `fetch_all()`, `_should_exclude()`, `_load_file()` |
| GitHubSource | `sources/github.py` | `fetch_all()`, `_fetch_file()` |
| RESTSource | `sources/rest.py` | `fetch_all()`, `_extract_items()`, `_get_nested()` |
| NotionSource | `sources/notion.py` | `fetch_all()`, `_page_to_entry()`, `_get_page_content()` |
| Loaders | `loaders.py` | Factory functions for each source type |
| Registry | `sources/__init__.py` | `SOURCE_REGISTRY`, lazy loading |

---

## Appendix: Complexity by Source

### LocalSource

| Function | Current | Optimal | Notes |
|----------|---------|---------|-------|
| `fetch_all()` | O(n log n + n × p) | **O(n)** | Remove sort, compile patterns |
| `_should_exclude()` | O(p) | **O(1)** | Pre-compiled regex |
| `_load_file()` | O(f + y) | O(f + y) | File + YAML, unavoidable |
| `get_last_modified()` | O(n) | O(n) | Already optimal |

### GitHubSource

| Function | Current | Optimal | Notes |
|----------|---------|---------|-------|
| `fetch_all()` | O(t + n × r) | **O(t + n/k × r)** | k concurrent requests |
| `_fetch_file()` | O(f) | O(f) | Already optimal |
| `get_last_modified()` | O(r) | O(r) | Single API call |

### NotionSource

| Function | Current | Optimal | Notes |
|----------|---------|---------|-------|
| `fetch_all()` | O(p + n × b) | **O(p + n/k × b)** | k concurrent pages |
| `_page_to_entry()` | O(b) | O(b) or O(1) cached | Block caching |
| `_get_page_content()` | O(⌈b/100⌉) | O(⌈b/100⌉) or O(1) | Cached |
| `_blocks_to_markdown()` | O(b × t) | O(b × t) | Already optimal |

### RESTSource

| Function | Current | Optimal | Notes |
|----------|---------|---------|-------|
| `fetch_all()` | O(p × n) | O(p × n) | Pagination bound |
| `_extract_items()` | O(i) | O(i) | Already optimal |
| `_item_to_entry()` | O(m) | O(m) | Already optimal |
| `_get_nested()` | O(d) | O(d) | Already optimal |

**Variables**: n=items, p=pages/patterns, t=tree size, r=round-trip, f=file size, b=blocks, k=concurrency, m=mappings, d=depth, y=YAML size

---

## Appendix: Space Complexity

### Current Space Usage

| Structure | Space | Notes |
|-----------|-------|-------|
| ContentLayerManager.sources | O(s) | s = source count |
| Source._config | O(c) | c = config items |
| LocalSource._exclude_patterns | O(p) | p = patterns |
| Cache files (disk) | O(n × e) | n entries, e = entry size |

### Additional Space from Optimizations

| New Structure | Space | Notes |
|---------------|-------|-------|
| LocalSource._exclude_regex | O(p) | Compiled regex |
| NotionSource._block_cache | O(min(n, 500)) | Bounded TTLCache, ~5MB max |
| Semaphore (ephemeral) | O(1) | Per fetch_all call |
| In-flight parallel requests | O(k × e) | k=concurrency, e=entry size |

**Total additional space**: Block cache is bounded at 500 entries (~5MB). In-flight requests are bounded by semaphore (10 for GitHub, 5 for Notion). Peak memory usage is predictable and acceptable for dev server.
