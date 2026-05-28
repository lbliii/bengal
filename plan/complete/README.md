<!-- markdownlint-disable MD013 -->

# Completed Plan Archive

Updated: 2026-05-28

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
- Rendering/templates: template object model, template error codes and overlay,
  directive base CSS, theme ecosystem phase 1, default/chirpui theme work, and
  Kida-related rendering fixes.
- Parsing/content/autodoc: Patitas extraction/performance/CommonMark work,
  container stack parsing, external references, OpenAPI filter unification, and
  REST autodoc layouts.
- Testing/release quality: behavioral test hardening, package separation,
  stale-code refresh, i18n production readiness, and release smoke coverage.

## How To Use This

Treat this directory as a pointer, not proof. If a completed idea matters for
new work, verify the current behavior in `bengal/`, `tests/`, docs, and
`CHANGELOG.md`. Do not resurrect old body text as requirements without a fresh
source audit.
