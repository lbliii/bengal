# RFC: CLI UX Polish (0.1.5)

**Status**: Draft
**Author**: AI Assistant
**Date**: 2025-11-26
**Related**: `plan/active/rfc-release-polish-v2.md`

---

## Executive Summary

Based on user feedback, the CLI experience has several friction points that can be addressed in the 0.1.5 release. This RFC proposes targeted UX improvements to reduce cognitive load, eliminate redundancy, and streamline the "zero to production" flow.

## Problem Statement

1.  **Command Ambiguity**: `bengal new site` and `bengal site new` exist simultaneously, causing user confusion.
2.  **False Optionality**: `questionary` is listed as a core dependency but the code treats it as optional with a "nag" warning.
3.  **Option Overload**: `bengal health linkcheck` exposes low-level HTTP options that obscure common usage.
4.  **Incomplete Init**: Users must manually edit `site.yaml` to set `baseurl` immediately after creation.
5.  **Validation Gaps**: Invalid arguments can cause raw stack traces instead of helpful errors.

## Proposed Changes

### 1. Unify Site Creation Workflow

**Goal**: Establish `bengal new` as the canonical entry point for creation.

- **Action**: Deprecate `bengal site new`.
- **Implementation**:
    - Add `hidden=True` to `bengal site new` command.
    - Add a `cli.warning()` if `bengal site new` is used, advising users to use `bengal new site` in the future.
    - Ensure docs only reference `bengal new site`.

### 2. streamline Dependencies

**Goal**: "Batteries Included" experience.

- **Action**: Treat `questionary` as a hard requirement.
- **Implementation**:
    - Remove `try/except ImportError` blocks for `questionary`.
    - Remove the "Install questionary" warning.
    - Since it's already in `pyproject.toml`, this is a code cleanup.

### 3. Simplify Health Check Interface

**Goal**: Progressive disclosure for `linkcheck`.

- **Action**: Hide advanced/low-level options from default help.
- **Implementation**:
    - Mark the following options as `hidden=True` (accessible but not cluttered):
        - `--max-concurrency`
        - `--per-host-limit`
        - `--timeout`
        - `--retries`
        - `--retry-backoff`
    - Keep high-value options visible: `--external-only`, `--internal-only`, `--exclude`, `--format`.

### 4. Complete Initialization

**Goal**: No manual config edits required for a basic start.

- **Action**: Prompt for `baseurl` during site creation.
- **Implementation**:
    - In `_create_site`, after prompting for `name`, prompt for `baseurl`.
    - Default to `https://example.com` (or `http://localhost:8000` if local dev context is detected/implied, though standard practice is prod URL).
    - Update `_create_config_directory` to accept and write this `baseurl`.

### 5. Robust Input Validation

**Goal**: Friendly error messages, no stack traces.

- **Action**: Add validation for common inputs.
- **Implementation**:
    - Ensure `name` and `baseurl` validation in `new site`.
    - Catch common exceptions in command entry points and route to `handle_cli_errors`.

## Implementation Plan

| Task | Priority | Effort | Files Affected |
|------|----------|--------|----------------|
| 1. Deprecate `site new` | P1 | 15m | `bengal/cli/commands/site.py` |
| 2. Enforce `questionary` | P1 | 10m | `bengal/cli/commands/new.py` |
| 3. Hide linkcheck options | P2 | 15m | `bengal/cli/commands/health.py` |
| 4. Add `baseurl` prompt | P1 | 30m | `bengal/cli/commands/new.py` |

**Total Effort**: ~1.5 hours

## Success Criteria

- [ ] `bengal site --help` does not list `new`.
- [ ] `bengal new site` prompts for `Base URL` (default: https://example.com).
- [ ] `bengal health linkcheck --help` fits on one screen without scrolling.
- [ ] No "Install questionary" warning ever appears.

