---
title: "health"
layout: api-reference
type: python-module
source_file: "../../bengal/health/__init__.py"
---

# health

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

**Source:** `../../bengal/health/__init__.py`

---


