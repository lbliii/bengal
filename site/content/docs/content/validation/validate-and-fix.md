---
title: Validate and Fix
nav_title: Validate & Fix
description: Run health checks and automatically fix common content issues
weight: 10
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

:::{note}
**Do I need this?** Yes when running `bengal check` or `bengal fix` in
your workflow. For auto-fix details, custom validators, and health config,
see [[docs/content/validation/validate-and-fix-reference|Validation Reference]].
:::

Bengal's health system validates content and can automatically fix many common issues.

## Quick Start

```bash
# Run all validators
bengal check

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
bengal check

# Validate specific file
bengal check --file content/docs/getting-started.md

# Validate changed files only (git-aware)
bengal check --changed

# Verbose output - show all checks, not just errors
bengal check --verbose
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
bengal inspect links

# Internal links only (fast)
bengal inspect links --internal-only

# External links only
bengal inspect links --external-only

# Exclude specific URL patterns
bengal inspect links --exclude "^/api/preview/"
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
| **Rendering** | HTML output quality | Template errors, undefined variables, missing social tags, malformed JSON-LD |
| **Output** | Generated pages, assets | Missing output, structure errors |
| **Asset URLs** | Asset references in HTML | Broken asset paths, fingerprinting mismatches, case issues |
| **Performance** | Build metrics | Slow builds, large pages |
| **URL Collisions** | Duplicate output paths | Multiple pages writing to same URL |

### Production Validators

| Validator | Checks | Common Issues |
|-----------|--------|---------------|
| **Sitemap** | sitemap.xml validity | SEO issues, missing pages |
| **RSS Feed** | RSS/Atom feed quality | Schema compliance, missing fields |
| **Fonts** | Font downloads, CSS | Missing fonts, subsetting issues |
| **Ownership Policy** | Reserved namespaces | Content in system directories |

### Validation Output

```bash
$ bengal check

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
        run: bengal check --verbose

      - name: Check Links
        run: bengal inspect links --internal-only

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
        entry: bengal check --changed
        language: system
        pass_filenames: false
```

### Failing on Errors

```bash
# Strict mode - treats warnings as errors
bengal build --strict

# Validate and exit with error code
bengal check && echo "Validation passed" || echo "Validation failed"
```

---


:::{seealso}
- [[docs/content/validation|Validation Overview]] — hub and built-in checks
- [[docs/content/validation/validate-and-fix-reference|Validation Reference]] — auto-fix, custom validators, config
:::
