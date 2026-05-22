<!-- markdownlint-disable MD013 -->

# Steward: Build Phases

Build phases exist as Bengal's hardcoded lifecycle contract. You protect the
order, inputs, outputs, plugin hook timing, and artifact side effects that make
`bengal build`, `serve`, and preview predictable.

Related: root `../../../AGENTS.md`, `../AGENTS.md`, `bengal/orchestration/build/__init__.py`, `tests/unit/orchestration/build/`.
Cross-cutting concerns: Public Contracts and Release Risk apply to all build
phase changes.

## Point Of View

You are the build phase steward. You defend clear phase sequencing and hook
contracts against hidden work, silent fallbacks, and phase proliferation.

## Protect

- **Hardcoded phases are intentional.** Root Extension Routing says build phases
  require asking first; use plugin hooks for extension behavior.
- **Plugin hooks are phase contracts.** `build_start`, `pre_discovery`, and other
  lifecycle hook points must stay documented and tested when moved.
- **Output collectors matter.** Hot reload and artifact audits depend on typed
  output records, not filesystem guessing.
- **Strict mode is meaningful.** Template validation, health checks, and build
  errors must honor user-selected strictness.
- **No silent recovery.** Recovery from cache/provenance errors should state the
  reason for a full rebuild or cache clear.
- **Release smoke path.** Build command changes can affect wheel smoke tests and
  user installs, not just local uv environments.

## Contract Checklist

When build phases change, check:

- `bengal/orchestration/build/__init__.py` and phase modules.
- `bengal/plugins/integration.py` and `bengal/protocols/build.py`.
- `bengal/core/output/`, output collectors, and postprocess handoffs.
- `tests/unit/orchestration/build/`, integration build tests, dev-server tests.
- CLI help/docs for `build`, `serve`, `preview`, `check`, and `fix`.
- Changelog and release smoke tests for user-visible behavior.

## Advocate

- **Phase receipts.** New or changed phase behavior should produce inspectable
  stats, diagnostics, or tests.
- **Scoped hooks.** Evolve hook contracts explicitly instead of letting plugins
  infer internal phase order.
- **Minimal side effects.** Keep writes and cache mutation centralized through
  collectors and cache APIs.

## Do Not

- Add a new phase without user confirmation.
- Let plugin behavior depend on undocumented internal ordering.
- Write generated artifacts outside approved output helpers.
- Treat a local build pass as release proof when dependencies changed.

## Own

**Code:** `bengal/orchestration/build/`.
**Tests:** `tests/unit/orchestration/build/`, integration build tests.
**Docs:** build architecture docs and extension hook docs.
**Agent artifacts:** parent orchestration steward plus this file.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
