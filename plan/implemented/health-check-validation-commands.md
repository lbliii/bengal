# Health Check: Validation Commands (Implemented)

**Status**: Implemented  
**Completed**: 2025-11-26  
**Release**: 0.1.5 (Unreleased)

---

## Summary

Implemented standalone validation and auto-fix commands for Bengal health checks.

## What Was Implemented

### `bengal validate` Command

```bash
bengal validate [OPTIONS] [SOURCE]

Options:
  --file PATH          Validate specific files (multiple)
  --changed            Only validate changed files
  --watch              Watch mode: validate on file changes
  --profile            Build profile (writer, theme-dev, developer)
  --verbose            Show all checks, not just problems
  --incremental        Use cached validation results
  --suggestions        Show quality suggestions
```

### `bengal fix` Command

```bash
bengal fix [OPTIONS] [SOURCE]

Options:
  --validator          Only fix issues from specific validator
  --dry-run            Show what would be fixed
  --confirm            Ask for confirmation before fixing
  --all                Apply all fixes including confirmable ones
```

### AutoFixer Framework

- `AutoFixer` class in `bengal/health/autofix.py`
- `FixAction` dataclass for fix operations
- `FixSafety` enum (SAFE, CONFIRM, MANUAL)
- Directive fence nesting auto-fix (SAFE level)

### Progressive Severity

- `CheckResult.suggestion()` method
- `is_actionable()` helper
- `--suggestions` flag for quality improvements
- Suggestions collapsed by default in reports

### Incremental Validation

- `BuildCache.validation_results` field
- `CheckResult` serialization (`to_cache_dict`/`from_cache_dict`)
- Cache-aware validation in `HealthCheck.run()`
- `BuildCache.VERSION` bumped to 2

## Files Changed

- `bengal/cli/commands/validate.py` (new)
- `bengal/cli/commands/fix.py` (new)
- `bengal/health/autofix.py` (new)
- `bengal/health/check_result.py` (updated)
- `bengal/health/health_check.py` (updated)
- `bengal/health/report.py` (updated)
- `bengal/cache/build_cache.py` (updated)

## Related Plans

- Original: `plan/active/health-check-strategy.md` (deleted)

