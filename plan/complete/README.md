<!-- markdownlint-disable MD013 -->

# Completed Plan Archive

Updated: 2026-06-17

Individual completed RFC bodies were removed after this distillation pass. Their
implementation state is now better verified from source, tests, `CHANGELOG.md`,
and release notes than from stale implementation sketches.

## Shipped Themes

- CLI/DX: Agent DX polish, upgrade notifications, cache inputs/hash commands,
  ty diagnostic reduction, command output templates, and graceful error
  communication.
- Build/cache/incremental: cache invalidation, rebuild decisions, global build
  state dependencies, pipeline input/output contracts, output cache,
  dev-server buffer hardening, and reactive dev-server work.
- Cache/provenance 2026-05-24 slice: provenance load diagnostics, POSIX output
  keys, O(1) output-dir emptiness checks, `BuildCache` recovery signaling,
  mtime short-circuiting, generated-page cache conservative misses, and autodoc
  doc-content hash tracking have shipped; remaining dependency-index work stays
  in the active root RFC.
- Rendering/templates: template object model, template error codes and overlay,
  directive base CSS, theme ecosystem phase 1, default/chirpui theme work, and
  Kida-related rendering fixes.
- Parsing/content/autodoc: Patitas extraction/performance/CommonMark work,
  container stack parsing, external references, OpenAPI filter unification, REST
  autodoc layouts (#289), and advanced schema rendering (#285).
- CSS minifier: tokenizer-based `bengal/css/` engine (#510); legacy heuristic
  minifier removed.
- First-party knowledge graph: D3 dropped; build-time layout + canvas explorer
  (v0.5.1).
- Pridelands theme (partial): zero-CDN capabilities (#533), OKLCH palettes
  (#534), `light-dark()` dark mode (#535), SEO structured data (#536), custom
  elements (#537) — epic #532 still open for remaining child sagas.
- Ty floor: 531 → 424 via `SiteLike.config_service` + graph nullable guards
  (#292 — close issue on PR).
- Immutable Page pipeline: SourcePage, ParsedPage, and RenderedPage exist as
  frozen records; PageProxy and the mutable `Page` compatibility class are
  deleted; public `bengal.Page` and `bengal.core.Page` re-exports are retired.
- Utility leaf hygiene: most low-risk `utils/primitives` cleanups shipped,
  including text helper tightening, `DotDict` contract docs, retry cleanup, date
  format reuse, and async/thread-local lazy initialization improvements.
- Testing/release quality: behavioral test hardening, package separation,
  stale-code refresh, i18n production readiness, and release smoke coverage.

## How To Use This

Treat this directory as a pointer, not proof. If a completed idea matters for
new work, verify the current behavior in `bengal/`, `tests/`, docs, and
`CHANGELOG.md`. Do not resurrect old body text as requirements without a fresh
source audit.
