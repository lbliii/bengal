# Enforce Python 3.14 for Tests

## Overview
This plan ensures all pytest runs use Python 3.14+ to align with Bengal's requirements and avoid compatibility issues seen in 3.12 tests.

## Implemented Steps
1. **Venv Preparation**: Verified `venv-3.14` exists and has dev deps installed.
2. **Test Runner Script**: Created `scripts/run-tests.sh` to activate venv and run `python -m pytest`.
3. **Documentation**: Added section to `GETTING_STARTED.md` guiding users.
4. **CI Workflow**: Added `.github/workflows/tests.yml` locking to Python 3.14.
5. **Linting Scripts**: Suggested `scripts/lint.sh` for ruff/mypy (optional follow-up).

## Verification
- Local: `./scripts/run-tests.sh --version` should show Python 3.14.
- CI: Triggers on push/PR, runs tests in 3.14.

## Next
- Test the script: Run `./scripts/run-tests.sh -v` and confirm version.
- Move to `plan/completed/` after validation.
- Atomic commit: "setup: enforce Python 3.14 for tests via script and CI".
