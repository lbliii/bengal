# health

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/health/__init__.py

Health check system for Bengal SSG.

Provides comprehensive validation of builds across all systems:
- Configuration validation
- Content discovery validation
- Rendering validation
- Navigation validation
- Taxonomy validation
- Output validation
- Cache integrity validation
- Performance validation

Usage:
    from bengal.health import HealthCheck

    health = HealthCheck(site)
    report = health.run()
    print(report.format_console())

*Note: Template has undefined variables. This is fallback content.*
