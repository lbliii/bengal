# RFC — Close Test Coverage Gaps and Harden Build Resilience

Status: Draft

Owner: TBD

Last updated: 2025-10-20

## Motivation

We have a strong test suite but several high-risk areas remain under-tested or lack explicit behavior. This RFC validates the active coverage-gaps plan against the current codebase and proposes concrete test additions and minimal code changes to improve resilience without regressing performance.

## Summary of Findings (Plan vs Code/Tests)

### Build interruption and cache corruption

- Plan: Missing tests; save uses atomic writes; add signal handling and recovery tests.
- Code reality: `BuildCache.save` uses `AtomicFile` (atomic temp-write→rename). Loader tolerates JSON errors and version mismatches. No file locking; last-writer-wins. Orchestrator lacks SIGINT/SIGTERM handling.
- Tests today: Basic save/load, no corruption/interruption or concurrency tests.

### Circular dependencies (templates, menus, cascades)

- Templates: No explicit cycle detection; rely on Jinja2 recursion errors at render. No tests that assert friendly error surfacing for include/extends loops.
- Menus: Contrary to the plan’s assumption, cycle detection exists in `MenuBuilder._has_cycle()` and raises `ValueError`. Tests should assert this behavior.
- Cascades: Implemented via hierarchical filesystem sections (`CascadeEngine.apply`). The filesystem hierarchy cannot be cyclic; “cascade cycles” are not a realistic failure mode. Keep out of scope; instead add tests for deep hierarchies and override precedence.

### Filesystem edge cases (symlinks, permissions, read-only)

- Code reality: `ContentDiscovery` descends directories; no symlink policy; unreadable files bubble exceptions from `_create_page`→`read_text_file(on_error="raise")` and can fail discovery. No cycle guard for directory symlinks.
- Tests today: None covering symlinks/permissions.

### Input validation fuzzing (front matter/configuration/encoding)

- Code reality: Robust file I/O helpers with encoding fallback; BOM not explicitly handled (uses `utf-8`, not `utf-8-sig`). Front matter YAML errors log at debug with content fallback; tolerant. The configuration validation logic exists; no input size limits.
- Tests today: Config loader/TemplateEngine tests exist; no fuzzing or front matter edge-case tests; no BOM test.

### Resource leak detection

- Code reality: No explicit leak checks; long-running server paths exist; build pipeline creates background managers; no tests for file descriptors/memory growth.
- Tests today: None for FD/memory leak trends.

## Proposed Changes

### A. Tests to add

1. Cache robustness and interruption

- Unit: `tests/unit/cache/test_cache_corruption.py`
  - Load truncated/invalid/empty JSON returns a fresh cache, no crash
  - Version downgrade tolerated (warns)
  - Fuzz binary data load never crashes
- Integration: `tests/integration/test_concurrent_builds.py`
  - Concurrent full builds last-writer-wins; cache remains valid
  - Concurrent incremental builds do not crash or corrupt cache
- Integration: `tests/integration/test_build_interrupt.py` (POSIX only)
  - SIGINT during build: process exits cleanly; if present, the cache file loads

2. Templates and menus

- Unit: `tests/unit/rendering/test_template_cycles.py`
  - Include/extends self and indirect cycles raise Jinja2 `TemplateError`; deep non-cyclic nesting renders
- Unit: `tests/unit/core/test_menu_cycles.py`
  - `MenuBuilder.build_hierarchy()` raises on cycles; valid trees pass

3. Filesystem behavior

- Unit: `tests/unit/discovery/test_symlinks.py`
  - Symlink to file respected per policy; circular directory symlinks do not loop indefinitely
- Unit: `tests/unit/discovery/test_permissions.py` (Unix only)
  - Skip unreadable files with a warning; read-only output produces a clear error
- Unit: `tests/unit/utils/test_path_limits.py`
  - Deep nesting handled; Windows MAX_PATH guarded (skipped elsewhere)

4. Input validation and encoding

- Unit: `tests/unit/discovery/test_frontmatter_fuzzing.py`
  - Mixed tabs/spaces YAML tolerated or skipped
  - XSS-like strings flow through metadata (escaping is a render concern)
  - Large front matter fields do not crash; configurable limit enforced (see B.2)
  - Null bytes and random text fuzz do not crash discovery
  - UTF-8 BOM at file start handled (see B.1)
- Unit: `tests/unit/config/test_config_fuzzing.py`
  - Randomized dictionaries check without crashing; long strings handled or rejected cleanly

5. Resource leaks (opt-in/slow)

- Integration: `tests/integration/test_resource_leaks.py` (marked slow, optional `psutil`)
  - Repeated incremental builds do not leak file descriptors or unbounded memory

### B. Minimal code changes

1. BOM handling in text reads

- Update `bengal.utils.file_io.read_text_file` to try `utf-8-sig` before `utf-8` when primary decode fails, or proactively strip `\ufeff` if present. This change makes front matter detection resilient to BOM.

2. Input size limits

- Add soft limits for front matter/configuration value sizes (for example, 1–5 MB per scalar field) and total front matter size (for example, 2–10 MB) with clear warnings and a safe fallback, configurable under `[build] input_limits`.

3. Content discovery resilience

- Add symlink policy to `ContentDiscovery` (default: follow files, do not follow directories; configurable). Add a visited-path guard (inode/realpath set) to break cycles if directory symlink traversal is enabled.
- On permission errors while reading/walking, log a warning and skip the file or directory instead of aborting discovery.

4. Build interruption hygiene (orchestrator)

- Install SIGINT/SIGTERM handlers that (a) close live progress cleanly, (b) avoid writing partial non-atomic outputs mid-phase, and (c) skip the final cache save if a prior critical phase failed. Cache writes are already atomic; the main goal is graceful shutdown and consistent logs.

5. Optional cache write advisory locking (deferred)

- Given `AtomicFile` last-writer-wins safety, file locking is optional. If needed for CI determinism, consider an `fcntl`/`msvcrt`-based advisory lock wrapper around cache save/load (config flag gated), but start without it.

### C. Acceptance criteria

- Cache load never crashes on malformed or partial files; tests confirm truncated/invalid/empty/fuzz cases.
- Concurrent builds do not corrupt the cache; tests pass consistently on Linux/macOS CI.
- Template include/extends cycles surface as clear errors; deep valid nests render.
- Menus defend against cycles; tests confirm existing behavior.
- Discovery handles BOM, unreadable files, and symlink edge cases per policy; tests validate behavior.
- Fuzzing reveals no crashes; the suite enforces size limits with clear logs.
- Leak tests show <10 FD delta after 100 builds and <50 MB RSS growth after 50 incremental builds (guard-railed and marked slow).

## Rollout plan

Phase 1 (Critical)

- Add cache corruption tests; template/menu cycle tests; concurrent build tests.
- Add BOM handling in `file_io`; permission-skip in discovery.

Phase 2 (Cross-Platform)

- Add symlink policy + visited guard; add symlink/permission tests.

Phase 3 (Inputs)

- Add input size limits + fuzz tests for front matter/config.

Phase 4 (Stability)

- Add signal handling in orchestrator; add resource leak tests (opt-in/slow).

## Risks and mitigations

- Performance regressions from added guards: keep checks O(1) and use configuration flags for infrequently used features (for example, directory symlink traversal).
- Flaky concurrency tests: restrict to thread-based concurrency; keep deterministic assertions (existence/validity vs exact content).
- Platform differences (Windows symlinks/permissions): mark with `skipif` and add Windows CI later.

## Appendix — Key Code References

```143:193:bengal/cache/build_cache.py
def save(self, cache_path: Path) -> None:
    # ... uses AtomicFile for atomic write; logs on failure
```

```160:185:bengal/utils/atomic_write.py
class AtomicFile:
    def __exit__(self, exc_type, *args):
        if exc_type is not None:
            self.tmp_path.unlink(missing_ok=True)
            return False
        self.tmp_path.replace(self.path)
        return False
```

```94:141:bengal/cache/dependency_tracker.py
def track_template(self, template_path: Path) -> None:
    if not hasattr(self.current_page, "value"):
        return
    self.cache.add_dependency(self.current_page.value, template_path)
```

```183:191:bengal/core/menu.py
# Detect cycles in built menu tree
if self._has_cycle(root, visited, set()):
    raise ValueError("Menu has circular reference...")
```

```121:136:bengal/rendering/template_engine.py
env_kwargs = {
  "loader": FileSystemLoader(template_dirs),
  "autoescape": select_autoescape(["html", "xml"]),
  # StrictUndefined optional; no explicit cycle detection
}
env = Environment(**env_kwargs)
```

```525:596:bengal/discovery/content_discovery.py
file_content = read_text_file(file_path, fallback_encoding="latin-1", on_error="raise")
# YAML errors downgraded; no BOM strip; unreadable files raise
```
