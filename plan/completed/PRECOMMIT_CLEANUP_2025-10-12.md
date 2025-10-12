# Pre-commit cleanup plan (2025-10-12)

- Run pre-commit hooks repository-wide until clean:
  - ruff
  - ruff-format
  - end-of-file-fixer
  - trailing-whitespace
- Stage all modifications.
- Commit with message: "style: apply pre-commit fixes (ruff, format, eof, ws)".
- If hooks modify files during commit, re-run until no changes.

Status log:
- Created by automation.
