---
title: Validate and Fix
nav_title: Validate & Fix
description: Run health checks and automatically fix common content issues
weight: 10
type: doc
icon: wrench
tags:
- validation
- health-checks
- auto-fix
- lint
keywords:
- validate
- fix
- health check
- lint
- auto-fix
- quality
category: how-to
---
# Validate and Fix Content

Bengal's health system validates content and can automatically fix many common issues.

## Quick Start

```bash
# Run all validators
bengal validate

# Preview auto-fixes
bengal fix --dry-run

# Apply safe fixes
bengal fix
```

---

## Validation Commands

### Basic Validation

```bash
# Validate entire site
bengal validate

# Validate specific file
bengal validate --file content/docs/getting-started.md

# Validate changed files only (git-aware)
bengal validate --changed

# Verbose output - show all checks, not just errors
bengal validate --verbose
```

### Validate During Build

```bash
# Fail build on validation errors (recommended for CI)
bengal build --strict

# Validate templates before building
bengal build --validate
```

### Check Specific Areas

```bash
# Link checking (internal + external)
bengal health linkcheck

# Internal links only (fast)
bengal health linkcheck --internal-only

# External links only
bengal health linkcheck --external-only

# Exclude specific URL patterns
bengal health linkcheck --exclude "^/api/preview/"
```

---

## Available Validators

Bengal includes validators organized by phase:

### Core Validators

| Validator | Checks | Common Issues |
|-----------|--------|---------------|
| **Links** | Internal/external links | Broken links, moved pages |
| **Directives** | MyST directive syntax | Unclosed fences, invalid options |
| **Configuration** | Site configuration | Invalid YAML, missing required fields |
| **Navigation** | Page nav (next/prev, breadcrumbs) | Broken navigation links |
| **Navigation Menus** | Menu structure and links | Missing menu items, broken links |

### Content Quality Validators

| Validator | Checks | Common Issues |
|-----------|--------|---------------|
| **Anchors** | Heading IDs, `[[#anchor]]` refs | Duplicate IDs, broken anchor links |
| **Cross-References** | Internal page references | Invalid page references |
| **Taxonomies** | Tags/categories | Orphan terms, inconsistent naming |
| **Connectivity** | Page link graph | Orphan pages, poor connectivity |

### Build & Output Validators

| Validator | Checks | Common Issues |
|-----------|--------|---------------|
| **Rendering** | HTML output quality | Template errors, undefined variables |
| **Output** | Generated pages, assets | Missing output, structure errors |
| **Asset Processing** | Asset optimization | Missing files, processing failures |
| **Asset URLs** | Asset references | Broken asset paths, fingerprinting issues |
| **Performance** | Build metrics | Slow builds, large pages |
| **Cache Integrity** | Incremental build cache | Stale cache, invalidation issues |

### Production Validators

| Validator | Checks | Common Issues |
|-----------|--------|---------------|
| **Sitemap** | sitemap.xml validity | SEO issues, missing pages |
| **RSS Feed** | RSS/Atom feed quality | Schema compliance, missing fields |
| **Accessibility** | HTML accessibility | Missing alt text, ARIA issues |
| **Fonts** | Font downloads, CSS | Missing fonts, subsetting issues |

### Validation Output

```bash
$ bengal validate

🔍 Running health checks...

✅ Config: 3 checks passed
✅ Navigation: 5 checks passed
⚠️ Links: 2 warnings
  → content/docs/old-page.md references moved page
  → content/api/client.md has broken anchor #deprecated

❌ Directives: 1 error
  → content/tutorials/setup.md:45 - Unclosed code fence

Summary: 1 error, 2 warnings, 8 passed
```

---

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

## CI/CD Integration

### GitHub Actions

```yaml
name: Validate Docs

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install Bengal
        run: pip install bengal

      - name: Validate Content
        run: bengal validate --verbose

      - name: Check Links
        run: bengal health linkcheck --internal-only

      - name: Build (strict mode)
        run: bengal build --strict
```

### Pre-Commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: bengal-validate
        name: Validate Bengal content
        entry: bengal validate --changed
        language: system
        pass_filenames: false
```

### Failing on Errors

```bash
# Strict mode - treats warnings as errors
bengal build --strict

# Validate and exit with error code
bengal validate && echo "Validation passed" || echo "Validation failed"
```

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
bengal validate --verbose

# Quick validation (local dev)
bengal validate --changed

# Pre-deploy validation
bengal health linkcheck && bengal build --strict
```

Available profiles:

| Profile | Use Case | Checks |
|---------|----------|--------|
| `writer` | Content authors | Fast, content-focused |
| `theme-dev` | Theme developers | Template validation |
| `developer` | Full development | All checks, strict |

```bash
# Writer profile (fast, less strict) - default
bengal validate --profile writer

# Theme developer profile
bengal validate --profile theme-dev

# Developer profile (strict, all checks)
bengal validate --profile developer
```

---

## Troubleshooting

### False Positives

Suppress specific check codes via CLI:

```bash
# Ignore specific check codes
bengal validate --ignore H101 --ignore H202
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
bengal health linkcheck --internal-only

# Exclude specific URL patterns
bengal health linkcheck --exclude "^/api/preview/"
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
bengal clean --cache && bengal validate

# Use incremental validation (only changed files)
bengal validate --incremental
```

---

## Quick Reference

```bash
# Validate
bengal validate                    # Run all validators
bengal validate --changed          # Only changed files
bengal validate --incremental      # Use cached validation state
bengal validate --verbose          # Show all checks
bengal validate --suggestions      # Show quality suggestions
bengal validate --file path.md     # Validate specific file
bengal validate --profile writer   # Use writer profile (fast)
bengal validate --ignore H101      # Ignore specific check codes
bengal validate --watch            # Watch mode (experimental)
bengal validate --templates        # Validate template syntax

# Auto-fix
bengal fix --dry-run               # Preview fixes
bengal fix                         # Apply safe fixes
bengal fix --all                   # Apply all fixes
bengal fix --confirm               # Ask before each fix
bengal fix --validator Directives  # Fix specific validator

# Link checking
bengal health linkcheck                   # Check all links
bengal health linkcheck --internal-only   # Internal only (fast)
bengal health linkcheck --external-only   # External only
bengal health linkcheck --format json     # JSON output for CI

# Build
bengal build --strict              # Fail on warnings
bengal build --validate            # Validate before building

# Clean
bengal clean --cache               # Clear build cache
```

---

:::{seealso}
- [Validation Overview](/docs/content/validation/) — Content quality strategies
- [CLI Cheatsheet](/docs/reference/cheatsheet/) — Quick command reference
- [Troubleshooting](/docs/building/troubleshooting/) — Common issues
:::
