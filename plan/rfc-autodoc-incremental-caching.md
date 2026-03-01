# RFC: Autodoc Incremental Caching Enhancement

**Status**: Draft (Revised - Post-Evaluation)  
**Author**: AI Assistant  
**Created**: 2026-01-14  
**Revised**: 2026-01-14  
**Related**: rfc-output-cache-architecture.md

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-14 | 2.1 | Improved based on evaluation: Added Design Options, Normalization Strategy, and Non-Goals |
| 2026-01-14 | 2.0 | Complete rewrite: Acknowledged existing selective rebuild infrastructure, refocused on docstring-level hashing gap, corrected file paths |
| 2026-01-14 | 1.0 | Initial draft (superseded - proposed features that already existed) |

---

## Executive Summary

Bengal's autodoc system has **existing** selective rebuild infrastructure that tracks source→page dependencies. However, the current implementation uses **file-level hashing**, meaning any change to a Python file (imports, comments, formatting) triggers autodoc page rebuilds even when docstrings are unchanged.

This RFC proposes **docstring-level content hashing** to reduce unnecessary rebuilds when Python files change in ways that don't affect documentation.

**Target**: Reduce autodoc rebuilds from "any file change" to "only docstring/signature changes".

---

## Current State Analysis

### What Already Exists ✅

Bengal already has comprehensive autodoc incremental build support:

| Feature | Location | Status |
|---------|----------|--------|
| Source→page dependency tracking | `bengal/cache/build_cache/autodoc_tracking.py:54` | ✅ Implemented |
| Selective page rebuild | `bengal/orchestration/incremental/taxonomy_detector.py:396` | ✅ Implemented |
| File-level content hashing | `bengal/orchestration/content.py:406` | ✅ Implemented |
| Self-validation (hash mismatch detection) | `autodoc_tracking.py:180-313` | ✅ Implemented |
| mtime-first optimization | `autodoc_tracking.py:280-282` | ✅ Implemented |

**Evidence** - Selective rebuild already works:

```python
# taxonomy_detector.py:396
affected_pages = self.cache.get_affected_autodoc_pages(source_path)
if affected_pages:
    autodoc_pages_to_rebuild.update(affected_pages)
```

```python
# autodoc_tracking.py:54-58
autodoc_dependencies: dict[str, set[str]] = field(default_factory=dict)
autodoc_source_metadata: dict[str, tuple[str, float]] = field(default_factory=dict)
```

### The Actual Gap ❌

The current system hashes **entire Python files**, not just the documentation-relevant content:

```python
# content.py:406 - Current implementation
source_hash = hash_file(src_path)  # Hashes ENTIRE file
```

**Problem**: Non-documentation changes trigger unnecessary rebuilds:

| Change Type | Current Behavior | Ideal Behavior |
|-------------|------------------|----------------|
| Docstring edit | Rebuild ✅ | Rebuild ✅ |
| Signature change | Rebuild ✅ | Rebuild ✅ |
| Import added | Rebuild ❌ | Skip |
| Comment changed | Rebuild ❌ | Skip |
| Code formatting | Rebuild ❌ | Skip |
| Type hint in body | Rebuild ❌ | Skip |

### Impact Assessment

| Scenario | Current | With Docstring Hashing |
|----------|---------|------------------------|
| Python file reformatted | All affected pages rebuild | 0 pages rebuild |
| Import added | All affected pages rebuild | 0 pages rebuild |
| Docstring edited | Affected pages rebuild | Affected pages rebuild |
| Full rebuild (cold cache) | All pages | All pages (no change) |

**Estimated improvement**: 30-50% reduction in unnecessary autodoc rebuilds during development.

---

## Design Options

### Option 1: Docstring & Signature Hashing (Recommended)

Focus on hashing exactly what the user sees in the documentation. This is high-impact and relatively simple to implement.

**Pros**:
- Directly correlates with documentation visual changes.
- Implementation is straightforward within the existing `DocElement` structure.
- Low performance overhead.

**Cons**:
- May miss subtle implementation changes that affect dynamic doc generation (if any).

### Option 2: Full AST-based Symbol Hashing

Parse the AST for each symbol and hash the entire subtree related to that symbol (excluding function bodies).

**Pros**:
- Extremely robust; catches any change in the symbol's definition.
- Future-proof for more complex documentation generators.

**Cons**:
- Higher complexity to implement.
- Potentially slower due to extensive AST traversal and normalization.
- Diminishing returns over Option 1.

---

## Proposed Solution

### Phase 1: Symbol Content Hashing

Add docstring-level hashing that only considers documentation-relevant content.

**Normalization Strategy**:
- All docstrings are stripped of leading/trailing whitespace.
- Multiple internal newlines are collapsed to a single newline for hashing purposes.
- Signatures are normalized by removing optional whitespace between parameters.
- Decorators are sorted alphabetically before hashing.

```python
# New: bengal/autodoc/hashing.py

def compute_doc_content_hash(
    element: DocElement,
    *,
    include_signature: bool = True,
) -> str:
    """
    Compute hash of documentation-relevant content only.

    Normalization:
    - Docstrings: strip(), collapse redundant newlines.
    - Signatures: strip(), remove param spacing.
    - Decorators: sorted() alphabetically.

    Does NOT hash (Non-Goals):
    - Implementation code (function/method bodies)
    - Import statements not part of signatures
    - Comments outside docstrings
    - Internal type hints in function bodies
    """
    parts: list[str] = []

    # Docstring (the primary documentation content)
    if element.docstring:
        normalized_doc = "\n".join(l.strip() for l in element.docstring.strip().splitlines() if l.strip())
        parts.append(normalized_doc)

    # Signature (affects documentation display)
    if include_signature and element.signature:
        parts.append(element.signature.replace(" ", ""))

    # For classes: bases affect inheritance documentation
    if element.element_type == "class" and element.bases:
        parts.append("|".join(sorted(element.bases)))

    # Decorators (may affect documentation)
    if element.decorators:
        parts.append("|".join(sorted(element.decorators)))

    # Cross-file inheritance handling:
    # If this is a child class, the MRO is included to detect parent changes
    if hasattr(element, "mro") and element.mro:
        parts.append("|".join(element.mro))

    content = "\n".join(parts)
    return hash_str(content, truncate=16)
```

### Phase 2: Integration with Dependency Tracking

Modify `page_builders.py` to use doc content hash instead of file hash:

```python
# bengal/autodoc/orchestration/page_builders.py

# Current (file-level):
result.add_dependency(str(source_file_for_tracking), source_id)

# Enhanced (doc-content-level):
doc_hash = compute_doc_content_hash(element)
result.add_dependency(
    str(source_file_for_tracking),
    source_id,
    content_hash=doc_hash,  # New parameter
)
```

### Phase 3: Cache Structure Update

Extend `AutodocTrackingMixin` to store doc content hashes:

```python
# autodoc_tracking.py - Add to metadata

# Current: source_file → (file_hash, mtime)
autodoc_source_metadata: dict[str, tuple[str, float]]

# Enhanced: source_file → (file_hash, mtime, doc_hashes)
# Where doc_hashes = {page_path: doc_content_hash}
autodoc_source_metadata: dict[str, tuple[str, float, dict[str, str]]]
```

**Validation logic update**:

```python
def is_doc_content_changed(
    self,
    source_key: str,
    page_path: str,
    current_doc_hash: str,
) -> bool:
    """Check if documentation content changed (not just file)."""
    entry = self.autodoc_source_metadata.get(source_key)
    if not entry or len(entry) < 3:
        return True  # No doc hashes stored, assume changed

    _file_hash, _mtime, doc_hashes = entry
    stored_hash = doc_hashes.get(page_path)

    return stored_hash != current_doc_hash
```

---

## Implementation Plan

### Sprint 1: Doc Content Hashing (2-3 hours)

**Files to create/modify**:
- `bengal/autodoc/hashing.py` (new) — `compute_doc_content_hash()`
- `bengal/autodoc/orchestration/result.py` — Extend `add_dependency()` signature

**Tasks**:
1. Create `compute_doc_content_hash()` function
2. Add unit tests for hash stability
3. Verify hash changes only for doc-relevant changes

### Sprint 2: Integration (2-3 hours)

**Files to modify**:
- `bengal/autodoc/orchestration/page_builders.py` — Call `compute_doc_content_hash()`
- `bengal/cache/build_cache/autodoc_tracking.py` — Store doc hashes
- `bengal/orchestration/content.py` — Pass doc hashes to cache

**Tasks**:
1. Extend `add_dependency()` to accept content hash
2. Modify cache structure to store doc hashes
3. Update serialization for backward compatibility

### Sprint 3: Validation Logic (2-3 hours)

**Files to modify**:
- `bengal/cache/build_cache/autodoc_tracking.py` — `is_doc_content_changed()`
- `bengal/orchestration/incremental/taxonomy_detector.py` — Use doc content check

**Tasks**:
1. Implement `is_doc_content_changed()` method
2. Integrate with `check_autodoc_changes()`
3. Add fallback to file-level hash when doc hash unavailable

### Sprint 4: Testing (2 hours)

**Files to create/modify**:
- `tests/unit/autodoc/test_hashing.py` (new)
- `tests/unit/cache/test_autodoc_tracking.py` — Extend for doc hashes
- `tests/integration/test_incremental_cache_stability.py` — Add doc-level tests

**Test cases**:
```python
class TestDocContentHashing:
    def test_hash_stable_for_same_docstring(self): ...
    def test_hash_changes_for_docstring_edit(self): ...
    def test_hash_changes_for_signature_change(self): ...
    def test_hash_unchanged_for_import_change(self): ...
    def test_hash_unchanged_for_comment_change(self): ...
    def test_hash_unchanged_for_code_formatting(self): ...
```

---

## API Design

### compute_doc_content_hash

```python
def compute_doc_content_hash(
    element: DocElement,
    *,
    include_signature: bool = True,
    include_decorators: bool = True,
) -> str:
    """
    Compute hash of documentation-relevant content.

    Args:
        element: DocElement with docstring, signature, etc.
        include_signature: Include function/method signature in hash
        include_decorators: Include decorators in hash

    Returns:
        16-character truncated SHA-256 hash of doc content

    Example:
        >>> element = DocElement(
        ...     name="my_func",
        ...     docstring="Does something.",
        ...     signature="(x: int) -> str",
        ... )
        >>> compute_doc_content_hash(element)
        'a1b2c3d4e5f6g7h8'
    """
```

### Extended add_dependency

```python
def add_dependency(
    self,
    source_file: str,
    page_path: str,
    *,
    content_hash: str | None = None,  # NEW
) -> None:
    """
    Register a dependency between a source file and an autodoc page.

    Args:
        source_file: Path to the Python/OpenAPI source file
        page_path: Path to the generated autodoc page
        content_hash: Optional doc content hash for fine-grained detection
    """
```

---

## Migration Path

### Backward Compatibility

- **First build after upgrade**: Uses file-level hash (no doc hashes in cache)
- **Subsequent builds**: Uses doc-level hash (cache populated)
- **Cache format**: Backward compatible — old caches work, just less optimal

### Fallback Behavior

```python
# When doc hash unavailable, fall back to file hash
if doc_hash_available:
    changed = is_doc_content_changed(source, page, current_doc_hash)
else:
    changed = is_file_changed(source)  # Existing behavior
```

---

## Risks and Mitigations

### Risk 1: Hash Instability

**Risk**: Different extraction runs produce different hashes for same content.

**Mitigation**:
- Normalize whitespace in docstrings before hashing
- Sort decorators alphabetically
- Use stable representation for signatures

### Risk 2: Inheritance Changes

**Risk**: Parent class docstring changes don't trigger child rebuild.

**Mitigation**:
- Include MRO in hash for classes
- Track inheritance dependencies in `autodoc_dependencies`

### Risk 3: External Type References

**Risk**: Type hints referencing other modules not tracked.

**Mitigation**:
- Initially, consider this out of scope (file-level fallback handles it)
- Future: Extend dependency tracking to cross-module types

---

## Success Criteria

1. **Formatting changes skip rebuild**: `black` reformatting a Python file → 0 autodoc pages rebuilt
2. **Import changes skip rebuild**: Adding an import → 0 autodoc pages rebuilt  
3. **Docstring changes rebuild**: Editing a docstring → Only affected pages rebuilt
4. **No false negatives**: Signature changes always trigger rebuild
5. **Backward compatible**: Old caches continue to work

---

## Appendix: Existing Architecture Reference

### Autodoc File Structure (Actual)

```
bengal/autodoc/
├── __init__.py           # Public API exports
├── base.py               # DocElement, Extractor base class
├── config.py             # Configuration loading
├── docstring_parser.py   # Docstring parsing
├── utils.py              # Utility functions
├── extractors/
│   ├── python/           # Python AST extraction
│   │   ├── extractor.py  # Main PythonExtractor
│   │   ├── signature.py  # Signature parsing
│   │   └── ...
│   ├── cli.py            # CLI command extraction
│   └── openapi.py        # OpenAPI spec extraction
├── models/               # Typed metadata dataclasses
├── orchestration/
│   ├── orchestrator.py   # VirtualAutodocOrchestrator
│   ├── page_builders.py  # Page creation
│   ├── section_builders.py
│   └── result.py         # AutodocRunResult
└── fallback/             # Fallback templates
```

### Incremental Build File Structure

```
bengal/cache/build_cache/
├── autodoc_tracking.py   # AutodocTrackingMixin
└── core.py               # BuildCache

bengal/orchestration/incremental/
├── taxonomy_detector.py  # check_autodoc_changes()
├── change_detector.py    # IncrementalChangeDetector
└── filter_engine.py      # IncrementalFilterEngine
```

### Current Page Counts (Bengal Site)

| Type | Count | Notes |
|------|-------|-------|
| autodoc-python | ~726 | API reference pages |
| autodoc-cli | ~96 | CLI command pages |
| autodoc-rest | ~23 | REST API pages |
| **Total** | **~845** | |

---

## References

- [RFC: Output Cache Architecture](rfc-output-cache-architecture.md) — Parent caching strategy
- `bengal/cache/build_cache/autodoc_tracking.py` — Existing dependency tracking
- `bengal/orchestration/incremental/taxonomy_detector.py:351-442` — Existing selective rebuild
- `tests/unit/cache/test_autodoc_tracking.py` — Existing unit tests
