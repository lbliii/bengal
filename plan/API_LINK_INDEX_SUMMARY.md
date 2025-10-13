# API Link Index - Implementation Summary

**Status**: ✅ Planning Complete - Ready for Implementation  
**Date**: 2025-10-12  
**Version**: v2 (Refined)

## Quick Summary

**Goal**: Enable `[[api:Symbol]]` syntax for linking to API documentation with build-time validation.

**Approach**: Extend existing CrossReferencePlugin and merge into unified xref_index.

**Timeline**: 4 weeks (3 core + 1 optional)

**Value**: 80% of Sphinx's semantic linking with 20% of the complexity.

## Key Design Decisions

### ✅ Unified Plugin Architecture
- **Extend** `CrossReferencePlugin` instead of creating new plugin
- **Why**: Reduces overhead, simpler code, consistent UX

### ✅ Merged Index Structure
- Store API symbols in `xref_index['api_symbols']`
- **Why**: Single source of truth, better caching, simpler invalidation

### ✅ Build Phase Placement
- Build API index in Phase 2.5 (after sections, before taxonomies)
- **Why**: Ensures autodoc metadata is stable before indexing

### ✅ Performance-First
- O(1) lookups, < 1% build overhead
- Auto-linking is opt-in (adds ~2-3ms per page)
- **Why**: Maintains Bengal's speed advantage

## Architecture Overview

```
[[api:Site]]           →  CrossReferencePlugin
                          ↓
                       xref_index['api_symbols']['Site']
                          ↓
                       <a href="/api/bengal/core/site/">Site</a>
```

## Implementation Phases

### Phase 1: Core Index (Week 1)
- `bengal/autodoc/api_index.py` - Extract symbols from autodoc pages
- Integration into content orchestrator (Phase 2.5)
- Cache integration

### Phase 2: Plugin Enhancement (Week 2)
- Extend `CrossReferencePlugin` to support `[[api:...]]`
- Pattern: `\[\[(api:|id:)?([^\]|]+)(?:\|([^\]]+))?\]\]`
- Parser integration

### Phase 3: Validation (Week 3)
- `bengal/health/validators/api_links.py` - Detect broken refs
- Fuzzy matching for suggestions
- CLI error reporting

### Phase 4: Auto-Linking (Week 4) - Optional
- `bengal/rendering/plugins/auto_link_code.py` - Auto-link `ClassName`
- Opt-in via config (performance consideration)
- Caching for repeated symbols

## Usage Examples

### Basic Linking
```markdown
The [[api:Site]] class handles site building.
Use [[api:Site.build]] to start the build process.
Call [[api:bengal.core.site.Site.build]] for fully qualified reference.
```

### With Custom Text
```markdown
The [[api:Site|Site class]] is the main entry point.
```

### Configuration
```toml
[autodoc]
link_index = true           # Enable API linking (default: true)
auto_link_code = false      # Auto-link code blocks (default: false)

[build]
validate_api_links = true   # Validate at build time (default: true)
strict_api_links = false    # Fail build on broken links (default: false)
```

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Index Build | < 50ms for 100 modules | ⏱️ To measure |
| Lookup | < 0.1ms per reference | ⏱️ To measure |
| Build Overhead | < 1% | ⏱️ To measure |
| Auto-linking | < 3ms per page | ⏱️ To measure |

## Testing Strategy

- **Unit Tests**: 95%+ coverage for new code
- **Integration Tests**: Full autodoc → index → render → validate flow
- **Performance Tests**: Benchmark on Bengal's 99 modules
- **Edge Cases**: Ambiguous symbols, broken refs, nested classes

## Success Criteria

- ✅ Index builds in < 50ms for 100 modules
- ✅ O(1) lookup performance
- ✅ < 1% build time overhead
- ✅ 95%+ test coverage
- ✅ Broken links caught at build time
- ✅ Helpful suggestions for typos/ambiguity
- ✅ Documentation with examples

## Key Changes from Original Plan

| Aspect | Original | Refined | Benefit |
|--------|----------|---------|---------|
| Plugin | New APILinkPlugin | Extend CrossReferencePlugin | Simpler, faster |
| Index | Separate api_index | Merge into xref_index | Single source of truth |
| Phase | After discovery | Phase 2.5 | Metadata stability |
| Timeline | 5 weeks | 4 weeks | Faster delivery |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Performance regression | Benchmark continuously, use efficient data structures |
| Ambiguous symbols | Detect and warn, show qualified name suggestions |
| Cache bugs | Hash autodoc files, validate on load |

## Next Steps

1. Create feature branch: `feat/api-link-index`
2. Implement Phase 1 (Core Index)
3. Run performance benchmarks on Bengal's codebase
4. Iterate based on measurements
5. Document usage patterns

## References

- **Refined Plan**: `plan/active/API_LINK_INDEX_REFINED.md`
- **Original Plan**: `plan/completed/API_LINK_INDEX_ORIGINAL.md`
- **Architecture**: `ARCHITECTURE.md`
- **Cross-References**: `bengal/rendering/plugins/cross_references.py`

---

**Status**: Ready for implementation 🚀
