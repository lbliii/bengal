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
    """Per-page AST cache for incremental diffing.

    Caches the Patitas Document AST from the last successful content parse
    for each page. When a page is edited, we parse the new content to an
    AST, diff against the cached version, and determine which template
    blocks need re-rendering.

    The cache is keyed by file path and stores (mtime, body_text, Document).

    Thread Safety:
        All access is protected by _lock. The cache is populated from the
        build trigger thread and read during fragment updates.

    """

    _cache: ClassVar[dict[Path, tuple[float, str, Any]]] = {}
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
            _mtime, body, ast = entry
            return body, ast

    @classmethod
    def put(cls, path: Path, mtime: float, body: str, ast: Any) -> None:
        """Store (body_text, Document AST) for a path."""
        with cls._lock:
            cls._cache[path] = (mtime, body, ast)
            # LRU eviction
            if len(cls._cache) > cls._cache_max:
                first_key = next(iter(cls._cache))
                del cls._cache[first_key]

    @classmethod
    def clear(cls) -> None:
        """Clear all cached ASTs."""
        with cls._lock:
            cls._cache.clear()


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


def get_affected_blocks(
    engine: Any,
    template_name: str,
    changed_context_paths: frozenset[str],
) -> list[str]:
    """Query template block metadata to find blocks affected by context changes.

    Uses Kida's block_metadata() to check each block's ``depends_on``
    against the changed context paths. Returns block names whose
    dependencies intersect with the changes.

    Args:
        engine: KidaTemplateEngine instance
        template_name: Template to inspect (e.g., "page.html")
        changed_context_paths: Set of changed context paths

    Returns:
        List of affected block names. Empty if metadata unavailable.
    """
    try:
        template = engine._env.get_template(template_name)
        meta = template.block_metadata()
        if not meta:
            return []

        return [
            name
            for name, m in meta.items()
            if m.depends_on & changed_context_paths  # set intersection
        ]
    except Exception:
        return []


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

    # Parse new content to AST
    new_ast = patitas_parse(new_body, source_file=str(path))

    # Get cached AST
    cached = ContentASTCache.get(path)
    if cached is None:
        # First time — cache and return broad context paths
        mtime = path.stat().st_mtime
        ContentASTCache.put(path, mtime, new_body, new_ast)
        return frozenset({"content"}), new_ast

    _old_body, old_ast = cached

    # Diff old vs new
    changes = diff_documents(old_ast, new_ast)

    # Update cache
    mtime = path.stat().st_mtime
    ContentASTCache.put(path, mtime, new_body, new_ast)

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
