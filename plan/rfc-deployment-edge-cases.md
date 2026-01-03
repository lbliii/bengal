# RFC: Deployment Robustness Edge Cases

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-01-03 |
| **Author** | Bengal Core Team |
| **Priority** | P2 (Medium) |
| **Related** | `bengal/health/validators/`, `bengal/discovery/`, `bengal/orchestration/build/` |
| **Confidence** | 85% 🟢 |

---

## Executive Summary

Following critical bugs in Bengal 0.1.6 (cache/output mismatch, assets in dotted paths), we conducted a comprehensive edge case audit of the build and deployment pipeline. While the critical issues have been fixed and new validators added (empty assets, GitHub Pages baseurl, case sensitivity), several **lower-priority edge cases** remain unaddressed.

This RFC documents these remaining edge cases and proposes solutions to make Bengal's deployment pipeline more robust across diverse environments (CI/CD platforms, different filesystems, concurrent workflows).

**Remaining Edge Cases**:
1. **Disk space exhaustion** — Build fails mid-write, corrupted output
2. **Concurrent builds** — Two builds writing to same output directory
3. **Symlinks in assets** — Potential loops or security issues
4. **Stale fingerprinted assets** — Disk bloat over time
5. **Output permission errors** — Can't write to output directory

**Estimated Effort**: 3-4 weeks

---

## Current State

### Already Implemented ✅

| Edge Case | Protection | Error Code |
|-----------|------------|------------|
| Cache/output mismatch | Force rebuild when output missing | — |
| Assets in dotted paths | Check relative path only for hidden files | — |
| No CSS files | ERROR (build fails) | H626 |
| Empty js/ directory | ERROR (build fails) | H627 |
| Empty CSS files (0-byte) | ERROR (build fails) | H628 |
| Empty JS files (0-byte) | ERROR (build fails) | H629 |
| GitHub Pages missing baseurl | WARNING | H012 |
| baseurl without leading `/` | WARNING | H013 |
| Case mismatch in asset URLs | WARNING | — |
| Symlink loops in content | Skip with warning | D012 |
| Stale output cleanup | Delete outputs for removed sources | — |
| Atomic writes | Temp file + rename | — |
| Filesystem retry | `rmtree_robust()` with retries | — |

### Remaining Gaps ⚠️

| Edge Case | Risk | Impact | Frequency |
|-----------|------|--------|-----------|
| Disk space exhaustion | Medium | Corrupted output, partial deploy | Rare |
| Concurrent builds | Medium | Race conditions, mixed outputs | Occasional |
| Symlinks in assets | Low | Security bypass, infinite loops | Rare |
| Stale fingerprinted assets | Low | Disk bloat, confusion | Common |
| Output permission errors | Medium | Build fails silently | Occasional |

---

## Proposed Solutions

### Solution 1: Disk Space Pre-Check

**Problem**: Build can fail mid-write if disk runs out of space, leaving corrupted output.

**Approach**: Estimate required space before build, warn if insufficient.

**Implementation**:

```python
# bengal/health/validators/system.py

class SystemResourceValidator(BaseValidator):
    """Validates system resources before build."""

    name = "System Resources"
    description = "Checks disk space and system resources"
    enabled_by_default = True

    # Minimum free space for safety margin
    MIN_FREE_SPACE_MB = 100

    @override
    def validate(self, site: Site, build_context: Any = None) -> list[CheckResult]:
        results = []

        # Estimate required space
        estimated_mb = self._estimate_output_size(site)

        # Check available space
        output_dir = site.output_dir
        try:
            import shutil
            total, used, free = shutil.disk_usage(output_dir.parent)
            free_mb = free / (1024 * 1024)

            if free_mb < estimated_mb + self.MIN_FREE_SPACE_MB:
                results.append(
                    CheckResult.error(
                        f"Insufficient disk space: {free_mb:.0f} MB free, "
                        f"~{estimated_mb:.0f} MB needed",
                        code="H700",
                        recommendation=(
                            "Free up disk space or reduce asset sizes.\n"
                            f"  Available: {free_mb:.0f} MB\n"
                            f"  Estimated needed: {estimated_mb:.0f} MB + {self.MIN_FREE_SPACE_MB} MB safety margin"
                        ),
                    )
                )
            elif free_mb < estimated_mb * 2:
                results.append(
                    CheckResult.warning(
                        f"Low disk space: {free_mb:.0f} MB free",
                        code="H701",
                        recommendation="Consider freeing disk space before build.",
                    )
                )
        except OSError as e:
            results.append(
                CheckResult.warning(
                    f"Could not check disk space: {e}",
                    code="H702",
                    recommendation="Ensure output directory is accessible.",
                )
            )

        return results

    def _estimate_output_size(self, site: Site) -> float:
        """Estimate output size in MB based on content and assets."""
        # Base estimate: ~50KB per page
        page_estimate = len(site.pages) * 50 / 1024

        # Asset size (if already discovered)
        asset_estimate = 0
        for asset in site.assets:
            try:
                asset_estimate += asset.source_path.stat().st_size / (1024 * 1024)
            except OSError:
                pass

        # Add 20% overhead for sitemap, RSS, JSON, etc.
        return (page_estimate + asset_estimate) * 1.2
```

**Integration**: Run as pre-build validator before content processing.

---

### Solution 2: Build Lock File

**Problem**: Two concurrent builds can write to the same output directory, causing race conditions and mixed outputs.

**Approach**: Use a lock file to prevent concurrent builds.

**Implementation**:

```python
# bengal/orchestration/build/lock.py

import os
import time
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LockInfo:
    """Information about the current lock holder."""
    pid: int
    hostname: str
    started: float
    command: str


class BuildLock:
    """
    Prevents concurrent builds to the same output directory.

    Uses a lock file with PID/hostname to detect stale locks.
    Lock is automatically released on process exit.
    """

    LOCK_FILENAME = ".bengal-build.lock"
    STALE_THRESHOLD_SECONDS = 3600  # 1 hour

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.lock_file = output_dir / self.LOCK_FILENAME
        self._held = False

    @contextmanager
    def acquire(self, timeout: float = 10.0) -> Generator[None, None, None]:
        """
        Acquire build lock with timeout.

        Args:
            timeout: Seconds to wait for lock (default 10s)

        Raises:
            BuildLockError: If lock cannot be acquired
        """
        start = time.time()

        while time.time() - start < timeout:
            if self._try_acquire():
                try:
                    yield
                finally:
                    self._release()
                return
            time.sleep(0.5)

        # Timeout - check if lock is stale
        if self._is_stale():
            logger.warning(
                "build_lock_stale",
                lock_file=str(self.lock_file),
                action="removing_stale_lock",
            )
            self._force_release()
            if self._try_acquire():
                try:
                    yield
                finally:
                    self._release()
                return

        # Cannot acquire
        lock_info = self._read_lock_info()
        raise BuildLockError(
            f"Another build is in progress (PID {lock_info.pid} on {lock_info.hostname}). "
            f"If this is stale, remove: {self.lock_file}"
        )

    def _try_acquire(self) -> bool:
        """Attempt to acquire lock atomically."""
        if self.lock_file.exists():
            return False

        try:
            # Atomic create with O_EXCL
            fd = os.open(
                str(self.lock_file),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )

            # Write lock info
            import socket
            import sys
            lock_info = {
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
                "started": time.time(),
                "command": " ".join(sys.argv),
            }
            os.write(fd, json.dumps(lock_info).encode())
            os.close(fd)

            self._held = True
            return True

        except FileExistsError:
            return False
        except OSError as e:
            logger.warning("build_lock_acquire_failed", error=str(e))
            return False

    def _release(self) -> None:
        """Release the lock."""
        if self._held:
            try:
                self.lock_file.unlink()
                self._held = False
            except OSError:
                pass

    def _force_release(self) -> None:
        """Force remove lock file (for stale locks)."""
        try:
            self.lock_file.unlink()
        except OSError:
            pass

    def _is_stale(self) -> bool:
        """Check if lock is stale (old or dead process)."""
        lock_info = self._read_lock_info()
        if not lock_info:
            return True

        # Check age
        age = time.time() - lock_info.started
        if age > self.STALE_THRESHOLD_SECONDS:
            return True

        # Check if process is still alive (same host only)
        import socket
        if lock_info.hostname == socket.gethostname():
            try:
                os.kill(lock_info.pid, 0)  # Check if process exists
                return False  # Process still running
            except OSError:
                return True  # Process dead

        # Different host - can't check process, use age only
        return False

    def _read_lock_info(self) -> LockInfo | None:
        """Read lock file info."""
        try:
            import json
            data = json.loads(self.lock_file.read_text())
            return LockInfo(**data)
        except (OSError, json.JSONDecodeError, TypeError):
            return None


class BuildLockError(Exception):
    """Raised when build lock cannot be acquired."""
    pass
```

**Integration**:

```python
# In bengal/orchestration/build/orchestrator.py

def build(self, ...):
    lock = BuildLock(self.site.output_dir)

    with lock.acquire(timeout=30.0):
        # ... existing build logic ...
```

**CLI Option**:

```bash
bengal build --no-lock  # Skip lock (for debugging)
bengal build --force-lock  # Remove stale lock and proceed
```

---

### Solution 3: Asset Symlink Handling

**Problem**: Assets directory may contain symlinks that could cause security issues (escape site root) or infinite loops.

**Approach**: Add symlink detection to `AssetDiscovery`, similar to content discovery.

**Implementation**:

```python
# bengal/discovery/asset_discovery.py (addition)

def discover(self, base_path: Path | None = None) -> list[Asset]:
    """Discover all static assets in the assets directory."""
    assets_dir = self.assets_dir if base_path is None else base_path
    if not assets_dir.exists():
        assets_dir.mkdir(parents=True, exist_ok=True)

    # Track inodes to detect symlink loops
    visited_inodes: set[int] = set()

    for file_path in self._walk_with_symlink_check(assets_dir, visited_inodes):
        # ... existing logic ...
        pass

def _walk_with_symlink_check(
    self,
    directory: Path,
    visited_inodes: set[int]
) -> Generator[Path, None, None]:
    """
    Walk directory with symlink loop detection.

    Security: Rejects symlinks that point outside the assets directory.
    """
    try:
        dir_stat = directory.stat()
        if dir_stat.st_ino in visited_inodes:
            logger.warning(
                "asset_symlink_loop_detected",
                path=str(directory),
                action="skipping",
            )
            return
        visited_inodes.add(dir_stat.st_ino)
    except OSError:
        return

    try:
        for item in directory.iterdir():
            if item.is_symlink():
                # Check if symlink target is within assets directory
                try:
                    target = item.resolve()
                    target.relative_to(self.assets_dir.resolve())
                except ValueError:
                    logger.warning(
                        "asset_symlink_outside_root",
                        path=str(item),
                        target=str(target),
                        action="skipping_for_security",
                    )
                    continue

            if item.is_file():
                yield item
            elif item.is_dir():
                yield from self._walk_with_symlink_check(item, visited_inodes)
    except PermissionError:
        logger.warning("asset_dir_permission_denied", path=str(directory))
```

**Validator Integration**:

```python
# bengal/health/validators/assets.py (addition)

def _check_symlinks(self, assets_dir: Path) -> list[CheckResult]:
    """Check for potentially problematic symlinks in assets."""
    results = []

    symlinks = []
    external_symlinks = []

    for item in assets_dir.rglob("*"):
        if item.is_symlink():
            symlinks.append(str(item.relative_to(assets_dir)))
            try:
                target = item.resolve()
                target.relative_to(assets_dir.resolve())
            except ValueError:
                external_symlinks.append(str(item.relative_to(assets_dir)))

    if external_symlinks:
        results.append(
            CheckResult.warning(
                f"{len(external_symlinks)} asset symlink(s) point outside assets directory",
                code="H631",
                recommendation=(
                    "Symlinks pointing outside the assets directory are skipped for security.\n"
                    "Consider copying the files instead of symlinking."
                ),
                details=external_symlinks[:5],
            )
        )

    return results
```

---

### Solution 4: Stale Fingerprint Cleanup

**Problem**: When assets change, old fingerprinted versions accumulate in output, causing disk bloat and potential confusion.

**Approach**: Clean up old fingerprinted versions when new ones are written.

**Implementation**:

```python
# bengal/core/asset/asset_core.py (enhancement)

def _cleanup_old_fingerprints(self, output_dir: Path) -> int:
    """
    Remove old fingerprinted versions of this asset.

    When style.abc123.css is written, removes style.*.css except the new one.

    Returns:
        Number of files removed
    """
    if not self.fingerprint:
        return 0

    # Get base name without fingerprint: style.abc123.css -> style
    base_name = self.output_path.stem.split(".")[0]
    suffix = self.output_path.suffix
    parent = output_dir / self.output_path.parent

    if not parent.exists():
        return 0

    removed = 0
    current_fingerprinted = f"{base_name}.{self.fingerprint}{suffix}"

    for existing in parent.glob(f"{base_name}.*{suffix}"):
        # Skip the current fingerprinted version
        if existing.name == current_fingerprinted:
            continue

        # Skip non-fingerprinted version (might be intentional)
        if existing.name == f"{base_name}{suffix}":
            continue

        # Check if it looks like a fingerprinted version
        stem_parts = existing.stem.split(".")
        if len(stem_parts) == 2 and len(stem_parts[1]) >= 6:
            # Looks like base.fingerprint pattern
            try:
                existing.unlink()
                removed += 1
                logger.debug(
                    "stale_fingerprint_removed",
                    path=str(existing.relative_to(output_dir)),
                )
            except OSError:
                pass

    return removed
```

**Integration**: Call during asset write phase.

**CLI Command**:

```bash
bengal clean --stale-assets  # Remove orphaned fingerprinted assets
```

---

### Solution 5: Output Permission Validation

**Problem**: Build can fail if output directory is read-only or inaccessible.

**Approach**: Pre-validate write permissions before build starts.

**Implementation**:

```python
# bengal/health/validators/system.py (addition)

def _check_output_permissions(self, site: Site) -> list[CheckResult]:
    """Check that output directory is writable."""
    results = []
    output_dir = site.output_dir

    # Create output dir if needed
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            results.append(
                CheckResult.error(
                    f"Cannot create output directory: {output_dir}",
                    code="H703",
                    recommendation=(
                        "Check directory permissions.\n"
                        f"  Run: chmod 755 {output_dir.parent}"
                    ),
                )
            )
            return results
        except OSError as e:
            results.append(
                CheckResult.error(
                    f"Cannot create output directory: {e}",
                    code="H704",
                    recommendation="Check that the path is valid and accessible.",
                )
            )
            return results

    # Test write permission with a temp file
    test_file = output_dir / ".bengal-write-test"
    try:
        test_file.write_text("test")
        test_file.unlink()
    except PermissionError:
        results.append(
            CheckResult.error(
                f"Output directory is not writable: {output_dir}",
                code="H705",
                recommendation=(
                    "Check directory permissions.\n"
                    f"  Run: chmod 755 {output_dir}"
                ),
            )
        )
    except OSError as e:
        results.append(
            CheckResult.warning(
                f"Could not verify write permissions: {e}",
                code="H706",
                recommendation="Ensure output directory is accessible.",
            )
        )

    return results
```

---

## Implementation Plan

### Phase 1: Build Lock (Week 1)

**Effort**: 1 week

**Tasks**:
1. Implement `BuildLock` class with atomic file locking
2. Add stale lock detection (age + process check)
3. Integrate with `BuildOrchestrator`
4. Add `--no-lock` and `--force-lock` CLI options
5. Write tests for concurrent build scenarios
6. Document in CLI reference

**Deliverables**:
- Build lock prevents concurrent builds
- Stale locks auto-detected and removable
- CI-friendly (process dies → lock stale)

---

### Phase 2: System Resource Validator (Week 1-2)

**Effort**: 0.5 week

**Tasks**:
1. Create `SystemResourceValidator` class
2. Implement disk space estimation
3. Implement output permission check
4. Register as pre-build validator
5. Write tests

**Deliverables**:
- Pre-build disk space check
- Output directory permission validation
- Clear error messages with fix suggestions

---

### Phase 3: Asset Symlink Handling (Week 2)

**Effort**: 1 week

**Tasks**:
1. Add symlink loop detection to `AssetDiscovery`
2. Add symlink-outside-root detection
3. Add symlink validator check
4. Update asset discovery tests
5. Document security behavior

**Deliverables**:
- Symlink loops detected and skipped
- External symlinks rejected with warning
- Consistent with content symlink handling

---

### Phase 4: Stale Fingerprint Cleanup (Week 3)

**Effort**: 1 week

**Tasks**:
1. Implement `_cleanup_old_fingerprints()` in Asset class
2. Integrate with asset write phase
3. Add `bengal clean --stale-assets` command
4. Write tests for cleanup scenarios
5. Document fingerprint lifecycle

**Deliverables**:
- Old fingerprinted assets auto-removed on rebuild
- Manual cleanup command available
- No disk bloat from repeated builds

---

## Success Criteria

### Build Lock
- [ ] Concurrent builds are blocked with clear message
- [ ] Stale locks (dead process, >1h old) are auto-detected
- [ ] `--force-lock` removes stale locks
- [ ] CI builds don't accumulate stale locks
- [ ] Lock file is `.gitignore`d

### System Resources
- [ ] Low disk space detected before build starts
- [ ] Insufficient space is ERROR (build aborted)
- [ ] Permission errors detected with fix suggestions
- [ ] Works on macOS, Linux, Windows

### Asset Symlinks
- [ ] Symlink loops detected and skipped
- [ ] External symlinks rejected with warning
- [ ] Valid internal symlinks work correctly
- [ ] Security: cannot escape assets directory

### Stale Fingerprints
- [ ] Old fingerprinted versions removed on new write
- [ ] Non-fingerprinted versions preserved
- [ ] Manual cleanup command available
- [ ] No data loss (only removes old versions)

---

## Error Code Reference

| Code | Level | Description |
|------|-------|-------------|
| H700 | ERROR | Insufficient disk space |
| H701 | WARNING | Low disk space |
| H702 | WARNING | Cannot check disk space |
| H703 | ERROR | Cannot create output directory |
| H704 | ERROR | Output directory creation failed |
| H705 | ERROR | Output directory not writable |
| H706 | WARNING | Cannot verify write permissions |
| H631 | WARNING | Asset symlinks point outside root |

---

## Open Questions

1. **Build lock scope**: Lock per-output-dir or per-site-root?
   - **Recommendation**: Per-output-dir (allows parallel builds to different outputs)

2. **Stale lock timeout**: 1 hour reasonable?
   - **Recommendation**: 1 hour default, configurable via env var `BENGAL_LOCK_TIMEOUT`

3. **Symlink policy**: Warn and skip vs. error and abort?
   - **Recommendation**: Warn and skip (matches content symlink behavior)

4. **Fingerprint cleanup**: Auto on build vs. manual only?
   - **Recommendation**: Auto on build, manual command for orphan cleanup

---

## References

- **Build Orchestrator**: `bengal/orchestration/build/orchestrator.py`
- **Asset Discovery**: `bengal/discovery/asset_discovery.py`
- **Health Validators**: `bengal/health/validators/`
- **Existing Symlink Handling**: `bengal/discovery/directory_walker.py:113`
- **Asset Fingerprinting**: `bengal/core/asset/asset_core.py:537`
- **Bug 1 Fix**: `bengal/orchestration/build/initialization.py:504-530`
- **Bug 2 Fix**: `bengal/discovery/asset_discovery.py:97-104`

---

## Appendix A: CI/CD Compatibility Matrix

| Platform | Build Lock | Disk Check | Symlinks | Notes |
|----------|------------|------------|----------|-------|
| GitHub Actions | ✅ | ✅ | ✅ | Runners have ~14GB free |
| GitLab CI | ✅ | ✅ | ✅ | Docker-based, varies |
| CircleCI | ✅ | ✅ | ✅ | Resource classes vary |
| Vercel | ⚠️ | ✅ | ✅ | Serverless, no lock needed |
| Netlify | ⚠️ | ✅ | ✅ | Build containers isolated |
| Local (macOS) | ✅ | ✅ | ✅ | Full support |
| Local (Linux) | ✅ | ✅ | ✅ | Full support |
| Local (Windows) | ✅ | ✅ | ⚠️ | Symlinks may require admin |

**Legend**: ✅ Full support | ⚠️ Partial/not needed | ❌ Not supported
