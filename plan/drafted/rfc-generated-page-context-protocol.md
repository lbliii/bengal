# RFC: Generated Page Context Protocol

**Status:** Drafted  
**Created:** 2025-03  
**Related:** Special page type fragility analysis

## Summary

Replace string-based dispatch for generated page context injection with a registry-based protocol using `PageKind` enum. Reduces fragility and enables extensibility for tag lists, tag pages, archives, and future generated page types.

## Problem

Special page types (tag, tag-index, archive, blog, etc.) have fragile output due to:

1. **String-based type dispatch** – `page.type == "tag"` scattered across renderer, content phases, finalization
2. **Multiple data sources** – `getattr(page, "tag_slug", None) or page.metadata.get("_tag_slug")`
3. **No defensive access** – `aggregate_content()` assumes `page.tags` exists
4. **Tag/tag-index not in content type registry** – Inconsistent template resolution

## Solution

### Phase 1: PageKind Enum + Generated Context Registry

- **PageKind** (`bengal/core/page/kind.py`): Canonical enum for page classification
- **from_page()**: Single source of truth for resolving kind from page metadata
- **GENERATED_CONTEXT_REGISTRY**: Maps PageKind → provider callable
- **get_generated_context(renderer, page)**: Registry dispatch for context injection

### Phase 2: Context Provider Refactor

- `_build_archive_page_context`, `_build_tag_page_context`, `_build_tag_index_page_context` return dicts
- Renderer registers providers at module load
- `_add_generated_page_context` delegates to registry

### Phase 3: Content Type Strategies

- **TagPageStrategy**, **TagIndexStrategy**: Added to CONTENT_TYPE_REGISTRY
- **normalize_page_type_to_content_type**: tag/tag-index now map to strategies

### Phase 4: Defensive Access

- **get_tags_safe(page)**: Safe tag access for mixed collections
- **aggregate_content()**: Uses get_tags_safe instead of page.tags

### Phase 5: Cleanup

- Remove debug print from site_wrappers.py
- Use PageKind in phase_update_pages_list, finalization

## Benefits

1. **Extensibility** – New generated page kinds: register provider, no renderer changes
2. **Type safety** – Enum dispatch instead of string comparison
3. **Single resolver** – PageKind.from_page() is canonical
4. **Consistency** – Tag pages use content type registry like blog/archive
5. **Robustness** – get_tags_safe prevents AttributeError on edge cases

## Files Changed

- `bengal/core/page/kind.py` (new)
- `bengal/core/utils/page_safe.py` (new)
- `bengal/rendering/context/generated_providers.py` (new)
- `bengal/rendering/renderer.py` (refactor)
- `bengal/orchestration/build/content.py` (PageKind)
- `bengal/orchestration/build/finalization.py` (PageKind)
- `bengal/core/section/ergonomics.py` (get_tags_safe)
- `bengal/content_types/registry.py` (tag, tag-index)
- `bengal/content_types/strategies.py` (TagPageStrategy, TagIndexStrategy)
- `bengal/rendering/context/site_wrappers.py` (remove debug print)
