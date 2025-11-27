# RFC: CLI UX Polish (0.1.5)

**Status**: Ready for Implementation
**Author**: AI Assistant
**Date**: 2025-11-26
**Related**: `plan/active/rfc-release-polish-v2.md`
**Supersedes**: `plan/deferred/dependency-optimization.md` Phase 6 (questionary optional) - decided to keep as core dependency

---

## Executive Summary

Based on user feedback, the CLI experience has several friction points that can be addressed in the 0.1.5 release. This RFC proposes targeted UX improvements to reduce cognitive load, eliminate redundancy, and streamline the "zero to production" flow.

## Problem Statement

1. **Command Ambiguity**: `bengal new site` and `bengal site new` exist simultaneously, causing user confusion.
2. **False Optionality**: `questionary` is listed as a core dependency (`pyproject.toml:42`) but the code treats it as optional with a "nag" warning (`new.py:273-278`).
3. **Option Overload**: `bengal health linkcheck` exposes 13 CLI options, many of which are low-level HTTP tuning that obscure common usage.
4. **Incomplete Init**: Users must manually edit `site.yaml` to set `baseurl` immediately after creation (told to do so at `new.py:543`).

## Proposed Changes

### 1. Unify Site Creation Workflow

**Goal**: Establish `bengal new` as the canonical entry point for creation.

- **Action**: Deprecate `bengal site new`.
- **Implementation**:
    - Add `hidden=True` to `bengal site new` command in `site.py:23`.
    - Add a `cli.warning()` if `bengal site new` is used, advising users to use `bengal new site`.
    - Ensure docs only reference `bengal new site`.

**Evidence**:
- `site.py:23-69` - Current `site new` command
- `new.py:553-584` - Current `new site` command  
- Both delegate to `_create_site()` at `new.py:370`

### 2. Enforce `questionary` as Core Dependency

**Goal**: "Batteries Included" experience - no optional dependency warnings for core features.

- **Action**: Remove try/except fallback since `questionary` is already a hard requirement.
- **Implementation**:
    - Remove `try/except ImportError` block at `new.py:273-278`
    - Import `questionary` at module level with other imports
    - Delete the "Install questionary" warning message

**Rationale**: The interactive wizard is a key differentiator for Bengal's UX. Since `questionary` is already in core dependencies, the fallback code is dead code that creates confusion.

**Note**: This supersedes `plan/deferred/dependency-optimization.md` Phase 6 which proposed making questionary optional. Decision: keep as core for better UX.

### 3. Simplify Health Check Interface

**Goal**: Progressive disclosure for `linkcheck` - show common options, hide advanced tuning.

Current options (13 total) at `health.py:37-104`:

| Option | Visibility | Rationale |
|--------|------------|-----------|
| `--external-only` | **Visible** | Common filtering |
| `--internal-only` | **Visible** | Common filtering |
| `--exclude` | **Visible** | Common filtering |
| `--format` | **Visible** | Output control |
| `--output` | **Visible** | CI/CD integration |
| `--max-concurrency` | Hidden | HTTP tuning |
| `--per-host-limit` | Hidden | HTTP tuning |
| `--timeout` | Hidden | HTTP tuning |
| `--retries` | Hidden | HTTP tuning |
| `--retry-backoff` | Hidden | HTTP tuning |
| `--exclude-domain` | Hidden | Advanced filtering |
| `--ignore-status` | Hidden | Advanced filtering |
| `--traceback` | Hidden | Debug |

- **Implementation**: Add `hidden=True` to the 8 options marked "Hidden" above.
- **Result**: `--help` shows 5 options instead of 13.

### 4. Complete Initialization with `baseurl` Prompt

**Goal**: No manual config edits required for a basic start.

- **Action**: Prompt for `baseurl` during site creation.
- **Implementation**:
    1. In `_create_site()` after prompting for `name` (around line 391), prompt for `baseurl`
    2. Default to `https://example.com` with clear placeholder text
    3. Validate input (must be valid URL or empty)
    4. Pass `baseurl` to `_create_config_directory()` (update signature at line 68)
    5. Use provided `baseurl` instead of hardcoded default at line 87

**Files Affected**:
- `bengal/cli/commands/new.py` - `_create_site()` and `_create_config_directory()`

## Implementation Plan

| Task | Priority | Effort | Files Affected |
|------|----------|--------|----------------|
| 1. Deprecate `site new` | P1 | 15m | `bengal/cli/commands/site.py` |
| 2. Enforce `questionary` | P1 | 10m | `bengal/cli/commands/new.py` |
| 3. Hide linkcheck options | P2 | 20m | `bengal/cli/commands/health.py` |
| 4. Add `baseurl` prompt | P1 | 45m | `bengal/cli/commands/new.py` |
| 5. Manual testing | P1 | 30m | N/A |

**Total Effort**: ~2 hours

## Success Criteria

- [ ] `bengal site --help` does not list `new` subcommand
- [ ] `bengal site new mysite` shows deprecation warning pointing to `bengal new site`
- [ ] `bengal new site` prompts for `Base URL` after site name (with default: `https://example.com`)
- [ ] `bengal health linkcheck --help` shows ≤6 options (currently 13)
- [ ] No "Install questionary" warning ever appears
- [ ] Created site's `config/_default/site.yaml` contains user-provided baseurl

## Testing Checklist

### Task 1: Deprecate `site new`
```bash
# Should not show 'new' in help
bengal site --help

# Should work but show deprecation warning
bengal site new test-site --no-init

# Should work without warning
bengal new site test-site --no-init
```

### Task 2: Enforce `questionary`
```bash
# Should not show any questionary warning
bengal new site  # Interactive mode
```

### Task 3: Hide linkcheck options
```bash
# Should show ~5 options, not 13
bengal health linkcheck --help

# Hidden options should still work
bengal health linkcheck --timeout 30 --retries 5
```

### Task 4: `baseurl` prompt
```bash
# Should prompt for name AND baseurl
bengal new site

# Verify config has correct baseurl
cat my-site/config/_default/site.yaml | grep baseurl
```

## Rollback Plan

All changes are additive/cosmetic. Rollback by:
1. Remove `hidden=True` flags
2. Restore try/except block for questionary
3. Remove baseurl prompt logic

No data migrations or breaking changes.
