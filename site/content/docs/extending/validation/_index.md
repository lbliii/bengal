---
title: Validation
description: Content validation and health checks
weight: 30
draft: false
lang: en
tags: [validation, health, checks]
keywords: [validation, health, checks, autofix, quality]
category: guide
---

# Validation

Ensure content quality with health checks and automatic fixes.

## Overview

Bengal's validation system provides:

- **Built-in checks** — Links, images, frontmatter, structure
- **Auto-fix** — Automatically repair common issues
- **Custom validators** — Add your own rules
- **CI integration** — Fail builds on errors

## Quick Start

```bash
# Run all health checks
bengal validate

# Check specific aspects
bengal validate --links
bengal validate --frontmatter
bengal validate --images

# Auto-fix issues
bengal fix
```

## Built-in Checks

| Check | Description |
|-------|-------------|
| `links` | Verify internal and external links |
| `images` | Check image references exist |
| `frontmatter` | Validate required fields |
| `structure` | Check content organization |
| `spelling` | Basic spell checking |

## Auto-Fix

Bengal can automatically fix:

- Missing frontmatter fields
- Broken relative links
- Incorrect slugs
- Common formatting issues

```bash
bengal fix --dry-run  # Preview changes
bengal fix            # Apply fixes
```

## In This Section

- **[Health Checks](/docs/extending/validation/health-checks/)** — Built-in validation rules
- **[Auto-Fix](/docs/extending/validation/autofix/)** — Automatic issue repair
- **[Custom Validators](/docs/extending/validation/custom-validators/)** — Create your own rules

