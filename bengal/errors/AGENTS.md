# Errors Steward

Errors are documentation for people under stress. Bengal errors should identify
what broke, where it broke, and what the author can do next.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/errors/`
- `../../site/content/docs/building/troubleshooting/`

## Point Of View

Errors represent the author at the moment Bengal failed them. Messages should
preserve context, avoid blame, and provide a credible next action.

## Protect

- `BengalError` with `code`, `context`, `suggestion`, and `debug_payload`.
- Reader-facing messages with concrete next steps.
- Diagnostics that preserve source path, phase, and user input context.
- Error rendering that does not introduce rendering/core import cycles.

## Contract Checklist

- Error tests under `tests/unit/errors/`, health/report tests, and CLI error
  display tests.
- Error reference docs, troubleshooting docs, and examples using error codes.
- Changelog/migration notes when error codes or structured fields change.
- Import-cycle checks when display/rendering code moves.

## Advocate

- Error codes and suggestions for recurring author mistakes.
- Aggregated diagnostics that avoid hiding individual failures.
- Tests for malformed input, not just happy-path formatting.

## Serve Peers

- Give CLI and health structured errors that render consistently.
- Give docs stable codes and troubleshooting paths.
- Give core a diagnostic sink instead of direct logging.

## Do Not

- Add silent `except Exception: pass`.
- Replace actionable errors with generic `ValueError` or raw tracebacks.
- Log directly from `bengal/core/`.
- Hide malformed user input behind fallback behavior.

## Own

- `site/content/docs/reference/errors/`
- Troubleshooting docs, including template error docs
- Tests: `tests/unit/errors/`, CLI error tests, health error paths
- Checks: `uv run pytest tests/unit/errors tests/unit/health tests/unit/cli/test_error_display.py -q`
- Checks: `uv run ruff check bengal/errors tests/unit/errors`
- Search for broad exception handling when touching error paths.
