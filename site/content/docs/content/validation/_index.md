---
title: Validation
description: Content validation and health checks
weight: 60
category: guide
icon: check-circle
card_color: purple
---
# Content Validation

Ensure content quality with health checks and automatic fixes.

## Do I Need This?

:::{note}
**Skip this if**: You manually check all links and content.  
**Read this if**: You want automated quality assurance and CI/CD integration.
:::

## Validation Flow

```mermaid
flowchart LR
    A[Content] --> B[Validators]
    B --> C{Issues?}
    C -->|Yes| D[Report]
    C -->|No| E[Pass]
    D --> F{Auto-fixable?}
    F -->|Yes| G[Auto-fix]
    F -->|No| H[Manual fix needed]
```

## Quick Start

::::{tab-set}
:::{tab-item} Validate
```bash
# Run all checks
bengal validate

# Validate specific files
bengal validate --file content/page.md

# Only validate changed files
bengal validate --changed

# Verbose output (show all checks)
bengal validate --verbose
```
:::

:::{tab-item} Auto-fix
```bash
# Preview fixes
bengal fix --dry-run

# Apply fixes
bengal fix
```

Fixes common issues:
- Missing frontmatter fields
- Broken relative links
- Incorrect slugs
:::

:::{tab-item} CI/CD
```bash
# Fail build on issues
bengal build --strict
```

The `--strict` flag makes warnings into errors.
:::
::::

## Built-in Checks

| Check | What it validates |
|-------|-------------------|
| `links` | Internal and external links work |
| `assets` | Asset references exist |
| `config` | Configuration is valid |
| `navigation` | Menu structure is correct |
| `rendering` | Templates render without errors |
| `cross_ref` | Cross-references are valid |
| `taxonomy` | Tags and categories are consistent |

## Custom Validators

Create project-specific rules by extending `BaseValidator`:

```python
# validators/custom.py
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

class RequireAuthorValidator(BaseValidator):
    """Validator that checks for author field in frontmatter."""

    name = "Author Required"
    description = "Ensures all pages have an author field"

    def validate(self, site, build_context=None):
        results = []
        for page in site.pages:
            if not page.metadata.get("author"):
                results.append(CheckResult.error(
                    f"Missing author field in {page.source_path}",
                    recommendation="Add 'author: Your Name' to frontmatter"
                ))
        return results
```

:::{tip}
**CI integration**: Add `bengal validate` to your CI pipeline to catch issues before deployment. Use `--verbose` to see all checks, not just problems.
:::
