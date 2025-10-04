---
title: "health.health_check"
layout: api-reference
type: python-module
source_file: "../../bengal/health/health_check.py"
---

# health.health_check

Main health check orchestrator.

Coordinates all validators and produces unified health reports.

**Source:** `../../bengal/health/health_check.py`

---

## Classes

### HealthCheck


Orchestrates health check validators and produces unified health reports.

By default, registers all standard validators. You can disable auto-registration
by passing auto_register=False, then manually register validators.

Usage:
    # Default: auto-registers all validators
    health = HealthCheck(site)
    report = health.run()
    print(report.format_console())
    
    # Manual registration:
    health = HealthCheck(site, auto_register=False)
    health.register(ConfigValidator())
    health.register(OutputValidator())
    report = health.run()




**Methods:**

#### __init__

```python
def __init__(self, site: 'Site', auto_register: bool = True)
```

Initialize health check system.

**Parameters:**

- **self**
- **site** (`'Site'`) - The Site object to validate
- **auto_register** (`bool`) = `True` - Whether to automatically register all default validators







---
#### register

```python
def register(self, validator: BaseValidator) -> None
```

Register a validator to be run.

**Parameters:**

- **self**
- **validator** (`BaseValidator`) - Validator instance to register

**Returns:** `None`






---
#### run

```python
def run(self, build_stats: dict = None, verbose: bool = False) -> HealthReport
```

Run all registered validators and produce a health report.

**Parameters:**

- **self**
- **build_stats** (`dict`) = `None` - Optional build statistics to include in report
- **verbose** (`bool`) = `False` - Whether to show verbose output during validation

**Returns:** `HealthReport` - HealthReport with results from all validators






---
#### run_and_print

```python
def run_and_print(self, build_stats: dict = None, verbose: bool = False) -> HealthReport
```

Run health checks and print console output.

**Parameters:**

- **self**
- **build_stats** (`dict`) = `None` - Optional build statistics
- **verbose** (`bool`) = `False` - Whether to show all checks (not just problems)

**Returns:** `HealthReport` - HealthReport






---
#### __repr__

```python
def __repr__(self) -> str
```

*No description provided.*

**Parameters:**

- **self**

**Returns:** `str`






---


