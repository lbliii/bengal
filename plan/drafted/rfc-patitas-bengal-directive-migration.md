# RFC: Bengal Directive Migration to Patitas

| Field        | Value                                      |
|--------------|-------------------------------------------|
| **Status**   | Draft                                      |
| **Author**   | Bengal Team                                |
| **Created**  | 2025-12-28                                 |
| **RFC**      | rfc-patitas-bengal-directive-migration     |
| **Depends**  | rfc-patitas-markdown-parser (Phase 2)      |

---

## Summary

Port all Bengal directives from mistune-based `BengalDirective` implementations to native Patitas `DirectiveHandler` implementations. This enables:

- **Thread-safe parsing** for Python 3.14t free-threading
- **Typed AST nodes** for better tooling and analysis
- **Removal of mistune dependency** for directive parsing
- **Identical HTML output** preserving all existing styling

---

## Motivation

Bengal currently has 60+ directives built on mistune's `DirectivePlugin` base class. While Phase 2 of Patitas created the `DirectiveHandler` protocol and example implementations, Bengal's production directives remain on mistune.

**Why not use adapters/shims?**

1. **Technical debt**: Adapters add complexity without removing mistune dependency
2. **Performance**: Two parsing passes (patitas → adapter → mistune shim)
3. **Maintenance burden**: Must maintain compatibility with two systems
4. **Free-threading**: mistune isn't designed for 3.14t; adapters inherit those limitations

**Native migration benefits:**

1. **Clean architecture**: Single parsing path with typed AST
2. **Performance**: Direct patitas parsing, no translation layer
3. **Thread-safe by design**: Immutable AST nodes, no shared state
4. **Full control**: Optimize directive implementations for patitas's model

---

## Current Architecture

### Bengal Directive (mistune-based)

```python
class DropdownDirective(BengalDirective):
    NAMES: ClassVar[list[str]] = ["dropdown", "details"]
    TOKEN_TYPE: ClassVar[str] = "dropdown"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DropdownOptions
    CONTRACT: ClassVar[DirectiveContract | None] = None

    def parse_directive(
        self, title: str, options: DropdownOptions,
        content: str, children: list[dict], state: Any
    ) -> DirectiveToken:
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={"title": title, "open": options.open, ...},
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        title = attrs.get("title", "Details")
        return f'<details class="dropdown">...'
```

### Patitas Directive (target)

```python
class DropdownDirective:
    names: ClassVar[tuple[str, ...]] = ("dropdown", "details")
    token_type: ClassVar[str] = "dropdown"
    options_class: ClassVar[type[DirectiveOptions]] = DropdownOptions
    contract: ClassVar[DirectiveContract | None] = None

    def parse(
        self, name: str, title: str | None, options: DirectiveOptions,
        content: str, children: Sequence[Block], location: SourceLocation
    ) -> Directive:
        return Directive(
            name=name,
            title=title or "Details",
            options=frozenset(options.as_items()),
            children=tuple(children),
            location=location,
        )

    def render(
        self, node: Directive, rendered_children: str, sb: StringBuilder
    ) -> None:
        sb.append(f'<details class="dropdown">...')
```

**Key differences:**

| Aspect | Bengal (mistune) | Patitas |
|--------|------------------|---------|
| State | Mutable `state` object | Immutable `SourceLocation` |
| Children | `list[dict]` tokens | `tuple[Block, ...]` AST nodes |
| Render output | Return `str` | Append to `StringBuilder` |
| Attributes | `dict[str, Any]` | `frozenset[tuple[str, str]]` |

---

## Migration Strategy

### Principle: Mechanical Translation

Most Bengal directives can be migrated via **mechanical translation**:

1. Change class signature: `BengalDirective` → implement `DirectiveHandler` protocol
2. Rename `NAMES` → `names` (tuple instead of list)
3. Rename `parse_directive` → `parse` with updated signature
4. Change `render` to use `StringBuilder` instead of returning string
5. Replace `attrs.get("key")` with typed options access
6. Preserve HTML generation logic exactly (identical output)

### Golden File Testing

To guarantee identical HTML output:

```python
# tests/migration/test_directive_parity.py

DIRECTIVE_TEST_CASES = [
    ("dropdown", ":::{dropdown} Title\nContent\n:::"),
    ("dropdown_open", ":::{dropdown} Title\n:open:\nContent\n:::"),
    ("tabs", "::::{tab-set}\n:::{tab-item} Tab 1\nContent\n:::\n::::"),
    # ... 200+ test cases covering all directives and options
]

@pytest.mark.parametrize("name,source", DIRECTIVE_TEST_CASES)
def test_html_parity(name: str, source: str):
    """Verify Patitas produces identical HTML to Bengal/mistune."""
    bengal_html = render_with_bengal_mistune(source)
    patitas_html = render_with_patitas(source)
    assert patitas_html == bengal_html, f"Mismatch in {name}"
```

---

## Directive Inventory

### Phase A: Core Directives (Week 1-2)

High-frequency directives used on most pages:

| Directive | Complexity | Notes |
|-----------|------------|-------|
| `note`, `tip`, `warning`, etc. | Low | 10 types, single implementation |
| `dropdown` / `details` | Low | Simple HTML5 `<details>` |
| `tab-set` / `tab-item` | Medium | Contract validation, 2 render modes |
| `container` / `div` | Low | Pass-through wrapper |
| `steps` / `step` | Medium | Numbered steps with contracts |

**Exit Criteria**: 90% of docs pages render identically

### Phase B: Content Directives (Week 3-4)

Rich content and layout directives:

| Directive | Complexity | Notes |
|-----------|------------|-------|
| `cards` / `card` / `grid` | High | Complex layout, child-cards |
| `code-tabs` | Medium | Language-sync, code highlighting |
| `list-table` | Medium | Table from list syntax |
| `data-table` | Medium | Table from YAML/JSON |
| `figure` / `gallery` | Medium | Image handling |
| `checklist` | Low | Interactive checkboxes |

**Exit Criteria**: All layout directives migrated

### Phase C: Specialized Directives (Week 5-6)

Domain-specific and embed directives:

| Directive | Complexity | Notes |
|-----------|------------|-------|
| `include` / `literalinclude` | High | File system access, caching |
| `youtube` / `vimeo` / `video` | Low | Embed iframes |
| `gist` / `codepen` / etc. | Low | Developer tool embeds |
| `glossary` | Medium | Cross-reference system |
| `marimo` | Medium | Notebook integration |
| `since` / `deprecated` / etc. | Low | Version badges |

**Exit Criteria**: Full directive library migrated

### Phase D: Integration & Deprecation (Week 7-8)

1. Update Bengal's parser factory to use Patitas
2. Run full test suite with Patitas backend
3. Deprecation warnings for direct mistune usage
4. Documentation updates

**Exit Criteria**: Bengal test suite passes, deprecation complete

---

## Technical Design

### Shared Utilities

Create `patitas/directives/utils.py` with Bengal's rendering helpers:

```python
# Migrated from bengal.directives.utils

def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    ...

def build_class_string(*classes: str) -> str:
    """Build CSS class string from multiple sources."""
    ...

def bool_attr(name: str, value: bool) -> str:
    """Generate HTML boolean attribute."""
    return f" {name}" if value else ""

def render_svg_icon(name: str, size: int = 20, css_class: str = "") -> str:
    """Render inline SVG icon."""
    ...
```

### Icon System

Icons are currently in `bengal/directives/_icons.py`. Options:

1. **Copy to Patitas**: Duplicate icon SVGs (increases package size)
2. **Import from Bengal**: `from bengal.directives._icons import ...`
3. **External package**: Extract to `bengal-icons` package

**Recommendation**: Option 2 initially (Bengal already depends on itself), extract later if Patitas becomes standalone.

### Options Migration

Bengal's `DirectiveOptions` and Patitas's `DirectiveOptions` have nearly identical patterns:

```python
# Bengal
@dataclass
class DropdownOptions(DirectiveOptions):
    open: bool = False
    icon: str = ""
    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}

# Patitas (identical)
@dataclass(frozen=True, slots=True)
class DropdownOptions(DirectiveOptions):
    open: bool = False
    icon: str = ""
    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}
```

**Migration**: Add `frozen=True, slots=True` decorators for immutability.

### Contract Migration

Contracts are already nearly identical:

```python
# Bengal
TAB_ITEM_CONTRACT = DirectiveContract(requires_parent=("tab_set",))

# Patitas (identical)
TAB_ITEM_CONTRACT = DirectiveContract(requires_parent=("tab_set",))
```

**Migration**: Direct copy, update imports.

---

## File Structure

```
bengal/rendering/parsers/patitas/directives/
├── __init__.py
├── protocol.py          # DirectiveHandler protocol
├── options.py           # DirectiveOptions base + common options
├── contracts.py         # DirectiveContract + predefined contracts
├── registry.py          # DirectiveRegistry
├── utils.py             # Rendering utilities (from bengal.directives.utils)
│
├── builtins/            # Patitas-native example directives
│   ├── __init__.py
│   ├── admonition.py    # Example implementation
│   ├── dropdown.py
│   └── tabs.py
│
└── bengal/              # Full Bengal directive library (migrated)
    ├── __init__.py
    ├── admonitions.py   # note, tip, warning, etc.
    ├── dropdown.py
    ├── tabs.py
    ├── cards/
    │   ├── __init__.py
    │   ├── card.py
    │   ├── cards_grid.py
    │   └── child_cards.py
    ├── steps.py
    ├── code_tabs.py
    ├── tables.py        # list-table, data-table
    ├── includes.py      # include, literalinclude
    ├── embeds.py        # youtube, gist, etc.
    ├── versioning.py    # since, deprecated, etc.
    └── ...
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| HTML output differences | Medium | High | Golden file tests for every directive/option combo |
| Missing edge cases | Medium | Medium | Port Bengal's directive tests alongside code |
| Icon system coupling | Low | Low | Use Bengal import initially |
| Performance regression | Low | Medium | Benchmark key directives |
| Free-threading issues | Low | High | TSan in CI, stress tests |

---

## Success Criteria

1. **Parity**: 100% of Bengal's directive test cases pass with Patitas
2. **Golden files**: Zero HTML diff between mistune and Patitas rendering
3. **Performance**: ≤5% regression on directive-heavy pages
4. **Thread-safe**: Zero TSan errors under concurrent parsing
5. **Clean break**: No runtime dependency on mistune for directive parsing

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1-2 | Phase A | Core directives (admonitions, dropdown, tabs, steps) |
| 3-4 | Phase B | Content directives (cards, tables, code-tabs, gallery) |
| 5-6 | Phase C | Specialized directives (includes, embeds, glossary) |
| 7-8 | Phase D | Integration, deprecation, documentation |

**Total: 8 weeks**

---

## Open Questions

1. **Standalone Patitas?** Should Patitas be extractable as a standalone package, or is Bengal-coupling acceptable?

2. **Icon handling**: Copy SVGs to Patitas, import from Bengal, or extract to separate package?

3. **Rosettes integration**: Should syntax highlighting be part of this RFC or separate?

4. **Role migration**: Bengal has inline roles too (e.g., `{ref}`, `{doc}`). Include in this RFC or separate?

---

## Related Documents

- [RFC: Patitas Markdown Parser](rfc-patitas-markdown-parser.md) - Core parser design
- [bengal/directives/base.py](../../bengal/directives/base.py) - Current BengalDirective base
- [bengal/directives/registry.py](../../bengal/directives/registry.py) - Current directive registry

---

## Appendix: Directive Migration Checklist Template

For each directive migration:

- [ ] Create Patitas `DirectiveHandler` implementation
- [ ] Port `Options` dataclass (add `frozen=True, slots=True`)
- [ ] Port `Contract` if applicable
- [ ] Port `render()` logic to use `StringBuilder`
- [ ] Add to `DirectiveRegistry`
- [ ] Port unit tests
- [ ] Add golden file test cases
- [ ] Verify HTML output matches exactly
- [ ] Update imports in Bengal
- [ ] Mark old implementation as deprecated
