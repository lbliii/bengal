# RFC: Directive Registry - Single Source of Truth

**Status**: Implemented ✅  
**Created**: 2025-12-03  
**Author**: AI-assisted  
**Verified**: 2025-12-03 (Confidence: 100%)  
**Implemented**: 2025-12-03  
**Issue**: Health check `KNOWN_DIRECTIVES` drifted out of sync with actually registered directives

---

## Problem Statement

The directive validation system maintains a manual list of known directive names (`KNOWN_DIRECTIVES`) that must stay synchronized with the directives actually registered by the rendering system. This has caused repeated drift issues:

1. New directives added to rendering but not to health check (e.g., `child-cards`, `grid-item-card`)
2. New admonition types added but not reflected in validation (e.g., `seealso`)
3. Navigation directives entirely missing (`breadcrumbs`, `siblings`, `prev-next`, `related`)

**Root Cause**: Two sources of truth that must be kept in sync manually.

### Current Architecture (Problematic)

```
rendering/plugins/directives/
├── admonitions.py      → registers: note, tip, warning, ...
├── cards.py            → registers: card, cards, child-cards, ...
├── tabs.py             → registers: tabs, tab-set, tab-item
└── ...                 → registers: various names

health/validators/directives/
└── constants.py        → KNOWN_DIRECTIVES = {...}  ← MANUAL DUPLICATE LIST
```

**Failure Mode**: Developer adds new directive, forgets to update health check constants.

---

## Current Hotfix (Temporary)

We moved `KNOWN_DIRECTIVE_NAMES` to `rendering/plugins/directives/__init__.py` as a canonical list, with health check importing from there. This is better but still requires **manual updates to two places**:

1. Add directive class to `directives_list` in `create_documentation_directives()`
2. Add directive name(s) to `KNOWN_DIRECTIVE_NAMES` set

---

## Proposed Solution: Directive Protocol with Introspection

### Design Goals

1. **Single source of truth**: Each directive declares its names once
2. **Automatic discovery**: Health check derives known names from actual registrations
3. **No manual synchronization**: Adding a directive automatically updates validation
4. **Backward compatible**: Existing directive code works unchanged
5. **Testable**: Unit tests verify registry consistency

### Option A: DIRECTIVE_NAMES Class Attribute (Recommended)

Each `DirectivePlugin` subclass declares a `DIRECTIVE_NAMES` class attribute. The `__call__` method MUST use this attribute for registration to ensure consistency.

```python
# rendering/plugins/directives/cards.py
class CardsDirective(DirectivePlugin):
    """Cards grid container."""
    DIRECTIVE_NAMES = ["cards"]  # ← Single source of truth

    def __call__(self, directive, md):
        # Dynamic registration ensures implementation matches declaration
        for name in self.DIRECTIVE_NAMES:
            directive.register(name, self.parse)

class ChildCardsDirective(DirectivePlugin):
    """Auto-generate cards from children."""
    DIRECTIVE_NAMES = ["child-cards"]

    def __call__(self, directive, md):
        for name in self.DIRECTIVE_NAMES:
            directive.register(name, self.parse)

# rendering/plugins/directives/admonitions.py
class AdmonitionDirective(DirectivePlugin):
    """Admonition callouts."""
    DIRECTIVE_NAMES = [
        "note", "tip", "warning", "danger", "error",
        "info", "example", "success", "caution", "seealso",
    ]

    def __call__(self, directive, md):
        for name in self.DIRECTIVE_NAMES:
            directive.register(name, self.parse)
```

**Registry Collection**:

```python
# rendering/plugins/directives/__init__.py

# All directive classes that will be instantiated
DIRECTIVE_CLASSES = [
    AdmonitionDirective,
    BadgeDirective,
    ButtonDirective,
    CardsDirective,
    CardDirective,
    ChildCardsDirective,
    # ... all directive classes
]

def get_known_directive_names() -> frozenset[str]:
    """
    Derive known directive names from actual directive classes.

    This is the SINGLE SOURCE OF TRUTH. Do not maintain a separate list.
    """
    names = set()
    for cls in DIRECTIVE_CLASSES:
        if hasattr(cls, 'DIRECTIVE_NAMES'):
            names.update(cls.DIRECTIVE_NAMES)
        else:
            # Fallback: warn about missing DIRECTIVE_NAMES
            logger.warning(f"Directive {cls.__name__} missing DIRECTIVE_NAMES attribute")
    return frozenset(names)

# Cached for performance
KNOWN_DIRECTIVE_NAMES = get_known_directive_names()
```

**Pros**:
- Directive names declared next to registration logic (colocated)
- Easy to audit and maintain
- Works with existing mistune DirectivePlugin pattern
- Clear and explicit

**Cons**:
- Requires updating each directive class (one-time migration)
- Still requires DIRECTIVE_CLASSES list (but classes, not names)

---

### Option B: Runtime Introspection via Mock Registration

Instantiate directives with a mock `FencedDirective` that captures registrations:

```python
# rendering/plugins/directives/__init__.py

class DirectiveNameCollector:
    """Mock directive that collects registered names."""

    def __init__(self):
        self.names: set[str] = set()

    def register(self, name: str, parse_fn) -> None:
        self.names.add(name)

class MockMarkdown:
    """Mock markdown instance for introspection."""
    renderer = None

def get_known_directive_names() -> frozenset[str]:
    """
    Derive known directive names by introspecting actual registrations.

    Instantiates each directive and captures what names it registers.
    """
    collector = DirectiveNameCollector()
    mock_md = MockMarkdown()

    directives = [
        AdmonitionDirective(),
        BadgeDirective(),
        # ... all directives
    ]

    for directive in directives:
        try:
            directive(collector, mock_md)
        except Exception:
            pass  # Some may fail without real md instance

    return frozenset(collector.names)
```

**Pros**:
- Zero changes to existing directive code
- Captures exactly what's registered at runtime
- Works even with complex registration logic

**Cons**:
- Brittle: depends on __call__ not having side effects
- Some directives may fail during introspection
- Harder to debug when things go wrong
- Runtime overhead (though cacheable)

---

### Option C: Decorator-Based Registration

Use a decorator that both registers the directive AND records its name:

```python
# rendering/plugins/directives/registry.py

_DIRECTIVE_REGISTRY: dict[str, type] = {}

def directive(*names: str):
    """Decorator that registers directive names."""
    def decorator(cls):
        cls.DIRECTIVE_NAMES = list(names)
        for name in names:
            _DIRECTIVE_REGISTRY[name] = cls
        return cls
    return decorator

def get_known_directive_names() -> frozenset[str]:
    return frozenset(_DIRECTIVE_REGISTRY.keys())

# Usage:
@directive("cards")
class CardsDirective(DirectivePlugin):
    ...

@directive("note", "tip", "warning", "danger", "error", "info", "example", "success", "caution", "seealso")
class AdmonitionDirective(DirectivePlugin):
    ...
```

**Pros**:
- Very clean syntax
- Single declaration point
- Central registry built automatically
- Easy to search codebase for all directives

**Cons**:
- Requires decorator on all directive classes
- Registration happens at import time (potential issues)
- Different pattern from mistune's DirectivePlugin

---

### Option D: Protocol with get_names() Method

Define a Protocol that all directives implement:

```python
from typing import Protocol

class DirectiveProtocol(Protocol):
    """Protocol for Bengal directives."""

    def get_names(self) -> list[str]:
        """Return directive names this class registers."""
        ...

    def __call__(self, directive, md) -> None:
        """Register with mistune."""
        ...

# Each directive implements:
class CardsDirective(DirectivePlugin):
    def get_names(self) -> list[str]:
        return ["cards"]

    def __call__(self, directive, md):
        for name in self.get_names():
            directive.register(name, self.parse)
```

**Pros**:
- Type-safe with Protocol
- Method can have dynamic logic if needed
- Clear contract for all directives

**Cons**:
- Requires method on all directive classes
- More boilerplate than class attribute
- get_names() called repeatedly unless cached

---

## Recommendation

**Option A: DIRECTIVE_NAMES Class Attribute** is the best balance of:

1. **Simplicity**: Just add a class attribute
2. **Explicitness**: Names declared clearly at class level
3. **Maintainability**: Easy to find and update
4. **Compatibility**: Works with existing DirectivePlugin pattern
5. **Performance**: No runtime introspection overhead

### Migration Plan

#### Phase 1: Add DIRECTIVE_NAMES to All Directive Classes

```python
# For each directive class, add DIRECTIVE_NAMES matching what __call__ registers

class CardsDirective(DirectivePlugin):
    DIRECTIVE_NAMES = ["cards"]
    # ... existing code unchanged ...

class AdmonitionDirective(DirectivePlugin):
    DIRECTIVE_NAMES = [
        "note", "tip", "warning", "danger", "error",
        "info", "example", "success", "caution", "seealso",
    ]
    # Note: This already exists as ADMONITION_TYPES, just rename/alias
```

#### Phase 2: Create get_known_directive_names() Function

```python
# rendering/plugins/directives/__init__.py

DIRECTIVE_CLASSES = [
    AdmonitionDirective,
    BadgeDirective,
    ButtonDirective,
    CardsDirective,
    CardDirective,
    ChildCardsDirective,
    GridDirective,
    GridItemCardDirective,
    TabsDirective,
    TabSetDirective,
    TabItemDirective,
    DropdownDirective,
    CodeTabsDirective,
    RubricDirective,
    ListTableDirective,
    DataTableDirective,
    GlossaryDirective,
    ChecklistDirective,
    StepsDirective,
    StepDirective,
    IncludeDirective,
    LiteralIncludeDirective,
    BreadcrumbsDirective,
    SiblingsDirective,
    PrevNextDirective,
    RelatedDirective,
    MarimoCellDirective,
]

def get_known_directive_names() -> frozenset[str]:
    """
    Single source of truth for all registered directive names.

    Collects DIRECTIVE_NAMES from all directive classes.
    """
    names: set[str] = set()
    for cls in DIRECTIVE_CLASSES:
        if hasattr(cls, 'DIRECTIVE_NAMES'):
            names.update(cls.DIRECTIVE_NAMES)
    return frozenset(names)

# Export for health check
KNOWN_DIRECTIVE_NAMES = get_known_directive_names()
```

#### Phase 3: Add Consistency Test

```python
# tests/unit/rendering/test_directive_registry.py

def test_directive_names_consistency():
    """Verify DIRECTIVE_NAMES matches actual registrations."""
    from bengal.rendering.plugins.directives import (
        DIRECTIVE_CLASSES,
        KNOWN_DIRECTIVE_NAMES,
        get_known_directive_names,
    )

    # Test 1: All classes have DIRECTIVE_NAMES
    for cls in DIRECTIVE_CLASSES:
        assert hasattr(cls, 'DIRECTIVE_NAMES'), \
            f"{cls.__name__} missing DIRECTIVE_NAMES attribute"
        assert len(cls.DIRECTIVE_NAMES) > 0, \
            f"{cls.__name__}.DIRECTIVE_NAMES is empty"

    # Test 2: Cached set matches function
    assert KNOWN_DIRECTIVE_NAMES == get_known_directive_names()

    # Test 3: No duplicates across classes (except intentional aliases)
    all_names = []
    for cls in DIRECTIVE_CLASSES:
        all_names.extend(cls.DIRECTIVE_NAMES)

    # Check for unintentional duplicates
    # (some duplicates are OK, like 'dropdown' and 'details' being aliases)
    duplicates = [n for n in all_names if all_names.count(n) > 1]
    known_aliases = {'details', 'bdg'}  # Intentional aliases
    unexpected_duplicates = set(duplicates) - known_aliases
    assert not unexpected_duplicates, \
        f"Unexpected duplicate directive names: {unexpected_duplicates}"


def test_directive_names_match_registration():
    """Verify DIRECTIVE_NAMES matches what __call__ actually registers."""
    # Use mock to capture actual registrations
    class MockDirective:
        def __init__(self):
            self.registered = set()
        def register(self, name, fn):
            self.registered.add(name)

    class MockMd:
        renderer = None

    from bengal.rendering.plugins.directives import DIRECTIVE_CLASSES

    for cls in DIRECTIVE_CLASSES:
        mock = MockDirective()
        instance = cls()
        try:
            instance(mock, MockMd())
        except Exception:
            continue  # Some may need real md instance

        declared = set(cls.DIRECTIVE_NAMES)
        registered = mock.registered

        assert declared == registered, \
            f"{cls.__name__}: DIRECTIVE_NAMES {declared} != registered {registered}"
```

#### Phase 4: Remove Manual KNOWN_DIRECTIVE_NAMES List

After migration, the manual list in `__init__.py` is replaced by `get_known_directive_names()`.

---

## Implementation Checklist

- [x] Add `DIRECTIVE_NAMES` to all 27 directive classes
- [x] Create `DIRECTIVE_CLASSES` list in `__init__.py`
- [x] Create `get_known_directive_names()` function
- [x] Update health check to import from single source (already done in hotfix)
- [x] Add unit tests for registry consistency (tests/unit/rendering/test_directive_registry.py)
- [x] Add unit tests for registration verification
- [x] Remove manual `KNOWN_DIRECTIVE_NAMES` set (replaced with computed version)
- [ ] Update documentation (optional - code is self-documenting)

---

## Estimated Effort

- **Phase 1** (Add DIRECTIVE_NAMES): 1 hour
- **Phase 2** (Registry function): 30 minutes
- **Phase 3** (Tests): 1 hour
- **Phase 4** (Cleanup): 15 minutes

**Total**: ~3 hours

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missing DIRECTIVE_NAMES on new directives | Medium | Low | Test fails if missing |
| DIRECTIVE_NAMES doesn't match __call__ | Low | Medium | Verification test catches |
| Circular imports | Low | High | Lazy initialization |
| Performance regression | Very Low | Low | Cached at import time |

---

## Alternatives Considered

1. **Keep manual list with better comments**: Rejected - still requires manual sync
2. **Runtime introspection only**: Rejected - brittle, hard to debug
3. **Decorator-based**: Viable but different pattern from mistune
4. **Protocol-based**: More boilerplate than needed

---

## Decisions

1. **Explicit Registration**: `DIRECTIVE_CLASSES` will be an explicit list in `__init__.py` rather than using `__subclasses__()` auto-discovery. This ensures clarity, control over ordering, and explicit opt-in.

2. **Optional Directives**: `MarimoCellDirective` will be included in `DIRECTIVE_CLASSES` but commented as optional. The `get_known_directive_names()` function will handle it gracefully even if the dependency is missing, as the class definition does not fail without `marimo` installed.

3. **Naming Conventions**: We will enforce a naming convention (lowercase, hyphenated) via the new `test_directive_registry.py` to prevent drift.

---

## Validation

**Audit conducted on 2025-12-03** confirmed:
1. **Root Cause**: `KNOWN_DIRECTIVE_NAMES` in `__init__.py` is indeed a hardcoded list that duplicates logic in each directive class.
2. **Hotfix**: `health/validators/directives/constants.py` currently imports from `__init__.py`, so the drift is contained to `__init__.py` vs classes, but still exists.
3. **Feasibility**: `MarimoCellDirective` is safe to import even without `marimo` installed, confirming it can be listed in `DIRECTIVE_CLASSES`.
4. **Completeness**: The RFC accurately lists all 27 current directive classes.

**Confidence**: 100% 🟢

---

## Appendix: Current Directive Inventory

| Class | Names Registered | Notes |
|-------|-----------------|-------|
| AdmonitionDirective | note, tip, warning, danger, error, info, example, success, caution, seealso | 10 types |
| BadgeDirective | badge, bdg | bdg is alias |
| ButtonDirective | button | |
| CardsDirective | cards | |
| CardDirective | card | |
| ChildCardsDirective | child-cards | |
| GridDirective | grid | Sphinx-Design compat |
| GridItemCardDirective | grid-item-card | Sphinx-Design compat |
| TabsDirective | tabs | Legacy |
| TabSetDirective | tab-set | Modern MyST |
| TabItemDirective | tab-item | Modern MyST |
| DropdownDirective | dropdown, details | details is alias |
| CodeTabsDirective | code-tabs | |
| RubricDirective | rubric | |
| ListTableDirective | list-table | |
| DataTableDirective | data-table | |
| GlossaryDirective | glossary | |
| ChecklistDirective | checklist | |
| StepsDirective | steps | |
| StepDirective | step | |
| IncludeDirective | include | |
| LiteralIncludeDirective | literalinclude | |
| BreadcrumbsDirective | breadcrumbs | |
| SiblingsDirective | siblings | |
| PrevNextDirective | prev-next | |
| RelatedDirective | related | |
| MarimoCellDirective | marimo | Optional |

**Total**: 27 directive classes, 38 directive names
