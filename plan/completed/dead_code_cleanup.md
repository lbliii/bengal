# Dead Code Cleanup Plan

Generated: 2025-10-16
Analysis Tool: vulture (confidence >= 60%) with manual verification

## Summary

Initial vulture scan: **233 dead code items**
After Phase 1 & 2 cleanup: **164 dead code items**
Removed: **69 items (100% verified dead)**

## Items Removed (Phase 1 & 2)

### Fixed (Phase 1) - 11 items
- Removed 11 unused exception/loop variables marked 100% confidence
- Files: pygments_cache.py, resource_manager.py, atomic_write.py, logger.py, community_detection.py, cli extractors, response_wrapper.py

### Deleted (Phase 2) - 5 items  
1. `bengal/server/response_wrapper.py` - Entire deprecated file marked for removal
2. `bengal/cli/site_templates.py:27` - `PageTemplate` class (not in __all__, unused)
3. `bengal/cache/build_cache.py:18` - `ParsedContentCache` class (never instantiated)
4. `bengal/postprocess/output_formats.py:907` - `JsonSerializer` class (never used)
5. `bengal/rendering/plugins/tables.py` - Entire WIP stub file (marked as skeleton)

## False Positives Found

Many vulture 60% confidence items are false positives:

1. **CLI Commands** - Functions decorated with `@click.command()` or `@somegroup.command()`
   - Vulture doesn't recognize Click decorator pattern
   - Examples: `swizzle_list`, `swizzle_update`, `list_themes`

2. **Test-Only Functions** - Used only in test files
   - Examples: `truncate_middle`, `generate_excerpt`, `escape_html`, `humanize_bytes`
   - These ARE used, just not in main code

3. **Utility/Helper Methods** - Exposed in public module APIs
   - Examples: `analyze_page_importance`, `analyze_build`, `get_suggestions_by_target`
   - These are part of published APIs even if not called internally

4. **Dataclass/Protocol Properties** - Used for serialization/typing
   - Attributes set in __init__ or used by frameworks
   - Examples: `is_page`, `kind`, `draft`, `author`

5. **Template Functions** - Used in Jinja2 templates dynamically
   - Not visible in code search
   - Examples: Various functions in rendering/template_functions/

## Remaining Items (164)

Majority are legitimate library APIs that shouldn't be removed:
- Analysis methods (used for feature expansion)
- Template functions (used in templates)
- Utility functions (public API)
- Properties (serialization targets)

## Recommendation

**Current cleanup is complete for obvious dead code.**
Further removal would require:
1. API stability audit (which functions are public?)
2. Testing against documentation examples
3. Checking external consumer code  
4. Explicit deprecation cycle before removal

The low-hanging fruit has been harvested. Remaining items likely serve purposes not visible to static analysis.
