# RFC: Dev Server Modernization

**Status**: Draft  
**Created**: 2024-12-18  
**Author**: AI Assistant  
**Confidence**: 85% 🟢

---

## Executive Summary

Modernize Bengal's dev server by adopting best practices from sphinx-autobuild while leveraging Python 3.14's free-threaded execution (PEP 703) and modern async patterns. Key improvements: process-isolated builds for resilience, `watchfiles` for faster file watching, pre/post build hooks, and regex ignore patterns.

---

## Problem Statement

Bengal's dev server works well but has architectural limitations discovered through comparison with sphinx-autobuild:

1. **Build crashes can affect server** - Builds run in shared thread pool; a catastrophic failure could leave server in bad state
2. **watchdog limitations** - Python-based file watcher is slower than Rust alternatives on large codebases
3. **No build hooks** - Users can't run custom commands before/after builds
4. **Limited ignore patterns** - Only glob patterns; no regex support
5. **Tight coupling** - Script injection is mixed into request handler rather than composable middleware

---

## Goals

1. **Resilience**: Builds should never crash the server
2. **Performance**: Faster file watching on large codebases
3. **Extensibility**: Pre/post build hooks for custom workflows
4. **Flexibility**: Regex-based ignore patterns
5. **Maintainability**: Cleaner separation of concerns
6. **Python 3.14**: Leverage free-threading where beneficial

## Non-Goals

- Full ASGI migration (too disruptive; separate RFC)
- WebSocket instead of SSE (SSE works well, simpler)
- Replacing the HTTP server (stdlib works fine for dev)

---

## Design Options

### Option A: Incremental Improvements (Recommended)

Adopt sphinx-autobuild's best ideas incrementally without major architectural changes.

**Components**:
1. Process-isolated builds via `concurrent.futures.ProcessPoolExecutor`
2. `watchfiles` as primary watcher (with watchdog fallback)
3. Pre/post build hooks via config
4. Regex ignore patterns
5. Middleware-style script injection (internal refactor)

**Pros**:
- Low risk, incremental delivery
- Can ship improvements independently
- Maintains backward compatibility

**Cons**:
- Doesn't fully modernize architecture
- Some technical debt remains

### Option B: Full Async Rewrite

Migrate to ASGI (Starlette + uvicorn) like sphinx-autobuild.

**Pros**:
- Modern async throughout
- Better WebSocket support if needed later
- Cleaner middleware patterns

**Cons**:
- Large breaking change
- New dependencies (uvicorn, starlette)
- Overkill for a dev server

### Option C: Python 3.14 Free-Threading Focus

Leverage PEP 703 (free-threaded Python) to simplify threading model.

**Pros**:
- No GIL means ThreadPoolExecutor is as good as ProcessPoolExecutor
- Simpler code (no process pickling issues)
- Future-proof

**Cons**:
- Requires Python 3.14+ (we already target this)
- Free-threading is experimental in 3.13, stable in 3.14

---

## Recommendation: Option A + C Hybrid

Adopt Option A's improvements while designing for Option C's free-threading benefits.

**Rationale**:
- Process isolation provides immediate resilience (works without free-threading)
- When free-threading matures, can simplify back to threads
- `watchfiles` and hooks are independent wins
- Incremental delivery reduces risk

---

## Detailed Design

### 1. Process-Isolated Builds

**Current**: Builds run in `ThreadPoolExecutor` sharing GIL with server.

**Proposed**: Use `ProcessPoolExecutor` for build execution.

```python
# bengal/server/build_executor.py (new file)
"""Process-isolated build execution for resilience."""

from __future__ import annotations

import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site

# Use spawn to avoid fork issues with threads
mp_context = multiprocessing.get_context("spawn")


@dataclass(frozen=True, slots=True)
class BuildRequest:
    """Serializable build request for cross-process execution."""
    
    site_root: Path
    changed_paths: tuple[Path, ...]
    incremental: bool = True
    profile: str = "WRITER"


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Serializable build result from subprocess."""
    
    success: bool
    pages_built: int
    build_time_ms: float
    error_message: str | None = None


def _execute_build(request: BuildRequest) -> BuildResult:
    """Execute build in subprocess (picklable function)."""
    try:
        from bengal.core.site import Site
        from bengal.utils.profile import BuildProfile
        
        site = Site.from_config(request.site_root)
        site.dev_mode = True
        
        profile = getattr(BuildProfile, request.profile)
        stats = site.build(profile=profile, incremental=request.incremental)
        
        return BuildResult(
            success=True,
            pages_built=stats.total_pages,
            build_time_ms=stats.build_time_ms,
        )
    except Exception as e:
        return BuildResult(
            success=False,
            pages_built=0,
            build_time_ms=0,
            error_message=str(e),
        )


class BuildExecutor:
    """Manages process-isolated build execution."""
    
    def __init__(self, max_workers: int = 1):
        self._executor = ProcessPoolExecutor(
            max_workers=max_workers,
            mp_context=mp_context,
        )
    
    def submit(self, request: BuildRequest) -> BuildResult:
        """Submit build request and wait for result."""
        future = self._executor.submit(_execute_build, request)
        return future.result()
    
    def shutdown(self) -> None:
        """Shutdown executor gracefully."""
        self._executor.shutdown(wait=True)
```

**Python 3.14 Consideration**: With free-threading (PEP 703), we could add a config option to use `ThreadPoolExecutor` instead when `sys._is_gil_enabled() == False`, avoiding subprocess overhead.

```python
import sys

def _get_executor_class():
    """Choose executor based on GIL status."""
    if hasattr(sys, '_is_gil_enabled') and not sys._is_gil_enabled():
        # Python 3.14+ with free-threading: threads are truly parallel
        from concurrent.futures import ThreadPoolExecutor
        return ThreadPoolExecutor
    else:
        # GIL-enabled: use processes for true parallelism
        from concurrent.futures import ProcessPoolExecutor
        return ProcessPoolExecutor
```

### 2. watchfiles Integration

**Current**: Uses `watchdog` with manual backend selection.

**Proposed**: Use `watchfiles` (Rust-based) as primary, with `watchdog` fallback.

```python
# bengal/server/file_watcher.py (new file)
"""Modern file watching with watchfiles and watchdog fallback."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Protocol


class FileWatcher(Protocol):
    """Protocol for file watchers."""
    
    async def watch(self) -> AsyncIterator[set[Path]]:
        """Yield sets of changed paths."""
        ...


class WatchfilesWatcher:
    """Primary watcher using Rust-based watchfiles."""
    
    def __init__(
        self,
        paths: list[Path],
        ignore_filter: Callable[[Path], bool],
    ):
        self.paths = paths
        self.ignore_filter = ignore_filter
    
    async def watch(self) -> AsyncIterator[set[Path]]:
        import watchfiles
        
        async for changes in watchfiles.awatch(
            *self.paths,
            watch_filter=lambda _, path: not self.ignore_filter(Path(path)),
        ):
            yield {Path(path) for (_, path) in changes}


class WatchdogWatcher:
    """Fallback watcher using Python-based watchdog."""
    
    def __init__(
        self,
        paths: list[Path],
        ignore_filter: Callable[[Path], bool],
        debounce_ms: int = 100,
    ):
        self.paths = paths
        self.ignore_filter = ignore_filter
        self.debounce_ms = debounce_ms
        self._changes: set[Path] = set()
        self._event = asyncio.Event()
    
    async def watch(self) -> AsyncIterator[set[Path]]:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
        
        handler = self._create_handler()
        observer = Observer()
        
        for path in self.paths:
            observer.schedule(handler, str(path), recursive=True)
        
        observer.start()
        try:
            while True:
                await self._event.wait()
                await asyncio.sleep(self.debounce_ms / 1000)
                
                changes = self._changes.copy()
                self._changes.clear()
                self._event.clear()
                
                if changes:
                    yield changes
        finally:
            observer.stop()
            observer.join()
    
    def _create_handler(self) -> FileSystemEventHandler:
        watcher = self
        
        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                path = Path(event.src_path)
                if not watcher.ignore_filter(path):
                    watcher._changes.add(path)
                    watcher._event.set()
        
        return Handler()


def create_watcher(
    paths: list[Path],
    ignore_filter: Callable[[Path], bool],
    backend: str = "auto",
) -> FileWatcher:
    """Create appropriate file watcher based on backend preference."""
    backend = os.environ.get("BENGAL_WATCH_BACKEND", backend).lower()
    
    if backend == "watchdog":
        return WatchdogWatcher(paths, ignore_filter)
    
    if backend == "watchfiles" or backend == "auto":
        try:
            import watchfiles  # noqa: F401
            return WatchfilesWatcher(paths, ignore_filter)
        except ImportError:
            if backend == "watchfiles":
                raise ImportError(
                    "watchfiles not installed. Install with: pip install watchfiles"
                )
    
    # Fallback to watchdog
    return WatchdogWatcher(paths, ignore_filter)
```

**Dependency**: Add `watchfiles>=0.20` as optional dependency in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev-server = ["watchfiles>=0.20"]
```

### 3. Pre/Post Build Hooks

**Current**: No hook support.

**Proposed**: Config-driven hooks with subprocess execution.

```yaml
# bengal.toml
[dev_server]
pre_build = [
    "npm run build:css",
    "python scripts/generate_api_spec.py",
]
post_build = [
    "echo 'Build complete!'",
]
```

```python
# bengal/server/build_hooks.py (new file)
"""Pre and post build hook execution."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def run_hooks(
    hooks: list[str],
    hook_type: str,
    cwd: Path,
    *,
    timeout: float = 60.0,
) -> bool:
    """
    Run a list of shell commands as hooks.
    
    Args:
        hooks: List of shell commands to run
        hook_type: 'pre_build' or 'post_build' for logging
        cwd: Working directory for commands
        timeout: Maximum time per command in seconds
    
    Returns:
        True if all hooks succeeded, False otherwise
    """
    for command in hooks:
        logger.info(f"{hook_type}_hook_running", command=command)
        
        try:
            # Use shell=True for command string, or parse for safety
            args = shlex.split(command)
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            if result.returncode != 0:
                logger.error(
                    f"{hook_type}_hook_failed",
                    command=command,
                    returncode=result.returncode,
                    stderr=result.stderr[:500] if result.stderr else None,
                )
                return False
            
            logger.debug(
                f"{hook_type}_hook_success",
                command=command,
                stdout_lines=len(result.stdout.splitlines()) if result.stdout else 0,
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"{hook_type}_hook_timeout", command=command, timeout=timeout)
            return False
        except Exception as e:
            logger.error(f"{hook_type}_hook_error", command=command, error=str(e))
            return False
    
    return True
```

### 4. Regex Ignore Patterns

**Current**: Only glob patterns via `exclude_patterns` config.

**Proposed**: Add `exclude_regex` config option.

```yaml
# bengal.toml
[dev_server]
# Existing glob patterns
exclude_patterns = ["*.pyc", "__pycache__"]

# New regex patterns
exclude_regex = [
    ".*\\.min\\.(js|css)$",      # Minified files
    "/node_modules/",             # Node modules anywhere
    "/\\..*",                     # Hidden directories
]
```

```python
# bengal/server/ignore_filter.py (new file)
"""Flexible ignore filtering with glob and regex patterns."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path


class IgnoreFilter:
    """Filter for determining which paths to ignore during file watching."""
    
    def __init__(
        self,
        glob_patterns: list[str] | None = None,
        regex_patterns: list[str] | None = None,
        directories: list[Path] | None = None,
    ):
        """
        Initialize ignore filter.
        
        Args:
            glob_patterns: Glob patterns (e.g., "*.pyc", "**/__pycache__")
            regex_patterns: Regex patterns (e.g., r".*\.min\.(js|css)$")
            directories: Directories to always ignore
        """
        self.glob_patterns = list(glob_patterns or [])
        self.regex_patterns = [re.compile(p) for p in (regex_patterns or [])]
        self.directories = [p.resolve() for p in (directories or [])]
        
        # Default ignores (always applied)
        self._default_dirs = {
            ".git", ".hg", ".svn",
            ".venv", "venv", ".env",
            "__pycache__", ".pytest_cache", ".mypy_cache",
            "node_modules", ".nox", ".tox",
            ".idea", ".vscode",
        }
    
    def __call__(self, path: Path) -> bool:
        """Return True if path should be ignored."""
        path = path.resolve()
        path_str = path.as_posix()
        
        # Check default directory names in path
        for part in path.parts:
            if part in self._default_dirs:
                return True
        
        # Check explicit directories
        for ignored_dir in self.directories:
            try:
                path.relative_to(ignored_dir)
                return True
            except ValueError:
                pass
        
        # Check glob patterns
        for pattern in self.glob_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if fnmatch.fnmatch(path.name, pattern):
                return True
        
        # Check regex patterns
        for regex in self.regex_patterns:
            if regex.search(path_str):
                return True
        
        return False
    
    @classmethod
    def from_config(cls, config: dict, output_dir: Path) -> "IgnoreFilter":
        """Create IgnoreFilter from bengal.toml config."""
        dev_server = config.get("dev_server", {})
        
        return cls(
            glob_patterns=dev_server.get("exclude_patterns", []),
            regex_patterns=dev_server.get("exclude_regex", []),
            directories=[output_dir],
        )
```

### 5. Middleware-Style Script Injection (Internal Refactor)

**Current**: `LiveReloadMixin` injects script in `do_GET`.

**Proposed**: Separate `ResponseMiddleware` class for cleaner composition.

```python
# bengal/server/middleware.py (new file)
"""Response middleware for script injection and header modification."""

from __future__ import annotations

import io
from typing import Callable


class ResponseMiddleware:
    """
    Middleware for modifying HTTP responses before sending.
    
    Supports:
    - Injecting scripts into HTML responses
    - Adding/modifying headers
    - Response transformation
    """
    
    def __init__(self):
        self._transformers: list[Callable[[bytes, dict], tuple[bytes, dict]]] = []
    
    def add_transformer(
        self,
        transformer: Callable[[bytes, dict], tuple[bytes, dict]],
    ) -> None:
        """Add a response transformer."""
        self._transformers.append(transformer)
    
    def transform(self, body: bytes, headers: dict) -> tuple[bytes, dict]:
        """Apply all transformers to response."""
        for transformer in self._transformers:
            body, headers = transformer(body, headers)
        return body, headers


def create_live_reload_transformer(script: bytes) -> Callable:
    """Create transformer that injects live reload script into HTML."""
    
    def transformer(body: bytes, headers: dict) -> tuple[bytes, dict]:
        content_type = headers.get("Content-Type", "")
        
        if not content_type.startswith("text/html"):
            return body, headers
        
        # Inject before </body> or at end
        if b"</body>" in body:
            body = body.replace(b"</body>", script + b"</body>")
        else:
            body = body + script
        
        # Update Content-Length
        if "Content-Length" in headers:
            headers["Content-Length"] = str(len(body))
        
        return body, headers
    
    return transformer


def create_cache_control_transformer() -> Callable:
    """Create transformer that adds no-cache headers."""
    
    def transformer(body: bytes, headers: dict) -> tuple[bytes, dict]:
        headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        headers["Pragma"] = "no-cache"
        headers["Expires"] = "0"
        return body, headers
    
    return transformer
```

---

## Migration Plan

### Phase 1: Foundation (Week 1)

1. Add `watchfiles` as optional dependency
2. Create `IgnoreFilter` with regex support
3. Add config options for `exclude_regex`
4. Tests for new ignore patterns

### Phase 2: File Watcher (Week 2)

1. Implement `WatchfilesWatcher` and `WatchdogWatcher`
2. Create `create_watcher()` factory with backend selection
3. Integrate into `BuildHandler`
4. Add `BENGAL_WATCH_BACKEND` env var

### Phase 3: Build Hooks (Week 2)

1. Implement `run_hooks()` function
2. Add config options for `pre_build` and `post_build`
3. Integrate into build cycle in `BuildHandler`
4. Documentation for hook usage

### Phase 4: Process Isolation (Week 3)

1. Implement `BuildExecutor` with `ProcessPoolExecutor`
2. Create serializable `BuildRequest` and `BuildResult`
3. Add Python 3.14 free-threading detection
4. Integration tests for process isolation

### Phase 5: Middleware Refactor (Week 3)

1. Extract `ResponseMiddleware` from `LiveReloadMixin`
2. Create transformer functions
3. Maintain backward compatibility with mixin
4. Internal refactor only (no user-facing changes)

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/server/test_ignore_filter.py
class TestIgnoreFilter:
    def test_glob_pattern_matches(self):
        f = IgnoreFilter(glob_patterns=["*.pyc"])
        assert f(Path("/project/foo.pyc")) is True
        assert f(Path("/project/foo.py")) is False
    
    def test_regex_pattern_matches(self):
        f = IgnoreFilter(regex_patterns=[r".*\.min\.(js|css)$"])
        assert f(Path("/project/app.min.js")) is True
        assert f(Path("/project/app.js")) is False
    
    def test_directory_matches(self):
        f = IgnoreFilter(directories=[Path("/project/dist")])
        assert f(Path("/project/dist/app.js")) is True
        assert f(Path("/project/src/app.js")) is False

# tests/unit/server/test_build_hooks.py
class TestBuildHooks:
    def test_successful_hook(self, tmp_path):
        result = run_hooks(["echo hello"], "pre_build", tmp_path)
        assert result is True
    
    def test_failed_hook(self, tmp_path):
        result = run_hooks(["false"], "pre_build", tmp_path)
        assert result is False
    
    def test_timeout_hook(self, tmp_path):
        result = run_hooks(["sleep 10"], "pre_build", tmp_path, timeout=0.1)
        assert result is False
```

### Integration Tests

```python
# tests/integration/test_dev_server_modernization.py
class TestWatchfilesIntegration:
    async def test_watchfiles_detects_changes(self, tmp_path):
        """Test that watchfiles correctly detects file changes."""
        ...

class TestProcessIsolation:
    def test_build_crash_doesnt_affect_server(self, tmp_path):
        """Test that a crashing build doesn't crash the server."""
        ...
```

---

## Rollout Plan

1. **Alpha** (1 week): Enable via feature flag `BENGAL_DEV_SERVER_V2=1`
2. **Beta** (2 weeks): Default on, disable via `BENGAL_DEV_SERVER_V2=0`
3. **GA** (after beta): Remove feature flag, document in changelog

---

## Dependencies

### New Dependencies

| Package | Version | Purpose | Optional |
|---------|---------|---------|----------|
| watchfiles | >=0.20 | Rust-based file watcher | Yes (falls back to watchdog) |

### Python Version

- Requires Python 3.14+ (already our target)
- Leverages `sys._is_gil_enabled()` for free-threading detection

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Process isolation overhead | Medium | Low | Only used for builds; <100ms overhead |
| watchfiles compatibility | Low | Medium | Watchdog fallback always available |
| Hook security concerns | Medium | High | Document risks; no shell=True; timeout |
| Free-threading instability | Low | Low | Detection-based; falls back to process |

---

## Open Questions

1. **Should hooks run in subprocess or current process?**
   - Subprocess: Isolation, but slower
   - Current process: Fast, but can affect server
   - **Recommendation**: Subprocess with short timeout

2. **Should we expose async watcher API?**
   - Would enable more advanced integrations
   - **Recommendation**: Internal only for now; expose later if needed

3. **Default ignore patterns - should they be configurable?**
   - Currently hardcoded (`.git`, `node_modules`, etc.)
   - **Recommendation**: Make them additive, not replaceable

---

## Success Metrics

- **Resilience**: 0 server crashes from build failures (currently: rare but possible)
- **Performance**: <50ms file change detection (watchfiles vs watchdog benchmark)
- **Adoption**: >50% of users use hooks within 6 months
- **Stability**: No regressions in existing behavior

---

## References

- [sphinx-autobuild source](https://github.com/sphinx-doc/sphinx-autobuild)
- [PEP 703 - Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [watchfiles documentation](https://watchfiles.helpmanual.io/)
- [Python 3.14 Release Schedule](https://peps.python.org/pep-0745/)

---

## Appendix: Python 3.14 Free-Threading

Python 3.14 introduces optional free-threading (no GIL) via PEP 703. This significantly impacts our design:

### Detection

```python
import sys

def is_free_threaded() -> bool:
    """Check if running on free-threaded Python."""
    return hasattr(sys, '_is_gil_enabled') and not sys._is_gil_enabled()
```

### Impact on This RFC

| Component | With GIL | Free-Threaded |
|-----------|----------|---------------|
| Build isolation | ProcessPoolExecutor | ThreadPoolExecutor |
| File watcher | Any | Any |
| Request handling | ThreadingTCPServer | ThreadingTCPServer (faster) |

The key benefit: With free-threading, we can use threads for true parallelism without the overhead of process spawning and pickling. This RFC designs for both modes.

---

**Confidence**: 85% 🟢
- Evidence: sphinx-autobuild patterns validated in production
- Consistency: Aligns with Bengal's existing architecture
- Recency: Python 3.14 features are current
- Tests: Comprehensive testing strategy defined

