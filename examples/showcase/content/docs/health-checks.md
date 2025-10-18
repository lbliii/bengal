---
title: "Health Check System"
description: "Comprehensive build validation with 9 health check validators"
date: 2025-10-04
weight: 10
tags: ["quality", "validation", "health-checks", "testing", "production"]
toc: true
---

# Health Check System

Bengal's **Health Check System** provides comprehensive build validation across 9 specialized validators. It catches issues before deployment, ensures quality standards, and helps maintain a healthy site.

```{success} Unique Feature
The health check system is **unique to Bengal** among static site generators. It provides production-grade quality assurance that catches issues other SSGs would miss!
```

---

## 🎯 Overview

### What is the Health Check System?

The health check system validates your site build across multiple dimensions:

- ✅ **Configuration** - Valid settings and structure
- ✅ **Content** - Proper markup and metadata
- ✅ **Navigation** - Working menus and links
- ✅ **Rendering** - Clean HTML output
- ✅ **Taxonomy** - Tags and categories
- ✅ **Output** - File sizes and structure
- ✅ **Links** - No broken internal links
- ✅ **Cache** - Incremental build integrity
- ✅ **Performance** - Build speed metrics

### Why Health Checks?

````{tabs}
:id: why-health-checks

### Tab: Catch Issues Early

Find problems **before** deployment:

- Broken links
- Missing assets
- Invalid configuration
- Malformed HTML
- Orphaned pages
- Cache corruption

**Better to fail fast in dev than in production!**

### Tab: Quality Assurance

Enforce quality standards:

- Page size limits
- Navigation completeness
- Taxonomy consistency
- Performance benchmarks

**Maintain professional quality automatically.**

### Tab: CI/CD Integration

Perfect for continuous deployment:

```bash
# Run health checks in CI
bengal site build
bengal health-check

# Exit code 0 = all checks passed
# Exit code 1 = checks failed
```

**Prevent bad builds from reaching production.**
````

---

## 📊 The 9 Validators

### 1. Configuration Validator

**Purpose:** Validates site configuration and structure.

```{example} What It Checks

**Configuration validity:**
- Required fields present (`site.title`, `site.baseurl`)
- Valid data types (booleans, strings, integers)
- No conflicting settings
- Theme exists and is valid
- Output directory is writable

**Structure:**
- Content directory exists
- Template directory accessible
- Data directory structure
- Asset directory organization
```

**Configuration:**

```toml
[health_check.validators]
config = true  # Enabled by default
```

**Example Output:**

```
✅ Configuration
  ✓ Site configuration is valid
  ✓ Theme 'default' found and valid
  ✓ All required directories exist
```

---

### 2. Output Validator

**Purpose:** Validates generated output files and structure.

```{example} What It Checks

**File sizes:**
- No pages exceed 500KB (warning)
- No assets exceed 5MB (warning)
- Total site size reasonable

**Output structure:**
- All pages generated
- Index files present
- Asset files copied
- No empty output files

**File quality:**
- Valid HTML structure
- No broken relative paths
- Proper file permissions
```

**Configuration:**

```toml
[health_check.validators]
output = true

[health_check.output]
max_page_size_kb = 500      # Warn if page > 500KB
max_asset_size_mb = 5       # Warn if asset > 5MB
check_empty_files = true    # Check for empty files
```

**Example Output:**

```
✅ Output
  ✓ 147 pages generated successfully
  ✓ 42 assets copied
  ⚠ Warning: '/posts/long-post/index.html' is 523KB (> 500KB)
  ✓ No empty files detected
```

---

### 3. Menu Validator

**Purpose:** Validates menu structure and navigation.

```{example} What It Checks

**Menu integrity:**
- All menu items have valid URLs
- No duplicate menu items
- Menu weights are logical
- Required menus exist

**Links:**
- Internal links resolve to real pages
- External links are properly formatted
- No circular references

**Structure:**
- Nested menus are properly structured
- Maximum depth not exceeded
- No orphaned menu items
```

**Configuration:**

```toml
[[menus.main]]
name = "Home"
url = "/"
weight = 1

[[menus.main]]
name = "Docs"
url = "/docs/"
weight = 2

[health_check.validators]
menu = true
```

**Example Output:**

```
✅ Menu
  ✓ Main menu has 5 items
  ✓ All menu URLs resolve to pages
  ✓ No duplicate entries
  ! Info: Footer menu not defined (optional)
```

---

### 4. Link Validator

**Purpose:** Detects broken internal links.

```{example} What It Checks

**Internal links:**
- Links to existing pages
- Cross-references resolve
- Anchor links to valid IDs
- Relative links work

**Link structure:**
- No malformed URLs
- No spaces in URLs
- Proper URL encoding
- Case sensitivity issues
```

**Configuration:**

```toml
[health_check.validators]
links = true

[health_check.links]
check_anchors = true      # Check #anchor links
check_external = false    # Don't check external links
ignore_patterns = [       # Patterns to ignore
  "^https://example.com",
  "^mailto:",
]
```

**Example Output:**

```
✅ Links
  ✓ Checked 847 internal links
  ✓ All links resolve successfully
  ✗ Error: /docs/advanced.md links to missing page '/docs/nonexistent.md'
  ⚠ Warning: /blog/post.md has anchor link to #missing-section

  📊 Statistics:
    - Internal links: 847
    - Cross-references: 123
    - Anchor links: 56
    - Broken links: 1
```

---

### 5. Navigation Validator

**Purpose:** Validates page navigation (next/prev, breadcrumbs).

```{example} What It Checks

**Next/Previous links:**
- Proper sequence in sections
- Bidirectional consistency
- No dead ends
- Logical ordering

**Breadcrumbs:**
- Complete breadcrumb trails
- Parent/child relationships
- No broken breadcrumbs

**Page hierarchy:**
- Section structure
- Orphaned pages
- Deep nesting issues
```

**Configuration:**

```toml
[health_check.validators]
navigation = true

[health_check.navigation]
check_next_prev = true        # Validate next/prev links
check_breadcrumbs = true      # Validate breadcrumbs
max_depth = 5                 # Maximum nesting depth
warn_orphaned = true          # Warn about orphaned pages
```

**Example Output:**

```
✅ Navigation
  ✓ 42 pages have next/prev links
  ✓ All breadcrumb trails complete
  ⚠ Warning: 3 orphaned pages (no parent section)
    - /misc/old-page.md
    - /temp/draft.md
    - /archive/outdated.md
```

---

### 6. Taxonomy Validator

**Purpose:** Validates taxonomy system (tags, categories).

```{example} What It Checks

**Taxonomy integrity:**
- All taxonomies defined in config
- Taxonomy pages generated
- No orphaned taxonomy pages
- Tag/category consistency

**Usage:**
- Unused tags/categories
- Overly broad tags (>100 pages)
- Singleton tags (1 page)
- Tag naming consistency

**Generated pages:**
- Tag list pages exist
- Category archive pages
- Taxonomy index pages
```

**Configuration:**

```toml
[taxonomies]
tags = "tags"
categories = "categories"
series = "series"

[health_check.validators]
taxonomy = true

[health_check.taxonomy]
warn_singleton_tags = true     # Tags with only 1 page
warn_broad_tags = 50           # Tags with > 50 pages
check_consistency = true       # Check naming consistency
```

**Example Output:**

```
✅ Taxonomy
  ✓ 45 tags used across site
  ✓ 8 categories defined
  ✓ All taxonomy pages generated

  📊 Tag statistics:
    - Most used: 'python' (23 pages)
    - Singleton tags: 7
    - Average per page: 3.2 tags

  ⚠ Warnings:
    - Tag 'getting-started' used inconsistently with 'getting_started'
    - 7 singleton tags (consider consolidating)
```

---

### 7. Rendering Validator

**Purpose:** Validates HTML quality and template function usage.

```{example} What It Checks

**HTML quality:**
- Valid HTML5 structure
- Proper tag nesting
- Required meta tags
- Semantic HTML usage

**Template functions:**
- No undefined template functions
- Correct parameter usage
- No template errors
- Filter chain validity

**Output quality:**
- No template variable leakage
- Proper escaping
- No debug output
- Clean rendered HTML
```

**Configuration:**

```toml
[health_check.validators]
rendering = true

[health_check.rendering]
check_html_validity = true      # Validate HTML5
check_meta_tags = true          # Check required meta tags
check_template_errors = true    # Check for template errors
required_meta = [               # Required meta tags
  "description",
  "viewport"
]
```

**Example Output:**

```
✅ Rendering
  ✓ All 147 pages have valid HTML5
  ✓ No template errors detected
  ⚠ Warning: 3 pages missing 'description' meta tag
    - /old-page/index.html
    - /archive/legacy.html
    - /temp/draft.html
  ✓ All template functions used correctly
```

---

### 8. Cache Validator

**Purpose:** Validates incremental build cache integrity.

```{example} What It Checks

**Cache integrity:**
- Cache files not corrupted
- Dependencies accurate
- No stale cache entries
- Cache size reasonable

**Build correctness:**
- Incremental builds produce same output
- Dependency tracking works
- No cache poisoning

**Performance:**
- Cache hit rates
- Cache effectiveness
- Stale entry cleanup
```

**Configuration:**

```toml
[build]
incremental = true

[health_check.validators]
cache = true

[health_check.cache]
check_integrity = true       # Validate cache integrity
check_dependencies = true    # Verify dependency tracking
max_cache_size_mb = 100     # Warn if cache > 100MB
clean_stale = true          # Auto-clean stale entries
```

**Example Output:**

```
✅ Cache
  ✓ Cache integrity verified
  ✓ Dependency tracking accurate
  ✓ No stale entries

  📊 Cache statistics:
    - Cache size: 23.4 MB
    - Cached pages: 147
    - Hit rate: 94.2%
    - Last cleanup: 2 hours ago
```

---

### 9. Performance Validator

**Purpose:** Validates build performance metrics.

```{example} What It Checks

**Build speed:**
- Build time acceptable
- Pages per second rate
- Parallel efficiency
- Incremental speedup

**Benchmarks:**
- Compare to baseline
- Detect regressions
- Track improvements
- Monitor trends

**Resource usage:**
- Memory consumption
- CPU utilization
- Disk I/O
- Cache effectiveness
```

**Configuration:**

```toml
[health_check.validators]
performance = true

[health_check.performance]
baseline_pages_per_sec = 50     # Expected pages/sec
warn_regression_pct = 20        # Warn if 20% slower
track_history = true            # Track performance over time
max_build_time_sec = 30         # Warn if > 30 seconds
```

**Example Output:**

```
✅ Performance
  ✓ Built 147 pages in 2.8 seconds
  ✓ Speed: 52.5 pages/second
  ✓ 18.3x faster than full rebuild

  📊 Performance metrics:
    - Parallel speedup: 3.2x
    - Cache hit rate: 94.2%
    - Memory peak: 87 MB
    - Total assets: 42 files

  ✓ Performance meets baseline (50 pages/sec)
```

---

## 🚀 Usage Examples

### Basic Usage

```bash
# Build with health checks
bengal site build

# Run health checks after build
bengal health-check

# Run specific validators
bengal health-check --validators=links,navigation

# Verbose output
bengal health-check --verbose
```

### Python API

```python
from bengal.core.site import Site
from bengal.health import HealthCheck
from bengal.health.validators import (
    OutputValidator,
    LinkValidatorWrapper,
    NavigationValidator,
)

# Build site
site = Site(".")
site.build()

# Create health check
health = HealthCheck(site)

# Register validators
health.register(OutputValidator())
health.register(LinkValidatorWrapper())
health.register(NavigationValidator())

# Run checks
report = health.run(verbose=True)

# Display results
print(report.format_console())

# Check if passed
if report.has_errors():
    print("❌ Health checks failed!")
    exit(1)
else:
    print("✅ All health checks passed!")
```

### CI/CD Integration

```yaml
# .github/workflows/deploy.yml
name: Deploy Site

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Bengal
        run: pip install bengal-ssg

      - name: Build Site
        run: bengal site build

      - name: Run Health Checks
        run: bengal health-check --strict

      - name: Deploy
        if: success()
        run: ./deploy.sh
```

---

## 📋 Configuration Reference

### Global Health Check Settings

```toml
[health_check]
enabled = true              # Enable health checks
fail_on_warning = false     # Treat warnings as errors
fail_on_error = true        # Fail build on errors
verbose = false             # Verbose output
report_format = "console"   # console, json, or both

[health_check.validators]
# Enable/disable individual validators
config = true
output = true
menu = true
links = true
navigation = true
taxonomy = true
rendering = true
cache = true
performance = true
```

### Validator-Specific Settings

```toml
[health_check.output]
max_page_size_kb = 500
max_asset_size_mb = 5
check_empty_files = true

[health_check.links]
check_anchors = true
check_external = false
ignore_patterns = ["^https://example.com"]

[health_check.navigation]
check_next_prev = true
check_breadcrumbs = true
max_depth = 5
warn_orphaned = true

[health_check.taxonomy]
warn_singleton_tags = true
warn_broad_tags = 50
check_consistency = true

[health_check.rendering]
check_html_validity = true
check_meta_tags = true
required_meta = ["description", "viewport"]

[health_check.cache]
check_integrity = true
check_dependencies = true
max_cache_size_mb = 100

[health_check.performance]
baseline_pages_per_sec = 50
warn_regression_pct = 20
max_build_time_sec = 30
```

---

## 📊 Report Formats

### Console Output

```bash
$ bengal health-check

🔍 Running Health Checks...

✅ Configuration
  ✓ Site configuration is valid
  ✓ Theme 'default' found

✅ Output
  ✓ 147 pages generated
  ⚠ Warning: 1 large page detected

✅ Links
  ✓ 847 internal links checked
  ✗ Error: 1 broken link found

✅ Navigation
  ✓ All navigation links valid

❌ Health Check Failed
  Errors: 1, Warnings: 1
  Time: 1.2s
```

### JSON Output

```json
{
  "status": "failed",
  "errors": 1,
  "warnings": 1,
  "duration": 1.23,
  "validators": [
    {
      "name": "Links",
      "status": "error",
      "results": [
        {
          "level": "error",
          "message": "Broken link: /docs/missing.md",
          "recommendation": "Create the page or remove the link"
        }
      ]
    }
  ]
}
```

---

## 🎯 Best Practices

### Development Workflow

````{tabs}
:id: dev-workflow

### Tab: During Development

**Run frequently:**

```bash
# Quick checks while developing
bengal site serve --watch --health-check

# Auto-checks on file changes
bengal site build --incremental --health-check
```

**Focus on:**
- Links validator (catch broken links early)
- Navigation validator (ensure structure)
- Rendering validator (template errors)

### Tab: Before Commit

**Run full validation:**

```bash
# All validators, strict mode
bengal health-check --strict --all

# Or in pre-commit hook
# .git/hooks/pre-commit
#!/bin/bash
bengal site build && bengal health-check --strict
```

**Fix all:**
- ❌ Errors (must fix)
- ⚠️ Warnings (should fix)
- ℹ️ Info (consider)

### Tab: In CI/CD

**Production checks:**

```bash
# Strict mode: fail on warnings
bengal site build
bengal health-check --strict --fail-on-warning

# Generate reports
bengal health-check --format=json > health-report.json
bengal health-check --format=console > health-report.txt
```

**Track trends:**
- Performance over time
- Link health history
- Cache effectiveness
````

---

## 💡 Pro Tips

```{tip} Custom Validators
You can create custom validators for your specific needs:

```python
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

class CustomValidator(BaseValidator):
    name = "Custom Checks"
    description = "Project-specific validation"

    def validate(self, site):
        results = []

        # Check custom requirement
        if not site.config.get('custom_field'):
            results.append(CheckResult.warning(
                "Custom field not set",
                recommendation="Add custom_field to config"
            ))
        else:
            results.append(CheckResult.success(
                "Custom field configured"
            ))

        return results

# Use it
health = HealthCheck(site)
health.register(CustomValidator())
```
```

```{success} Performance Impact
Health checks are **fast**:
- Most validators: < 100ms
- Total overhead: ~1-2 seconds for 1000 pages
- Parallel execution where possible
- Negligible impact on build time

**The confidence they provide is worth it!**
```

```{note} Selective Validation
Don't run all validators all the time:

**During active development:**
- Links, Navigation, Rendering

**Before commits:**
- All validators

**In CI/CD:**
- All validators + strict mode

Use `--validators=` flag to control.
```

---

## 🐛 Common Issues and Solutions

```{dropdown} "False positive: Link validator reports valid links as broken"

**Cause:** Case sensitivity or URL encoding

**Solution:**
```toml
[health_check.links]
ignore_patterns = [
  "^/api/",  # Ignore API routes
  "^/external/"
]
```

Or fix the links to match exactly.
```

```{dropdown} "Performance validator warns about slow builds"

**Cause:** Not using incremental builds or parallel processing

**Solution:**
```toml
[build]
incremental = true
parallel = true
```

```bash
bengal site build --incremental --parallel
```
```

```{dropdown} "Too many warnings about singleton tags"

**Cause:** Many one-off tags

**Solution:**
1. Consolidate similar tags
2. Remove unused tags
3. Or disable the check:

```toml
[health_check.taxonomy]
warn_singleton_tags = false
```
```

```{dropdown} "Cache validator reports corruption"

**Cause:** Interrupted builds or version changes

**Solution:**
```bash
# Clear cache and rebuild
bengal site clean
bengal site build
```
```

---

## 📚 Related Documentation

- **[Configuration Reference](../configuration/full-reference.md)** - All health check config options
- **[Build Process](../core-concepts/build-process.md)** - How health checks fit in
- **[CI/CD Guide](../deployment/ci-cd.md)** - Integrating health checks
- **[Debugging](../development/debugging.md)** - Troubleshooting failed checks

---

## 🎉 Summary

Bengal's health check system provides **9 comprehensive validators**:

| # | Validator | Purpose | Key Benefit |
|---|-----------|---------|-------------|
| 1 | Configuration | Valid settings | Catch config errors early |
| 2 | Output | File sizes & structure | Prevent huge pages |
| 3 | Menu | Navigation integrity | Ensure menus work |
| 4 | Links | Broken link detection | No 404s for users |
| 5 | Navigation | Next/prev & breadcrumbs | Complete navigation |
| 6 | Taxonomy | Tags & categories | Consistent taxonomies |
| 7 | Rendering | HTML quality | Professional output |
| 8 | Cache | Build integrity | Reliable incremental builds |
| 9 | Performance | Build metrics | Monitor performance |

**This is a unique feature** that sets Bengal apart from other static site generators!

---

**Last Updated:** October 4, 2025  
**Version:** 1.0.0  
**Coverage:** All 9 validators documented
