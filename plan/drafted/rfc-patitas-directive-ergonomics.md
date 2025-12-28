# RFC: Patitas Directive Ergonomics Improvements

| Field        | Value                                      |
|--------------|-------------------------------------------|
| **Status**   | Draft                                      |
| **Author**   | Bengal Team                                |
| **Created**  | 2025-12-28                                 |
| **Updated**  | 2025-12-28                                 |
| **RFC**      | rfc-patitas-directive-ergonomics           |
| **Depends**  | rfc-patitas-bengal-directive-migration     |
| **Blocks**   | —                                          |

---

## Executive Summary

**Problem**: After implementing 25+ directives for Patitas, several API friction points emerged that add boilerplate and reduce developer experience without benefiting thread-safety or correctness.

**Solution**: Four targeted improvements to the directive authoring experience:

| Improvement | Impact | Risk |
|-------------|--------|------|
| Typed options preservation | High — eliminates serialize/deserialize | Low |
| `preserves_raw_content` flag | Medium — discoverable pattern | Low |
| Auto-contract validation | Medium — catches errors early | Medium |
| `@directive` decorator | Medium — reduces boilerplate | Low |

**Goal**: Make directive authoring feel as ergonomic as Flask route handlers while maintaining full thread-safety guarantees.

---

## Motivation

### Current Pain Points

After implementing directives for cards, checklist, media, and tables, four consistent friction points emerged:

#### 1. Options Type Erasure

**Current**: Options are serialized to `frozenset[tuple[str, str]]` in `parse()`, then manually reconstructed in `render()`:

```python
# In parse() — serialize typed options to strings
def parse(self, name, title, options, content, children, location):
    opts_items = [
        ("columns", str(options.columns)),      # int → str
        ("lightbox", str(options.lightbox)),    # bool → str  
        ("gap", options.gap),
    ]
    return Directive(..., options=frozenset(opts_items))

# In render() — deserialize strings back to types
def render(self, node, rendered_children, sb):
    opts = dict(node.options)
    columns = int(opts.get("columns", "3"))     # str → int
    lightbox = opts.get("lightbox", "True") != "False"  # str → bool
```

**Problems**:
- Type information lost in transit
- Boilerplate in both directions
- Easy to introduce bugs (`"True"` vs `"true"` vs `True`)
- No IDE autocomplete in `render()`

#### 2. Raw Content Discovery

**Current**: Directives needing unparsed content must:
1. Know to pass `raw_content=content` in `parse()`
2. Access `node.raw_content` in `render()`

```python
def parse(self, ...):
    return Directive(
        ...,
        raw_content=content,  # Easy to forget!
    )

def render(self, node, ...):
    images = self._parse_images(node.raw_content or "")  # or "" for safety
```

**Problems**:
- Not discoverable from protocol definition
- Easy to forget, causing `None` access errors
- No clear signal that a directive needs raw content

#### 3. Contract Validation is Manual

**Current**: Contracts are defined but never enforced:

```python
# In contracts.py
CARD_CONTRACT = DirectiveContract(requires_parent=("cards",))

# In CardDirective
contract = CARD_CONTRACT  # Defined but not checked!

# This renders without error even when card is outside cards:
:::{card} Orphan Card
Content
:::
```

**Problems**:
- Contracts are metadata only
- Nesting violations silently produce invalid HTML
- No build-time or parse-time warnings

#### 4. Directive Class Boilerplate

**Current**: Every directive requires the same class structure:

```python
class ChecklistDirective:
    names: ClassVar[tuple[str, ...]] = ("checklist",)
    token_type: ClassVar[str] = "checklist"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ChecklistOptions]] = ChecklistOptions

    def parse(self, name, title, options, content, children, location):
        ...

    def render(self, node, rendered_children, sb):
        ...
```

**Problems**:
- 4 class attributes + 2 methods for every directive
- `token_type` often duplicates directive name
- Common patterns repeated across directives

---

## Proposed Solutions

### Solution 1: Typed Options on Directive Node

**Change**: Store typed options object directly on `Directive` node instead of `frozenset[tuple[str, str]]`.

#### Before (Current)

```python
@dataclass(frozen=True, slots=True)
class Directive(Node):
    name: str
    title: str | None
    options: frozenset[tuple[str, str]]  # Type-erased
    children: tuple[Block, ...]
    raw_content: str | None = None
```

#### After (Proposed)

```python
@dataclass(frozen=True, slots=True)
class Directive(Node):
    name: str
    title: str | None
    options: DirectiveOptions  # Typed options object
    children: tuple[Block, ...]
    raw_content: str | None = None
```

#### Impact on Directive Authors

**Before**:
```python
def parse(self, name, title, options, content, children, location):
    # Manual serialization
    opts_items = [
        ("columns", str(options.columns)),
        ("lightbox", str(options.lightbox)),
    ]
    return Directive(..., options=frozenset(opts_items))

def render(self, node, rendered_children, sb):
    # Manual deserialization
    opts = dict(node.options)
    columns = int(opts.get("columns", "3"))
```

**After**:
```python
def parse(self, name, title, options, content, children, location):
    # Just pass through!
    return Directive(..., options=options)

def render(self, node, rendered_children, sb):
    # Direct typed access!
    columns = node.options.columns  # IDE autocomplete works!
```

#### Thread Safety

Still safe — `DirectiveOptions` is a frozen dataclass:

```python
@dataclass(frozen=True, slots=True)
class GalleryOptions(DirectiveOptions):
    columns: int = 3
```

#### Migration Path

1. Add `typed_options: DirectiveOptions | None = None` field to `Directive`
2. Keep `options: frozenset[...]` for backward compatibility
3. Update renderer to prefer `typed_options` when present
4. Deprecate `options` frozenset in next major version

---

### Solution 2: `preserves_raw_content` Class Attribute

**Change**: Add explicit class attribute to signal directives that need raw content.

#### Protocol Addition

```python
@runtime_checkable
class DirectiveHandler(Protocol):
    names: ClassVar[tuple[str, ...]]
    token_type: ClassVar[str]
    contract: ClassVar[DirectiveContract | None]
    options_class: ClassVar[type[DirectiveOptions]]
    preserves_raw_content: ClassVar[bool] = False  # NEW
```

#### Usage

```python
class GalleryDirective:
    names = ("gallery",)
    token_type = "gallery"
    preserves_raw_content = True  # Clear signal!

    def render(self, node, rendered_children, sb):
        # Parser automatically preserved raw_content
        images = self._parse_images(node.raw_content)  # Guaranteed non-None
```

#### Parser Behavior

```python
def parse_directive(self, handler, ...):
    # Auto-preserve if handler signals it
    raw_content = content if handler.preserves_raw_content else None

    return handler.parse(
        name, title, options, content, children, location
    )
```

---

### Solution 3: Automatic Contract Validation

**Change**: Validate contracts at parse time, emit warnings for violations.

#### Validation Points

```
Parse Time (build):     Check parent/child constraints
                        Emit warning + continue (soft fail)

Strict Mode (opt-in):   Emit error + halt (hard fail)
```

#### Implementation

```python
class DirectiveParser:
    def __init__(self, registry, strict_contracts: bool = False):
        self.strict_contracts = strict_contracts

    def parse_directive(self, handler, parent_name, ...):
        contract = handler.contract

        if contract and contract.requires_parent:
            if parent_name not in contract.requires_parent:
                msg = f"Directive '{handler.names[0]}' requires parent {contract.requires_parent}, found '{parent_name}'"

                if self.strict_contracts:
                    raise DirectiveContractError(msg)
                else:
                    logger.warning("directive_contract_violation", message=msg)
```

#### Contract Extensions

```python
@dataclass(frozen=True)
class DirectiveContract:
    requires_parent: tuple[str, ...] | None = None
    requires_children: tuple[str, ...] | None = None
    allows_children: tuple[str, ...] | None = None  # Whitelist
    forbids_children: tuple[str, ...] | None = None  # Blacklist
    max_depth: int | None = None  # Nesting limit

    # NEW: Validation behavior
    severity: Literal["error", "warning", "info"] = "warning"
    message: str | None = None  # Custom error message
```

---

### Solution 4: `@directive` Decorator

**Change**: Provide a decorator that reduces boilerplate for simple directives.

#### Current (Verbose)

```python
class ChecklistDirective:
    names: ClassVar[tuple[str, ...]] = ("checklist",)
    token_type: ClassVar[str] = "checklist"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ChecklistOptions]] = ChecklistOptions

    def parse(self, name, title, options, content, children, location):
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,
            children=tuple(children),
        )

    def render(self, node, rendered_children, sb):
        # ... actual rendering logic
```

#### Proposed (Concise)

```python
@directive("checklist", options=ChecklistOptions)
def render_checklist(node: Directive, children: str, sb: StringBuilder) -> None:
    opts = node.options  # Typed as ChecklistOptions

    sb.append(f'<div class="checklist">')
    sb.append(children)
    sb.append('</div>')
```

Or for directives needing custom parse logic:

```python
@directive("gallery", options=GalleryOptions, preserves_raw_content=True)
class GalleryDirective:
    def render(self, node, children, sb):
        images = self._parse_images(node.raw_content)
        # ...
```

#### Decorator Implementation

```python
def directive(
    *names: str,
    options: type[DirectiveOptions] = DirectiveOptions,
    contract: DirectiveContract | None = None,
    preserves_raw_content: bool = False,
    token_type: str | None = None,
):
    """Decorator to create directive handlers with minimal boilerplate."""

    def decorator(func_or_class):
        effective_token_type = token_type or names[0]

        if isinstance(func_or_class, type):
            # Class decorator — add attributes
            func_or_class.names = names
            func_or_class.token_type = effective_token_type
            func_or_class.contract = contract
            func_or_class.options_class = options
            func_or_class.preserves_raw_content = preserves_raw_content
            return func_or_class
        else:
            # Function decorator — wrap in class
            render_func = func_or_class

            class GeneratedDirective:
                names = names
                token_type = effective_token_type
                contract = contract
                options_class = options
                preserves_raw_content = preserves_raw_content

                def parse(self, name, title, opts, content, children, location):
                    return Directive(
                        location=location,
                        name=name,
                        title=title,
                        options=opts,
                        children=tuple(children),
                        raw_content=content if preserves_raw_content else None,
                    )

                def render(self, node, rendered_children, sb):
                    return render_func(node, rendered_children, sb)

            return GeneratedDirective

    return decorator
```

---

## Implementation Plan

### Phase 1: Typed Options (Week 1)

| Task | Effort | Risk |
|------|--------|------|
| Add `typed_options` field to `Directive` node | 1h | Low |
| Update parser to populate `typed_options` | 2h | Low |
| Update renderer to use `typed_options` | 2h | Low |
| Migrate existing directives | 4h | Low |
| Add deprecation warning for `options` | 1h | Low |

### Phase 2: Raw Content Flag (Week 1)

| Task | Effort | Risk |
|------|--------|------|
| Add `preserves_raw_content` to protocol | 0.5h | Low |
| Update parser to check flag | 1h | Low |
| Update existing directives | 1h | Low |
| Add tests | 1h | Low |

### Phase 3: Contract Validation (Week 2)

| Task | Effort | Risk |
|------|--------|------|
| Add validation logic to parser | 3h | Medium |
| Add `strict_contracts` configuration | 1h | Low |
| Extend `DirectiveContract` dataclass | 1h | Low |
| Add tests for violation detection | 2h | Low |
| Update documentation | 1h | Low |

### Phase 4: Decorator API (Week 2)

| Task | Effort | Risk |
|------|--------|------|
| Implement `@directive` decorator | 3h | Low |
| Add tests for decorator patterns | 2h | Low |
| Document decorator usage | 1h | Low |
| (Optional) Migrate simple directives | 2h | Low |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing directive handlers | Low | High | Backward-compatible changes, deprecation period |
| Performance regression from typed options | Low | Low | Benchmark before/after |
| Contract validation too noisy | Medium | Low | Default to warnings, opt-in strict mode |
| Decorator magic obscures behavior | Medium | Medium | Keep class-based API as primary, decorator as convenience |

---

## Alternatives Considered

### Alternative A: Keep Current API

**Pros**: No migration, no risk
**Cons**: Papercuts persist, developer friction continues
**Decision**: Rejected — ergonomics impact is real and fixable

### Alternative B: Full API Redesign

**Pros**: Clean slate, optimal ergonomics
**Cons**: Major breaking change, migration burden
**Decision**: Rejected — incremental improvements achieve 80% of benefit with 20% of risk

### Alternative C: Code Generation

**Pros**: Maximum boilerplate reduction
**Cons**: Magic, harder to debug, tooling overhead
**Decision**: Rejected — decorator provides similar benefit without codegen complexity

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Lines per simple directive | ~50 | ~20 |
| Type errors caught at dev time | ~60% | ~95% |
| Contract violations caught at build | 0% | 100% |
| IDE autocomplete coverage in `render()` | ~30% | ~95% |

---

## Open Questions

1. **Should `typed_options` replace `options` entirely, or coexist?**
   - Proposal: Coexist during deprecation period, then replace

2. **Should contract validation be on by default?**
   - Proposal: Warnings by default, errors opt-in via `strict_contracts=True`

3. **Should the decorator support async render methods?**
   - Proposal: Not in v1, add if needed later

4. **Should we provide base classes for common patterns?**
   - Example: `ContainerDirective`, `AdmonitionDirective` base classes
   - Proposal: Consider for v2 after gathering usage patterns

---

## References

- [rfc-patitas-bengal-directive-migration](./rfc-patitas-bengal-directive-migration.md) — Parent RFC
- [Flask Route Decorators](https://flask.palletsprojects.com/en/2.3.x/quickstart/#routing) — Inspiration for `@directive` ergonomics
- [Pydantic Field Validators](https://docs.pydantic.dev/latest/concepts/validators/) — Typed options pattern inspiration
