# Data Model Organization Analysis

**Date**: October 9, 2025  
**Status**: Analysis & Recommendations  
**Question**: Should data models be organized differently like orchestrators are?

---

## Current State

### Orchestrators (Well Organized) ✅
```
bengal/orchestration/
├── __init__.py
├── build.py              # BuildOrchestrator
├── content.py            # ContentOrchestrator
├── render.py             # RenderOrchestrator
├── taxonomy.py           # TaxonomyOrchestrator
├── asset.py              # AssetOrchestrator
├── menu.py               # MenuOrchestrator
├── section.py            # SectionOrchestrator
├── postprocess.py        # PostprocessOrchestrator
└── incremental.py        # IncrementalOrchestrator
```

**Pattern**: 
- ✅ Grouped by purpose (orchestration)
- ✅ Flat file structure (one orchestrator per file)
- ✅ Clear naming: `{domain}.py` → `{Domain}Orchestrator`
- ✅ Centralized imports in `__init__.py`

---

### Data Models (Mixed Organization) ⚠️
```
bengal/core/
├── __init__.py
├── page/                 # Page model (PACKAGE - 6 files)
│   ├── __init__.py
│   ├── metadata.py
│   ├── navigation.py
│   ├── computed.py
│   ├── relationships.py
│   └── operations.py
├── section.py            # Section model (FILE - 1 file)
├── site.py               # Site model (FILE - 1 file)
├── asset.py              # Asset model (FILE - 1 file)
└── menu.py               # Menu model (FILE - 1 file)
```

**Issues**:
- ⚠️ Inconsistent: Page is a package, others are files
- ⚠️ Name `core` is generic (what is "core"?)
- ⚠️ Mixed with non-model files
- ⚠️ No clear pattern for growth

---

## Analysis of Common Patterns

### Option 1: Keep Current Structure ✅ (Recommended)

**Keep `bengal/core/` as is**

**Rationale:**
```
bengal/core/          # "Core domain models"
bengal/orchestration/ # "Operations on models"
bengal/rendering/     # "Rendering services"
bengal/discovery/     # "Discovery services"
bengal/cache/         # "Caching services"
bengal/health/        # "Health check services"
```

**Pros:**
- ✅ Minimal disruption
- ✅ `core` implies "foundational/essential"
- ✅ Common Python pattern (Django uses `models.py`, Flask uses various)
- ✅ Page package already shows path forward for complex models
- ✅ Matches your mental model: services operate on core models

**Cons:**
- ⚠️ Name `core` less specific than `orchestration`
- ⚠️ Inconsistent: Page is package, others are files

**Recommendation**: ✅ **Keep, but standardize growth pattern**

---

### Option 2: Rename to `bengal/models/` ❌ (Not Recommended)

```
bengal/models/
├── page/
├── section.py
├── site.py
├── asset.py
└── menu.py
```

**Pros:**
- More explicit naming
- Common in Django/SQLAlchemy projects

**Cons:**
- ❌ Breaking change (all imports change)
- ❌ `models` implies database/ORM (Bengal doesn't use DB)
- ❌ Low value for high disruption
- ❌ Inconsistent with `orchestration` naming (why not `orchestrators`?)

**Recommendation**: ❌ **Don't do this**

---

### Option 3: Package Everything ❌ (Over-engineering)

```
bengal/core/
├── page/
│   ├── __init__.py
│   ├── metadata.py
│   └── ...
├── section/
│   ├── __init__.py
│   └── section.py
├── site/
│   ├── __init__.py
│   └── site.py
├── asset/
│   ├── __init__.py
│   └── asset.py
└── menu/
    ├── __init__.py
    └── menu.py
```

**Pros:**
- Consistent structure

**Cons:**
- ❌ Over-engineering for simple models
- ❌ Extra boilerplate for no benefit
- ❌ Harder to navigate (more nesting)

**Recommendation**: ❌ **Don't do this**

---

## Recommended Organization Pattern

### Standard: File per Model (Simple Models)

```python
# bengal/core/section.py
@dataclass
class Section:
    """Single file, < 300 lines, simple model"""
    pass
```

**When to use:**
- Model < 300-400 lines
- No complex mixins needed
- Clear single responsibility

**Examples**: Section, Site, Asset, Menu

---

### Exception: Package per Model (Complex Models)

```python
# bengal/core/page/__init__.py
from .metadata import PageMetadataMixin
from .navigation import PageNavigationMixin
# ...

class Page(mixins...):
    pass
```

**When to use:**
- Model > 400 lines
- Multiple concerns/mixins
- Benefits from modularization

**Examples**: Page (726 lines → package)

---

## Naming Conventions

### Current (Keep These) ✅

**Models:**
- `Page` - Simple, clear
- `Section` - Simple, clear
- `Site` - Simple, clear
- `Asset` - Simple, clear
- `Menu` - Simple, clear

**Orchestrators:**
- `BuildOrchestrator` - Clear suffix
- `ContentOrchestrator` - Clear suffix
- Pattern: `{Domain}Orchestrator`

**Services:**
- `LinkValidator` - Clear suffix
- `PerformanceCollector` - Clear suffix
- `BuildCache` - Clear suffix

---

## Comparison with Other Frameworks

### Django
```
myapp/
├── models.py         # or models/ package
├── views.py
├── urls.py
└── admin.py
```
**Pattern**: Grouped by layer (models, views, etc.)

### FastAPI / SQLAlchemy
```
app/
├── models/
│   ├── user.py
│   ├── post.py
├── schemas/
│   ├── user.py
│   ├── post.py
└── api/
    ├── endpoints/
```
**Pattern**: Grouped by type, then by domain

### Bengal (Current)
```
bengal/
├── core/              # Domain models
├── orchestration/     # Operations
├── rendering/         # Services
└── utils/             # Utilities
```
**Pattern**: Grouped by architectural layer

**Verdict**: Bengal's pattern is valid and clean ✅

---

## Recommendations

### 1. ✅ Keep `bengal/core/` Name

**Why:**
- Established convention in your codebase
- `core` = "foundational domain models"
- Low disruption, high clarity
- Consistent with other layer names

**Action**: None needed

---

### 2. ✅ Standardize Model Organization Pattern

**Rule of Thumb:**

```python
# Simple model (< 400 lines) → Single file
bengal/core/section.py      # ✅ 296 lines
bengal/core/site.py         # ✅ 441 lines (borderline)
bengal/core/asset.py        # ✅ 144 lines
bengal/core/menu.py         # ✅ 89 lines

# Complex model (> 400 lines) → Package
bengal/core/page/           # ✅ 726 lines → package
bengal/core/site/           # 🤔 441 lines (could consider)
```

**Action**: Document this pattern

---

### 3. ✅ Add Clear Module-Level Docstrings

**Pattern:**
```python
# bengal/core/section.py
"""
Section data model - represents content groupings.

This module contains the Section class, which represents a folder or
logical grouping of pages in the site hierarchy.

Part of: Core Domain Models
Pattern: Simple file-based model (< 400 lines)
"""

# bengal/core/page/__init__.py
"""
Page data model - represents individual content pages.

This module contains the Page class with multiple mixins for
different concerns (metadata, navigation, computed properties, etc.).

Part of: Core Domain Models
Pattern: Package-based model (> 400 lines, multiple concerns)
"""
```

**Action**: Add to all core models

---

### 4. ✅ Update `bengal/core/__init__.py` Documentation

```python
"""
Core domain models for Bengal SSG.

This package contains the foundational data models that represent
the content structure of a Bengal site:

- Page: Individual content pages (complex model with mixins)
- Section: Content groupings and hierarchy
- Site: Top-level site container
- Asset: Static assets (CSS, JS, images)
- Menu: Navigation menus

Organization Pattern:
- Simple models (< 400 lines): Single file (section.py)
- Complex models (> 400 lines): Package (page/)

Related:
- Operations on these models: bengal/orchestration/
- Discovery of models: bengal/discovery/
- Rendering of models: bengal/rendering/
"""

from .page import Page
from .section import Section
from .site import Site
from .asset import Asset
from .menu import Menu

__all__ = ['Page', 'Section', 'Site', 'Asset', 'Menu']
```

**Action**: Update `__init__.py`

---

### 5. ⚠️ Consider: Future Growth

**If Site.py grows beyond 500 lines**, consider:

```
bengal/core/site/
├── __init__.py           # Main Site class
├── discovery.py          # Discovery methods
├── references.py         # Reference setup methods
└── cascades.py           # Cascade logic
```

**Similar pattern to Page package**

**Action**: Monitor site.py size (currently 441 lines)

---

## File Organization Matrix

| Model | Lines | Structure | Rationale |
|-------|-------|-----------|-----------|
| **Page** | 726 → 827 | Package (6 files) | ✅ Complex, multiple concerns |
| **Site** | 441 | Single file | ⚠️ Borderline (could modularize) |
| **Section** | 296 | Single file | ✅ Simple, single responsibility |
| **Asset** | 144 | Single file | ✅ Simple, single responsibility |
| **Menu** | 89 | Single file | ✅ Simple, single responsibility |

**Growth Triggers:**
- **< 400 lines**: Keep as single file
- **400-500 lines**: Consider modularization
- **> 500 lines**: Strong candidate for package

---

## Comparison: Models vs Orchestrators

### Why the Difference is OK

**Models (`bengal/core/`)**:
- Purpose: Data structures and domain logic
- Pattern: File or package per model (based on complexity)
- Examples: Page (package), Section (file)
- Growth: Vertical (one model becomes package)

**Orchestrators (`bengal/orchestration/`)**:
- Purpose: Operations and workflows
- Pattern: One file per orchestrator (all similar complexity)
- Examples: BuildOrchestrator, RenderOrchestrator
- Growth: Horizontal (add new orchestrators)

**Both patterns are appropriate for their use cases!**

---

## Architecture Summary

```
bengal/
│
├─ core/                      # 🏛️ DOMAIN MODELS (data)
│  ├─ page/                   # Complex model (package)
│  ├─ section.py              # Simple model (file)
│  ├─ site.py                 # Simple model (file)
│  └─ ...                     # Simple models (files)
│
├─ orchestration/             # 🎭 OPERATIONS (business logic)
│  ├─ build.py                # Orchestrator (file)
│  ├─ render.py               # Orchestrator (file)
│  └─ ...                     # Orchestrators (files)
│
├─ rendering/                 # 🎨 SERVICES (rendering)
│  ├─ parser.py               # Service (file)
│  ├─ pipeline.py             # Service (file)
│  └─ plugins/                # Service group (package)
│
├─ discovery/                 # 🔍 SERVICES (discovery)
│  ├─ content_discovery.py    # Service (file)
│  └─ asset_discovery.py      # Service (file)
│
├─ cache/                     # 💾 SERVICES (caching)
├─ health/                    # 🏥 SERVICES (health checks)
├─ server/                    # 🌐 SERVICES (dev server)
└─ utils/                     # 🛠️ UTILITIES (helpers)
```

**Pattern**: Each top-level package represents an architectural layer or concern.

---

## Implementation Checklist

- [x] ✅ Keep `bengal/core/` as models location
- [ ] 📝 Add module docstrings to all core models
- [ ] 📝 Update `bengal/core/__init__.py` with organization pattern
- [ ] 📝 Document 400-line threshold for package conversion
- [ ] 👀 Monitor `site.py` size (currently 441 lines)
- [ ] 📚 Add architecture doc explaining layer organization

---

## Conclusion

**Answer**: Your current organization is correct! ✅

**Key Points:**
1. ✅ `bengal/core/` is appropriate for models (like `orchestration/` for orchestrators)
2. ✅ Page package shows good pattern for complex models
3. ✅ Other models appropriately stay as simple files
4. ✅ The asymmetry (package vs files) is intentional and correct
5. 📝 Just needs better documentation of the pattern

**No refactoring needed** - just document the existing pattern!

---

## Related Documents

- `PAGE_REFACTORING.md` - Page package modularization
- `PAGE_OBSERVABILITY_ANALYSIS.md` - Why models don't log
- `ARCHITECTURE.md` - Overall system architecture

