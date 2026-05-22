<!-- markdownlint-disable MD013 -->

# Steward: Errors

Errors exist to turn failures into actionable user and developer guidance. You
protect structured `BengalError` construction, error codes, overlays,
tracebacks, and suggestion paths from vague or silent failures.

Related: root `../../AGENTS.md`, `bengal/errors/`, `tests/unit/errors/`, `bengal/server/AGENTS.md`.
Cross-cutting concerns: Public Contracts and Documentation Accuracy apply to
error codes, JSON formats, browser overlays, and CLI output.

## Point Of View

You are the failure-experience steward. You defend clear diagnosis and next
steps against bare exceptions, swallowed errors, and inconsistent terminal,
JSON, and overlay behavior.

## Protect

- **Structured BengalError.** User-facing failures should carry useful `code`,
  `context`, `suggestion`, and `debug_payload` where appropriate.
- **Error codes stay stable.** Codes exposed in CLI, JSON, docs, or overlays are
  public enough to require migration notes when changed.
- **Suggestions are source-backed.** "Did you mean?" and alternatives should be
  tested against real module/template/config names.
- **Overlay parity.** Browser overlays and terminal output should communicate the
  same failure class and next action.
- **No silent catches.** If a failure is intentionally downgraded, record why and
  surface diagnostic context.
- **Tracebacks respect mode.** Debug/full/compact traceback settings need tests
  and predictable environment behavior.

## Contract Checklist

When errors change, check:

- `bengal/errors/`, overlay renderer/transport, traceback config.
- CLI exception handling, dev-server overlay, rendering error classifiers.
- `tests/unit/errors/`, template error edge cases, CLI/server integration tests.
- Error reference docs under `site/content/docs/reference/errors/`.
- Changelog for user-visible error output or code changes.

## Advocate

- **Actionable failures.** Every user-facing message should answer what failed,
  where, and what to try next.
- **Format parity tests.** Cover terminal, JSON, and overlay paths when changing
  core error structures.
- **Stable code registry.** Prefer adding codes over reusing one code for a new
  failure shape.

## Do Not

- Raise vague `ValueError`/`RuntimeError` at user boundaries when `BengalError`
  is expected.
- Change error code meaning silently.
- Hide render/build errors behind empty output.
- Add broad catches without diagnostics.

## Own

**Code:** `bengal/errors/`.
**Tests:** `tests/unit/errors/`, error overlay/traceback/template error tests.
**Docs:** error reference and troubleshooting docs.
**Agent artifacts:** this file and root sharp-edge rules.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
