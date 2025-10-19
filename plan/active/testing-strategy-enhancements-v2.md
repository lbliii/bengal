Title: Bengal test strategy enhancements v2 (with lessons from Sphinx)

Status: Active RFC v2

Owners: testing@bengal, @llane

Revision History:
- v1: Initial draft based on Sphinx analysis
- v2: Refined based on Bengal codebase review; more conservative snapshot approach, specific cache cleanup, selective migration strategy

---

## Motivation

We want Bengal's test suite to be faster, more reliable, and more ergonomic to author and review. Sphinx's test suite offers mature patterns we can adapt while keeping Bengal's simpler, pythonic style.

**Observed Performance Issue**: Test suite runs fast until ~95% completion, then hangs for 2-5 minutes on the last 5-10 tests. Analysis reveals:
- `test_output_quality.py` rebuilds a 292-page showcase site **11 times** (function-scoped fixture, read-only tests)
- Stateful Hypothesis tests generate 100+ sequences with multiple builds each
- Poor load balancing with `pytest-xdist`: workers sit idle while a few handle slow tests

**Current Pain Points**:
- Significant duplication in integration test setup (each test manually creates site structure)
- Function-scoped fixtures rebuilding large sites repeatedly for read-only tests
- No centralized HTTP server fixtures for link/asset tests
- Inconsistent application of test markers (especially `@pytest.mark.slow`)
- Missing cleanup for stateful singletons/caches
- Integration tests that are readable but verbose (50-100 lines of setup)

**Quick Wins Available**: Changing `test_output_quality.py` fixture to class-scope would eliminate ~1.5-4 minutes from the long tail immediately.

## What Bengal Already Does Well (keep and lean into)

- **Failure artifact capture**: We persist rich failure details to `.pytest_cache/last_failure.txt` for quick AI/human debugging.
- **Rich console hygiene**: Autouse fixture to reset Live displays prevents cross-test interference.
- **Property-based tests**: Hypothesis-backed tests (115 tests, 11.6K examples) on URL strategy and text utilities catch edge cases.
- **Incremental build coverage**: Integration tests exercise full→incremental→full sequences and cache behavior.
- **Performance awareness**: Dedicated performance tests and micro-benchmarks (separate from pytest).
- **Parametrized integration assertions**: Base URL, link generation, and template variants are covered via parametrization.
- **Explicit assertions**: Tests use clear, readable assertions (`assert 'href="/bengal/' in html`) that communicate intent.

## High-Level Goals

1. **Reliability**: Reduce flaky tests and cross-test coupling; deterministic outputs by default.
2. **Speed**: Avoid repeated heavy setup; reduce integration test time by 20-30% through fixture reuse.
3. **Ergonomics**: One-liners to stand up a site and assert outputs; fewer bespoke setups.
4. **Observability**: Consistent logs, warnings, and metrics capture for assertions.
5. **Clarity**: Maintain Bengal's readable test style; don't sacrifice clarity for DRYness.

## Scope (what we'll add)

### 1. Canonical Test Roots

**Problem**: Current tests like `test_baseurl_builds.py` and `test_documentation_builds.py` duplicate 50-100 lines of site setup per test.

**Solution**: Create `tests/roots/<scenario>/` directories with minimal `bengal.toml`, `content/`, and optional `assets/themes`.

**Structure**:
```
tests/roots/
├── README.md                    # Documents purpose of each root
├── test-basic/                  # Minimal site: 1 page, default theme
│   ├── bengal.toml
│   └── content/
│       └── index.md
├── test-baseurl/                # Tests path/absolute baseurl handling
│   ├── bengal.toml             # baseurl = "/site"
│   └── content/
│       ├── index.md
│       └── about.md
├── test-taxonomy/               # Minimal taxonomy (2 tags, 3 pages)
│   ├── bengal.toml
│   └── content/
│       ├── post1.md (tags: [python, testing])
│       ├── post2.md (tags: [python])
│       └── post3.md (tags: [testing])
├── test-templates/              # Documentation pages with template examples
│   ├── bengal.toml
│   └── content/
│       └── guide.md            # Contains {{/* examples */}}
└── test-assets/                 # Theme assets and custom assets
    ├── bengal.toml
    ├── content/...
    └── assets/
        └── images/sample.png
```

**Guidance**:
- Each root is **tiny and focused** on one scenario (≤5 files unless necessary)
- Prefer composition over monolithic roots
- Document the purpose in `tests/roots/README.md`
- Roots are **read-only templates** (copied to tmp_path for tests)

**Fixtures**:
```python
@pytest.fixture(scope="session")
def rootdir():
    """Path to tests/roots/ directory."""
    return Path(__file__).parent / "roots"

@pytest.fixture
def site_factory(tmp_path, rootdir):
    """Factory to create Site from testroot with overrides."""
    def _factory(testroot, confoverrides=None):
        # Copy root to tmp_path
        root_path = rootdir / testroot
        site_dir = tmp_path / "site"
        shutil.copytree(root_path, site_dir)

        # Apply confoverrides to bengal.toml
        if confoverrides:
            config_path = site_dir / "bengal.toml"
            apply_config_overrides(config_path, confoverrides)

        # Create Site
        site = Site.from_config(site_dir)
        site.discover_content()
        site.discover_assets()
        return site

    return _factory
```

### 2. Pytest Marker and Plugin

**Problem**: Integration test setup is ad-hoc; no standardized pattern for "build a site and assert outputs".

**Solution**: Introduce `@pytest.mark.bengal(testroot=..., confoverrides=...)` that wires a ready site fixture.

**Plugin Structure**:
```
tests/_testing/
├── __init__.py              # Declares pytest_plugins
├── fixtures.py              # rootdir, site_factory, logs_capture
├── markers.py               # Implements pytest_collection_modifyitems
├── cli.py                   # CLI runner utilities
├── http.py                  # HTTP server fixtures (Phase 3)
├── normalize.py             # HTML/JSON normalization (Phase 3)
└── README.md                # Documents the testing utilities
```

**Usage Example**:
```python
@pytest.mark.bengal(testroot="test-basic")
def test_site_builds(site, build_site):
    """Minimal test using test-basic root."""
    build_site()
    assert len(site.pages) == 1
    assert (site.output_dir / "index.html").exists()

@pytest.mark.bengal(
    testroot="test-baseurl",
    confoverrides={"site.baseurl": "https://example.com/sub"}
)
def test_absolute_baseurl(site, build_site):
    """Override baseurl for this test."""
    build_site()
    html = (site.output_dir / "index.html").read_text()
    assert 'href="https://example.com/sub/assets/' in html
```

**Marker Implementation**:
- Resolves `testroot` into a concrete project path under `tests/roots/`
- Applies `confoverrides` on top of `bengal.toml` when constructing the Site
- Exposes fixtures: `site` (pre-discovery), `build_site` (callable), `logs_capture` (captured status/warnings)

**Report Header**:
Add `pytest_report_header` to print:
- Python version
- Bengal version
- GIL mode (Python 3.13+)
- Test roots path
- Temp directory base path

### 3. CLI Runner Wrapper

**Problem**: CLI tests use raw `subprocess.run()` with inconsistent patterns for capturing/sanitizing output.

**Solution**: Provide `run_cli()` helper that standardizes CLI invocation, output capture, and ANSI stripping.

**Primary Approach (subprocess)**:
```python
# tests/_testing/cli.py
import os
import re
import subprocess
import sys
from dataclasses import dataclass

# ANSI escape code pattern
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return ANSI_RE.sub('', text)

@dataclass
class CLIResult:
    returncode: int
    stdout: str
    stderr: str

    def assert_ok(self):
        assert self.returncode == 0, f"CLI failed: {self.stderr}"

    def assert_fail_with(self, code=None):
        assert self.returncode != 0
        if code:
            assert self.returncode == code

    def assert_stderr_contains(self, text):
        assert text in self.stderr

def run_cli(args, cwd=None, env=None, capture_ansi=False, timeout=30):
    """Run bengal CLI as subprocess with sanitization.

    Args:
        args: List of CLI arguments (e.g., ["site", "build"])
        cwd: Working directory (defaults to current)
        env: Environment variables (merged with os.environ)
        capture_ansi: If False (default), strip ANSI codes for easier assertions
        timeout: Command timeout in seconds

    Returns:
        CLIResult with returncode, stdout, stderr
    """
    result = subprocess.run(
        [sys.executable, "-m", "bengal.cli", *args],
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    stdout = result.stdout if capture_ansi else strip_ansi(result.stdout)
    stderr = result.stderr if capture_ansi else strip_ansi(result.stderr)

    return CLIResult(returncode=result.returncode, stdout=stdout, stderr=stderr)
```

**Why subprocess**: Tests actual CLI invocation, avoids import-time side effects, matches production behavior.

**Secondary Approach (click.testing for unit tests)**:
For speed-critical unit tests of CLI logic:
```python
from click.testing import CliRunner

def run_cli_click(args):
    """Fast in-process CLI runner for unit tests."""
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, args)
    return CLIResult(result.exit_code, result.stdout, result.stderr)
```

**Migration Path**:
- Use `run_cli()` for integration tests (current `subprocess.run()` calls)
- Use `run_cli_click()` for new unit tests of CLI logic

### 4. Cleanup and Cache Hygiene

**Problem**: Tests may have cross-contamination from stateful singletons and caches.

**Solution**: Expand autouse cleanup to reset all stateful components.

**Specific Bengal Caches/State to Reset**:
```python
@pytest.fixture(autouse=True)
def reset_bengal_state():
    """Reset all stateful singletons/caches between tests."""
    yield  # Run test

    # Rich console (already done, keep it)
    try:
        from bengal.utils.rich_console import reset_console
        reset_console()
    except ImportError:
        pass

    # TODO Phase 1: Identify and reset:
    # - PageProxyCache (if exists as singleton)
    # - TaxonomyIndex caching state
    # - Template engine instances/bytecode cache
    # - Asset dependency map state
    # - Discovery caches (content/asset)
    # - URL map caches
    # - Font/pygments registries (if stateful)
    # - Global logger handlers (if accumulated)
```

**Action Item**: Survey Bengal codebase for:
- Module-level mutable state
- Singleton patterns
- LRU caches that aren't function-local
- Registry patterns (asset types, content types)

### 5. Output Normalization (Conservative Approach)

**Problem**: HTML/JSON output contains volatile data (timestamps, hashes, absolute paths) that makes assertions brittle.

**Solution**: Provide normalization helpers for **explicit assertions**, not snapshots initially.

**Normalization Utilities**:
```python
# tests/_testing/normalize.py
import re
from bs4 import BeautifulSoup

def normalize_html(html_str, preserve_structure=True):
    """Normalize HTML for deterministic assertions.

    - Strip timestamps and build dates
    - Replace absolute paths with placeholders
    - Replace asset hashes with stable markers
    - Normalize whitespace (optional)
    - Sort attributes (optional)
    """
    html = html_str

    # Replace absolute paths
    html = re.sub(r'/[a-zA-Z]:/[^\s"\'<>]+', 'PATH', html)
    html = re.sub(r'file://[^\s"\'<>]+', 'PATH', html)

    # Replace asset hashes (e.g., style.abc123.css -> style.HASH.css)
    html = re.sub(r'\.([a-f0-9]{8,})\.', '.HASH.', html)

    # Strip timestamps
    html = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'TIMESTAMP', html)

    if preserve_structure:
        # Minimal whitespace normalization
        html = re.sub(r'\n\s*\n', '\n', html)  # Remove blank lines

    return html

def normalize_json(data):
    """Normalize JSON data for deterministic assertions.

    - Sort keys recursively
    - Strip time/host dependent fields
    - Stable indent
    """
    if isinstance(data, dict):
        return {k: normalize_json(v) for k, v in sorted(data.items())}
    elif isinstance(data, list):
        return [normalize_json(item) for item in data]
    return data

def extract_head_meta(html_str):
    """Extract just <head> meta tags for structural assertions."""
    soup = BeautifulSoup(html_str, "html.parser")
    head = soup.find("head")
    if not head:
        return ""

    # Keep only meta/link tags, strip content values
    meta_tags = []
    for tag in head.find_all(["meta", "link"]):
        # Keep tag name and attribute names, anonymize values
        meta_tags.append(f"<{tag.name} {' '.join(sorted(tag.attrs.keys()))}>")

    return "\n".join(sorted(meta_tags))
```

**Usage in Tests**:
```python
def test_baseurl_in_assets(site, build_site):
    build_site()
    html = (site.output_dir / "index.html").read_text()

    # Normalize for stable assertion
    norm_html = normalize_html(html)
    assert 'href="/bengal/assets/css/style.HASH.css"' in norm_html
```

### 6. Snapshots (Deferred, Narrow Scope When Implemented)

**Status**: **Not in Phase 1-2**. Prove value with explicit assertions first.

**If/When Implemented** (Phase 5+):
- Use `pytest-regressions` plugin (better than raw files)
- Snapshot **only** stable, structural fragments
- Never snapshot full HTML pages

**Snapshot Boundaries**:

✅ **Good candidates** (stable structures):
- Meta tag structure in `<head>` (tag names/attributes, not values)
- Navigation hierarchy (menu structure, not content)
- Asset manifest shapes (JSON keys/structure)
- Search index structure
- Sitemap XML structure

❌ **Bad candidates** (too volatile):
- Full HTML pages
- Content with timestamps/hashes
- Theme-dependent styling (CSS class names)
- Generated IDs or inline styles
- RSS feeds with dates

**Example** (if pursued later):
```python
@pytest.mark.snapshot
def test_head_meta_structure(site, build_site, data_regression):
    """Snapshot meta tag structure (not values)."""
    build_site()
    html = (site.output_dir / "index.html").read_text()

    # Extract just structure
    meta_structure = extract_head_meta(html)

    # Snapshot (regenerate with --force-regen)
    data_regression.check({"meta_tags": meta_structure})
```

**Rationale for Deferral**:
- Bengal updates themes frequently
- Baseurl/asset hashing makes output dynamic
- Current explicit assertions are clear and working
- Prove snapshot value incrementally, don't commit upfront

### 7. HTTP Server Utilities (Phase 3)

**Problem**: No centralized pattern for ephemeral HTTP servers in tests.

**Solution**: Provide `http_server` fixture for link/asset tests.

**Implementation** (Phase 3):
```python
# tests/_testing/http.py
import http.server
import socket
import socketserver
import threading
import time
from functools import partial

import pytest

def wait_for_port(port: int, host: str = "localhost", timeout: float = 5.0) -> None:
    """Wait until a port is listening or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return  # Port is listening
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(0.1)
    raise TimeoutError(f"Port {port} not listening after {timeout}s")

@pytest.fixture
def http_server(tmp_path):
    """Ephemeral HTTP server for testing links/assets."""
    class TestHTTPServer:
        def __init__(self):
            self.server = None
            self.thread = None
            self.port = None

        def start(self, directory, port=0):
            """Start server on ephemeral port."""
            handler = partial(http.server.SimpleHTTPRequestHandler, directory=directory)
            self.server = socketserver.TCPServer(("localhost", port), handler)
            self.port = self.server.server_address[1]

            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()

            # Wait until listening
            wait_for_port(self.port, timeout=5)

            return f"http://localhost:{self.port}"

        def stop(self):
            if self.server:
                self.server.shutdown()
                self.thread.join(timeout=5)

    server = TestHTTPServer()
    yield server
    server.stop()
```

**Usage**:
```python
def test_external_link_checking(site, build_site, http_server):
    """Test link checking against ephemeral server."""
    # Start server serving test fixtures
    base_url = http_server.start(tmp_path / "fixtures")

    # Build site with links to ephemeral server
    build_site()

    # Assert link checking works
    ...
```

### 8. Marker Taxonomy and Defaults

**Current State**: `pytest.ini` already has good markers: `slow`, `hypothesis`, `serial`, `integration`, `cli`, `requires_network`.

**Gaps**:
- No `snapshot` marker (add when/if snapshots are used)
- `requires_network` should standardize to just `network`

**Updated Markers**:
```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, multiple components)
    slow: Slow-running tests (full site builds, >5s per test)
    hypothesis: Property-based tests using Hypothesis
    serial: Tests that must run sequentially (no parallel)
    cli: CLI command tests
    network: Tests requiring internet access
    snapshot: Tests using snapshot assertions (deferred)
```

**CI Selection**:
```bash
# Fast PR checks (~20s)
pytest -m "not slow and not network" -n auto

# Full suite for main/release (~40s)
pytest -n auto

# Nightly with slow tests
pytest -n auto  # Include slow
```

## Design Details: Migration Strategy

**Key Principle**: Be **selective, not exhaustive**. Don't migrate all 2,297 tests.

**Target Tests for Migration** (Phase 2-3):
1. **High-duplication integration tests** (20-30 tests):
   - `test_baseurl_builds.py` (2 tests, 50+ lines of setup each)
   - `test_documentation_builds.py` (3 tests, 40+ lines each)
   - `test_full_site_url_consistency.py`
   - `test_cascade_integration.py`

2. **Core build workflows** (10 tests):
   - `test_full_to_incremental_sequence.py`
   - `test_phase2b_cache_integration.py`

3. **CLI integration tests** (5-10 tests):
   - `test_cli_output_integration.py` → use `run_cli()`

**Tests to Leave Alone**:
- ✅ Unit tests (fast, clean, minimal setup)
- ✅ Simple integration tests (<20 lines)
- ✅ One-off debugging tests
- ✅ Performance benchmarks (separate harness)

**Success Metric**: If 30-40 tests (1.5% of suite) are migrated and show clear ergonomic/speed wins, that's sufficient.

## Adoption Plan (Phased)

### Phase 0: Quick Wins (30 minutes, HIGH IMPACT)

**Do these FIRST before full RFC implementation** - they address the immediate long-tail performance issue:

- [ ] **Fix `test_output_quality.py` fixture scope**:
  ```python
  # Change from function-scoped to class-scoped
  @pytest.fixture(scope="class")
  def built_site(tmp_path_factory):  # Note: tmp_path_factory for class scope
      tmp_path = tmp_path_factory.mktemp("showcase_site")
      # ... rest of fixture ...
  ```
  **Impact**: 11 builds → 1 build, **saves 1.5-4 minutes**

- [ ] **Add `@pytest.mark.slow` to showcase tests**:
  ```python
  @pytest.mark.slow
  class TestOutputQuality:
      ...
  ```
  **Impact**: Devs can skip with `-m "not slow"` for 20s feedback loop

- [ ] **Tune Hypothesis for dev vs CI**:
  ```python
  # tests/integration/stateful/test_build_workflows.py
  from hypothesis import settings
  settings.register_profile("ci", max_examples=100)
  settings.register_profile("dev", max_examples=20)
  settings.load_profile("dev" if os.getenv("CI") != "true" else "ci")
  ```
  **Impact**: **saves 30-90 seconds** in dev

- [ ] **Validate improvements**:
  ```bash
  # Before
  time pytest tests/integration/test_output_quality.py -v

  # After Phase 0
  time pytest tests/integration/test_output_quality.py -v

  # Dev workflow
  time pytest -m "not slow" -n auto  # Should be ~20s
  ```

**Expected Result**: Long tail reduced from 3-5 minutes to 30-60 seconds. Developer workflow (`-m "not slow"`) drops to ~20s.

**Decision Point**: If Phase 0 shows dramatic improvement, it validates the RFC's fixture-scoping strategy. Proceed to Phase 1.

---

### Phase 1: Infrastructure & Prototype (2-3 days)

**Deliverables**:
- [ ] Create `tests/_testing/` package:
  - `__init__.py` (declares pytest_plugins)
  - `fixtures.py` (rootdir, site_factory)
  - `markers.py` (pytest_collection_modifyitems for @pytest.mark.bengal)
  - `cli.py` (run_cli, CLIResult)
  - `normalize.py` (normalize_html, normalize_json)
  - `README.md` (documents utilities)

- [ ] Create `tests/roots/` with 5 minimal roots:
  - `test-basic` (1 page, default theme)
  - `test-baseurl` (2 pages, path baseurl)
  - `test-taxonomy` (3 pages, 2 tags)
  - `test-templates` (1 page with {{/* examples */}})
  - `test-assets` (custom assets + theme assets)
  - `README.md` (documents purpose of each root)

- [ ] Update `pytest.ini`:
  - Standardize markers (add `snapshot`, rename `requires_network` to `network`)
  - Add pytest_plugins reference in conftest.py

- [ ] **Prototype-driven validation**: Convert **one** test as proof-of-concept:
  ```python
  # tests/integration/test_baseurl_builds.py
  @pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
  def test_build_with_path_baseurl(site, build_site):
      build_site()
      html = (site.output_dir / "index.html").read_text()
      assert 'href="/bengal/assets/css/' in html

      index_json = (site.output_dir / "index.json").read_text()
      data = json.loads(index_json)
      assert data["site"]["baseurl"] == "/bengal"
  ```

**Validation**: If prototype feels ergonomic and reads well, proceed to Phase 2. If awkward, iterate on API.

### Phase 2: Pilot Migrations & Validation (2-3 days)

**Deliverables**:
- [ ] Migrate 5-8 high-duplication integration tests:
  - `test_baseurl_builds.py` (2 tests)
  - `test_documentation_builds.py` (3 tests)
  - `test_cascade_integration.py` (2-3 tests)

- [ ] Migrate 3-5 CLI tests to use `run_cli()`:
  - `test_cli_output_integration.py` (5 tests)

- [ ] Add normalization to 2-3 tests with brittle assertions

- [ ] Measure impact:
  ```bash
  # Before migration
  time pytest tests/integration/test_baseurl_builds.py

  # After migration
  time pytest tests/integration/test_baseurl_builds.py

  # Expected: 10-20% faster due to fixture reuse
  ```

**Decision Point**: Review ergonomics and performance. If positive, proceed to Phase 3. If neutral/negative, reassess approach.

### Phase 3: Selective Broader Migration (3-4 days)

**Deliverables**:
- [ ] Migrate 15-20 additional integration tests (focus on duplication)
- [ ] Implement HTTP server utilities (`tests/_testing/http.py`)
- [ ] Add `reset_bengal_state()` fixture with comprehensive cache cleanup
- [ ] Update `CONTRIBUTING.md` with "Writing Tests" section:
  ```markdown
  ## Writing Tests

  ### Integration Tests (New Style)
  Use `@pytest.mark.bengal` with test roots for site-based tests:

  ```python
  @pytest.mark.bengal(testroot="test-basic")
  def test_feature(site, build_site):
      build_site()
      assert site.pages[0].url == "/"
  ```

  ### When to Use Old Style
  - Simple, one-off tests (<20 lines)
  - Tests requiring unique site structure not covered by roots
  - Temporary debugging tests

  ### CLI Tests
  Use `run_cli()` for subprocess-based CLI tests:

  ```python
  from tests._testing.cli import run_cli

  def test_build_command(tmp_path):
      result = run_cli(["site", "build"], cwd=tmp_path)
      result.assert_ok()
      assert "Build complete" in result.stdout
  ```
  ```

**Target**: 30-40 tests migrated (1.5% of suite), demonstrating pattern for future tests.

### Phase 4: Data-Driven Optimization (1-2 days)

**Before optimizing, profile**:
```bash
# Identify actual bottlenecks
pytest --durations=20 tests/integration/

# Profile specific slow tests
pytest --profile tests/integration/test_documentation_builds.py
```

**Optimization Targets** (based on data):
- If **Hypothesis tests** are slow (likely ~11s): Tune `max_examples` in conftest
- If **showcase builds** dominate: Pre-build fixture at session scope
- If **parsing** is slow: Add package-scoped cached parse fixtures
- If **parallel overhead**: Adjust `-n auto` worker count

**Deliverables** (conditional on profiling):
- [ ] Cached parse fixtures (if parsing is bottleneck)
- [ ] Session-scoped pre-built site fixtures (if full builds dominate)
- [ ] Hypothesis tuning (if example generation is slow)

**Realistic Target**: 20-30% reduction in integration test time (15s → 10-12s).

### Phase 5: Stabilization & Continuous Improvement (Ongoing)

**Deliverables**:
- [ ] Monitor flake rate (<0.5% target)
- [ ] Add normalization rules as nondeterminism sources are discovered
- [ ] Optionally introduce narrow snapshot use cases:
  - Meta tag structure
  - Navigation hierarchy
  - Asset manifest shape
- [ ] Document patterns for new contributors
- [ ] Periodic review: Are test roots still minimal? Do they need consolidation?

**Metrics to Track**:
- Integration test duration (target: 10-12s from current 15s)
- Flake rate over 7 days (target: <0.5%)
- Test authoring time (new integration test in ≤10 lines)
- Test readability (subjective: reviews should confirm clarity)

## CI and Tooling

**pytest.ini Updates**:
```ini
[pytest]
# ... existing config ...

# Marker taxonomy
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, multiple components)
    slow: Slow-running tests (full site builds, >5s per test)
    hypothesis: Property-based tests using Hypothesis
    serial: Tests that must run sequentially (no parallel)
    cli: CLI command tests
    network: Tests requiring internet access
    snapshot: Tests using snapshot assertions (future)
```

**conftest.py Updates** (plugin registration must be in Python, not pytest.ini):
```python
# tests/conftest.py

# Register custom plugins
pytest_plugins = ["tests._testing.fixtures", "tests._testing.markers"]

# ... rest of existing conftest.py ...
```

**CI Jobs**:
```yaml
# Fast PR checks
- name: Fast Tests
  run: pytest -m "not slow and not network" -n auto --durations=10

# Full suite (main/release)
- name: Full Tests
  run: pytest -n auto --durations=20 --cov=bengal --cov-report=xml

# Upload artifacts on failure
- name: Upload Failure Artifacts
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: test-failures
    path: |
      .pytest_cache/last_failure.txt
      htmlcov/
```

**Coverage**:
- Stable measurement per job
- Gate on 85%+ for critical paths
- Exclude test roots from coverage: `omit = tests/roots/*`

## Success Criteria (Realistic)

**Speed**:
- ✅ **Phase 0 Quick Wins**: Long tail reduced from 3-5 min to <1 min (~70-80% improvement)
- ✅ **Developer workflow**: `-m "not slow"` runs in ~20s (vs current ~5-6 min full suite)
- ✅ **Full suite**: Integration test duration reduced by 20-30% (15s → 10-12s) after RFC implementation
- ✅ Setup duplication eliminated in 30-40 migrated tests

**Reliability**:
- ✅ Flake rate <0.5% over 7 days
- ✅ Retry depth ≤1 across CI runs
- ✅ No cross-test contamination from shared state

**Ergonomics**:
- ✅ New integration test in ≤10 lines (marker + assertions)
- ✅ Positive feedback from contributors on test authoring
- ✅ Reduced cognitive load for reviewing test PRs

**Clarity**:
- ✅ Tests remain readable (subjective: maintain explicit assertions)
- ✅ Test roots are well-documented and minimal
- ✅ Contributing guide clearly explains patterns

## Risk Management

**1. Over-Abstraction Risk**
- **Mitigation**: Migrate selectively (30-40 tests, not all 2,297); keep explicit assertions
- **Indicator**: If tests become harder to understand, pause and simplify

**2. Snapshot Churn Risk**
- **Mitigation**: Defer snapshots to Phase 5+; prove value incrementally
- **Indicator**: If snapshots break on trivial changes, scope down or abandon

**3. Migration Burnout Risk**
- **Mitigation**: Target only high-duplication tests; leave unit tests alone
- **Indicator**: If Phase 2 feels tedious, reassess scope

**4. Maintenance Burden Risk**
- **Mitigation**: Keep test roots minimal (<5 files each); document purpose
- **Indicator**: If roots proliferate (>10), consolidate or archive

**5. Performance Assumption Risk**
- **Mitigation**: Profile before optimizing (Phase 4); measure actual bottlenecks
- **Indicator**: If optimizations don't yield 20%+ gains, investigate root cause

## Backout/Compatibility

- ✅ Maintain old-style tests while migrating (no forced migration)
- ✅ Marker and fixtures are additive (opt-in adoption)
- ✅ If Phase 2 shows no benefit, stop migration and keep infrastructure for new tests only
- ✅ Old subprocess.run() patterns still work; `run_cli()` is a convenience

## Deliverables Checklist

### Phase 1 (Infrastructure)
- [ ] `tests/_testing/{__init__.py, fixtures.py, markers.py, cli.py, normalize.py, README.md}`
- [ ] `tests/roots/{test-basic, test-baseurl, test-taxonomy, test-templates, test-assets, README.md}`
- [ ] `pytest.ini` marker and plugin updates
- [ ] One prototype test migrated and validated

### Phase 2 (Pilot)
- [ ] 5-8 integration tests migrated
- [ ] 3-5 CLI tests using `run_cli()`
- [ ] Performance measured (before/after)
- [ ] Decision: proceed or iterate?

### Phase 3 (Selective Migration)
- [ ] 15-20 additional tests migrated (total 30-40)
- [ ] HTTP server utilities added
- [ ] `reset_bengal_state()` fixture with cache cleanup
- [ ] `CONTRIBUTING.md` updated with test patterns

### Phase 4 (Optimization)
- [ ] Profiling results analyzed
- [ ] Targeted optimizations implemented (conditional)
- [ ] Performance gains validated (20-30% target)

### Phase 5 (Stabilization)
- [ ] Flake monitoring in place
- [ ] Snapshot use cases evaluated (if any)
- [ ] Documentation complete and reviewed
- [ ] Patterns established for future tests

## Next Steps

1. **IMMEDIATE: Execute Phase 0** quick wins (30 minutes):
   - Fix `test_output_quality.py` fixture scope
   - Add `@pytest.mark.slow` markers
   - Tune Hypothesis for dev vs CI
   - **Measure and validate**: Should see dramatic improvement in long tail

2. **Review this RFC** with team; gather feedback on approach

3. **Implement Phase 1** infrastructure (2-3 days):
   - Create `tests/_testing/` package
   - Create 5 test roots
   - Migrate one prototype test

4. **Validate ergonomics**: Does the prototype feel good? Adjust API if needed

5. **Execute Phase 2** pilot migrations (2-3 days)

6. **Measure impact**: Speed, readability, contributor feedback

7. **Decide**: Proceed to Phase 3 or adjust strategy

**Key Success Indicators**:
- **Phase 0**: Long tail drops from 3-5 min to <1 min (validates fixture scoping strategy)
- **Phase 2**: Writing new integration tests feels significantly easier and faster (validates test root approach)

---

## Appendix: Example Test Root

**tests/roots/test-basic/bengal.toml**:
```toml
[site]
title = "Test Site"
baseurl = "/"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"

[markdown]
parser = "mistune"
```

**tests/roots/test-basic/content/index.md**:
```markdown
---
title: Home
---

# Welcome

This is a minimal test page.
```

**Purpose**: Minimal site for basic build smoke tests (1 page, default config).

---

## Appendix: Migration Example

**Before** (current style):
```python
def test_build_with_path_baseurl(tmp_path: Path):
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    cfg = site_dir / "bengal.toml"
    cfg.write_text(
        f"""
[site]
title = "Test"
baseurl = "/bengal"

[build]
output_dir = "public"
        """,
        encoding="utf-8",
    )

    (site_dir / "content" / "index.md").write_text(
        """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
    )

    site = Site.from_config(site_dir)
    orchestrator = BuildOrchestrator(site)
    orchestrator.build()

    assert (site_dir / "public" / "assets").exists()
    html = (site_dir / "public" / "index.html").read_text(encoding="utf-8")
    assert 'href="/bengal/assets/css/style' in html
```

**After** (with test roots and marker):
```python
@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_build_with_path_baseurl(site, build_site):
    build_site()

    assert (site.output_dir / "assets").exists()
    html = (site.output_dir / "index.html").read_text()
    assert 'href="/bengal/assets/css/style' in html
```

**Improvement**: 30 lines → 8 lines, clearer intent, reusable test root.
