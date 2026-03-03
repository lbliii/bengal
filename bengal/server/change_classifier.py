"""
Change classification for surgical warm rebuilds.

Consolidates all change classification logic from BuildTrigger into a pure
function. Classifies file changes into rebuild tiers: BODY_ONLY, FRONTMATTER,
CASCADE, or FULL.

Tier definitions:
- BODY_ONLY: Single .md, frontmatter hash unchanged. Use reactive path (~5ms).
- FRONTMATTER: Single .md (not _index.md cascade change). Patch + re-render (~20ms).
- CASCADE: Single _index.md, cascade block changed. Rebuild subtree (~100ms).
- FULL: Structural, template, config, multi-file. Full prepare_for_rebuild (~500ms+).

Related:
- bengal/server/build_trigger.py: Uses classify_change for rebuild decisions
- bengal/server/surgical_handler.py: Handles FRONTMATTER and CASCADE tiers
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from bengal.utils.paths.normalize import to_posix

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

# Keys that only affect the changed page (safe for Tier 2)
SAFE_KEYS: frozenset[str] = frozenset(
    {"description", "summary", "excerpt", "image", "icon", "draft", "hidden"}
)

# Keys that affect section listing (re-render section index too)
LISTING_KEYS: frozenset[str] = frozenset({"title", "weight", "date", "nav_title"})

# Keys that affect taxonomy (re-render affected taxonomy pages)
TAXONOMY_KEYS: frozenset[str] = frozenset({"tags", "categories"})

# Keys that force full rebuild (Tier 3b)
FULL_REBUILD_KEYS: frozenset[str] = frozenset(
    {"menu", "cascade", "permalink", "slug", "aliases", "redirect"}
)


class RebuildTier:
    """Rebuild tier enum for change classification."""

    BODY_ONLY = "body_only"
    FRONTMATTER = "frontmatter"
    CASCADE = "cascade"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class RebuildScope:
    """Result of change classification with impact analysis."""

    tier: str
    changed_page: Path | None
    cascade_dirty: bool
    nav_dirty: bool
    tags_changed: bool
    old_frontmatter: dict[str, Any] | None
    new_frontmatter: dict[str, Any] | None


def _extract_frontmatter(path: Path) -> tuple[dict[str, Any], str] | None:
    """Extract frontmatter and body from markdown file. Returns (fm, body) or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        fm = yaml.safe_load(match.group(1)) or {}
        if not isinstance(fm, dict):
            return None
        return dict(fm), match.group(2)
    except yaml.YAMLError:
        return None


def _hash_cascade_block(fm: dict[str, Any]) -> str:
    """Hash the cascade block for change detection."""
    cascade = fm.get("cascade", {})
    if not cascade:
        return ""
    import json

    return hashlib.sha256(json.dumps(cascade, sort_keys=True).encode()).hexdigest()[:16]


def _is_index_md(path: Path) -> bool:
    """Check if path is _index.md."""
    return path.name == "_index.md"


def _is_markdown(path: Path) -> bool:
    """Check if path is a markdown file."""
    return path.suffix.lower() in {".md", ".markdown"}


def classify_change(
    changed_paths: set[Path],
    event_types: set[str],
    content_hash_cache: dict[Path, Any],
    cascade_block_hashes: dict[Path, str],
    site: SiteLike,
    *,
    is_template_change: bool,
    should_regenerate_autodoc: bool,
    is_shared_content_change: bool,
    is_version_config_change: bool,
    is_svg_icon_change: bool,
) -> RebuildScope:
    """
    Classify a set of file changes into a rebuild tier.

    Pure function: takes all inputs explicitly. Caller provides predicates
    for template/autodoc/shared/version/svg checks (from BuildTrigger).

    Args:
        changed_paths: Set of changed file paths
        event_types: Set of event types (created, modified, deleted, moved)
        content_hash_cache: Map of path -> ContentHashCacheEntry (mtime, fm_hash, content_hash)
        cascade_block_hashes: Map of path -> hash of cascade block (for _index.md)
        site: Site instance (for root_path, etc.)
        is_template_change: True if template change requires full rebuild
        should_regenerate_autodoc: True if autodoc source changed
        is_shared_content_change: True if _shared/ content changed
        is_version_config_change: True if versioning config changed
        is_svg_icon_change: True if SVG icon in themes changed

    Returns:
        RebuildScope with tier and impact flags
    """
    # Structural events -> FULL
    if {"created", "deleted", "moved"} & event_types:
        return RebuildScope(
            tier=RebuildTier.FULL,
            changed_page=None,
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter=None,
        )

    # Template/config/autodoc/SVG/shared/version -> FULL
    if (
        is_template_change
        or should_regenerate_autodoc
        or is_shared_content_change
        or is_version_config_change
        or is_svg_icon_change
    ):
        return RebuildScope(
            tier=RebuildTier.FULL,
            changed_page=None,
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter=None,
        )

    # Multiple changed .md files -> FULL (could relax later)
    md_paths = [p for p in changed_paths if _is_markdown(p)]
    if len(md_paths) > 1:
        return RebuildScope(
            tier=RebuildTier.FULL,
            changed_page=None,
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter=None,
        )

    # No markdown changes
    if not md_paths:
        return RebuildScope(
            tier=RebuildTier.FULL,
            changed_page=None,
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter=None,
        )

    path = md_paths[0]
    if event_types != {"modified"}:
        return RebuildScope(
            tier=RebuildTier.FULL,
            changed_page=path,
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter=None,
        )

    # Single .md, modified
    resolved = path.resolve()
    parsed = _extract_frontmatter(path)
    if parsed is None:
        return RebuildScope(
            tier=RebuildTier.FULL,
            changed_page=path,
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter=None,
        )

    new_fm, _ = parsed
    fm_hash = hashlib.sha256(
        str(sorted(new_fm.items())).encode()
    ).hexdigest()[:16]

    content_hash_entry = content_hash_cache.get(resolved)
    if content_hash_entry is not None:
        old_fm_hash = content_hash_entry.frontmatter_hash
        if old_fm_hash == fm_hash:
            # Frontmatter unchanged -> BODY_ONLY
            return RebuildScope(
                tier=RebuildTier.BODY_ONLY,
                changed_page=path,
                cascade_dirty=False,
                nav_dirty=False,
                tags_changed=False,
                old_frontmatter=None,
                new_frontmatter=None,
            )

    # Frontmatter changed
    if _is_index_md(path):
        # Check if cascade block changed
        new_cascade_hash = _hash_cascade_block(new_fm)
        old_cascade_hash = cascade_block_hashes.get(resolved, "")
        if new_cascade_hash != old_cascade_hash:
            return RebuildScope(
                tier=RebuildTier.CASCADE,
                changed_page=path,
                cascade_dirty=True,
                nav_dirty=False,
                tags_changed=False,
                old_frontmatter=None,
                new_frontmatter=new_fm,
            )
        # _index.md but cascade unchanged -> FRONTMATTER (section index page)
        return _scope_for_frontmatter_change(new_fm, path, None)

    # Regular page, frontmatter changed -> FRONTMATTER
    return _scope_for_frontmatter_change(new_fm, path, None)


def _scope_for_frontmatter_change(
    new_fm: dict[str, Any],
    path: Path,
    old_fm: dict[str, Any] | None,
) -> RebuildScope:
    """Build RebuildScope for FRONTMATTER tier with impact flags."""
    old_keys = set(old_fm.keys()) if old_fm else set()
    new_keys = set(new_fm.keys())
    all_keys = old_keys | new_keys
    changed_keys = {
        k for k in all_keys
        if (old_fm or {}).get(k) != (new_fm or {}).get(k)
    }

    # FULL_REBUILD_KEYS -> upgrade to FULL (handled by caller when tier is FRONTMATTER)
    if changed_keys & FULL_REBUILD_KEYS:
        return RebuildScope(
            tier=RebuildTier.FULL,
            changed_page=path,
            cascade_dirty=False,
            nav_dirty=True,
            tags_changed=bool(changed_keys & TAXONOMY_KEYS),
            old_frontmatter=old_fm,
            new_frontmatter=new_fm,
        )

    nav_dirty = bool(changed_keys & LISTING_KEYS)
    tags_changed = bool(changed_keys & TAXONOMY_KEYS)

    return RebuildScope(
        tier=RebuildTier.FRONTMATTER,
        changed_page=path,
        cascade_dirty=False,
        nav_dirty=nav_dirty,
        tags_changed=tags_changed,
        old_frontmatter=old_fm,
        new_frontmatter=new_fm,
    )
