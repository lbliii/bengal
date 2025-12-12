# JS Loading Strategy (Deferred)

**Status**: Deferred  
**Reason**: Dynamic loading broke graph initialization  
**Deferred**: 2025-11-26

---

## Summary

RFC proposed conditional JS loading for D3.js and Mermaid to reduce page load times.

## What Was Attempted

Commit `23051d2` shows dynamic script loading was implemented but then reverted:
- D3.js and Mermaid loaded conditionally based on container presence
- Graph components failed to initialize reliably in production builds
- Race conditions between script loading and component initialization

## Decision

Static JS loading is intentionally used for reliability:
- D3.js and Mermaid load on every page
- Graph initialization is reliable
- Trade-off: slightly larger page payload vs guaranteed functionality

## Future Consideration

Could revisit with:
- ES modules with `type="module"` and `import()`
- Framework-level lazy loading (if Bengal adopts a JS build step)
- Web Components with shadow DOM encapsulation

For now, reliability > performance optimization.

## Related

- Commit `23051d2` - Reverted dynamic to static loading
- Original RFC: `plan/active/rfc-js-loading-strategy.md` (deleted)
