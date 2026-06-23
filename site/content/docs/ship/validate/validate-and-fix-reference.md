---


title: Validate and Fix Reference
nav_title: Validation Reference
description: Auto-fix workflows, custom validators, health config, and troubleshooting
weight: 11
icon: wrench
tags:
- persona-operator
- reference
aliases:
  - /docs/content/validation/validate-and-fix-reference/
aliases:
  - /docs/ship/validate/validate-and-fix-reference/
  - /docs/content/validation/validate-and-fix-reference/
---

# Validate and Fix Reference

Auto-fix commands, custom validators, health configuration, and troubleshooting.

:::{note}
**Do I need this?** Use when wiring CI, writing custom validators, or tuning
health config. For day-to-day checks, see
[[docs/ship/validate/validate-and-fix|Validate and Fix]].
:::

## Auto-Fix

### Preview Fixes

Always preview before applying:

```bash
bengal fix --dry-run
```

**Output:**

```
🔧 Auto-Fix (dry run)

Found 3 fix(es):
  • 2 safe (can be applied automatically)
  • 1 requires confirmation

Safe fixes:
  • Fix unclosed code fence at content/tutorials/setup.md:45
  • Add missing closing tag at content/api/reference.md:112

Would apply 2 fixes. Run without --dry-run to apply.
```

### Apply Fixes

```bash
# Apply safe fixes only (default)
bengal fix

# Apply all fixes including those needing confirmation
bengal fix --all

# Ask before each fix
bengal fix --confirm

# Fix specific validator only
bengal fix --validator Directives
```

### Fix Categories

| Safety | Description | Auto-Apply |
|--------|-------------|------------|
| **Safe** | Reversible, no side effects | ✅ Yes |
| **Confirm** | May have side effects | Needs `--all` or `--confirm` |
| **Unsafe** | Requires manual review | Never auto-applied |

### Common Auto-Fixes

**Directives:**
- Missing closing fences (`:::` or `` ``` ``)
- Incorrect fence syntax
- Invalid directive options

**Links:**
- Update paths for renamed files
- Fix relative link depth
- Correct asset references

**Frontmatter:**
- Fix YAML syntax errors
- Add missing required fields
- Correct date formats

---

## Custom Validators

Create project-specific validation rules:

```python
# validators/require_author.py
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, Severity

class RequireAuthorValidator(BaseValidator):
    """Ensure all blog posts have an author."""

    name = "Author Required"
    description = "Validates that blog posts have author metadata"

    def validate(self, site, build_context=None):
        results = []

        for page in site.pages:
            # Only check blog posts
            if not page.section or page.section.name != "blog":
                continue

            if not page.metadata.get("author"):
                results.append(CheckResult(
                    severity=Severity.ERROR,
                    message=f"Missing author in {page.source_path}",
                    recommendation="Add 'author: Your Name' to frontmatter",
                    file_path=page.source_path,
                    line_number=1,
                ))

        return results
```

### Register Custom Validator

```python
# bengal.py (site configuration)
from validators.require_author import RequireAuthorValidator

validators = [
    RequireAuthorValidator(),
]
```

### Severity Levels

| Severity | Meaning | Strict Mode |
|----------|---------|-------------|
| `ERROR` | Must fix | Fails build |
| `WARNING` | Should fix | Fails build |
| `INFO` | Consider fixing | Passes |
| `DEBUG` | Developer info | Hidden |

---

## Configuration

### Disable Validators

```yaml
# config/_default/health.yaml
health:
  validators:
    links:
      enabled: true
      external: false    # Skip external link checks
    performance:
      enabled: false     # Disable performance checks
```

### Link Check Settings

```yaml
health:
  linkcheck:
    external: true
    max_concurrency: 10
    timeout: 30
    retries: 2
    exclude:
      - "https://example.com/private/*"
    exclude_domains:
      - "localhost"
      - "*.internal.company.com"
```

### Validation Profiles

Different validation for different contexts:

```bash
# Full validation (CI)
bengal check --verbose

# Quick validation (local dev)
bengal check --changed

# Pre-deploy validation
bengal inspect links && bengal build --strict
```

Available profiles:

| Profile | Use Case | Checks |
|---------|----------|--------|
| `writer` | Content authors | Fast, content-focused |
| `theme-dev` | Theme developers | Template validation |
| `developer` | Full development | All checks, strict |

```bash
# Writer profile (fast, less strict) - default
bengal check --profile writer

# Theme developer profile
bengal check --profile theme-dev

# Developer profile (strict, all checks)
bengal check --profile developer
```

---

## Troubleshooting

### False Positives

Suppress specific check codes via CLI:

```bash
# Ignore specific check codes
bengal check --ignore H101 --ignore H202
```

Or in page frontmatter:

```yaml
---
validate:
  skip:
    - links        # Skip link validation for this page
    - anchors      # Skip anchor validation
---
```

Or via configuration:

```yaml
# config/_default/health.yaml
health:
  ignore_patterns:
    - "content/drafts/**"
    - "content/archived/**"
```

### Slow External Link Checks

```bash
# Check internal links only (fast)
bengal inspect links --internal-only

# Exclude specific URL patterns
bengal inspect links --exclude "^/api/preview/"
```

:::{tip}
Advanced options like `--max-concurrency`, `--timeout`, and `--exclude-domain` are available but hidden from help output. Use them when needed for fine-tuning.
:::

### Validation Cache

Validation uses the build cache for incremental checks:

```bash
# Clear build cache (includes validation state)
bengal clean --cache

# Force full re-validation by clearing cache first
bengal clean --cache && bengal check

# Use incremental validation (only changed files)
bengal check --incremental
```

---

## Quick Reference

```bash
# Validate
bengal check                    # Run all validators
bengal check --changed          # Only changed files
bengal check --incremental      # Use cached validation state
bengal check --verbose          # Show all checks
bengal check --suggestions      # Show quality suggestions
bengal check --file path.md     # Validate specific file
bengal check --profile writer   # Use writer profile (fast)
bengal check --ignore H101      # Ignore specific check codes
bengal check --watch            # Watch mode (experimental)
bengal check --templates        # Validate template syntax

# Auto-fix
bengal fix --dry-run               # Preview fixes
bengal fix                         # Apply safe fixes
bengal fix --all                   # Apply all fixes
bengal fix --confirm               # Ask before each fix
bengal fix --validator Directives  # Fix specific validator

# Link checking
bengal inspect links                   # Check all links
bengal inspect links --internal-only   # Internal only (fast)
bengal inspect links --external-only   # External only
bengal inspect links --output-format json     # JSON output for CI

# Build
bengal build --strict              # Fail on warnings
bengal build --validate            # Validate before building

# Clean
bengal clean --cache               # Clear build cache
```

---

:::{seealso}
- [Validation Overview](/docs/ship/validate/) — Content quality strategies
- [CLI Cheatsheet](/docs/reference/cheatsheet/) — Quick command reference
- [Troubleshooting](/docs/ship/troubleshooting/) — Common issues
:::
