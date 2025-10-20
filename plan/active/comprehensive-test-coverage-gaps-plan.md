# Comprehensive Test Coverage Gaps Plan

**Status:** Draft → Active  
**Priority:** High (Build Reliability & Cross-Platform Support)  
**Estimated Effort:** 40-60 hours  
**Created:** 2025-10-20

---

## Executive Summary

Bengal has **excellent test coverage** (65% overall, 75-100% critical path) with 2,661 high-quality tests including 116 property-based tests. However, analysis reveals **critical gaps** in:
1. **Build interruption recovery** (cache corruption, partial writes)
2. **Circular dependency detection** (templates, menus, cascades)
3. **Concurrent build safety** (multi-process, dev server conflicts)
4. **Cross-platform edge cases** (filesystems, paths, encodings)
5. **Input validation fuzzing** (malformed frontmatter, config)

These gaps represent **production risks** that users will encounter in CI environments, international deployments, and edge-case scenarios.

---

## Current Testing Strategy (Baseline)

### What We Do Well ✅

**From `TEST_COVERAGE.md` and `tests/README.md`:**
- **2,661 tests** with ~40s execution time
- **116 property-based tests** (Hypothesis) generating 11,600+ examples
- **148 integration tests** covering multi-component workflows
- **Critical path coverage**: 75-100% on core modules
- **Fast feedback loop**: `-m "not slow"` for ~20s dev runs

**Test Organization:**
```
tests/
├── unit/           # Component isolation (2,412 tests)
├── integration/    # Multi-component workflows (148 tests)
├── performance/    # Benchmarks (separate suite)
├── manual/         # Interactive dev server tests (14 tests)
└── _testing/       # Shared fixtures, helpers, markers
```

**Testing Tools:**
- `pytest` + `pytest-cov` (coverage)
- `pytest-xdist` (parallel execution)
- `hypothesis` (property-based testing)
- `pytest-timeout` (prevents hangs)

**Current Strengths:**
- Property-based testing on utils (text, dates, paths, pagination)
- Parametrized tests for better visibility
- Atomic write tests (concurrent scenarios)
- Stateful build workflow tests (Hypothesis state machines)
- Integration tests for incremental builds, cache migration

### What We're Missing ⚠️

**Identified Gaps:**
1. **Build interruption & recovery** (no tests)
2. **Circular dependencies** (no detection)
3. **Concurrent build conflicts** (limited tests)
4. **Filesystem permissions & edge cases** (limited coverage)
5. **Input validation fuzzing** (limited malformed input tests)
6. **Resource leak detection** (no systematic tests)
7. **Cross-platform paths** (some normalization tests, but gaps)
8. **Text encoding edge cases** (UTF-8 BOM, mixed encodings)

---

## Gap Analysis by Code Area

### 1. Build Interruption & Cache Corruption

**Priority:** 🔴 CRITICAL  
**Risk:** Users Ctrl+C builds; corrupted cache → cascading failures

#### Current State
- ✅ Atomic writes tested: `tests/unit/utils/test_atomic_write.py`
- ✅ Cache loading tested: `tests/unit/cache/test_build_cache.py`
- ❌ **NOT TESTED:** Interrupted builds, partial cache writes, recovery

#### Code Areas
- **`bengal/cache/build_cache.py:143-193`** - `save()` method
  - Uses `AtomicFile` for crash-safety
  - Logs errors but doesn't test corruption recovery
  - Exception handling: lines 185-192

- **`bengal/orchestration/build.py:66-252`** - Build pipeline
  - No signal handling (SIGINT, SIGTERM)
  - No cleanup on interruption
  - Cache saved at end (line ~850+)

#### Specific Gaps
```python
# NOT TESTED:
1. Build interrupted during cache.save()
2. Partial JSON write to .bengal-cache.json
3. Cache file with invalid JSON (truncated)
4. Cache version downgrade (only upgrade tested)
5. Orphaned dependencies (references to deleted files)
6. Recovery from completely corrupted cache
7. Concurrent cache writes (two builds running)
```

#### Test Plan

**A. Cache Corruption Resilience** (`tests/unit/cache/test_cache_corruption.py`)

```python
import signal
import json
import pytest
from pathlib import Path
from bengal.cache.build_cache import BuildCache

class TestCacheCorruption:
    """Test cache handling of corrupted/invalid data."""

    def test_load_truncated_json(self, tmp_path):
        """Cache loading should handle truncated JSON gracefully."""
        cache_file = tmp_path / ".bengal-cache.json"
        cache_file.write_text('{"version": 1, "file_hashes": {"content/page.md"')  # Truncated

        cache = BuildCache.load(cache_file)

        # Should return empty cache, not crash
        assert len(cache.file_hashes) == 0
        assert cache.version == BuildCache.VERSION

    def test_load_invalid_json_characters(self, tmp_path):
        """Cache loading should handle invalid JSON (control chars, etc.)."""
        cache_file = tmp_path / ".bengal-cache.json"
        cache_file.write_bytes(b'{"version": 1, \x00\x01\x02 "invalid": true}')

        cache = BuildCache.load(cache_file)
        assert len(cache.file_hashes) == 0

    def test_load_empty_file(self, tmp_path):
        """Cache loading should handle empty cache file."""
        cache_file = tmp_path / ".bengal-cache.json"
        cache_file.write_text("")

        cache = BuildCache.load(cache_file)
        assert cache.version == BuildCache.VERSION

    def test_load_version_downgrade(self, tmp_path):
        """Cache should handle version downgrade (future → current)."""
        cache_file = tmp_path / ".bengal-cache.json"
        future_cache = {
            "version": 99,  # Future version
            "file_hashes": {"content/page.md": "abc123"},
            "future_field": "unknown",
        }
        cache_file.write_text(json.dumps(future_cache))

        cache = BuildCache.load(cache_file)

        # Should load with best-effort (logs warning)
        assert len(cache.file_hashes) == 1  # Known fields preserved

    def test_load_missing_required_fields(self, tmp_path):
        """Cache should handle missing fields gracefully."""
        cache_file = tmp_path / ".bengal-cache.json"
        cache_file.write_text('{"version": 1}')  # Missing all data fields

        cache = BuildCache.load(cache_file)
        assert len(cache.file_hashes) == 0
        assert len(cache.dependencies) == 0

    def test_orphaned_dependencies(self, tmp_path):
        """Cache with references to deleted files should be cleaned."""
        cache = BuildCache()

        # Add dependencies for files that no longer exist
        cache.dependencies["deleted/page.md"] = {"templates/base.html"}
        cache.file_hashes["deleted/page.md"] = "abc123"

        # Verify affected pages includes deleted file
        affected = cache.get_affected_pages(Path("templates/base.html"))
        assert "deleted/page.md" in affected

        # TODO: Add cleanup logic to prune orphaned entries

    @pytest.mark.hypothesis
    @given(st.binary())
    def test_cache_load_fuzzing(self, tmp_path, binary_data):
        """Fuzz test cache loading with random binary data."""
        cache_file = tmp_path / ".bengal-cache.json"
        cache_file.write_bytes(binary_data)

        # Should never crash, always return valid cache
        cache = BuildCache.load(cache_file)
        assert isinstance(cache, BuildCache)
        assert cache.version >= 1


class TestBuildInterruption:
    """Test build behavior when interrupted."""

    def test_interrupted_during_cache_save(self, tmp_path):
        """Simulate build interrupted during cache save."""
        import threading
        import time

        cache = BuildCache()
        cache.file_hashes["content/page.md"] = "abc123"
        cache_file = tmp_path / ".bengal-cache.json"

        def interrupt_during_save():
            time.sleep(0.01)  # Let save start
            # Simulate file corruption mid-write
            if cache_file.exists():
                cache_file.write_text('{"version": 1, "file_hashes": {')  # Truncate

        thread = threading.Thread(target=interrupt_during_save)
        thread.start()

        try:
            cache.save(cache_file)
        except Exception:
            pass  # Ignore errors during test

        thread.join()

        # Next load should handle corrupted file
        recovered = BuildCache.load(cache_file)
        assert isinstance(recovered, BuildCache)

    def test_signal_handling_during_build(self, temp_site):
        """Test that SIGINT/SIGTERM during build leaves cache in valid state."""
        from bengal.core.site import Site
        import signal
        import multiprocessing

        def build_with_interrupt(site_path):
            site = Site.from_config(site_path)

            # Start build
            def interrupt_handler(signum, frame):
                # Cleanup should happen here
                raise KeyboardInterrupt()

            signal.signal(signal.SIGINT, interrupt_handler)

            try:
                site.build(parallel=False, incremental=True)
            except KeyboardInterrupt:
                pass  # Expected

            # Check cache file validity
            cache_file = site_path / ".bengal-cache.json"
            if cache_file.exists():
                cache = BuildCache.load(cache_file)
                return cache.version == BuildCache.VERSION
            return True

        # Run in subprocess to avoid affecting main process
        process = multiprocessing.Process(target=build_with_interrupt, args=(temp_site,))
        process.start()
        process.join(timeout=5)

        if process.is_alive():
            process.terminate()
            process.join()
```

**B. Concurrent Build Safety** (`tests/integration/test_concurrent_builds.py`)

```python
import pytest
import concurrent.futures
from pathlib import Path
from bengal.core.site import Site

class TestConcurrentBuilds:
    """Test that multiple concurrent builds don't corrupt state."""

    def test_concurrent_full_builds(self, temp_site):
        """Run multiple full builds concurrently on same site."""
        def build_site(iteration):
            site = Site.from_config(temp_site)
            site.build(parallel=False, incremental=False)
            return iteration

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(build_site, i) for i in range(10)]
            results = [f.result() for f in futures]

        # All builds should complete
        assert len(results) == 10

        # Cache should be valid (last build wins)
        cache_file = temp_site / ".bengal-cache.json"
        assert cache_file.exists()

        from bengal.cache.build_cache import BuildCache
        cache = BuildCache.load(cache_file)
        assert len(cache.file_hashes) > 0

    def test_concurrent_incremental_builds(self, temp_site):
        """Run concurrent incremental builds (race condition test)."""
        # First build to create cache
        site = Site.from_config(temp_site)
        site.build(parallel=False, incremental=True)

        def incremental_build(iteration):
            site = Site.from_config(temp_site)
            site.build(parallel=False, incremental=True)
            return iteration

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(incremental_build, i) for i in range(5)]
            results = [f.result() for f in futures]

        assert len(results) == 5

    def test_dev_server_and_cli_build_concurrent(self, temp_site):
        """Simulate dev server running while CLI build executes."""
        # TODO: Implement with actual dev server
        # This tests file lock contention on .bengal-cache.json
        pass

    def test_cache_file_locking(self, tmp_path):
        """Test that cache writes use file locking."""
        from bengal.cache.build_cache import BuildCache
        import threading

        cache_file = tmp_path / ".bengal-cache.json"

        def write_cache(worker_id):
            cache = BuildCache()
            cache.file_hashes[f"file_{worker_id}.md"] = f"hash_{worker_id}"
            cache.save(cache_file)
            return worker_id

        threads = []
        for i in range(10):
            thread = threading.Thread(target=write_cache, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Final cache should be valid (one of the writes)
        cache = BuildCache.load(cache_file)
        assert len(cache.file_hashes) > 0
```

**Implementation Steps:**
1. Add tests to `tests/unit/cache/test_cache_corruption.py` ✓
2. Add tests to `tests/integration/test_concurrent_builds.py` ✓
3. Add signal handling to `bengal/orchestration/build.py` (cleanup on Ctrl+C)
4. Add cache pruning logic to remove orphaned entries
5. Consider file locking for cache writes (fcntl on Unix, msvcrt on Windows)

**Success Metrics:**
- ✅ 100% cache corruption scenarios handled gracefully
- ✅ Zero cache corruption in concurrent build tests
- ✅ Signal handling allows clean shutdown

---

### 2. Circular Dependency Detection

**Priority:** 🔴 CRITICAL  
**Risk:** Infinite loops, stack overflows, silent failures

#### Current State
- ✅ Dependency tracking: `bengal/cache/dependency_tracker.py`
- ✅ Template inclusion chain: `bengal/rendering/errors.py:28-43` (InclusionChain)
- ❌ **NOT TESTED:** Circular dependencies in templates, menus, cascades

#### Code Areas
- **`bengal/rendering/template_engine.py`** - Jinja2 template loading
  - No cycle detection for includes/extends
  - Jinja2 may detect some cycles, but not all

- **`bengal/core/menu.py`** - Menu hierarchy
  - No cycle detection in parent references

- **`bengal/orchestration/content.py`** - Cascade application
  - Lines ~400+: `apply_cascades()`
  - No cycle detection in cascade inheritance

- **`bengal/cache/dependency_tracker.py:20-40`** - Dependency graph
  - `add_dependency()` doesn't check for cycles

#### Specific Gaps
```python
# NOT TESTED:
1. Template A includes Template B, which includes Template A
2. Template extends itself (base.html extends base.html)
3. Menu entry points to parent menu (navigation loop)
4. Page cascade references create cycle
5. Cross-reference loops (Page A → Page B → Page C → Page A)
6. Section parent loop (section references ancestor as child)
```

#### Test Plan

**A. Template Circular Dependencies** (`tests/unit/rendering/test_template_cycles.py`)

```python
import pytest
from pathlib import Path
from bengal.rendering.template_engine import TemplateEngine
from jinja2.exceptions import TemplateError

class TestTemplateCircularDependencies:
    """Test detection of circular template includes/extends."""

    def test_direct_self_include(self, tmp_path):
        """Template including itself should be detected."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create self-referencing template
        (templates_dir / "loop.html").write_text("{% include 'loop.html' %}")

        engine = TemplateEngine(templates_dir)

        # Should detect cycle (Jinja2 may handle this)
        with pytest.raises(TemplateError, match="recursion"):
            template = engine.env.get_template("loop.html")
            template.render()

    def test_indirect_include_cycle(self, tmp_path):
        """A → B → A include cycle should be detected."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        (templates_dir / "a.html").write_text("{% include 'b.html' %}")
        (templates_dir / "b.html").write_text("{% include 'a.html' %}")

        engine = TemplateEngine(templates_dir)

        with pytest.raises(TemplateError, match="recursion"):
            template = engine.env.get_template("a.html")
            template.render()

    def test_three_way_cycle(self, tmp_path):
        """A → B → C → A cycle should be detected."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        (templates_dir / "a.html").write_text("{% include 'b.html' %}")
        (templates_dir / "b.html").write_text("{% include 'c.html' %}")
        (templates_dir / "c.html").write_text("{% include 'a.html' %}")

        engine = TemplateEngine(templates_dir)

        with pytest.raises(TemplateError):
            template = engine.env.get_template("a.html")
            template.render()

    def test_extends_cycle(self, tmp_path):
        """Template extending itself should be detected."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        (templates_dir / "base.html").write_text("{% extends 'base.html' %}")

        engine = TemplateEngine(templates_dir)

        with pytest.raises(TemplateError):
            template = engine.env.get_template("base.html")
            template.render()

    def test_valid_deep_nesting_not_flagged(self, tmp_path):
        """Deep but valid nesting should work."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create 10-level deep nesting (no cycle)
        for i in range(10):
            next_file = f"level{i+1}.html" if i < 9 else "'END'"
            (templates_dir / f"level{i}.html").write_text(f"{{% include {next_file} %}}")

        (templates_dir / "level9.html").write_text("END")

        engine = TemplateEngine(templates_dir)
        template = engine.env.get_template("level0.html")

        # Should render successfully
        output = template.render()
        assert "END" in output


class TestDependencyGraphCycles:
    """Test cycle detection in dependency graph."""

    def test_detect_template_dependency_cycle(self):
        """Dependency tracker should detect cycles."""
        from bengal.cache.dependency_tracker import DependencyTracker

        tracker = DependencyTracker()

        # Build cycle: page1 → tmpl_a → tmpl_b → tmpl_a
        tracker.add_dependency("page1.md", "tmpl_a.html")
        tracker.add_dependency("tmpl_a.html", "tmpl_b.html")

        # This should detect cycle (if we add cycle detection)
        # Currently, this is NOT implemented
        with pytest.raises(ValueError, match="[Cc]ircular"):
            tracker.add_dependency("tmpl_b.html", "tmpl_a.html")
```

**B. Menu Circular Dependencies** (`tests/unit/core/test_menu_cycles.py`)

```python
import pytest
from bengal.core.menu import Menu, MenuItem

class TestMenuCircularDependencies:
    """Test cycle detection in menu hierarchies."""

    def test_menu_self_reference(self):
        """Menu item pointing to itself should be detected."""
        menu = Menu("main")
        item = MenuItem(name="Self", url="/self")

        # Attempt to add item as its own child
        item.children.append(item)

        # Cycle detection should prevent this
        # TODO: Implement in Menu.validate()
        with pytest.raises(ValueError, match="[Cc]ircular"):
            menu.validate()

    def test_menu_parent_child_cycle(self):
        """Parent-child cycle should be detected."""
        parent = MenuItem(name="Parent", url="/parent")
        child = MenuItem(name="Child", url="/child")

        parent.children.append(child)
        child.children.append(parent)  # Cycle!

        menu = Menu("main")
        menu.items.append(parent)

        with pytest.raises(ValueError, match="[Cc]ircular"):
            menu.validate()
```

**C. Cascade Circular Dependencies** (`tests/unit/orchestration/test_cascade_cycles.py`)

```python
import pytest
from pathlib import Path
from bengal.orchestration.content import ContentOrchestrator

class TestCascadeCircularDependencies:
    """Test cycle detection in cascade inheritance."""

    def test_cascade_cycle_detection(self, tmp_path):
        """Cascade creating circular inheritance should be detected."""
        # Create sections with circular cascade references
        # Section A inherits from Section B
        # Section B inherits from Section A

        # TODO: Implement cascade cycle detection in ContentOrchestrator
        pass
```

**Implementation Steps:**
1. Add explicit cycle detection to `DependencyTracker.add_dependency()`
2. Add `Menu.validate()` method with cycle detection
3. Add cascade cycle detection to `apply_cascades()`
4. Add all tests above
5. Document cycle detection in architecture docs

**Success Metrics:**
- ✅ All template cycles detected before infinite loop
- ✅ Menu cycles detected during build
- ✅ Cascade cycles detected during application

---

### 3. Filesystem Edge Cases

**Priority:** 🟡 MEDIUM (Cross-Platform Compatibility)  
**Risk:** Silent failures on different OSes, permission errors

#### Current State
- ✅ Path normalization: `tests/_testing/normalize.py`
- ✅ Some edge cases: `tests/unit/utils/test_paths.py:294-355` (unicode, spaces)
- ❌ **NOT TESTED:** Symlinks, permissions, readonly filesystems

#### Code Areas
- **`bengal/discovery/content_discovery.py`** - File traversal
  - No symlink handling (line ~200+)
  - No permission error handling

- **`bengal/utils/paths.py`** - Path utilities
  - Works with Path objects, but no symlink resolution

- **All file I/O** - No systematic permission handling

#### Specific Gaps
```python
# NOT TESTED:
1. Symlinks in content directory
2. Circular symlinks (content/a → content/b → content/a)
3. Permission denied reading files
4. Permission denied writing to output
5. Readonly filesystem (Docker volumes)
6. Case-insensitive vs case-sensitive filesystems
7. Very deep nesting (100+ levels)
8. Windows MAX_PATH (260 chars)
9. UNC paths (\\server\share)
10. Network drives on Windows
```

#### Test Plan

**A. Symlink Handling** (`tests/unit/discovery/test_symlinks.py`)

```python
import os
import pytest
from pathlib import Path
from bengal.discovery.content_discovery import ContentDiscovery

@pytest.mark.skipif(os.name == "nt", reason="Symlink tests require Unix or admin on Windows")
class TestSymlinkHandling:
    """Test content discovery with symlinks."""

    def test_follow_symlink_to_file(self, tmp_path):
        """Symlink to content file should be discovered."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create real file
        real_file = tmp_path / "outside" / "page.md"
        real_file.parent.mkdir()
        real_file.write_text("---\ntitle: Page\n---\nContent")

        # Create symlink inside content dir
        symlink = content_dir / "linked.md"
        symlink.symlink_to(real_file)

        discovery = ContentDiscovery(content_dir)
        pages = discovery.discover_content()

        # Should discover symlink (or not? Policy decision)
        # Current behavior: probably follows symlinks
        assert len(pages) >= 0  # Document expected behavior

    def test_circular_symlink_detection(self, tmp_path):
        """Circular symlinks should be detected and skipped."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        dir_a = content_dir / "a"
        dir_b = content_dir / "b"
        dir_a.mkdir()
        dir_b.mkdir()

        # Create circular symlinks
        (dir_a / "link_to_b").symlink_to(dir_b)
        (dir_b / "link_to_a").symlink_to(dir_a)

        discovery = ContentDiscovery(content_dir)

        # Should not hang or crash
        with pytest.raises(RecursionError):
            pages = discovery.discover_content()

        # TODO: Add cycle detection to prevent RecursionError

    def test_broken_symlink_skipped(self, tmp_path):
        """Broken symlinks should be skipped with warning."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create broken symlink
        symlink = content_dir / "broken.md"
        symlink.symlink_to("/nonexistent/file.md")

        discovery = ContentDiscovery(content_dir)
        pages = discovery.discover_content()

        # Should skip broken symlink
        assert len(pages) == 0


**B. Permission Handling** (`tests/unit/discovery/test_permissions.py`)

```python
import os
import pytest
from pathlib import Path
from bengal.discovery.content_discovery import ContentDiscovery
from bengal.core.site import Site

@pytest.mark.skipif(os.name == "nt", reason="Unix permission tests")
class TestPermissionHandling:
    """Test handling of permission errors."""

    def test_unreadable_file_skipped(self, tmp_path):
        """File with no read permission should be skipped."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create file and remove read permission
        unreadable = content_dir / "secret.md"
        unreadable.write_text("---\ntitle: Secret\n---\nContent")
        unreadable.chmod(0o000)

        try:
            discovery = ContentDiscovery(content_dir)
            pages = discovery.discover_content()

            # Should skip unreadable file with warning
            assert len(pages) == 0
        finally:
            # Restore permissions for cleanup
            unreadable.chmod(0o644)

    def test_unwritable_output_dir_fails_gracefully(self, temp_site):
        """Build should fail gracefully if output dir is readonly."""
        output_dir = temp_site / "public"
        output_dir.mkdir()
        output_dir.chmod(0o444)  # Readonly

        try:
            site = Site.from_config(temp_site)

            with pytest.raises(PermissionError):
                site.build()
        finally:
            output_dir.chmod(0o755)

    def test_readonly_filesystem(self, tmp_path):
        """Build on readonly filesystem should fail early."""
        # This is hard to test without Docker or mount --bind,ro
        # Skip for now
        pass


**C. Path Length Limits** (`tests/unit/utils/test_path_limits.py`)

```python
import pytest
from pathlib import Path
from bengal.discovery.content_discovery import ContentDiscovery

class TestPathLengthLimits:
    """Test handling of very long paths."""

    def test_very_deep_nesting(self, tmp_path):
        """100-level deep nesting should work."""
        content_dir = tmp_path / "content"

        # Create 100-level deep directory
        deep_path = content_dir
        for i in range(100):
            deep_path = deep_path / f"level{i}"

        deep_path.mkdir(parents=True)

        # Create content file at bottom
        content_file = deep_path / "deep.md"
        content_file.write_text("---\ntitle: Deep\n---\nContent")

        discovery = ContentDiscovery(content_dir)
        pages = discovery.discover_content()

        assert len(pages) == 1

    @pytest.mark.skipif(os.name != "nt", reason="Windows MAX_PATH test")
    def test_windows_max_path_length(self, tmp_path):
        """Paths > 260 chars should fail gracefully on Windows."""
        # Windows MAX_PATH = 260 characters
        # Create path that exceeds limit

        long_name = "a" * 300
        long_path = tmp_path / long_name / "page.md"

        with pytest.raises(OSError, match="path too long"):
            long_path.parent.mkdir(parents=True)
```

**Implementation Steps:**
1. Add symlink policy to discovery (follow, ignore, or error)
2. Add permission error handling to all file I/O
3. Add path length validation
4. Add all tests above
5. Document filesystem requirements

**Success Metrics:**
- ✅ Symlinks handled according to documented policy
- ✅ Permission errors logged and handled gracefully
- ✅ Path limits respected with clear errors

---

### 4. Input Validation Fuzzing

**Priority:** 🟡 MEDIUM (Security & Robustness)  
**Risk:** XSS, crashes from malformed input

#### Current State
- ✅ Config validation: `bengal/config/validators.py`
- ✅ Some frontmatter parsing: `bengal/discovery/content_discovery.py:555-560`
- ❌ **NOT TESTED:** Malformed YAML/TOML, large inputs, special chars

#### Code Areas
- **`bengal/config/loader.py:100-165`** - Config loading
  - YAML/TOML parsing with `tomllib`, `pyyaml`
  - Lines 110, 145, 160: Debug logging on errors

- **`bengal/discovery/content_discovery.py:400-600`** - Frontmatter parsing
  - Line 555: YAML errors logged at debug level

- **`bengal/config/validators.py:72-120`** - Validation logic
  - Type checking, range validation

#### Specific Gaps
```python
# NOT TESTED:
1. YAML with tabs vs spaces (mixed indentation)
2. TOML with invalid Unicode
3. Frontmatter with 10MB description field
4. Binary data in frontmatter
5. Null bytes in paths
6. XSS attempts in title: "<script>alert(1)</script>"
7. SQL injection attempts in fields
8. Emoji in slugs/URLs
9. UTF-8 BOM in files
10. Mixed encodings (latin-1 frontmatter + UTF-8 content)
```

#### Test Plan

**A. Frontmatter Fuzzing** (`tests/unit/discovery/test_frontmatter_fuzzing.py`)

```python
import pytest
from hypothesis import given, strategies as st
from bengal.discovery.content_discovery import ContentDiscovery

class TestFrontmatterFuzzing:
    """Fuzz test frontmatter parsing."""

    def test_yaml_mixed_indentation(self, tmp_path):
        """YAML with mixed tabs/spaces should be handled."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create file with mixed indentation
        bad_yaml = """---
title: Test
tags:
\t- tag1  # Tab
  - tag2  # Spaces
---
Content"""

        file = content_dir / "bad.md"
        file.write_text(bad_yaml)

        discovery = ContentDiscovery(content_dir)
        pages = discovery.discover_content()

        # Should skip or handle gracefully
        assert len(pages) == 0 or pages[0].metadata.title == "Test"

    def test_frontmatter_with_xss_attempt(self, tmp_path):
        """XSS in frontmatter should be escaped in output."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        xss_yaml = """---
title: "<script>alert(1)</script>"
description: "<img src=x onerror=alert(1)>"
---
Content"""

        file = content_dir / "xss.md"
        file.write_text(xss_yaml)

        discovery = ContentDiscovery(content_dir)
        pages = discovery.discover_content()

        assert len(pages) == 1
        # Title should be stored as-is (escaping happens in rendering)
        assert "<script>" in pages[0].metadata.title

    def test_frontmatter_with_very_large_field(self, tmp_path):
        """10MB frontmatter field should be rejected or handled."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        large_description = "x" * (10 * 1024 * 1024)  # 10MB
        large_yaml = f"""---
title: Test
description: "{large_description}"
---
Content"""

        file = content_dir / "large.md"
        file.write_text(large_yaml)

        discovery = ContentDiscovery(content_dir)

        # Should handle gracefully (may skip or truncate)
        pages = discovery.discover_content()
        # Don't crash

    def test_frontmatter_with_null_bytes(self, tmp_path):
        """Null bytes in frontmatter should be rejected."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        file = content_dir / "null.md"
        file.write_bytes(b"---\ntitle: Test\x00Null\n---\nContent")

        discovery = ContentDiscovery(content_dir)
        pages = discovery.discover_content()

        # Should skip file with null bytes
        assert len(pages) == 0

    def test_utf8_bom_in_file(self, tmp_path):
        """UTF-8 BOM should be handled."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        file = content_dir / "bom.md"
        # UTF-8 BOM + content
        file.write_bytes(b"\xef\xbb\xbf---\ntitle: Test\n---\nContent")

        discovery = ContentDiscovery(content_dir)
        pages = discovery.discover_content()

        assert len(pages) == 1
        assert pages[0].metadata.title == "Test"

    @pytest.mark.hypothesis
    @given(st.text())
    def test_fuzz_frontmatter_values(self, tmp_path, fuzz_text):
        """Fuzz test arbitrary text in frontmatter fields."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        yaml_content = f"""---
title: {fuzz_text!r}
---
Content"""

        file = content_dir / "fuzz.md"
        file.write_text(yaml_content)

        discovery = ContentDiscovery(content_dir)

        # Should never crash
        try:
            pages = discovery.discover_content()
        except Exception as e:
            pytest.fail(f"Crashed on fuzz input: {e}")


**B. Config Fuzzing** (`tests/unit/config/test_config_fuzzing.py`)

```python
import pytest
from hypothesis import given, strategies as st
from bengal.config.validators import ConfigValidator

class TestConfigFuzzing:
    """Fuzz test config validation."""

    @given(st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.one_of(st.booleans(), st.integers(), st.text(), st.none())
    ))
    def test_fuzz_config_values(self, fuzz_config):
        """Fuzz test arbitrary config values."""
        validator = ConfigValidator()

        # Should never crash
        try:
            validated = validator.validate(fuzz_config)
        except Exception as e:
            # Validation errors are expected
            if "validation" not in str(e).lower():
                pytest.fail(f"Unexpected error: {e}")

    def test_config_with_extremely_long_strings(self):
        """Config with very long strings should be handled."""
        config = {
            "title": "x" * 1_000_000,  # 1MB title
            "baseurl": "http://" + "a" * 1000 + ".com",
        }

        validator = ConfigValidator()

        # Should validate or reject cleanly
        result = validator.validate(config)
```

**Implementation Steps:**
1. Add input size limits to config/frontmatter parsing
2. Add XSS prevention documentation (escaping in templates)
3. Add null byte filtering
4. Add UTF-8 BOM handling
5. Add all fuzzing tests above

**Success Metrics:**
- ✅ No crashes on malformed input
- ✅ XSS attempts documented and handled
- ✅ Input size limits enforced

---

### 5. Resource Leak Detection

**Priority:** 🟢 LOW (Dev Server Stability)  
**Risk:** Long-running dev server exhausts file descriptors or memory

#### Current State
- ✅ Logger cleanup: `tests/integration/test_logging_integration.py:366-384`
- ✅ Temp file cleanup: `tests/integration/test_resource_cleanup.py`
- ❌ **NOT TESTED:** File descriptor leaks, memory growth over time

#### Specific Gaps
```python
# NOT TESTED:
1. File descriptors left open after build
2. Memory growth over multiple incremental builds
3. Template engine cache growing unbounded
4. Parsed content cache memory usage
5. Thread pool not shutting down cleanly
6. WebSocket connections in dev server
```

#### Test Plan

**A. Resource Leak Tests** (`tests/integration/test_resource_leaks.py`)

```python
import pytest
import gc
import psutil
import os

class TestResourceLeaks:
    """Test for resource leaks over multiple builds."""

    def test_file_descriptors_not_leaking(self, temp_site):
        """File descriptors should not leak over multiple builds."""
        from bengal.core.site import Site

        # Get initial FD count
        process = psutil.Process(os.getpid())
        initial_fds = process.num_fds() if hasattr(process, 'num_fds') else 0

        # Run 100 builds
        for i in range(100):
            site = Site.from_config(temp_site)
            site.build(parallel=False, incremental=True)

        # Get final FD count
        final_fds = process.num_fds() if hasattr(process, 'num_fds') else 0

        # Should not have significant FD growth
        fd_growth = final_fds - initial_fds
        assert fd_growth < 10, f"File descriptor leak detected: {fd_growth} FDs leaked"

    def test_memory_not_leaking_incremental_builds(self, temp_site):
        """Memory should not grow over repeated incremental builds."""
        from bengal.core.site import Site

        # Get initial memory
        process = psutil.Process(os.getpid())
        initial_mem = process.memory_info().rss / 1024 / 1024  # MB

        # Run 50 incremental builds
        for i in range(50):
            site = Site.from_config(temp_site)
            site.build(parallel=False, incremental=True)
            gc.collect()  # Force garbage collection

        # Get final memory
        final_mem = process.memory_info().rss / 1024 / 1024  # MB

        # Allow 50MB growth max (caches are expected)
        mem_growth = final_mem - initial_mem
        assert mem_growth < 50, f"Memory leak detected: {mem_growth:.1f}MB growth"

    def test_template_cache_bounded(self, temp_site):
        """Template cache should have size limit."""
        from bengal.core.site import Site

        site = Site.from_config(temp_site)
        site.build()

        # Check template engine cache size
        # TODO: Access template_engine and check cache
        pass
```

**Implementation Steps:**
1. Add resource leak tests
2. Add template cache size limit
3. Add parsed content cache eviction policy
4. Monitor in CI (fail if leaks detected)

**Success Metrics:**
- ✅ Zero FD leaks over 100 builds
- ✅ Memory growth < 50MB over 50 builds

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1-2)
- ✅ Cache corruption tests
- ✅ Build interruption handling
- ✅ Circular dependency detection (templates, menus)
- ✅ Concurrent build tests

**Deliverables:**
- 50+ new tests
- Signal handling in build orchestrator
- Cycle detection in 3 areas

### Phase 2: Cross-Platform (Week 3-4)
- ✅ Symlink handling policy
- ✅ Permission error handling
- ✅ Path length validation
- ✅ Windows-specific tests (CI)

**Deliverables:**
- 30+ new tests
- Documented filesystem requirements
- Windows CI integration

### Phase 3: Input Validation (Week 5)
- ✅ Frontmatter fuzzing tests
- ✅ Config fuzzing tests
- ✅ Input size limits
- ✅ XSS prevention documentation

**Deliverables:**
- 20+ fuzz tests
- Input validation improvements
- Security documentation

### Phase 4: Resource Management (Week 6)
- ✅ Resource leak tests
- ✅ Cache size limits
- ✅ Memory profiling in CI

**Deliverables:**
- 10+ resource tests
- Bounded caches
- CI monitoring

---

## Success Criteria

### Test Coverage
- 🎯 **Overall:** 65% → 70%
- 🎯 **Critical path:** 75-100% → 80-100%
- 🎯 **New tests:** 110+ (50 + 30 + 20 + 10)
- 🎯 **Execution time:** Maintain ~40s (use markers)

### Bug Prevention
- ✅ Zero cache corruption in production
- ✅ Zero infinite loops from circular dependencies
- ✅ Graceful handling of all filesystem edge cases
- ✅ Zero crashes on malformed input

### Cross-Platform
- ✅ Windows CI passing all tests
- ✅ Symlink policy documented
- ✅ Permission handling documented

---

## Maintenance Plan

### Ongoing
1. **Add tests for new features** (before merge)
2. **Run full suite in CI** (including slow tests)
3. **Monitor coverage trends** (fail if < 65%)
4. **Profile test suite** monthly (keep < 60s)

### Quarterly
1. **Review test gaps** (architecture changes)
2. **Update fuzzing strategies** (new input types)
3. **Benchmark resource usage** (memory, FDs)

---

## References

### Current Testing Docs
- `TEST_COVERAGE.md` - Coverage report (65% overall, 2,661 tests)
- `tests/README.md` - Testing strategy and quick runs
- `architecture/testing.md` - Testing infrastructure

### Code Areas Referenced
- `bengal/cache/build_cache.py` - Cache persistence
- `bengal/orchestration/build.py` - Build pipeline
- `bengal/rendering/errors.py` - Template error handling
- `bengal/config/validators.py` - Config validation
- `bengal/discovery/content_discovery.py` - Content discovery
- `bengal/cache/dependency_tracker.py` - Dependency graph
- `bengal/core/menu.py` - Menu hierarchy

### External Resources
- Hypothesis documentation: https://hypothesis.readthedocs.io/
- pytest-xdist: https://pytest-xdist.readthedocs.io/
- psutil: https://psutil.readthedocs.io/

---

**Next Steps:**
1. Review this plan with team
2. Create GitHub issues for each phase
3. Start Phase 1 implementation
4. Update TEST_COVERAGE.md after each phase

**Plan Owner:** TBD  
**Last Updated:** 2025-10-20
