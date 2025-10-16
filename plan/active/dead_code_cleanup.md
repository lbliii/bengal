# Dead Code Cleanup Plan

Generated: 2025-10-16
Analysis Tool: vulture (confidence >= 60%)

## Summary

Found **233 dead code items** across the codebase:
- 100% Confidence (Unused Variables): 11 items
- 60% Confidence: 222 items

## Categories of Dead Code

### 1. Unused Variables (100% Confidence) - 11 items
**Safe to remove** - Variables assigned but never used:
- `bengal/analysis/community_detection.py:311` - `from_community` variable
- `bengal/autodoc/extractors/cli.py:96` - `is_root` variable
- `bengal/rendering/pygments_cache.py:245` - `exc` variable
- `bengal/server/resource_manager.py:215` - `exc_tb`, `exc_val` variables
- `bengal/server/response_wrapper.py:24` - `modified_data` variable
- `bengal/utils/atomic_write.py:172` - `exc_tb`, `exc_val` variables
- `bengal/utils/logger.py:213` - `event_type` variable
- `bengal/utils/logger.py:374` - `exc_tb`, `exc_val` variables

### 2. Unused Methods - 75 items
Candidates for removal (methods not called elsewhere):
- **analysis/**: 9 methods (get_top_pages_by_degree, get_largest_communities, get_leaves, etc.)
- **autodoc/**: 3 config getter functions
- **cache/**: 7 methods in build_cache and dependency_tracker
- **cli/**: 5 functions and classes (swizzle_*, list_themes, menu functions)
- **core/**: 9 methods (cascade, metadata properties, operations, relationships)
- **orchestration/**: 4 methods
- **postprocess/**: 3 methods
- **rendering/**: 20+ methods (HTML parsers, enhancers, validators)
- **server/**: 8 methods
- **utils/**: 25+ methods

### 3. Unused Functions - 28 items
Top-level functions not called:
- `bengal/analysis/page_rank.py:253` - analyze_page_importance
- `bengal/analysis/performance_advisor.py:483` - analyze_build
- `bengal/autodoc/utils.py:58` - truncate_text
- And many utility functions

### 4. Unused Classes - 6 items
- `bengal/cache/build_cache.py:17` - ParsedContentCache
- `bengal/cli/site_templates.py:27` - PageTemplate
- `bengal/cli/templates/base.py:40` - TemplateProvider
- `bengal/postprocess/output_formats.py:907` - JsonSerializer
- `bengal/rendering/plugins/tables.py:24` - TablePlugin
- `bengal/services/validation.py:7` - TemplateValidationService

### 5. Unused Variables/Constants - 30+ items
- Constants not used (OPTIMIZATION, MAX_NESTING_DEPTH, MIN_SIZE, etc.)
- Unused attributes (fonts_time_ms, _affected_tags, health_report, etc.)

## Cleanup Strategy

**Phase 1 - 100% Confidence (Low Risk)**
- Remove unused variable assignments in except/exit blocks
- Remove unused loop variables

**Phase 2 - Analysis Module (Lower Risk)**
- This module appears to be analytical/experimental features
- Remove unused analysis methods that aren't exposed in public API

**Phase 3 - Cache/Dependency Tracking (Medium Risk)**
- Review which methods are truly unused vs. potentially used internally
- Verify against tests before removal

**Phase 4 - CLI/Config (Medium Risk)**
- Confirm CLI functions aren't referenced elsewhere
- Check if config functions are used by external consumers

**Phase 5 - Rendering/Utils (Higher Risk)**
- Review rendering methods carefully - may be used by plugins
- Utils functions might be used for backward compatibility

## Removal Order

1. Start with 100% confidence items (safest)
2. Move to obvious dead code (unused methods in non-critical modules)
3. Test thoroughly after each phase
4. Get code review for higher-risk removals
