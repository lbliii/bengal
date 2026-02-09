"""AST-aware fragment updates for reactive hot reload.

Integrates Patitas AST diffing with Kida block metadata to determine
exactly which template blocks are affected by a content change and
push only those blocks as fragments.

Phase 2 of the reactive hot reload plan:
- Caches Patitas ASTs per page for O(change) diffing
- Maps AST node changes to template context paths
- Queries Kida block_metadata to find affected blocks
- Pushes only affected blocks (vs Phase 1's whole "content" block)

Architecture:
    _try_fragment_update (build_trigger.py)
         |
    ContentASTCache (this module) — stores per-page ASTs
         |
    ast_changes_to_context_paths() — maps AST changes to context paths
         |
    get_affected_blocks() — queries block_metadata for affected blocks

Thread Safety:
    ContentASTCache uses a threading.Lock for concurrent access.
    All functions are safe to call from the build trigger thread.

Related:
    - bengal/server/build_trigger.py: Calls into this module
    - patitas.differ: diff_documents for AST comparison
    - patitas.nodes: Heading, Paragraph, etc.
    - kida.template.introspection: block_metadata

"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, ClassVar


class ContentASTCache:
    """Per-page AST cache for incremental diffing and build reuse.

    Caches the Patitas Document AST from the last successful content parse
    for each page. Serves two purposes:

    1. **Fragment fast path** (dev server): When a page is edited, parse the
       new content to an AST, diff against the cached version, and determine
       which template blocks need re-rendering.

    2. **Build parsing reuse** (Phase 2a): After each page is parsed during
       a build, store its AST keyed by (source_path, content_hash). On
       subsequent builds, pages with matching content hashes skip parsing
       entirely.

    The cache is keyed by file path and stores (content_hash, body_text, Document).
    Optionally persists to disk via Patitas ``to_json()``/``from_json()``
    to survive server restarts.

    Thread Safety:
        All access is protected by _lock. The cache is populated from the
        build trigger thread and read during fragment updates and parsing.

    RFC: reactive-rebuild-architecture Phase 2a
    """

    # (content_hash, body_text, Document)
    _cache: ClassVar[dict[Path, tuple[str, str, Any]]] = {}
    _cache_max: ClassVar[int] = 500
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def get(cls, path: Path) -> tuple[str, Any] | None:
        """Get cached (body_text, Document) for a path.

        Returns:
            Tuple of (body_text, Document AST) or None if not cached.
        """
        with cls._lock:
            entry = cls._cache.get(path)
            if entry is None:
                return None
            _hash, body, ast = entry
            return body, ast

    @classmethod
    def get_by_hash(cls, path: Path, content_hash: str) -> Any | None:
        """Get cached Document AST only if content_hash matches.

        Used during build parsing to reuse ASTs for unchanged pages.

        Args:
            path: Source file path (cache key).
            content_hash: Hash of the current file content.

        Returns:
            Document AST if cached and hash matches, else None.
        """
        with cls._lock:
            entry = cls._cache.get(path)
            if entry is None:
                return None
            cached_hash, _body, ast = entry
            if cached_hash == content_hash:
                return ast
            return None

    @classmethod
    def put(cls, path: Path, content_hash: str, body: str, ast: Any) -> None:
        """Store (body_text, Document AST) for a path.

        Args:
            path: Source file path (cache key).
            content_hash: Hash of the file content (for cache validation).
            body: Markdown body text (without frontmatter).
            ast: Patitas Document AST.
        """
        with cls._lock:
            cls._cache[path] = (content_hash, body, ast)
            # LRU eviction
            if len(cls._cache) > cls._cache_max:
                first_key = next(iter(cls._cache))
                del cls._cache[first_key]

    @classmethod
    def clear(cls) -> None:
        """Clear all cached ASTs."""
        with cls._lock:
            cls._cache.clear()

    @classmethod
    def stats(cls) -> dict[str, int]:
        """Return cache statistics."""
        with cls._lock:
            return {"entries": len(cls._cache), "max": cls._cache_max}

    @classmethod
    def save_to_disk(cls, cache_dir: Path) -> int:
        """Persist cached ASTs to disk for server restart survival.

        Uses Patitas ``to_json()`` for deterministic serialization.

        Args:
            cache_dir: Directory to store AST cache files.

        Returns:
            Number of ASTs persisted.
        """
        try:
            from patitas.serialization import to_json
        except ImportError:
            return 0

        cache_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        with cls._lock:
            for content_hash, _body, ast in cls._cache.values():
                try:
                    # Use content_hash as filename for O(1) lookup
                    out_path = cache_dir / f"{content_hash}.json"
                    if not out_path.exists():
                        out_path.write_text(to_json(ast))
                    count += 1
                except Exception:
                    continue
        return count

    @classmethod
    def load_from_disk(cls, cache_dir: Path) -> int:
        """Load persisted ASTs from disk.

        Uses Patitas ``from_json()`` for deserialization.

        Args:
            cache_dir: Directory containing AST cache files.

        Returns:
            Number of ASTs loaded.
        """
        try:
            from patitas.serialization import from_json
        except ImportError:
            return 0

        if not cache_dir.exists():
            return 0

        count = 0
        # We can't fully reconstruct (path → hash) mappings from disk alone,
        # but we store a companion index file.
        index_path = cache_dir / "_index.json"
        if not index_path.exists():
            return 0

        try:
            import json

            index: dict[str, str] = json.loads(index_path.read_text())
        except Exception:
            return 0

        with cls._lock:
            for path_str, content_hash in index.items():
                ast_path = cache_dir / f"{content_hash}.json"
                if not ast_path.exists():
                    continue
                try:
                    ast = from_json(ast_path.read_text())
                    cls._cache[Path(path_str)] = (content_hash, "", ast)
                    count += 1
                except Exception:
                    continue
        return count


def ast_changes_to_context_paths(changes: tuple[Any, ...]) -> frozenset[str]:
    """Map Patitas ASTChange objects to template context paths.

    Examines which AST node types were affected and returns the set of
    template context paths that may have changed. Template blocks can
    then check their ``depends_on`` against this set.

    Mapping rules:
    - Heading change → {"content", "toc", "toc_items"} (+ "page.title" if h1)
    - Paragraph/List/etc → {"content"}
    - FrontMatter change → {"metadata", "page"} (triggers full rebuild)
    - Any other node → {"content"}

    Args:
        changes: Tuple of ASTChange objects from diff_documents()

    Returns:
        Frozen set of affected context path strings.
    """
    try:
        from patitas.nodes import Heading
    except ImportError:
        # Patitas not available — assume all context changed
        return frozenset({"content", "toc", "toc_items", "page.title"})

    paths: set[str] = set()

    for change in changes:
        node = change.new_node or change.old_node
        if node is None:
            paths.add("content")
            continue

        if isinstance(node, Heading):
            paths.update({"content", "toc", "toc_items"})
            # Level 1 heading often drives page.title
            if hasattr(node, "level") and node.level == 1:
                paths.add("page.title")
        else:
            # Paragraph, List, CodeBlock, BlockQuote, etc.
            paths.add("content")

    return frozenset(paths) if paths else frozenset({"content"})


# RFC: reactive-rebuild-architecture Phase 4c
# Frontmatter key → context path mapping for fragment targeting.
# Keys not in this map (and not in NAV_AFFECTING_KEYS) get generic "metadata".
_FM_KEY_TO_CONTEXT: dict[str, tuple[str, ...]] = {
    "tags": ("page.taxonomies", "page.tags"),
    "categories": ("page.taxonomies", "page.categories"),
    "topics": ("page.taxonomies", "page.topics"),
    "series": ("page.taxonomies", "page.series"),
    "description": ("page.description", "metadata"),
    "summary": ("page.summary", "metadata"),
    "date": ("page.date", "metadata"),
    "updated": ("page.date", "metadata"),
    "lastmod": ("page.date", "metadata"),
    "author": ("page.author", "metadata"),
    "authors": ("page.author", "metadata"),
    "image": ("page.image", "metadata"),
    "thumbnail": ("page.image", "metadata"),
}


def frontmatter_changes_to_context_paths(
    changed_keys: set[str],
) -> frozenset[str]:
    """Map changed frontmatter keys to template context paths.

    Non-nav-affecting frontmatter changes can be handled by the fragment
    fast path if we know which template blocks depend on them.

    Args:
        changed_keys: Set of frontmatter key names that changed.

    Returns:
        Frozen set of affected context path strings.
    """
    paths: set[str] = set()
    for key in changed_keys:
        mapped = _FM_KEY_TO_CONTEXT.get(key.lower())
        if mapped:
            paths.update(mapped)
        else:
            # Generic metadata catch-all
            paths.add("metadata")
    return frozenset(paths) if paths else frozenset({"metadata"})


def get_affected_blocks(
    engine: Any,
    template_name: str,
    changed_context_paths: frozenset[str],
) -> tuple[list[str], bool]:
    """Query template block metadata to find blocks affected by context changes.

    Uses Kida's block_metadata() to check each block's ``depends_on``
    against the changed context paths. Returns block names whose
    dependencies intersect with the changes, plus whether the metadata
    was available (so the caller can decide whether to trust the result
    or fall back to a default block list).

    RFC: reactive-rebuild-architecture Phase 4b
    When metadata IS available, the returned list is the precise set of
    blocks that need re-rendering — the caller should trust it rather
    than always forcing "content" into the list.

    Args:
        engine: KidaTemplateEngine instance
        template_name: Template to inspect (e.g., "page.html")
        changed_context_paths: Set of changed context paths

    Returns:
        Tuple of (affected_block_names, metadata_available).
        If metadata_available is False, the list will be empty and
        the caller should use its own default (e.g., ["content"]).
    """
    try:
        template = engine._env.get_template(template_name)
        meta = template.block_metadata()
        if not meta:
            return [], False

        affected = [
            name
            for name, m in meta.items()
            if m.depends_on & changed_context_paths  # set intersection
        ]
        return affected, True
    except Exception:
        return [], False


def diff_content_ast(
    path: Path,
    new_body: str,
) -> tuple[frozenset[str], Any] | None:
    """Diff new content against cached AST and return affected context paths.

    Parses the new body text to a Patitas AST, diffs against the cached
    AST for this path, and maps the changes to context paths.

    Also updates the cache with the new AST for future diffs.

    Args:
        path: File path (cache key)
        new_body: New markdown body text (without frontmatter)

    Returns:
        Tuple of (affected_context_paths, new_document_ast) if diff
        succeeded, or None if AST caching/diffing is unavailable.
    """
    try:
        from patitas import parse as patitas_parse
        from patitas.differ import diff_documents
    except ImportError:
        return None

    import hashlib

    body_hash = hashlib.sha256(new_body.encode()).hexdigest()[:16]

    # Get cached AST for incremental parsing
    cached = ContentASTCache.get(path)

    if cached is None:
        # First time — full parse, cache, and return broad context paths
        new_ast = patitas_parse(new_body, source_file=str(path))
        ContentASTCache.put(path, body_hash, new_body, new_ast)
        return frozenset({"content"}), new_ast

    old_body, old_ast = cached

    # RFC: reactive-rebuild-architecture Phase 4a
    # Use parse_incremental() for O(change) instead of O(document) parsing.
    # Find the edit region by comparing old and new source text, then splice
    # only the edited region into the existing AST.
    new_ast = None
    try:
        from patitas.incremental import parse_incremental

        if old_body != new_body:
            # Find the first differing character (edit_start)
            min_len = min(len(old_body), len(new_body))
            edit_start = 0
            for i in range(min_len):
                if old_body[i] != new_body[i]:
                    edit_start = i
                    break
            else:
                edit_start = min_len

            # Find the last differing character from the end
            old_end = len(old_body) - 1
            new_end = len(new_body) - 1
            while old_end > edit_start and new_end > edit_start:
                if old_body[old_end] != new_body[new_end]:
                    break
                old_end -= 1
                new_end -= 1

            edit_end = old_end + 1  # exclusive end in old source
            new_length = new_end - edit_start + 1

            new_ast = parse_incremental(
                new_body,
                old_ast,
                edit_start,
                edit_end,
                new_length,
                source_file=str(path),
            )
    except Exception:
        new_ast = None  # Fall back to full parse

    if new_ast is None:
        # Incremental parse unavailable or failed — full parse
        new_ast = patitas_parse(new_body, source_file=str(path))

    # Diff old vs new
    changes = diff_documents(old_ast, new_ast)

    # Update cache
    ContentASTCache.put(path, body_hash, new_body, new_ast)

    if not changes:
        # No structural changes (content is semantically identical)
        return frozenset(), new_ast

    # Map changes to context paths
    context_paths = ast_changes_to_context_paths(changes)
    return context_paths, new_ast


def check_cascade_safety(
    site: Any,
    changed_paths: set[Any],
) -> bool:
    """Check if content changes might cascade to other pages.

    Uses two data sources to detect cross-page dependencies:

    1. **BuildCache.reverse_dependencies** (persisted) — maps each dependency
       to the set of source files that declared it.  If a changed content
       file appears as a dependency of *another* page, the fast path is
       unsafe.

    2. **BuildEffectTracer.outputs_needing_rebuild** (in-memory, from last
       build) — computes the transitive closure of which outputs would need
       regeneration.  If more outputs are affected than the changed files
       themselves, there's a cascade.

    For body-only changes (frontmatter unchanged), cascades are rare:
    - Other pages depend on templates/partials, not on other page bodies
    - Navigation/taxonomy depends on frontmatter (excluded by Gate 3)
    - The main cascade scenario is shared content (_shared/ directory)

    Args:
        site: Site instance with _cache or build cache access
        changed_paths: Set of changed file Paths

    Returns:
        True if it's safe to use the fast path (no cascades detected).
        False if cascades are possible (should fall back to full rebuild).

    RFC: content-only-hot-reload (Phase 3)
    """
    try:
        # --- Check 1: BuildCache reverse_dependencies (persisted graph) ---
        cache = getattr(site, "_cache", None)
        if cache is not None:
            reverse_deps = getattr(cache, "reverse_dependencies", {})
            for path in changed_paths:
                path_str = str(path)
                dependents = reverse_deps.get(path_str, set())
                if dependents:
                    # Filter out self-references (a page depends on its own source)
                    other_dependents = dependents - {path_str}
                    if other_dependents:
                        return False

        # --- Check 2: EffectTracer transitive outputs (in-memory) ---
        # BuildEffectTracer is a singleton that persists across builds.
        # If it has recorded effects from the last build, use its transitive
        # output computation for a more precise cascade check.
        try:
            from bengal.effects.render_integration import BuildEffectTracer

            tracer_instance = BuildEffectTracer.get_instance()
            if tracer_instance._enabled and tracer_instance._tracer.effects:
                outputs = tracer_instance._tracer.outputs_needing_rebuild(changed_paths)
                # If there are outputs beyond the directly changed files' own
                # outputs, other pages are affected → cascade detected.
                # A page's own source always maps to its own output, so
                # we expect exactly len(changed_paths) outputs if no cascade.
                if outputs and len(outputs) > len(changed_paths):
                    return False
        except Exception:
            pass  # EffectTracer not available — rely on reverse_deps only

        return True

    except Exception:
        # On any error, assume safe (conservative fallback is already
        # handled by the full rebuild path)
        return True
