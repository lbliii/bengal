# performance_collector

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/performance_collector.py

Performance metrics collection for Bengal SSG.

Collects and persists build performance metrics including timing and memory usage.
This is Phase 1 of the continuous performance tracking system.

Example:
    from bengal.utils.performance_collector import PerformanceCollector

    collector = PerformanceCollector()
    collector.start_build()

    # ... run build ...

    stats = collector.end_build(build_stats)
    collector.save(stats)

*Note: Template has undefined variables. This is fallback content.*
