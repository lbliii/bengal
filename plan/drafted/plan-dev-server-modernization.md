# Plan: Dev Server Modernization

**RFC**: `rfc-dev-server-modernization.md`  
**Status**: Draft  
**Created**: 2024-12-18  
**Estimated Time**: 3 weeks (phased delivery)

---

## Summary

Modernize Bengal's dev server with process-isolated builds, `watchfiles` integration, pre/post build hooks, and configurable ignore patterns. Builds on existing free-threading detection and backend selection infrastructure.

---

## Tasks

### Phase 1: Foundation (Week 1)

#### Task 1.1: Add watchfiles as optional dependency

- **Files**: `pyproject.toml`
- **Action**: Add `watchfiles>=0.20` to optional dependencies under `[project.optional-dependencies]`
- **Commit**: `config: add watchfiles>=0.20 as optional dev-server dependency`

---

#### Task 1.2: Create IgnoreFilter class

- **Files**: `bengal/server/ignore_filter.py` (new)
- **Action**: Implement `IgnoreFilter` class with:
  - Glob pattern matching via `fnmatch`
  - Regex pattern matching via compiled patterns
  - Default directory ignores (`.git`, `node_modules`, etc.)
  - `from_config()` classmethod for config integration
  - `__call__` protocol for use as filter function
- **Commit**: `server: add IgnoreFilter class with glob and regex pattern support`

---

#### Task 1.3: Add ignore pattern config options

- **Files**: `bengal/config/schema.py`, `bengal/config/defaults.py`
- **Action**: Add `exclude_patterns` (list[str]) and `exclude_regex` (list[str]) to `[dev_server]` config section
- **Depends on**: Task 1.2
- **Commit**: `config: add exclude_patterns and exclude_regex options to dev_server section`

---

#### Task 1.4: Unit tests for IgnoreFilter

- **Files**: `tests/unit/server/test_ignore_filter.py` (new)
- **Action**: Test cases for:
  - Glob pattern matching (`*.pyc`, `**/__pycache__`)
  - Regex pattern matching (`.*\.min\.(js|css)$`)
  - Default directory ignores
  - Directory path matching
  - `from_config()` factory method
- **Depends on**: Task 1.2
- **Commit**: `tests(server): add unit tests for IgnoreFilter`

---

#### Task 1.5: Integrate IgnoreFilter into BuildHandler

- **Files**: `bengal/server/build_handler.py`
- **Action**:
  - Replace `_should_ignore_file()` with `IgnoreFilter` instance
  - Create filter from config in `__init__`
  - Maintain backward compatibility (existing behavior unchanged by default)
- **Depends on**: Task 1.2, Task 1.3
- **Commit**: `server(build_handler): adopt IgnoreFilter; deprecate _should_ignore_file`

---

### Phase 2: File Watcher (Week 2)

#### Task 2.1: Create file watcher protocol and implementations

- **Files**: `bengal/server/file_watcher.py` (new)
- **Action**: Implement:
  - `FileWatcher` protocol with async `watch()` method
  - `WatchfilesWatcher` - primary watcher using Rust-based watchfiles
  - `WatchdogWatcher` - fallback watcher using Python watchdog
  - `create_watcher()` factory with backend selection
  - Support `BENGAL_WATCH_BACKEND` env var (auto/watchfiles/watchdog)
- **Commit**: `server: add FileWatcher abstraction with watchfiles and watchdog backends`

---

#### Task 2.2: Unit tests for file watchers

- **Files**: `tests/unit/server/test_file_watcher.py` (new)
- **Action**: Test cases for:
  - WatchfilesWatcher availability detection
  - WatchdogWatcher fallback behavior
  - Backend selection via env var
  - Filter callback integration
  - Change debouncing (watchdog)
- **Depends on**: Task 2.1
- **Commit**: `tests(server): add unit tests for file watcher abstraction`

---

#### Task 2.3: Integration test for file watcher backends

- **Files**: `tests/integration/server/test_file_watcher_integration.py` (new)
- **Action**: Integration tests:
  - Detect file creation, modification, deletion
  - Verify ignore filter is applied
  - Test debouncing behavior
  - Measure detection latency
- **Depends on**: Task 2.1, Task 1.2
- **Commit**: `tests(server): add integration tests for file watcher backends`

---

### Phase 3: Build Hooks (Week 2)

#### Task 3.1: Implement build hooks module

- **Files**: `bengal/server/build_hooks.py` (new)
- **Action**: Implement `run_hooks()` function:
  - Execute list of shell commands via subprocess
  - Configurable timeout per command
  - Capture stdout/stderr for logging
  - Return success/failure status
  - Support pre_build and post_build hook types
- **Commit**: `server: add build_hooks module for pre/post build command execution`

---

#### Task 3.2: Add hook config options

- **Files**: `bengal/config/schema.py`, `bengal/config/defaults.py`
- **Action**: Add `pre_build` (list[str]) and `post_build` (list[str]) to `[dev_server]` config section with default empty lists
- **Depends on**: Task 3.1
- **Commit**: `config: add pre_build and post_build hooks to dev_server section`

---

#### Task 3.3: Unit tests for build hooks

- **Files**: `tests/unit/server/test_build_hooks.py` (new)
- **Action**: Test cases for:
  - Successful hook execution
  - Failed hook (non-zero exit code)
  - Hook timeout
  - Multiple hooks in sequence
  - Hook execution stops on first failure
- **Depends on**: Task 3.1
- **Commit**: `tests(server): add unit tests for build hooks`

---

#### Task 3.4: Integrate hooks into build cycle

- **Files**: `bengal/server/build_handler.py`
- **Action**:
  - Run pre_build hooks before build execution
  - Run post_build hooks after successful builds
  - Log hook execution status
  - Skip build if pre_build hook fails
- **Depends on**: Task 3.1, Task 3.2
- **Commit**: `server(build_handler): integrate pre/post build hooks into build cycle`

---

### Phase 4: Process Isolation (Week 3)

#### Task 4.1: Create build executor with process isolation

- **Files**: `bengal/server/build_executor.py` (new)
- **Action**: Implement:
  - `BuildRequest` dataclass (frozen, slots) - serializable build request
  - `BuildResult` dataclass (frozen, slots) - serializable build result
  - `_execute_build()` function for subprocess execution
  - `BuildExecutor` class wrapping ProcessPoolExecutor
  - Use `spawn` multiprocessing context for thread safety
- **Commit**: `server: add BuildExecutor with process-isolated build execution`

---

#### Task 4.2: Add free-threading aware executor selection

- **Files**: `bengal/server/build_executor.py`
- **Action**:
  - Detect free-threaded Python via `sys._is_gil_enabled()`
  - Use ThreadPoolExecutor when GIL is disabled (Python 3.14+)
  - Use ProcessPoolExecutor when GIL is enabled
  - Add `BENGAL_BUILD_EXECUTOR` env var override (thread/process/auto)
- **Depends on**: Task 4.1
- **Commit**: `server(build_executor): add free-threading detection for executor selection`

---

#### Task 4.3: Unit tests for build executor

- **Files**: `tests/unit/server/test_build_executor.py` (new)
- **Action**: Test cases for:
  - BuildRequest/BuildResult serialization
  - Successful build execution
  - Failed build error capture
  - Executor shutdown
  - Free-threading detection mock tests
- **Depends on**: Task 4.1, Task 4.2
- **Commit**: `tests(server): add unit tests for BuildExecutor`

---

#### Task 4.4: Integration test for process isolation resilience

- **Files**: `tests/integration/server/test_build_executor_resilience.py` (new)
- **Action**: Test cases for:
  - Build crash doesn't affect server process
  - Timeout handling for hanging builds
  - Multiple sequential builds in executor
  - Executor recovery after failed build
- **Depends on**: Task 4.1
- **Commit**: `tests(server): add resilience tests for process-isolated builds`

---

#### Task 4.5: Integrate BuildExecutor into dev server

- **Files**: `bengal/server/build_handler.py`, `bengal/server/dev_server.py`
- **Action**:
  - Replace direct build calls with BuildExecutor.submit()
  - Create executor in dev server startup
  - Shutdown executor in server cleanup
  - Maintain backward compatibility via config flag
- **Depends on**: Task 4.1, Task 4.2
- **Commit**: `server: integrate BuildExecutor for process-isolated builds`

---

### Phase 5: Feature Flag and Rollout

#### Task 5.1: Add feature flag for v2 dev server

- **Files**: `bengal/server/dev_server.py`
- **Action**:
  - Check `BENGAL_DEV_SERVER_V2` env var
  - When `=1`: Enable all new features (watchfiles, hooks, process isolation)
  - When `=0`: Use legacy code paths
  - Default: v2 enabled (after beta period)
- **Commit**: `server: add BENGAL_DEV_SERVER_V2 feature flag for gradual rollout`

---

#### Task 5.2: Documentation for new dev server features

- **Files**: `site/content/docs/dev-server/hooks.md` (new), `site/content/docs/dev-server/configuration.md` (update)
- **Action**:
  - Document pre_build and post_build hooks with examples
  - Document exclude_patterns and exclude_regex config
  - Document BENGAL_WATCH_BACKEND env var
  - Document BENGAL_BUILD_EXECUTOR env var
- **Depends on**: All previous tasks
- **Commit**: `docs: document dev server modernization features`

---

### Phase 6: Optional Middleware Refactor (Low Priority)

> **Note**: Only pursue if time permits after core features ship.

#### Task 6.1: Extract ResponseMiddleware from LiveReloadMixin

- **Files**: `bengal/server/middleware.py` (new)
- **Action**:
  - Create `ResponseMiddleware` class with transformer pipeline
  - Create `create_live_reload_transformer()` function
  - Create `create_cache_control_transformer()` function
  - Maintain backward compatibility (mixin still works)
- **Commit**: `server: extract ResponseMiddleware for reusable response transformation`

---

#### Task 6.2: Unit tests for middleware

- **Files**: `tests/unit/server/test_middleware.py` (new)
- **Action**: Test transformer composition and HTML injection
- **Depends on**: Task 6.1
- **Commit**: `tests(server): add unit tests for ResponseMiddleware`

---

### Phase 7: Validation

- [ ] All existing server tests pass
- [ ] New unit tests pass with >90% coverage on new code
- [ ] Integration tests verify resilience (crash recovery)
- [ ] Linter passes (`ruff check bengal/server/`)
- [ ] Type checking passes (`mypy bengal/server/`)
- [ ] Manual smoke test: `bengal site serve` works with watchfiles
- [ ] Manual smoke test: pre/post hooks execute correctly
- [ ] Performance: File detection latency <50ms with watchfiles

---

## File Summary

### New Files (8)

| File | Phase | Purpose |
|------|-------|---------|
| `bengal/server/ignore_filter.py` | 1 | Configurable ignore patterns |
| `bengal/server/file_watcher.py` | 2 | File watcher abstraction |
| `bengal/server/build_hooks.py` | 3 | Pre/post build hooks |
| `bengal/server/build_executor.py` | 4 | Process-isolated builds |
| `tests/unit/server/test_ignore_filter.py` | 1 | IgnoreFilter tests |
| `tests/unit/server/test_file_watcher.py` | 2 | File watcher tests |
| `tests/unit/server/test_build_hooks.py` | 3 | Build hooks tests |
| `tests/unit/server/test_build_executor.py` | 4 | Build executor tests |

### Modified Files (4)

| File | Phase | Changes |
|------|-------|---------|
| `pyproject.toml` | 1 | Add watchfiles dependency |
| `bengal/config/schema.py` | 1, 3 | Add dev_server config options |
| `bengal/server/build_handler.py` | 1, 3, 4 | Integrate new components |
| `bengal/server/dev_server.py` | 4, 5 | Feature flag, executor lifecycle |

---

## Rollout Strategy

1. **Alpha** (Week 1): `BENGAL_DEV_SERVER_V2=1` enables new features
2. **Beta** (Week 2-3): Default enabled, `BENGAL_DEV_SERVER_V2=0` disables
3. **GA** (Week 4): Remove feature flag, document in changelog

---

## Dependencies

| Package | Version | Optional | Fallback |
|---------|---------|----------|----------|
| watchfiles | >=0.20 | Yes | watchdog |

---

## Changelog Entry

```markdown
### Dev Server Modernization

- **Process-isolated builds**: Builds now run in subprocess for resilience; a crash won't take down the server
- **watchfiles integration**: Rust-based file watcher for 10-50x faster change detection on large codebases
- **Pre/post build hooks**: Run custom commands before/after builds via `pre_build` and `post_build` config
- **Configurable ignore patterns**: New `exclude_patterns` (glob) and `exclude_regex` config options
- **Free-threading support**: Automatically uses threads instead of processes on Python 3.14+ with GIL disabled
```
