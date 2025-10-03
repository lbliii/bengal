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
    from bengal.health import HealthCheck
    
    health = HealthCheck(site)
    report = health.run()
    print(report.format_console())
"""

from bengal.health.health_check import HealthCheck
from bengal.health.report import HealthReport, CheckResult, CheckStatus
from bengal.health.base import BaseValidator

__all__ = [
    'HealthCheck',
    'HealthReport',
    'CheckResult',
    'CheckStatus',
    'BaseValidator',
]

