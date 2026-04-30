# Errors Steward

Errors are documentation for people under stress. Bengal errors should identify
what broke, where it broke, and what the author can do next.

Related architecture docs:

- `../../AGENTS.md`

## Protect

- `BengalError` with `code`, `context`, `suggestion`, and `debug_payload`.
- Reader-facing messages with concrete next steps.
- Diagnostics that preserve source path and phase context.
- Error rendering that does not introduce rendering/core import cycles.

## Do Not

- Add silent `except Exception: pass`.
- Replace actionable errors with generic `ValueError` or raw tracebacks.
- Log directly from `bengal/core/`.
- Hide malformed user input behind fallback behavior.

## Documentation Ownership

- Own `site/content/docs/reference/errors/`.
- Keep troubleshooting docs, including `site/content/docs/building/troubleshooting/template-errors.md`, aligned with user-facing errors.
- Update examples when `BengalError` context, codes, or suggestions change.

## Local Checks

- `uv run pytest tests/unit/errors tests/unit/health -q`
- `uv run ruff check bengal/errors tests/unit/errors`
- Search for broad exception handling when touching error paths.
