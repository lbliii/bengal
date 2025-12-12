---
title: Health Check System
nav_title: Health
description: Comprehensive build validation and health checks
weight: 30
category: subsystems
tags:
- subsystems
- health
- validation
- validators
- build-checks
- quality
keywords:
- health checks
- validation
- validators
- build checks
- quality assurance
- testing
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
| **ConnectivityValidator** | Page connectivity using semantic link model and weighted scoring |
| **CacheValidator** | Incremental build cache integrity and consistency |
| **PerformanceValidator** | Build performance metrics and bottleneck detection |

**Production-Ready Validation:**
| Validator | Validates |
|-----------|-----------|
| **RSSValidator** | RSS feed quality, XML validity, URL formatting |
| **SitemapValidator** | Sitemap.xml validity for SEO, no duplicate URLs |
| **FontValidator** | Font downloads, CSS generation, file sizes |
| **AssetValidator** | Asset optimization, minification hints, size analysis |

## Connectivity Validator

The Connectivity Validator uses a **semantic link model** with weighted scoring to provide nuanced page connectivity analysis beyond binary orphan detection.

**Link Types and Weights:**
| Link Type | Weight | Description |
|-----------|--------|-------------|
| **Explicit** | 1.0 | Human-authored markdown links |
| **Menu** | 10.0 | Navigation menu items (high editorial intent) |
| **Taxonomy** | 1.0 | Shared tags/categories |
| **Related** | 0.75 | Algorithm-computed related posts |
| **Topical** | 0.5 | Section hierarchy (parent → child) |
| **Sequential** | 0.25 | Next/prev navigation |

**Connectivity Levels:**
| Level | Score Range | Status |
|-------|-------------|--------|
| 🟢 Well-Connected | ≥ 2.0 | No action needed |
| 🟡 Adequately Linked | 1.0 - 2.0 | Could improve |
| 🟠 Lightly Linked | 0.25 - 1.0 | Should improve (only structural links) |
| 🔴 Isolated | < 0.25 | Needs attention |

**Configuration:**
```toml
[health_check]
# Connectivity thresholds
isolated_threshold = 5      # Max isolated pages before error
lightly_linked_threshold = 20  # Max lightly-linked before warning

# Customize weights (optional)
[health_check.link_weights]
explicit = 1.0
menu = 10.0
taxonomy = 1.0
related = 0.75
topical = 0.5
sequential = 0.25
```

**CLI Commands:**
```bash
# Full connectivity report
bengal graph report

# List isolated pages
bengal graph orphans --level isolated

# List lightly-linked pages
bengal graph orphans --level lightly

# CI mode with exit code
bengal graph report --ci --threshold-isolated 5
```

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
