# Phase 2c: Cache Usage - Visual Overview

**Status**: PLANNING  
**Depends On**: Phase 2b ✅  
**Expected Completion**: ~7 days

## The Three Optimizations at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2C: THREE CACHE USAGE OPTIMIZATIONS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1️⃣  LAZY PAGE LOADING                                          │
│     Pages: Unchanged → PageProxy (metadata only)               │
│     Gain: ~75ms (skip parsing unchanged pages)                 │
│                                                                 │
│  2️⃣  INCREMENTAL TAG GENERATION                                 │
│     Tags: Compare cached → regenerate only changed              │
│     Gain: ~160ms (skip unchanged tag pages)                    │
│                                                                 │
│  3️⃣  SELECTIVE ASSET DISCOVERY                                  │
│     Assets: Include only those used by changed pages            │
│     Gain: ~80ms (skip processing unused assets)                │
│                                                                 │
│     TOTAL GAIN: ~315ms per incremental build                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Current Flow (Phases 2a + 2b)

```
INCREMENTAL BUILD FLOW:
├── Discover ALL pages (100% discovery)
│   └── 500ms disk I/O + parsing
├── Filter pages_to_build (find_work_early)
│   └── 30ms savings from Phase 2a
├── Render pages_to_build
├── Post-process (ALL tags, ALL assets)
│   └── Build-time: ~8-9 seconds total
└── Result: ~2-3 seconds saved (best case)
```

## Future Flow (After Phase 2c)

```
LAZY INCREMENTAL BUILD FLOW:
├── Discover content (mixed Page + PageProxy)
│   ├── Changed files → full Page objects
│   ├── Unchanged files → PageProxy (metadata only)
│   └── 75ms saved (skip parsing)
├── Filter pages_to_build
├── Render pages_to_build
│   ├── PageProxy auto-loads if touched during render
│   └── All proxy pages remain unloaded (not rendered)
├── Post-process:
│   ├── Tags: Generate only changed tags (160ms saved)
│   ├── Assets: Process only referenced assets (80ms saved)
│   └── Build-time: ~7-8 seconds total
└── Result: ~2-3 seconds saved (better consistency + foundation for future)
```

## The PageProxy Concept

```
┌─────────────────────────────────────────────────┐
│ PAGPROXY: Lazy-Loaded Page Placeholder          │
├─────────────────────────────────────────────────┤
│                                                 │
│  METADATA (loaded from cache):                  │
│  • source_path                                  │
│  • title                                        │
│  • date                                         │
│  • tags                                         │
│  • section                                      │
│  • slug                                         │
│  • weight                                       │
│  • lang                                         │
│                                                 │
│  FULL CONTENT (lazy-loaded on first access):   │
│  • content (markdown/raw)                       │
│  • metadata (full dict)                         │
│  • rendered_html                                │
│  • links                                        │
│  • version                                      │
│                                                 │
│  LOADING TRIGGER:                              │
│  • On-demand when property accessed             │
│  • Automatic: cache → disk → parse              │
│  • Transparent: calling code doesn't know      │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Performance Breakdown

| Operation | Current | With Phase 2c | Savings |
|-----------|---------|---------------|---------|
| Discover pages | 500ms | 425ms | 75ms |
| Build taxonomies | 200ms | 200ms | - |
| Generate tags | 250ms | 90ms | 160ms |
| Process assets | 300ms | 220ms | 80ms |
| Render pages | 400ms | 400ms | - |
| Total (incremental) | ~9000ms | ~8335ms | **~665ms** |

For 1000-page site with 10% changed: **~665ms faster per build**

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Lazy proxy breaks rendering | Medium | High | Thorough testing, prototype first |
| Async loading issues | Low | High | Keep synchronous, fully eager-load if touched |
| Asset discovery misses dependencies | Medium | Medium | Conservative: include assets transitively |
| Complex cascades fail with proxy | Low | Medium | Load full page if cascade detected |

## Implementation Roadmap

### Phase 2c.1: Lazy Page Loading (2-3 days)
- [ ] Create PageProxy class
- [ ] Update ContentDiscovery to use cache
- [ ] Wire into incremental builds
- [ ] Test rendering with mixed pages
- [ ] Performance benchmarking

### Phase 2c.2: Incremental Tag Generation (1 day)
- [ ] Add comparison logic to TaxonomyIndex
- [ ] Update tag generation to skip unchanged
- [ ] Wire into orchestrator
- [ ] Verify output matches Phase 2a

### Phase 2c.3: Selective Asset Discovery (2 days)
- [ ] Add asset filtering to AssetOrchestrator
- [ ] Implement conservative matching
- [ ] Add opt-out config flag
- [ ] Test with showcase site

### Integration & Testing (2 days)
- [ ] All 11 Phase 2b tests still pass
- [ ] 15+ new integration tests
- [ ] Benchmark builds
- [ ] Documentation updates

---

## Key Decisions

✅ **Keep discovery always full** (even with cache)
- Simpler to maintain
- Cache is metadata, not object store
- PageProxy makes this feasible

✅ **PageProxy uses cache + lazy disk access**
- Fast for metadata access (common case)
- Automatic full load if needed (safe)
- Transparent to calling code

✅ **Feature flags for all three optimizations**
- Can disable individually if issues found
- Gradual rollout strategy
- Safe defaults (all enabled)

---

## Success Metrics

After Phase 2c completion:

| Metric | Target | Current | Gain |
|--------|--------|---------|------|
| Incremental build time | ~8s | ~9s | 1s |
| Pages in memory | ~500MB | ~500MB | - |
| Disk I/O | 100MB | 200MB | 100MB less |
| Tag pages generated | ~10 | ~100 | 90% reduction |
| Assets processed | ~50 | ~200 | 75% reduction |
| Cache hit rate | 80-95% | 100%* | - |

*All pages discovered, but skipped during processing

---

## What Makes Phase 2c Special

Unlike typical SSGs, Bengal's Phase 2c:

1. **Keeps code simple** - Lazy loading is transparent
2. **Maintains correctness** - No cache consistency issues
3. **Enables future growth** - Foundation for distributed builds
4. **Has safety nets** - Feature flags, easy rollback
5. **Is testable** - Each component tested independently

The architecture is sound because:
- Caches persist (from Phase 2b)
- Lazy loading is on-demand (safe)
- Tag generation is deterministic (compare-before-regen)
- Asset discovery is conservative (include more, not less)

---

## Timeline

```
Week 1:
├─ Mon: Phase 2c.1 architecture & PageProxy
├─ Tue-Wed: Implement & test PageProxy
├─ Thu: Integrate into discovery
├─ Fri: Benchmark, fix issues

Week 2:
├─ Mon-Tue: Phase 2c.2 tag generation
├─ Wed: Phase 2c.3 asset discovery
├─ Thu: Integration tests
├─ Fri: Documentation & polish

Total: ~7 days active development
```

---

**Ready to start building Phase 2c!**

Next: Start with PageProxy (Phase 2c.1)
