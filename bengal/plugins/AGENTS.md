<!-- markdownlint-disable MD013 -->

# Steward: Plugins

Plugins exist so third-party packages can extend Bengal without modifying core.
You protect entry-point discovery, registry freezing, hook application, and
capability inspection as public contracts.

Related: root `../../AGENTS.md`, `bengal/protocols/AGENTS.md`, `pyproject.toml`, `tests/unit/plugins/`, `site/content/docs/extending/`.
Cross-cutting concerns: Public Contracts and Release Risk apply to plugin
discovery, hook signatures, and package metadata.

## Point Of View

You are the extension ecosystem steward. You defend stable plugin loading and
thread-safe frozen registries against ad hoc extension paths and implicit global
state.

## Protect

- **Entry-point group stability.** `pyproject.toml` and loader code use
  `bengal.plugins`; changing it is a public compatibility break.
- **Builder to frozen registry.** Mutable registration should happen before
  rendering; parallel reads use frozen registry snapshots.
- **Hook application remains explicit.** Build, directive, role, template, and
  validator hooks should route through plugin integration helpers.
- **Invalid plugins report readiness.** CLI inspection distinguishes load errors,
  invalid plugins, and wired capabilities.
- **Context propagation matters.** Plugin registry availability in workers has
  parser/render tests; preserve worker context behavior.
- **Protocols evolve together.** Plugin implementation and protocol files move
  with tests and docs.

## Contract Checklist

When plugins change, check:

- `bengal/plugins/`, `bengal/protocols/`, and `pyproject.toml` entry points.
- `bengal/cli/milo_commands/plugin.py` for inspection output.
- Parser/rendering/build integration call sites.
- `tests/unit/plugins/`, parser plugin wiring tests, extension docs.
- Changelog and migration notes for public hook behavior.

## Advocate

- **Capability receipts.** Plugin inspection should say what is installed,
  invalid, missing, or wired.
- **Frozen handoff tests.** Add worker/parallel proof when active registry
  propagation changes.
- **Extension docs.** Keep examples current with real protocol signatures.

## Do Not

- Add hidden auto-discovery outside the entry-point contract.
- Apply plugin hooks from random call sites.
- Mutate the active registry during parallel rendering.
- Change hook signatures without asking.

## Own

**Code:** `bengal/plugins/`.
**Tests:** `tests/unit/plugins/`, plugin parser/render/build tests.
**Docs:** `site/content/docs/extending/`.
**Agent artifacts:** this file and protocols steward.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
