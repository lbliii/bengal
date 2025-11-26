---
title: Health Check System
description: Comprehensive build validation and health checks
weight: 30
category: subsystems
tags: [subsystems, health, validation, validators, build-checks, quality]
keywords: [health checks, validation, validators, build checks, quality assurance, testing]
---

# Health Check System (`bengal/health/`)

Bengal includes a comprehensive health check system that validates builds across all components.

## Health Check (`bengal/health/health_check.py`)
- **Purpose**: Orchestrates validators and produces unified health reports
- **Features**:
  - Modular validator architecture
  - Fast execution (< 100ms per validator)
  - Configurable per-validator enable/disable
  - Console and JSON report formats
  - Integration with build stats
- **Usage**:
  ```python
  from bengal.health import HealthCheck

  health = HealthCheck(site)
  report = health.run(build_stats=stats)
  print(report.format_console())
  ```

## Base Validator (`bengal/health/base.py`)
- **Purpose**: Abstract base class for all validators
- **Interface**: `validate(site) -> List[CheckResult]`
- **Features**:
  - Independent execution (no validator dependencies)
  - Error handling and crash recovery
  - Performance tracking per validator
  - Configuration-based enablement

## Health Report (`bengal/health/report.py`)
- **Purpose**: Unified reporting structure for health check results
- **Components**:
  - `CheckStatus`: SUCCESS, INFO, WARNING, ERROR
  - `CheckResult`: Individual check result with recommendation
  - `ValidatorReport`: Results from a single validator
  - `HealthReport`: Aggregated report from all validators
- **Formats**:
  - Console output (colored, formatted)
  - JSON output (machine-readable)
  - Summary statistics (pass/warning/error counts)

## Validators (`bengal/health/validators/`)

**All Validators (14 total)**:

**Basic Validation:**
| Validator | Validates |
|-----------|-----------|
| **ConfigValidatorWrapper** | Configuration validity, essential fields, common issues |
| **OutputValidator** | Page sizes, asset presence, directory structure |
| **MenuValidator** | Menu structure integrity, circular reference detection |
| **LinkValidatorWrapper** | Broken links detection (internal and external) |

**Content Validation:**
| Validator | Validates |
|-----------|-----------|
| **NavigationValidator** | Page navigation (next/prev, breadcrumbs, ancestors) |
| **TaxonomyValidator** | Tags, categories, archives, pagination integrity |
| **RenderingValidator** | HTML quality, template function usage, SEO metadata |
| **DirectiveValidator** | Directive syntax, completeness, and performance |

**Advanced Validation:**
| Validator | Validates |
|-----------|-----------|
| **CacheValidator** | Incremental build cache integrity and consistency |
| **PerformanceValidator** | Build performance metrics and bottleneck detection |

**Production-Ready Validation:**
| Validator | Validates |
|-----------|-----------|
| **RSSValidator** | RSS feed quality, XML validity, URL formatting |
| **SitemapValidator** | Sitemap.xml validity for SEO, no duplicate URLs |
| **FontValidator** | Font downloads, CSS generation, file sizes |
| **AssetValidator** | Asset optimization, minification hints, size analysis |

## Configuration
Health checks can be configured via `bengal.toml`:
```toml
[health_check]
# Globally enable/disable health checks
validate_build = true

# Per-validator configuration (all enabled by default)
[health_check.validators]
# Phase 1: Basic
configuration = true
output = true
navigation_menus = true
links = true

# Phase 2: Content
navigation = true
taxonomies = true
rendering = true
directives = true

# Phase 3: Advanced
cache_integrity = true
performance = true

# Phase 4: Production-ready
rss_feed = true
sitemap = true
fonts = true
asset_processing = true
```

## Integration
Health checks run automatically after builds in strict mode and can be triggered manually:
```python
# Automatic validation in strict mode
site.config["strict_mode"] = True
stats = site.build()

# Manual validation
from bengal.health import HealthCheck
health = HealthCheck(site)
report = health.run(build_stats=stats)
```
