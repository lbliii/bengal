"""
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

```python
from bengal.health import HealthCheck

health = HealthCheck(site)
report = health.run()
print(report.format_console())
```
"""

from __future__ import annotations

from bengal.health.base import BaseValidator
from bengal.health.health_check import HealthCheck
from bengal.health.report import CheckResult, CheckStatus, HealthReport

__all__ = [
    "BaseValidator",
    "CheckResult",
    "CheckStatus",
    "HealthCheck",
    "HealthReport",
]
