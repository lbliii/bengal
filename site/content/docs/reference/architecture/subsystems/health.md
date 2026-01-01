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
- **Interface**: `validate(site, build_context=None) -> list[CheckResult]`
- **Features**:
  - Independent execution (no validator dependencies)
  - Error handling and crash recovery
  - Performance tracking per validator
  - Configuration-based enablement
  - Access to cached build artifacts via `build_context`

## Health Report (`bengal/health/report.py`)
- **Purpose**: Unified reporting structure for health check results
- **Components**:
  - `CheckStatus`: SUCCESS, INFO, SUGGESTION, WARNING, ERROR (ordered by severity)
  - `CheckResult`: Individual check result with recommendation
  - `ValidatorReport`: Results from a single validator
  - `HealthReport`: Aggregated report from all validators
- **Formats**:
  - Console output (colored, progressive disclosure)
  - JSON output (machine-readable)
  - Summary statistics (pass/warning/error counts)
  - Quality scoring (0-100 with ratings)

## Validators (`bengal/health/validators/`)

Validators are registered in phases based on execution cost and dependencies.

**Phase 1 - Core Validation:**
| Validator | Validates |
|-----------|-----------|
| **ConfigValidatorWrapper** | Configuration validity, essential fields, common issues |
| **URLCollisionValidator** | Duplicate URL detection (catches conflicts early) |
| **OwnershipPolicyValidator** | URL ownership and content governance |

**Phase 2 - Content Validation:**
| Validator | Validates |
|-----------|-----------|
| **RenderingValidator** | HTML quality, template function usage, SEO metadata |
| **DirectiveValidator** | Directive syntax, completeness, and performance |
| **NavigationValidator** | Page navigation (next/prev, breadcrumbs, ancestors) |
| **MenuValidator** | Menu structure integrity, circular reference detection |
| **TaxonomyValidator** | Tags, categories, archives, pagination integrity |
| **TrackValidator** | Learning track structure and progression |
| **LinkValidatorWrapper** | Broken links detection (internal and external) |
| **AnchorValidator** | Explicit anchor targets and cross-reference integrity |

**Phase 3 - Advanced Validation:**
| Validator | Validates |
|-----------|-----------|
| **CacheValidator** | Incremental build cache integrity and consistency |
| **PerformanceValidator** | Build performance metrics and bottleneck detection |

**Phase 4 - Production-Ready Validation:**
| Validator | Validates |
|-----------|-----------|
| **RSSValidator** | RSS feed quality, XML validity, URL formatting |
| **SitemapValidator** | Sitemap.xml validity for SEO, no duplicate URLs |
| **FontValidator** | Font downloads, CSS generation, file sizes |
| **AssetValidator** | Asset optimization, minification hints, size analysis |

**Phase 5 - Knowledge Graph Validation:**
| Validator | Validates |
|-----------|-----------|
| **ConnectivityValidator** | Page connectivity using semantic link model and weighted scoring |

**Specialized Validators** (not auto-registered):
| Validator | Validates |
|-----------|-----------|
| **AutodocValidator** | API documentation HTML structure validation |
| **OutputValidator** | Page sizes, asset presence (redundant with build errors) |
| **CrossReferenceValidator** | Internal cross-reference resolution |
| **AccessibilityValidator** | WCAG compliance and accessibility checks |
| **AssetURLValidator** | Asset URL resolution and validation |

**Utility Classes** (not BaseValidator subclasses):
| Class | Purpose |
|-------|---------|
| **TemplateValidator** | Jinja2 template syntax validation (requires TemplateEngine) |

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

**Connectivity levels:**
| Level | Score Range | Status |
|-------|-------------|--------|
| Well-connected | ≥ 2.0 | No action needed |
| Adequately linked | 1.0 - 2.0 | Could improve |
| Lightly linked | 0.25 - 1.0 | Should improve (only structural links) |
| Isolated | < 0.25 | Needs attention |

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

Health checks use a **tiered validation system** for optimal performance:

| Tier | Name | Time | Trigger | Validators |
|------|------|------|---------|------------|
| 1 | `build` | <100ms | Always | Config, URL Collisions, Rendering, Directives, Navigation, Menu, Taxonomy |
| 2 | `full` | ~500ms | `--full` flag | + Connectivity, Cache, Performance, Anchors |
| 3 | `ci` | ~30s | `--ci` flag or CI env | + External link checking (LinkValidatorWrapper) |

**Configuration via `bengal.toml`:**

```toml
[health_check]
enabled = true
verbose = false
strict_mode = false

# Connectivity thresholds
isolated_threshold = 5        # Max isolated pages before error
lightly_linked_threshold = 20 # Max lightly-linked before warning

# Connectivity score thresholds
[health_check.connectivity_thresholds]
well_connected = 2.0    # Score >= 2.0
adequately_linked = 1.0 # Score 1.0-2.0
lightly_linked = 0.25   # Score 0.25-1.0
# Score < 0.25 = isolated

# Link type weights for scoring
[health_check.link_weights]
explicit = 1.0    # Human-authored markdown links
menu = 10.0       # Navigation menu items
taxonomy = 1.0    # Shared tags/categories
related = 0.75    # Algorithm-computed related posts
topical = 0.5     # Section hierarchy (parent → child)
sequential = 0.25 # Next/prev navigation
```

**Per-profile validator filtering:**

Validators run based on the active build profile:

| Profile | Validators Enabled |
|---------|-------------------|
| `writer` | Config, Menu (fast feedback) |
| `theme-dev` | + Rendering, Directives |
| `dev` | All validators (full observability) |

Validators can be explicitly enabled/disabled in config regardless of profile.

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
