# RFC: Patitas Directive Ergonomics Improvements

| Field        | Value                                      |
|--------------|-------------------------------------------|
| **Status**   | Draft (Ready for Review)                   |
| **Author**   | Bengal Team                                |
| **Created**  | 2025-12-28                                 |
| **Updated**  | 2025-12-28                                 |
| **RFC**      | rfc-patitas-directive-ergonomics           |
| **Depends**  | rfc-patitas-bengal-directive-migration     |
| **Blocks**   | —                                          |
| **LOC**      | ~600 (implementation estimate)             |

---

## Executive Summary

**Problem**: After implementing 25+ directives for Patitas, several API friction points emerged that add boilerplate and reduce developer experience without benefiting thread-safety or correctness. Directive authors are forced into manual serialization/deserialization cycles, lose IDE type safety, and have no automated structural validation for nested components.

**Solution**: Four targeted improvements to the directive authoring experience:

| Improvement | Impact | Risk | Dependency |
|-------------|--------|------|------------|
| Generic typed options (`Directive[TOptions]`) | High — eliminates serialize/deserialize | Low | None |
| `preserves_raw_content` flag | Medium — discoverable pattern | Low | None |
| Auto-contract validation | Medium — catches errors early | Medium | Parser changes |
| `@directive` decorator | Medium — reduces boilerplate | Low | Solution 1 |

**Goal**: Make directive authoring feel as ergonomic as Flask route handlers or Pydantic models while maintaining Bengal's strict thread-safety and performance guarantees.

---

## Design Principles

The improvements in this RFC are guided by three core principles:

1. **Type-First Architecture**: Leverage Python's modern typing system (Generics, Protocols, Dataclasses) to move errors from runtime to dev-time.
2. **Zero-Copy Options**: Eliminate the overhead and error surface of string-based serialization by passing immutable options objects directly from the parser to the renderer.
3. **Discoverable Constraints**: Move hidden requirements (like raw content needs or nesting rules) into explicit class metadata where they are visible to both the system and the developer.

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

## Current Architecture Reference

Before proposing solutions, here's the current directive system architecture:

| Component | Location | Purpose |
|-----------|----------|---------|
| `Directive` node | `nodes.py:348-358` | AST node with `options: frozenset[tuple[str, str]]` |
| `DirectiveHandler` protocol | `protocol.py:38-134` | Interface for directive implementations |
| `DirectiveContract` | `contracts.py:30-87` | Validation rules (defined but not enforced) |
| `DirectiveOptions` | `options.py` | Base class for typed options |
| `Parser._parse_directive()` | `parser.py:594-649` | Parses directive blocks into AST |

**Key insight**: Contract validation methods exist (`validate_parent`, `validate_children`) but are never called by the parser. The parser builds `Directive` nodes without checking contracts.

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
from typing import Generic, TypeVar, Any
from dataclasses import dataclass

TOptions = TypeVar("TOptions", bound=DirectiveOptions)

@dataclass(frozen=True, slots=True)
class Directive(Node, Generic[TOptions]):
    name: str
    title: str | None
    options: TOptions  # Typed options object — IDE knows the exact type!
    children: tuple[Block, ...]
    raw_content: str | None = None
```

This enables full type inference:

```python
def render(self, node: Directive[GalleryOptions], ...) -> None:
    node.options.columns  # IDE: int
    node.options.lightbox  # IDE: bool
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

1. **Phase 1A**: Add `Directive[TOptions]` generic support.
2. **Phase 1B**: Update `Renderer._render_directive` to use `node.options` directly.
3. **Phase 1C**: Mandatory migration of all 25+ built-in directives to use `node.options` directly. This is a "clean break" migration to avoid technical debt.

#### Renderer Logic

```python
# In renderer.py or patitas/renderers/html.py
def _render_directive(self, node: Directive, sb: StringBuilder) -> None:
    handler = self._registry.get(node.name)

    # Simple, direct dispatch. All handlers MUST implement the new signature.
    handler.render(node, rendered_children, sb)
```

The handler's `render()` method accesses options uniformly via `node.typed_options` (new) or `node.options` (legacy). Migrated handlers get full type safety; unmigrated handlers continue working.

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

#### Error Definitions

A new exception type will be added to `bengal/rendering/parsers/patitas/errors.py`:

```python
class DirectiveContractError(BengalError):
    """Raised when a directive nesting contract is violated in strict mode."""
    def __init__(self, message: str, location: SourceLocation | None = None):
        super().__init__(message, location=location)
```

#### Validation Points

```
Parse Time (build):     Check parent/child constraints
                        Emit warning + continue (soft fail)

Strict Mode (opt-in):   Emit error + halt (hard fail)
```

#### Implementation

The `strict_contracts` flag will be added to the global `BengalConfig` in `bengal/config/types.py` under the `ContentConfig` section to allow project-wide enforcement.

Integration with existing `Parser._parse_directive()` method in `parser.py`:

```python
class Parser:
    def __init__(self, source: str, *, strict_contracts: bool = False):
        self.strict_contracts = strict_contracts
        self._directive_stack: list[str] = []  # NEW: Track nesting

    def _parse_directive(self) -> Directive:
        """Parse directive block (:::{name} ... :::)."""
        # ... existing token parsing ...

        # Get handler from registry
        handler = self._directive_registry.get(name)
        if handler is None:
            return self._parse_unknown_directive(name, ...)

        # NEW: Validate parent contract
        parent_name = self._directive_stack[-1] if self._directive_stack else None
        if handler.contract:
            violation = handler.contract.validate_parent(name, parent_name)
            if violation:
                if self.strict_contracts:
                    raise DirectiveContractError(violation.message)
                else:
                    logger.warning("directive_contract_violation",
                                   directive=name, parent=parent_name,
                                   message=violation.message)

        # NEW: Push onto stack before parsing children
        self._directive_stack.append(name)
        try:
            children = self._parse_directive_children()
        finally:
            self._directive_stack.pop()

        # NEW: Validate children contract
        if handler.contract:
            child_directives = [c for c in children if isinstance(c, Directive)]
            violations = handler.contract.validate_children(name, child_directives)
            for v in violations:
                if self.strict_contracts:
                    raise DirectiveContractError(v.message)
                else:
                    logger.warning("directive_contract_violation", message=v.message)

        # ... rest of existing logic ...
```

**Note**: This integrates with the existing `Parser` class in `parser.py`, not a separate `DirectiveParser` class.

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
from typing import TypeVar

TOptions = TypeVar("TOptions", bound=DirectiveOptions)

@directive("checklist", options=ChecklistOptions)
def render_checklist(node: Directive[ChecklistOptions], children: str, sb: StringBuilder) -> None:
    opts = node.options  # IDE knows this is ChecklistOptions

    sb.append(f'<div class="checklist" data-style="{opts.style}">')
    sb.append(children)
    sb.append('</div>')
```

Or for directives needing custom parse logic:

```python
@directive("gallery", options=GalleryOptions, preserves_raw_content=True)
class GalleryDirective:
    def render(self, node: Directive[GalleryOptions], children: str, sb: StringBuilder) -> None:
        images = self._parse_images(node.raw_content)
        columns = node.options.columns  # IDE autocomplete works!
        # ...
```

**Note**: The `Directive[TOptions]` generic requires Solution 1 (typed options) to be implemented first.

#### Decorator Implementation

```python
from typing import Callable, TypeVar, overload

TOptions = TypeVar("TOptions", bound=DirectiveOptions)
TClass = TypeVar("TClass", bound=type)


@overload
def directive(
    *names: str,
    options: type[TOptions] = ...,
    contract: DirectiveContract | None = ...,
    preserves_raw_content: bool = ...,
    token_type: str | None = ...,
) -> Callable[[Callable[[Directive[TOptions], str, StringBuilder], None]], type]: ...


@overload
def directive(
    *names: str,
    options: type[TOptions] = ...,
    contract: DirectiveContract | None = ...,
    preserves_raw_content: bool = ...,
    token_type: str | None = ...,
) -> Callable[[TClass], TClass]: ...


def directive(
    *names: str,
    options: type[DirectiveOptions] = DirectiveOptions,
    contract: DirectiveContract | None = None,
    preserves_raw_content: bool = False,
    token_type: str | None = None,
):
    """Decorator to create directive handlers with minimal boilerplate.

    Works with both functions (simple directives) and classes (complex directives).

    Example (function):
        @directive("note", options=NoteOptions)
        def render_note(node: Directive[NoteOptions], children: str, sb: StringBuilder) -> None:
            sb.append(f'<div class="note">{children}</div>')

    Example (class):
        @directive("gallery", options=GalleryOptions, preserves_raw_content=True)
        class GalleryDirective:
            def render(self, node: Directive[GalleryOptions], children: str, sb: StringBuilder) -> None:
                ...
    """

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

            GeneratedDirective.__name__ = f"{render_func.__name__}_directive"
            GeneratedDirective.__qualname__ = f"{render_func.__qualname__}_directive"
            return GeneratedDirective

    return decorator
```

---

## Implementation Plan

### Phase 1: Typed Options & Mandatory Migration (Week 1)

| Task | Effort | Risk |
|------|--------|------|
| Make `Directive` generic: `Directive[TOptions]` | 1h | Low |
| Change `options` field type from `frozenset` to `TOptions` | 1h | Low |
| Update parser to pass typed options directly | 2h | Low |
| Update renderer to use typed options directly | 1h | Low |
| **Migrate all 25+ existing directives (remove serialize/deserialize)** | 6h | Medium |
| Verify all parity tests pass with new architecture | 2h | Low |

### Phase 2: Raw Content Flag (Week 1)

| Task | Effort | Risk |
|------|--------|------|
| Add `preserves_raw_content` to protocol | 0.5h | Low |
| Update parser to check flag | 1h | Low |
| Update existing directives | 1h | Low |
| Add tests | 1h | Low |

### Phase 3: Contract Validation & Configuration (Week 2)

| Task | Effort | Risk |
|------|--------|------|
| **Define `DirectiveContractError` exception** | 0.5h | Low |
| **Add `strict_contracts` to `BengalConfig` / `ContentConfig`** | 1h | Low |
| Add `_directive_stack` to `Parser` for parent tracking | 1h | Low |
| Integrate `validate_parent()` calls in `_parse_directive()` | 2h | Medium |
| Integrate `validate_children()` calls after child parsing | 1h | Medium |
| Extend `DirectiveContract` with `severity` and `message` fields | 1h | Low |
| Add tests for violation detection (parent, children, mixed) | 2h | Low |
| Update documentation | 1h | Low |

**Note**: This phase modifies `Parser._parse_directive()` in `parser.py`, not a separate class.

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
| Breaking existing directive handlers | High | High | One-time mandatory migration of all built-in handlers; verify with 100% test coverage |
| Performance regression from typed options | Low | Low | Benchmark before/after; frozen dataclasses are already optimized |
| Contract validation too noisy | Medium | Low | Default to warnings, opt-in strict mode via `strict_contracts=True` |
| Decorator magic obscures behavior | Medium | Medium | Keep class-based API as primary, decorator as convenience |
| Parser directive stack adds complexity | Low | Low | Stack is simple list; push/pop in try/finally |
| Generic `Directive[TOptions]` breaks type hints | Low | Medium | Use `Directive[DirectiveOptions]` as default; explicit types for handlers |

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
   - Decision: **Replace entirely.** We are opting for a "clean break" migration to minimize technical debt and maximize performance/type safety from day one.
   - All built-in directives will be migrated as part of this RFC implementation.

2. **Should contract validation be on by default?**
   - Proposal: Warnings by default, errors opt-in via `strict_contracts=True`
   - Rationale: Avoids breaking existing content; warnings surface issues without blocking builds

3. **Should the decorator support async render methods?**
   - Proposal: Not in v1, add if needed later
   - Rationale: No current async rendering use cases; easy to add via `@directive_async` variant

4. **Should we provide base classes for common patterns?**
   - Example: `ContainerDirective`, `AdmonitionDirective` base classes
   - Proposal: Consider for v2 after gathering usage patterns from 25+ migrated directives

5. **Should `Directive` become generic (`Directive[TOptions]`) for full type safety?**
   - Proposal: Yes, as part of Phase 1
   - This enables `node.options` to be typed correctly in both handlers and decorators
   - Implementation: `class Directive(Node, Generic[TOptions]): options: TOptions`

---

## Appendix: Before/After Comparison

### Full Directive: Before (Current)

```python
@dataclass(frozen=True, slots=True)
class GalleryOptions(DirectiveOptions):
    columns: int = 3
    lightbox: bool = True
    gap: str = "1rem"


class GalleryDirective:
    names: ClassVar[tuple[str, ...]] = ("gallery",)
    token_type: ClassVar[str] = "gallery"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[GalleryOptions]] = GalleryOptions

    def parse(self, name, title, options, content, children, location):
        # Manual serialization — 8 lines of boilerplate
        opts_items = [
            ("columns", str(options.columns)),
            ("lightbox", str(options.lightbox)),
            ("gap", options.gap),
        ]
        return Directive(
            location=location,
            name=name,
            title=title,
            options=frozenset(opts_items),
            children=tuple(children),
            raw_content=content,  # Easy to forget!
        )

    def render(self, node, rendered_children, sb):
        opts = dict(node.options)

        # Manual deserialization — error-prone string parsing
        try:
            columns = int(opts.get("columns", "3"))
        except ValueError:
            columns = 3
        lightbox = opts.get("lightbox", "True") != "False"  # Ugh!
        gap = opts.get("gap", "1rem")

        # ... actual rendering logic ...
```

**Lines**: ~45  |  **Type safety**: ~30%  |  **IDE autocomplete**: Minimal

### Full Directive: After (Proposed)

```python
@dataclass(frozen=True, slots=True)
class GalleryOptions(DirectiveOptions):
    columns: int = 3
    lightbox: bool = True
    gap: str = "1rem"


@directive("gallery", options=GalleryOptions, preserves_raw_content=True)
class GalleryDirective:
    def render(self, node: Directive[GalleryOptions], children: str, sb: StringBuilder) -> None:
        # Direct typed access — IDE knows exact types!
        columns = node.options.columns   # int
        lightbox = node.options.lightbox  # bool
        gap = node.options.gap            # str

        # ... actual rendering logic ...
```

**Lines**: ~20  |  **Type safety**: ~95%  |  **IDE autocomplete**: Full

---

## References

- [rfc-patitas-bengal-directive-migration](./rfc-patitas-bengal-directive-migration.md) — Parent RFC
- [Flask Route Decorators](https://flask.palletsprojects.com/en/2.3.x/quickstart/#routing) — Inspiration for `@directive` ergonomics
- [Pydantic Field Validators](https://docs.pydantic.dev/latest/concepts/validators/) — Typed options pattern inspiration
- [Python Generic Classes (PEP 484)](https://peps.python.org/pep-0484/#generics) — `Directive[TOptions]` pattern
