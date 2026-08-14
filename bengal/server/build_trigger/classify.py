"""Change classification for the dev-server rebuild loop.

Detects what kind of edit a watcher event represents: content-only body
edits, navigation frontmatter, shared/versioned paths, and rendered
dependents. BuildTrigger delegates here; behavior is unchanged.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bengal.core.section.utils import get_page_section
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.normalize import to_posix

logger = get_logger("bengal.server.build_trigger")


@dataclass(frozen=True, slots=True)
class FrontmatterCacheEntry:
    """Cache entry for frontmatter nav-key detection (mtime, has_nav_keys)."""

    mtime: float
    mtime_ns: int
    has_nav_keys: bool


@dataclass(frozen=True, slots=True)
class ContentHashCacheEntry:
    """Cache entry for content-only change detection (mtime, fm_hash, content_hash)."""

    mtime: float
    mtime_ns: int
    frontmatter_hash: str
    content_hash: str


def _can_use_reactive_path(trigger: Any, changed_paths: set[Path], event_types: set[str]) -> bool:
    """Check if content-only reactive path can be used (skips full build).

    Content-only = frontmatter unchanged, body changed. The fast reactive
    path is only safe when no rendered dependents need excerpts/listings
    refreshed; otherwise use the warm build path for parity.
    """
    if len(changed_paths) != 1 or event_types != {"modified"}:
        return False
    path = next(iter(changed_paths))
    if path.suffix.lower() not in {".md", ".markdown"}:
        return False
    return trigger._is_content_only_change(path) and not trigger._has_rendered_dependents(path)


def _has_rendered_dependents(trigger: Any, path: Path) -> bool:
    """Return True when a content edit should rebuild dependent pages."""
    try:
        changed = path.resolve()
    except OSError:
        changed = path

    for page in getattr(trigger.site, "pages", []):
        source_path = getattr(page, "source_path", None)
        if source_path is None:
            continue
        try:
            page_path = Path(source_path).resolve()
        except OSError, TypeError, ValueError:
            continue
        if page_path != changed:
            continue

        section = get_page_section(page)
        if section is None:
            return False
        index_page = getattr(section, "index_page", None)
        if index_page is None or index_page is page:
            return False
        return getattr(index_page, "output_path", None) is not None

    return False


def _is_shared_content_change(trigger: Any, changed_paths: set[Path]) -> bool:
    """
    Check if any changed path is in _shared/ directory.

    Shared content is included in all versions, so changes require
    a full rebuild to cascade to all versioned pages.

    Args:
        changed_paths: Set of changed file paths

    Returns:
        True if any changed file is in _shared/
    """
    if not getattr(trigger.site, "versioning_enabled", False):
        return False

    for path in changed_paths:
        path_str = to_posix(path)
        # Check for _shared/ anywhere in path
        if "/_shared/" in path_str or path_str.startswith("_shared/"):
            return True
        # Also check content/_shared/ pattern
        if "/content/_shared/" in path_str:
            return True

    return False


def _get_affected_versions(trigger: Any, changed_paths: set[Path]) -> set[str]:
    """
    Determine which versions are affected by changes.

    Maps changed file paths to version IDs:
    - _versions/<id>/* → version id
    - Regular content (docs/, etc.) → latest version
    - _shared/* → all versions (handled separately)

    Args:
        changed_paths: Set of changed file paths

    Returns:
        Set of affected version IDs
    """
    if not getattr(trigger.site, "versioning_enabled", False):
        return set()

    version_config = getattr(trigger.site, "version_config", None)
    if not version_config or not version_config.enabled:
        return set()

    affected: set[str] = set()

    for path in changed_paths:
        path_str = to_posix(path)

        # Check if in _versions/<id>/
        if "/_versions/" in path_str or path_str.startswith("_versions/"):
            # Extract version ID from path
            if "/_versions/" in path_str:
                parts = path_str.split("/_versions/")[1].split("/")
            else:
                parts = path_str.split("_versions/")[1].split("/")

            if parts:
                version_id = parts[0]
                affected.add(version_id)

        # Check if in versioned section (implies latest version)
        elif not path_str.startswith("_"):
            # Check if path is in a versioned section
            for section in version_config.sections:
                if f"/{section}/" in path_str or path_str.startswith(f"{section}/"):
                    if version_config.latest_version:
                        affected.add(version_config.latest_version.id)
                    break

    return affected


def _is_version_config_change(trigger: Any, changed_paths: set[Path]) -> bool:
    """
    Check if versioning config changed (requires full rebuild).

    Detects changes to versioning.yaml or version-related config files.

    Args:
        changed_paths: Set of changed file paths

    Returns:
        True if version config changed
    """
    for path in changed_paths:
        # Check for versioning.yaml
        if path.name == "versioning.yaml":
            return True

        path_str = to_posix(path)

        # Check for version config in config directories
        if "/config/" in path_str and "version" in path.name.lower():
            return True

    return False


def _detect_nav_changes(
    trigger: Any,
    changed_paths: set[Path],
    needs_full_rebuild: bool,
) -> set[Path]:
    """
    Detect which changed files have navigation-affecting frontmatter.

    Uses caching with mtime invalidation for efficiency:
    - Cache hit: O(1) lookup
    - Cache miss: Read only first 4KB (frontmatter is at file start)
    """
    if needs_full_rebuild:
        return set()

    nav_changed: set[Path] = set()

    for path in changed_paths:
        if path.suffix.lower() not in {".md", ".markdown"}:
            continue

        if trigger._has_nav_affecting_frontmatter(path):
            nav_changed.add(path)
            logger.debug("nav_frontmatter_detected", file=str(path))

    return nav_changed


def _has_nav_affecting_frontmatter(trigger: Any, path: Path) -> bool:
    """
    Check if file has navigation-affecting frontmatter (cached).

    Optimizations:
    1. LRU cache keyed by (path, mtime) - avoids re-parsing unchanged files
    2. Partial read (4KB) - frontmatter is always at file start

    Args:
        path: Path to markdown file

    Returns:
        True if file has navigation-affecting frontmatter keys
    """
    try:
        stat = path.stat()
        mtime = stat.st_mtime
        mtime_ns = stat.st_mtime_ns
        resolved = path.resolve()

        # Check cache (keyed by resolved path for watcher/discovery consistency)
        cached = trigger._frontmatter_cache.get(resolved)
        if cached is not None and cached.mtime_ns == mtime_ns:
            return cached.has_nav_keys

        # Read only first 4KB (frontmatter is at start)
        # Most frontmatter is < 500 bytes, but YAML-heavy files may be larger
        with open(path, encoding="utf-8") as f:
            text = f.read(4096)

        # Extract frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
        if not match:
            result = False
        else:
            try:
                fm = yaml.safe_load(match.group(1)) or {}
                if not isinstance(fm, dict):
                    result = False
                else:
                    from bengal.orchestration.constants import NAV_AFFECTING_KEYS

                    result = any(str(key).lower() in NAV_AFFECTING_KEYS for key in fm)
            except yaml.YAMLError:
                result = False

        # Update cache with LRU eviction (resolved path for watcher consistency)
        if len(trigger._frontmatter_cache) >= trigger._frontmatter_cache_max:
            first_key = next(iter(trigger._frontmatter_cache))
            del trigger._frontmatter_cache[first_key]
        trigger._frontmatter_cache[resolved] = FrontmatterCacheEntry(
            mtime=mtime, mtime_ns=mtime_ns, has_nav_keys=result
        )

        return result

    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.debug("frontmatter_check_failed", file=str(path), error=str(e))
        return False


def _compute_content_hashes(trigger: Any, path: Path) -> ContentHashCacheEntry | None:
    """
    Read a markdown file and compute frontmatter/content hashes.

    Returns None if the file has no frontmatter or cannot be read.
    Used by _is_content_only_change and seed_content_hash_cache.
    """
    import hashlib

    if path.suffix.lower() not in {".md", ".markdown"}:
        return None

    try:
        stat = path.stat()
        mtime = stat.st_mtime
        mtime_ns = stat.st_mtime_ns
        with open(path, encoding="utf-8") as f:
            text = f.read()

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
        if not match:
            return None

        fm_hash = hashlib.sha256(match.group(1).encode()).hexdigest()[:16]
        content_hash = hashlib.sha256(match.group(2).encode()).hexdigest()[:16]
        return ContentHashCacheEntry(
            mtime=mtime,
            mtime_ns=mtime_ns,
            frontmatter_hash=fm_hash,
            content_hash=content_hash,
        )
    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.debug("content_hash_check_failed", file=str(path), error=str(e))
        return None


def _is_content_only_change(trigger: Any, path: Path) -> bool:
    """
    Check if a markdown file change is content-only (frontmatter unchanged).

    Content-only changes can potentially use faster rendering paths that
    skip template processing and inject new content into cached page shells.

    Args:
        path: Path to the markdown file

    Returns:
        True if only the markdown body changed (not frontmatter)

    RFC: content-only-hot-reload
    """
    entry = trigger._compute_content_hashes(path)
    if entry is None:
        return False

    resolved = path.resolve()
    cached = trigger._content_hash_cache.get(resolved)
    if (
        cached is not None
        and cached.frontmatter_hash == entry.frontmatter_hash
        and cached.content_hash != entry.content_hash
    ):
        logger.debug(
            "content_only_change_detected",
            file=str(path),
            hint="frontmatter_unchanged",
        )
        trigger._content_hash_cache[resolved] = entry
        return True

    # Update cache with LRU eviction (resolved path for watcher consistency)
    if len(trigger._content_hash_cache) >= trigger._content_hash_cache_max:
        first_key = next(iter(trigger._content_hash_cache))
        del trigger._content_hash_cache[first_key]
    trigger._content_hash_cache[resolved] = entry
    return False


def seed_content_hash_cache(trigger: Any, pages: list[Any]) -> None:
    """
    Populate content hash cache for content pages after a successful build.

    Enables the first content-only edit after startup to use the reactive path
    instead of falling back to full build (RFC: content-only-hot-reload).

    Keys are resolved to absolute paths to match the watcher's path format
    (watchfiles yields absolute paths). Without this, the first edit after
    startup misses the cache and falls through to a full warm build.
    """
    root = trigger.site.root_path
    for page in pages:
        src = getattr(page, "source_path", None)
        if src is None:
            continue
        path = Path(src) if not isinstance(src, Path) else src
        if path.suffix.lower() not in {".md", ".markdown"}:
            continue
        try:
            if path.is_absolute():
                abs_path = path
            elif root is not None:
                abs_path = (root / path).resolve()
            else:
                abs_path = path.resolve()
        except OSError, ValueError:
            continue
        entry = trigger._compute_content_hashes(abs_path)
        if entry is None:
            continue
        if len(trigger._content_hash_cache) >= trigger._content_hash_cache_max:
            first_key = next(iter(trigger._content_hash_cache))
            del trigger._content_hash_cache[first_key]
        trigger._content_hash_cache[abs_path] = entry
