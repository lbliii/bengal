# Viability Analysis: Async Link Checker RFC

**Date:** 2025-10-19  
**Analyst:** AI Assistant  
**Status:** ✅ VIABLE with minor adjustments needed

---

## Executive Summary

The RFC for an async link checker is **highly viable** and well-aligned with Bengal's existing architecture. The codebase already has:
- A health check system with validator infrastructure
- Basic link validation (internal only, stub implementation)
- JSON reporting capabilities
- CLI command structure with Click
- Cache infrastructure (JSON-based, on-disk)

**Key Finding:** ~80% of the infrastructure exists. Main work needed:
1. **NEW:** Async external link checking (httpx integration)
2. **NEW:** Persistent link cache with TTL
3. **NEW:** Dedicated CLI command (`bengal health linkcheck`)
4. **REFACTOR:** Complete the internal link validator (currently a stub)
5. **EXTEND:** Health report format to support richer link data

**Recommendation:** Proceed with implementation. Estimated effort: 3-5 days for Phase 1.

---

## Codebase Assessment

### ✅ Existing Infrastructure (Ready to Use)

#### 1. Health Check System (`bengal/health/`)

**Status:** Mature, well-designed, ready for extension

**Structure:**
```
bengal/health/
├── base.py              # BaseValidator abstract class
├── health_check.py      # HealthCheck orchestrator
├── report.py            # CheckResult, HealthReport with JSON support
└── validators/
    ├── links.py         # LinkValidatorWrapper (exists but basic)
    └── [13 other validators]
```

**Key Features:**
- Auto-registration of validators
- Per-validator enable/disable via `bengal.toml`
- Structured reporting with CheckResult (success/info/warning/error)
- JSON export via `report.format_json()`
- Console output with 3 modes: quiet/normal/verbose
- Timing/profiling built-in

**Integration Points:**
```python
# From health_check.py
class HealthCheck:
    def __init__(self, site: Site, auto_register: bool = True)
    def register(self, validator: BaseValidator)
    def run(self, build_stats: dict | None = None, verbose: bool = False) -> HealthReport
```

**Config Pattern:**
```toml
[health_check.validators]
links = true  # Enable/disable

[health_check.links]
check_anchors = true
check_external = false
ignore_patterns = ["^https://example.com"]
```

**✅ Assessment:** Perfect foundation. Minimal changes needed.

---

#### 2. Link Validator (`bengal/rendering/link_validator.py`)

**Status:** Stub implementation, needs completion

**Current Implementation:**
```python
class LinkValidator:
    def validate_page_links(self, page: Page) -> list[str]
    def validate_site(self, site: Any) -> list[tuple]
    def _is_valid_link(self, link: str, page: Page) -> bool
```

**Current Behavior:**
- ✅ Collects links from `page.links`
- ✅ Skips external links (http/https)
- ✅ Skips special links (mailto, tel, #, data:)
- ❌ **Stub:** Internal links always return True (line 126)

**Comments in Code:**
```python
# For now, assume internal links are valid
# A full implementation would need to:
# 1. Resolve the link relative to the page
# 2. Check if the target file exists in the output
# 3. Handle anchors (#sections)
```

**✅ Assessment:** Clear TODO, easy to complete. No conflicts with RFC.

---

#### 3. Cache Infrastructure (`bengal/cache/`)

**Status:** Robust, JSON-based, ready for link cache

**Pattern:**
```python
@dataclass
class BuildCache:
    VERSION: int = 1
    file_hashes: dict[str, str] = field(default_factory=dict)
    # ... other indexes ...

    @classmethod
    def load(cls, cache_path: Path) -> "BuildCache"

    def save(self, cache_path: Path) -> None
```

**Features:**
- JSON serialization (no object references)
- Versioned schema with tolerant loading
- Set → list conversion for JSON compatibility
- SHA256 hashing for change detection

**✅ Assessment:** Perfect template for link cache. Can reuse pattern:
```python
@dataclass
class LinkCache:
    VERSION: int = 1
    url_checks: dict[str, LinkCheckResult]  # url -> result
    last_checked: dict[str, datetime]       # url -> timestamp
    ttl_hours: int = 24
```

---

#### 4. CLI Structure (`bengal/cli/`)

**Status:** Modular, Click-based, extensible

**Current Structure:**
```python
bengal/cli/
├── __init__.py          # Main entry point, BengalGroup
├── base.py             # BengalGroup, BengalCommand
└── commands/
    ├── site.py         # site_cli group (build, serve, clean)
    ├── graph/          # Graph commands (subdir for multi-command)
    └── [other commands]
```

**Pattern for Command Groups:**
```python
# commands/site.py
@click.group("site", cls=BengalGroup)
def site_cli():
    """Site building and serving commands."""
    pass

site_cli.add_command(build)
site_cli.add_command(serve)
```

**✅ Assessment:** Ready for `bengal health linkcheck`. Two options:
1. **Option A:** Create `commands/health.py` with `health_cli` group
2. **Option B:** Add standalone `linkcheck` command to site_cli

**Recommendation:** Option A (health group) for future health commands.

---

#### 5. Reporting and JSON Output

**Status:** Mature, feature-complete

**Capabilities:**
- `HealthReport.format_json()` returns structured dict
- Already supports: timestamp, summary, validators, build_stats
- Can be extended for per-link detail

**Current JSON Schema:**
```json
{
  "timestamp": "2025-10-19T...",
  "summary": {
    "total_checks": 123,
    "passed": 120,
    "warnings": 2,
    "errors": 1,
    "quality_score": 98
  },
  "validators": [
    {
      "name": "Links",
      "duration_ms": 842,
      "results": [
        {
          "status": "error",
          "message": "Broken link",
          "recommendation": "Fix it",
          "details": ["url1", "url2"]
        }
      ]
    }
  ]
}
```

**✅ Assessment:** Can accommodate RFC's JSON schema with minor extensions.

---

### ❌ Missing Components (Need to Build)

#### 1. Async HTTP Client

**Status:** Not present

**Evidence:**
```bash
$ grep "^import (aiohttp|httpx|asyncio)" bengal
# No results
```

**Dependencies:**
```toml
# pyproject.toml
dependencies = [
    "click>=8.1.7",
    "markdown>=3.5.0",
    # ... no httpx or aiohttp
]
```

**Requirements:**
- Add `httpx>=0.27.0` to dependencies
- Implement `AsyncLinkChecker` class
- Handle async context in Click command (use `asyncio.run()`)

**Complexity:** Medium (2-3 days)

**Recommendation:**
- Use **httpx** (not aiohttp) for consistency with modern patterns
- Bengal SSG is primarily synchronous; async only needed for HTTP checks
- Wrap async checker in sync interface for health system integration

---

#### 2. Concurrency Control

**Status:** Not present

**Needed:**
- Global semaphore (max_concurrency)
- Per-host semaphores (per_host_limit)
- Connection pooling (httpx handles this)

**Pattern:**
```python
class AsyncLinkChecker:
    def __init__(self, max_concurrency=20, per_host_limit=4):
        self._global_sem = asyncio.Semaphore(max_concurrency)
        self._host_sems: dict[str, asyncio.Semaphore] = {}

    async def check_url(self, url: str) -> LinkCheckResult:
        host = urlparse(url).netloc
        if host not in self._host_sems:
            self._host_sems[host] = asyncio.Semaphore(self.per_host_limit)

        async with self._global_sem:
            async with self._host_sems[host]:
                # Check URL
                ...
```

**Complexity:** Low-Medium (1 day)

---

#### 3. Retry/Backoff Logic

**Status:** Not present

**Needed:**
- Exponential backoff with jitter
- Configurable retries
- Status-specific retry logic (retry 5xx, not 404)

**Pattern:**
```python
async def check_with_retry(self, url: str, retries: int = 2) -> LinkCheckResult:
    for attempt in range(retries + 1):
        try:
            result = await self._check_url_once(url)
            if result.status < 500:  # Don't retry non-server errors
                return result
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt < retries:
                backoff = self.retry_backoff * (2 ** attempt) + random.uniform(0, 0.1)
                await asyncio.sleep(backoff)
            else:
                raise
```

**Complexity:** Low (0.5 days)

---

#### 4. Persistent Link Cache

**Status:** Not present (but pattern exists)

**Needed:**
- JSON-based cache (similar to BuildCache)
- TTL handling (expire after N hours)
- ETag/Last-Modified support (optional Phase 2)

**Schema:**
```python
@dataclass
class LinkCheckResult:
    url: str
    status: int
    reason: str
    checked_at: datetime
    duration_ms: float
    error: str | None = None

@dataclass
class LinkCache:
    VERSION: int = 1
    checks: dict[str, LinkCheckResult]  # url -> result
    ttl_hours: int = 24

    def is_valid(self, url: str) -> bool:
        if url not in self.checks:
            return False
        age = datetime.now() - self.checks[url].checked_at
        return age.total_seconds() < (self.ttl_hours * 3600)
```

**Location:** `bengal/cache/link_cache.py`

**Complexity:** Low (0.5 days, reuse BuildCache pattern)

---

#### 5. CLI Command

**Status:** Not present

**Needed:**
```bash
bengal health linkcheck [PATH]
  --external-only
  --internal-only
  --max-concurrency INT
  --timeout FLOAT
  --retries INT
  --format [console|json]
  --output FILE
```

**Implementation:**
```python
# bengal/cli/commands/health.py

@click.group("health", cls=BengalGroup)
def health_cli():
    """Health check commands."""
    pass

@health_cli.command("linkcheck")
@click.argument("path", required=False, default=".")
@click.option("--external-only", is_flag=True)
@click.option("--internal-only", is_flag=True)
@click.option("--max-concurrency", type=int, default=20)
@click.option("--timeout", type=float, default=10.0)
@click.option("--retries", type=int, default=2)
@click.option("--format", type=click.Choice(["console", "json"]), default="console")
@click.option("--output", type=click.Path())
def linkcheck_cmd(path, external_only, internal_only, ...):
    """Check internal and external links."""
    # Load site
    # Run LinkCheckOrchestrator
    # Format output
    sys.exit(0 if report.has_errors() else 1)
```

**Complexity:** Low (0.5 days)

---

### 🔧 Components Needing Refactor

#### 1. Internal Link Resolution

**Current:** Stub (always returns True)

**Needed:**
1. Resolve relative links to absolute paths
2. Check if output file exists in `site.public_dir`
3. Validate anchor existence (use page TOC or parse HTML)

**Pattern:**
```python
def _is_valid_internal_link(self, link: str, page: Page, site: Site) -> bool:
    # Parse link and anchor
    if "#" in link:
        path, anchor = link.split("#", 1)
    else:
        path, anchor = link, None

    # Resolve to output path
    if path.startswith("/"):
        output_path = site.public_dir / path.lstrip("/")
    else:
        # Relative to current page
        output_path = (site.public_dir / page.output_path).parent / path

    # Check file exists
    if not output_path.exists():
        return False

    # Check anchor if present
    if anchor:
        return self._anchor_exists(output_path, anchor, site)

    return True

def _anchor_exists(self, html_path: Path, anchor: str, site: Site) -> bool:
    # Option 1: Use page.toc if available
    page = site.get_page_by_output_path(html_path)
    if page and hasattr(page, "toc"):
        return any(item.anchor == anchor for item in page.toc)

    # Option 2: Parse HTML (fallback)
    html = html_path.read_text()
    return f'id="{anchor}"' in html or f"id='{anchor}'" in html
```

**Complexity:** Medium (1-2 days)

**Caveat:** Anchor checking requires either:
- Access to page.toc (if available)
- HTML parsing (use stdlib `html.parser`, not BS4 per codebase pattern)

---

#### 2. Ignore Policy Engine

**Current:** Not present

**Needed:**
- Regex pattern matching for URLs
- Domain exclusion
- Status code range parsing (e.g., "500-599", "403")

**Implementation:**
```python
@dataclass
class IgnorePolicy:
    patterns: list[re.Pattern] = field(default_factory=list)
    domains: set[str] = field(default_factory=set)
    status_ranges: list[tuple[int, int]] = field(default_factory=list)

    def should_ignore_url(self, url: str) -> bool:
        if any(pattern.match(url) for pattern in self.patterns):
            return True

        parsed = urlparse(url)
        if parsed.netloc in self.domains:
            return True

        return False

    def should_ignore_status(self, status: int) -> bool:
        return any(low <= status <= high for low, high in self.status_ranges)

    @classmethod
    def from_config(cls, config: dict) -> "IgnorePolicy":
        # Parse config["exclude"], config["exclude_domain"], config["ignore_status"]
        ...
```

**Complexity:** Low (0.5 days)

---

## RFC Alignment Assessment

### ✅ Well-Aligned Sections

| RFC Section | Codebase Match | Notes |
|-------------|----------------|-------|
| **CLI Design** | 95% | Can use existing Click patterns, need new command |
| **Configuration** | 100% | Health check config pattern already exists |
| **JSON Output** | 90% | HealthReport.format_json() exists, needs minor extension |
| **Integration** | 100% | Health system ready for new validator |
| **Reporting** | 95% | Console/JSON modes already implemented |

### ⚠️ Sections Needing Adjustment

#### 1. CLI Command Structure

**RFC Proposes:**
```bash
bengal health linkcheck [PATH]
```

**Current Reality:**
- No `health` command group exists
- Health checks run via `bengal site build --validate` (implicit)
- Or programmatically: `HealthCheck(site).run()`

**Recommendation:**
- **Adopt RFC proposal:** Create `bengal health` group
- **Rationale:** Future-proof for more health commands
  - `bengal health linkcheck`
  - `bengal health report` (view last report)
  - `bengal health run` (run all validators)

**Implementation:**
```python
# bengal/cli/commands/health.py
@click.group("health", cls=BengalGroup)
def health_cli():
    """Health check commands."""
    pass

# Register in __init__.py
main.add_command(health_cli)
```

---

#### 2. JSON Output Schema

**RFC Proposes:**
```json
{
  "status": "passed|failed",
  "summary": {
    "checked": 123,
    "broken": 4,
    "ignored": 7,
    "duration_ms": 842
  },
  "results": [
    {
      "url": "https://example.com/a",
      "kind": "external",
      "status": 404,
      "reason": "Not Found",
      "first_ref": "/docs/page.md",
      "ref_count": 3,
      "ignored": false
    }
  ]
}
```

**Existing Schema:**
```json
{
  "timestamp": "...",
  "summary": {
    "total_checks": 123,
    "passed": 120,
    "warnings": 2,
    "errors": 1
  },
  "validators": [
    {
      "name": "Links",
      "results": [...]
    }
  ]
}
```

**Conflict:** RFC schema is link-specific; existing schema is generic.

**Recommendation:** Support both
1. **Generic health format:** `bengal health run --format=json`
2. **Link-specific format:** `bengal health linkcheck --format=json`

**Implementation:**
```python
# LinkCheckOrchestrator returns rich LinkCheckReport
class LinkCheckReport:
    def format_health_json(self) -> dict:
        """Format for generic health system."""
        return HealthReport(...).format_json()

    def format_linkcheck_json(self) -> dict:
        """Format for link-specific output (RFC schema)."""
        return {
            "status": "passed" if not self.has_errors else "failed",
            "summary": {...},
            "results": [...]  # Per RFC
        }
```

**Complexity:** Low (0.5 days)

---

#### 3. Cache Location

**RFC Proposes:**
> Cache layer (on-disk SQLite or JSONL)

**Codebase Reality:**
- All caches use JSON (`.bengal-cache.json`)
- No SQLite usage in codebase
- Performance: JSON is fast enough for link cache

**Recommendation:** Use JSON, not SQLite
- **Rationale:**
  - Consistency with codebase patterns
  - Simpler dependencies (no SQLite driver)
  - Human-readable/debuggable
  - Fast enough for 2k-10k URLs

**File:** `.bengal-link-cache.json`

**Schema:**
```json
{
  "version": 1,
  "ttl_hours": 24,
  "checks": {
    "https://example.com": {
      "status": 200,
      "checked_at": "2025-10-19T...",
      "duration_ms": 234.5
    }
  }
}
```

---

## Dependencies and Requirements

### Python Dependencies to Add

```toml
[project]
dependencies = [
    # ... existing ...
    "httpx>=0.27.0",  # Async HTTP client
]
```

**Rationale:**
- **httpx** over aiohttp:
  - Modern, well-maintained
  - Better API (similar to requests)
  - Excellent HTTP/2 and timeout handling
  - Good connection pooling

### Python Version

**Current:** `>=3.12` (pyproject.toml line 10)

**Requirement:** asyncio with modern features
- ✅ asyncio.TaskGroup (Python 3.11+)
- ✅ asyncio.Semaphore (Python 3.4+)

**✅ Compatible:** No issues

---

## Implementation Roadmap

### Phase 1: Core Functionality (RFC Target)

**Duration:** 3-5 days

**Tasks:**
1. ✅ Add httpx dependency
2. ✅ Implement `AsyncLinkChecker`
   - HEAD/GET fallback
   - Timeout/retry/backoff
   - Concurrency control
3. ✅ Refactor internal link validator
   - File resolution
   - Anchor checking
4. ✅ Create `LinkCheckOrchestrator`
   - Merge internal + external results
   - Apply ignore policies
5. ✅ Implement `LinkCache`
   - JSON persistence
   - TTL handling
6. ✅ Create CLI command
   - `bengal health linkcheck`
   - All flags from RFC
7. ✅ Unit tests
   - Mock HTTP server
   - Retry logic
   - Cache TTL
8. ✅ Integration test
   - Run against examples/showcase

**Deliverables:**
- Working `bengal health linkcheck` command
- Console + JSON output
- Persistent cache
- Documentation

---

### Phase 2: Advanced Features (Future)

**Duration:** 2-3 days

**Tasks:**
1. ETag/Last-Modified support
2. Per-domain policies
3. Streaming JSON output for large sites
4. Analytics (most broken links, slowest domains)
5. CI/CD recipes and GitHub Action

**Nice-to-Have:**
- Parallel internal link checking (currently sequential)
- WebSocket link validation
- robots.txt respect (if desired)

---

## Risk Assessment

### Low Risks ✅

| Risk | Mitigation | Status |
|------|-----------|--------|
| **Async in sync codebase** | Use `asyncio.run()` wrapper; health system stays sync | ✅ Manageable |
| **Flaky endpoints** | Retries, backoff, cache, ignore 5xx by default | ✅ Designed for |
| **Rate limits** | Per-host concurrency, HEAD first, configurable delays | ✅ Designed for |
| **Large sites** | Bounded concurrency, streaming (Phase 2) | ✅ Mitigated |

### Medium Risks ⚠️

| Risk | Mitigation | Status |
|------|-----------|--------|
| **Internal link anchor validation** | Requires page.toc or HTML parsing; may be incomplete | ⚠️ Needs design decision |
| **Relative link resolution edge cases** | Thorough testing needed for ../../../ paths | ⚠️ Test coverage critical |
| **Cache invalidation** | TTL-based only; no smart invalidation | ⚠️ Acceptable for MVP |

### High Risks ❌

| Risk | Mitigation | Status |
|------|-----------|--------|
| None identified | - | ✅ Clear path |

---

## Testing Strategy

### Unit Tests

**Location:** `tests/unit/health/test_link_checker.py`

**Coverage:**
- AsyncLinkChecker
  - Retry/backoff logic
  - Concurrency limits
  - Timeout handling
  - Status code interpretation
- Internal link resolution
  - Relative paths
  - Absolute paths
  - Anchor links
- IgnorePolicy
  - Pattern matching
  - Domain exclusion
  - Status range parsing
- LinkCache
  - TTL expiration
  - JSON serialization
  - Version tolerance

**Mock Strategy:**
```python
import pytest
from unittest.mock import AsyncMock
import httpx

@pytest.mark.asyncio
async def test_retry_on_timeout():
    checker = AsyncLinkChecker(retries=2)

    # Mock httpx.AsyncClient
    client = AsyncMock()
    client.head.side_effect = [
        httpx.TimeoutException("timeout"),
        httpx.Response(200)
    ]

    result = await checker.check_url("https://example.com", client)
    assert result.status == 200
    assert client.head.call_count == 2
```

---

### Integration Tests

**Location:** `tests/integration/test_link_checker_integration.py`

**Setup:**
- Spin up local HTTP server (use pytest-httpserver or http.server)
- Create routes: 200, 301, 404, 500, slow (for timeout), flaky (random fail)

**Tests:**
1. Check all status codes handled correctly
2. Retry logic with flaky endpoint
3. Timeout handling
4. Concurrency (check N URLs, verify parallel execution)
5. Cache persistence (run twice, second run uses cache)

**Pattern:**
```python
from pytest_httpserver import HTTPServer

def test_external_link_checking(httpserver: HTTPServer):
    httpserver.expect_request("/ok").respond_with_data("OK", status=200)
    httpserver.expect_request("/notfound").respond_with_data("Not Found", status=404)

    checker = AsyncLinkChecker()
    results = asyncio.run(checker.check_urls([
        httpserver.url_for("/ok"),
        httpserver.url_for("/notfound")
    ]))

    assert results[0].status == 200
    assert results[1].status == 404
```

---

### E2E Tests

**Location:** `tests/integration/test_linkcheck_cli.py`

**Tests:**
1. Run against examples/showcase
2. Verify JSON output schema
3. Test --external-only and --internal-only
4. Test --output FILE
5. Verify exit codes (0 = pass, 1 = fail)

**Pattern:**
```python
from click.testing import CliRunner
from bengal.cli.commands.health import linkcheck_cmd

def test_linkcheck_cli_json_output(tmp_path):
    runner = CliRunner()
    output_file = tmp_path / "report.json"

    result = runner.invoke(linkcheck_cmd, [
        "examples/showcase",
        "--format=json",
        "--output", str(output_file)
    ])

    assert result.exit_code == 0
    data = json.loads(output_file.read_text())
    assert "status" in data
    assert "summary" in data
```

---

## Performance Targets

### RFC Targets

> 95th percentile link check under 5 minutes for 2k external links with defaults.

**Analysis:**
- 2000 links
- max_concurrency = 20
- avg response time = 500ms
- time = 2000 / 20 * 0.5s = **50 seconds**

**✅ Feasible** with good network conditions.

**With Cache:**
- Second run with 90% cache hits: **5 seconds**

**Worst Case (slow sites, retries):**
- timeout = 10s
- retries = 2
- 10% failure rate
- time ≈ 100-200 seconds = **1.5-3 minutes**

**✅ Within target** (< 5 minutes)

---

### Internal Link Performance

**Current Status:** Unknown (stub implementation)

**Expected:**
- File existence checks: O(1) per link
- 1000 internal links
- avg time = 0.1ms per check
- total = **100ms**

**✅ Fast** (no network I/O)

---

## Security and Privacy

### Concerns

1. **User privacy:** HTTP requests reveal site content
2. **Server load:** Aggressive checking could DDoS small sites
3. **Secrets in URLs:** API keys in query params might be logged

### Mitigations

1. **No custom headers by default**
   - User-Agent: "Bengal-LinkChecker/0.1.2"
   - No tracking headers
2. **Respect rate limits**
   - Default per_host_limit = 4 (conservative)
   - Exponential backoff
3. **URL sanitization**
   - Strip query params in logs (optional)
   - Config: `sanitize_urls = true`
4. **Cache security**
   - Store in project dir (`.bengal-link-cache.json`)
   - Don't commit to git (add to .gitignore example)

---

## Documentation Requirements

### User Documentation

**File:** `examples/showcase/content/docs/link-checker.md`

**Sections:**
1. Introduction and use cases
2. Quick start
   ```bash
   bengal health linkcheck
   ```
3. Configuration (bengal.toml)
4. CLI reference (all flags)
5. Ignore patterns and policies
6. JSON output schema
7. CI/CD integration
8. Performance tuning
9. Troubleshooting
10. FAQ

---

### Developer Documentation

**File:** `bengal/health/validators/links.md` or inline docstrings

**Content:**
- Architecture overview
- AsyncLinkChecker API
- LinkCheckOrchestrator design
- Cache format and TTL logic
- Testing strategy
- Extension points

---

## Blockers and Dependencies

### Blockers: None ✅

All required infrastructure exists or can be added cleanly.

### Dependencies

**Technical:**
- httpx (external)
- asyncio (stdlib)

**Internal:**
- Health system (exists)
- Config system (exists)
- Cache system (pattern exists)

**Human:**
- Code review and approval
- User testing (optional Phase 2)

---

## Recommendation

### ✅ PROCEED with Implementation

**Confidence:** High (90%)

**Rationale:**
1. Infrastructure largely exists
2. No architectural conflicts
3. RFC is well-designed and realistic
4. Clear implementation path
5. Low risk profile
6. High user value (CI/CD integration)

### Suggested Modifications to RFC

1. **Cache Format:** JSON, not SQLite (consistency)
2. **CLI Structure:** Add `health` command group (future-proof)
3. **JSON Schema:** Support both generic and link-specific formats
4. **Anchor Checking:** Make optional in Phase 1 (complexity)

### Success Criteria

**Phase 1 (MVP):**
- [ ] `bengal health linkcheck` command works
- [ ] External links checked async with retry/backoff
- [ ] Internal links validated (files + anchors)
- [ ] Cache persists across runs
- [ ] JSON output matches RFC schema
- [ ] Exit codes correct (0/1)
- [ ] 95% test coverage
- [ ] Documentation complete
- [ ] Works on examples/showcase

**Phase 2 (Polish):**
- [ ] ETag support
- [ ] Advanced analytics
- [ ] CI/CD recipes
- [ ] Performance optimization (streaming)

---

## Appendix: Code Snippets

### Proposed File Structure

```
bengal/
├── health/
│   └── validators/
│       ├── links.py                # Refactor existing wrapper
│       └── link_checker/           # NEW
│           ├── __init__.py
│           ├── async_checker.py    # AsyncLinkChecker
│           ├── internal_checker.py # Internal link validation
│           ├── orchestrator.py     # LinkCheckOrchestrator
│           ├── ignore_policy.py    # IgnorePolicy
│           └── cache.py            # LinkCache
├── cache/
│   └── link_cache.py               # Or keep in link_checker/
└── cli/
    └── commands/
        └── health.py               # NEW: health_cli group

tests/
├── unit/
│   └── health/
│       └── link_checker/
│           ├── test_async_checker.py
│           ├── test_internal_checker.py
│           ├── test_orchestrator.py
│           └── test_cache.py
└── integration/
    ├── test_link_checker_integration.py
    └── test_linkcheck_cli.py
```

---

### Sample Implementation: AsyncLinkChecker

```python
"""
Async external link checker with retry/backoff and concurrency control.
"""
import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import httpx


@dataclass
class LinkCheckResult:
    url: str
    status: int
    reason: str
    duration_ms: float
    checked_at: datetime
    error: str | None = None


class AsyncLinkChecker:
    """
    Validates external links asynchronously with retry and concurrency control.
    """

    def __init__(
        self,
        max_concurrency: int = 20,
        per_host_limit: int = 4,
        timeout: float = 10.0,
        retries: int = 2,
        retry_backoff: float = 0.5,
    ):
        self.max_concurrency = max_concurrency
        self.per_host_limit = per_host_limit
        self.timeout = timeout
        self.retries = retries
        self.retry_backoff = retry_backoff

        self._global_sem = asyncio.Semaphore(max_concurrency)
        self._host_sems: dict[str, asyncio.Semaphore] = {}

    async def check_urls(self, urls: list[str]) -> list[LinkCheckResult]:
        """Check multiple URLs in parallel."""
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            tasks = [self.check_url(url, client) for url in urls]
            return await asyncio.gather(*tasks)

    async def check_url(self, url: str, client: httpx.AsyncClient) -> LinkCheckResult:
        """Check a single URL with retry and backoff."""
        host = urlparse(url).netloc

        # Get or create per-host semaphore
        if host not in self._host_sems:
            self._host_sems[host] = asyncio.Semaphore(self.per_host_limit)

        async with self._global_sem:
            async with self._host_sems[host]:
                return await self._check_with_retry(url, client)

    async def _check_with_retry(
        self, url: str, client: httpx.AsyncClient
    ) -> LinkCheckResult:
        """Check URL with exponential backoff."""
        start_time = asyncio.get_event_loop().time()

        for attempt in range(self.retries + 1):
            try:
                # Try HEAD first (faster)
                response = await client.head(url)

                # Some servers don't support HEAD
                if response.status_code == 405:
                    response = await client.get(url)

                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                return LinkCheckResult(
                    url=url,
                    status=response.status_code,
                    reason=response.reason_phrase,
                    duration_ms=duration_ms,
                    checked_at=datetime.now(),
                )

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < self.retries:
                    # Exponential backoff with jitter
                    backoff = self.retry_backoff * (2**attempt) + random.uniform(0, 0.1)
                    await asyncio.sleep(backoff)
                else:
                    # Final attempt failed
                    duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    return LinkCheckResult(
                        url=url,
                        status=0,
                        reason="Network Error",
                        duration_ms=duration_ms,
                        checked_at=datetime.now(),
                        error=str(e),
                    )

        # Should never reach here
        raise RuntimeError("Retry logic error")
```

---

## Conclusion

The async link checker RFC is **highly viable** and ready for implementation. The codebase provides ~80% of the needed infrastructure. Main work is:

1. Add httpx and implement async checker (3 days)
2. Complete internal link validator (1 day)
3. Build orchestrator and CLI (1 day)

**Total Effort:** 5-7 days for Phase 1 MVP.

**Recommendation:** ✅ **APPROVE and IMPLEMENT**

---

**Next Steps:**
1. Review this analysis with team
2. Approve dependency addition (httpx)
3. Create implementation branch
4. Begin Phase 1 work
5. Target completion: 2025-10-26

**Questions or Concerns:** None identified. Proceed with confidence.
