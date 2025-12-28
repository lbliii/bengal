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

Bengal currently has 55+ directive names (31 directive modules) built on mistune's `DirectivePlugin` base class. While Phase 2 of Patitas created the `DirectiveHandler` protocol and example implementations, Bengal's production directives remain on mistune.

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
| Class attrs | `NAMES` (list, SCREAMING_CASE) | `names` (tuple, snake_case) |
| Immutability | Mutable dataclasses | `frozen=True, slots=True` |

---

## Migration Strategy

### Principle: Mechanical Translation

Most Bengal directives can be migrated via **mechanical translation**:

1. Change class signature: `BengalDirective` → implement `DirectiveHandler` protocol
2. Rename `NAMES` → `names` (tuple instead of list)
3. Rename `parse_directive` → `parse` with updated signature
4. Change `render` to use `StringBuilder` instead of returning string
5. Replace `attrs.get("key")` with typed options access
6. Add `frozen=True, slots=True` to options dataclasses
7. Preserve HTML generation logic exactly (identical output)

### Complexity Scoring

| Score | Criteria | Examples |
|-------|----------|----------|
| **Low** | Single HTML element, no children, simple options | `badge`, `rubric`, `video` |
| **Medium** | Nested structure, contract validation, options logic | `dropdown`, `tabs`, `steps` |
| **High** | File I/O, cross-references, complex state | `include`, `glossary`, `cards` |

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

## Complete Directive Inventory

### Admonitions (10 directive names, 1 module)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `note` | — | Low | Multi-name registration pattern |
| `tip` | — | Low | |
| `warning` | — | Low | |
| `danger` | — | Low | |
| `error` | — | Low | |
| `info` | — | Low | |
| `example` | — | Low | |
| `success` | — | Low | |
| `caution` | — | Low | Maps to `warning` CSS |
| `seealso` | — | Low | |

### Layout & Structure (12 directive names)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `dropdown` | `details` | Low | HTML5 `<details>` element |
| `container` | `div` | Low | Pass-through wrapper |
| `tab-set` | `tabs` | Medium | Contract: requires `tab-item` children |
| `tab-item` | `tab` | Medium | Contract: requires `tab-set` parent |
| `steps` | — | Medium | Contract: requires `step` children |
| `step` | — | Medium | Contract: requires `steps` parent |
| `cards` | — | High | Grid layout, contract validation |
| `card` | — | High | Contract: requires `cards` parent |
| `child-cards` | — | High | Auto-generates cards from children |

### Content & Tables (6 directive names)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `code-tabs` | `code_tabs` | Medium | Language sync, syntax highlighting |
| `list-table` | — | Medium | Table from list syntax |
| `data-table` | — | Medium | Table from YAML/JSON |
| `checklist` | — | Low | Interactive checkboxes |
| `gallery` | — | Medium | Image grid layout |
| `figure` | — | Medium | Image with caption |

### Embeds - Video (5 directive names)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `youtube` | — | Low | Embed iframe |
| `vimeo` | — | Low | Embed iframe |
| `video` | — | Low | HTML5 `<video>` |
| `tiktok` | — | Low | Embed iframe |
| `audio` | — | Low | HTML5 `<audio>` |

### Embeds - Developer Tools (6 directive names)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `gist` | — | Low | GitHub Gist embed |
| `codepen` | — | Low | CodePen embed |
| `codesandbox` | — | Low | CodeSandbox embed |
| `stackblitz` | — | Low | StackBlitz embed |
| `spotify` | — | Low | Spotify embed |
| `soundcloud` | — | Low | SoundCloud embed |

### File Inclusion (3 directive names)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `include` | — | High | File system access, caching |
| `literalinclude` | — | High | Code file inclusion with options |
| `marimo` | — | Medium | Notebook integration |

### Navigation (4 directive names)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `breadcrumbs` | — | Medium | Site navigation context |
| `siblings` | — | Medium | Adjacent page links |
| `prev-next` | — | Medium | Sequential navigation |
| `related` | — | Medium | Related content links |

### Versioning (6 directive names)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `since` | `versionadded` | Low | Version badge |
| `deprecated` | `versionremoved` | Low | Deprecation notice |
| `changed` | `versionchanged` | Low | Change notice |

### Miscellaneous (9 directive names)

| Directive | Aliases | Complexity | Notes |
|-----------|---------|------------|-------|
| `badge` | `bdg` | Low | Inline badge |
| `button` | — | Low | Styled button/link |
| `icon` | `svg-icon` | Low | Inline SVG icon |
| `rubric` | — | Low | Section heading |
| `target` | `anchor` | Low | Link target |
| `example-label` | — | Low | Example annotation |
| `glossary` | — | Medium | Cross-reference system (⚠️ requires roles) |
| `build` | — | Low | Build-time directive |
| `asciinema` | — | Low | Terminal recording embed |

**Total: 55+ directive names across 31 modules**

---

## Phase Plan

### Phase 0: Pre-work (Week 0)

Validate existing Patitas builtins match Bengal output before proceeding.

| Task | Status | Notes |
|------|--------|-------|
| Audit `patitas/builtins/admonition.py` | Pending | Compare HTML output |
| Audit `patitas/builtins/dropdown.py` | Pending | Compare HTML output |
| Audit `patitas/builtins/tabs.py` | Pending | Compare HTML output |
| Create golden file test harness | Pending | Framework for parity tests |
| Extract icon utilities to shared module | Pending | Unblock icon-dependent directives |

**Exit Criteria**: 3 existing builtins produce identical HTML to Bengal

### Phase A: Core Directives (Week 1-2)

High-frequency directives used on most pages:

| Directive | Complexity | Patitas Status | Icon Deps |
|-----------|------------|----------------|-----------|
| Admonitions (10) | Low | ✅ Exists | Yes |
| `dropdown` / `details` | Low | ✅ Exists | Yes |
| `tab-set` / `tab-item` | Medium | ✅ Exists | No |
| `container` / `div` | Low | Pending | No |
| `steps` / `step` | Medium | Pending | No |

**Deliverables**:
- Validate 3 existing builtins
- Migrate `container`, `steps`
- Extract icon utilities to `patitas/directives/utils/icons.py`

**Exit Criteria**: 90% of docs pages render identically

### Phase B: Content Directives (Week 3-4)

Rich content and layout directives:

| Directive | Complexity | Icon Deps | Notes |
|-----------|------------|-----------|-------|
| `cards` / `card` / `child-cards` | High | Yes | Complex layout |
| `code-tabs` | Medium | No | Language-sync |
| `list-table` | Medium | No | |
| `data-table` | Medium | No | |
| `figure` / `gallery` / `audio` | Medium | No | |
| `checklist` | Low | No | |

**Exit Criteria**: All layout directives migrated

### Phase C: Specialized Directives (Week 5-6)

Domain-specific and embed directives:

| Directive | Complexity | Dependencies | Notes |
|-----------|------------|--------------|-------|
| `include` / `literalinclude` | High | File system | Caching |
| Video embeds (5) | Low | None | iframes |
| Developer embeds (6) | Low | None | iframes |
| Navigation (4) | Medium | Site context | |
| Versioning (6) | Low | None | Badges |
| `glossary` | Medium | **Role system** | ⚠️ Blocked without roles |
| `marimo` | Medium | None | Notebook |

**Note**: `glossary` requires role system (`{term}` role). Either:
1. Include role migration in this RFC
2. Defer `glossary` to Phase D
3. Create separate RFC for roles

**Exit Criteria**: Full directive library migrated (except role-dependent)

### Phase D: Integration & Deprecation (Week 7-8)

1. Update Bengal's parser factory to use Patitas
2. Run full test suite with Patitas backend
3. Deprecation warnings for direct mistune usage
4. Documentation updates
5. Role system migration (if included in this RFC)

**Exit Criteria**: Bengal test suite passes, deprecation complete

---

## Technical Design

### Icon System Migration

Icons are used by 7 directive modules. Current architecture:

```
bengal/directives/_icons.py
├── ICONS: dict[str, str]     # SVG data
├── ICON_MAP: dict[str, str]  # Semantic aliases
├── render_svg_icon()         # Render utility
└── warn_missing_icon()       # Warning helper
```

**Migration approach** (Phase A):

1. Create `patitas/directives/utils/icons.py`
2. Copy icon utilities (not SVG data)
3. Import SVG data from Bengal: `from bengal.directives._icons import ICONS`
4. Future: Extract to `bengal-icons` package if Patitas becomes standalone

```python
# patitas/directives/utils/icons.py
from bengal.directives._icons import ICONS, ICON_MAP

def render_svg_icon(name: str, size: int = 20, css_class: str = "") -> str:
    """Render inline SVG icon."""
    ...
```

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
```

### Options Migration

Bengal's `DirectiveOptions` and Patitas's `DirectiveOptions` have nearly identical patterns:

```python
# Bengal
@dataclass
class DropdownOptions(DirectiveOptions):
    open: bool = False
    icon: str = ""
    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}

# Patitas (add frozen + slots)
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

## Test Migration Strategy

### Existing Test Coverage

Bengal directive tests live in:
- `tests/unit/directives/` - Unit tests per directive
- `tests/integration/` - Full parsing tests

### Migration Approach

1. **Port unit tests alongside code**
   - Each directive migration includes its test migration
   - Update imports from `bengal.directives` → `patitas.directives.bengal`

2. **Golden file tests** (new)
   - Generate expected HTML from current Bengal/mistune
   - Store in `tests/fixtures/directive_golden/`
   - Compare Patitas output against golden files

3. **Parity test harness**
   ```python
   def assert_html_parity(source: str, directive_name: str):
       """Run same source through both parsers, assert identical output."""
       bengal_html = normalize_html(render_bengal(source))
       patitas_html = normalize_html(render_patitas(source))
       assert patitas_html == bengal_html, f"{directive_name}: HTML mismatch"
   ```

4. **Thread safety tests**
   - TSan (ThreadSanitizer) in CI
   - Concurrent parsing stress tests
   - Location: `tests/thread_safety/`

### CI Integration

```yaml
# .github/workflows/test.yml
- name: Directive Parity Tests
  run: pytest tests/migration/test_directive_parity.py -v

- name: Thread Safety (TSan)
  run: |
    python -X dev -m pytest tests/thread_safety/ \
      --tb=short -q
```

---

## File Structure

```
bengal/rendering/parsers/patitas/directives/
├── __init__.py
├── protocol.py          # DirectiveHandler protocol
├── options.py           # DirectiveOptions base + common options
├── contracts.py         # DirectiveContract + predefined contracts
├── registry.py          # DirectiveRegistry
├── utils/
│   ├── __init__.py
│   ├── html.py          # escape_html, build_class_string, bool_attr
│   └── icons.py         # Icon rendering (imports SVGs from Bengal)
│
├── builtins/            # Patitas-native example directives
│   ├── __init__.py
│   ├── admonition.py    # ✅ Exists
│   ├── dropdown.py      # ✅ Exists
│   └── tabs.py          # ✅ Exists
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
    ├── embeds/
    │   ├── __init__.py
    │   ├── video.py     # youtube, vimeo, video, tiktok
    │   └── developer.py # gist, codepen, codesandbox, stackblitz
    ├── navigation.py    # breadcrumbs, siblings, prev-next, related
    ├── versioning.py    # since, deprecated, changed
    └── ...
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| HTML output differences | **High** | High | Phase 0: Audit existing builtins; golden file tests for every directive/option combo |
| Missing edge cases | Medium | Medium | Port Bengal's directive tests alongside code |
| Icon system coupling | **Medium** | Medium | Phase A: Extract icon utilities early |
| Performance regression | Low | Medium | Benchmark key directives |
| Free-threading issues | Low | High | TSan in CI, stress tests |
| Role system dependency | **Medium** | Medium | Decision: include roles or gate Phase C items |
| Existing builtin drift | **Medium** | High | Phase 0 validates builtins before proceeding |

---

## Success Criteria

1. **Parity**: 100% of Bengal's directive test cases pass with Patitas
2. **Golden files**: Zero HTML diff between mistune and Patitas rendering
3. **Performance**: ≤5% regression on directive-heavy pages
4. **Thread-safe**: Zero TSan errors under concurrent parsing
5. **Clean break**: No runtime dependency on mistune for directive parsing
6. **Test coverage**: All migrated directives have parity tests

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 0 | Phase 0 | Audit builtins, golden file harness, icon extraction |
| 1-2 | Phase A | Core directives (admonitions, dropdown, tabs, steps, container) |
| 3-4 | Phase B | Content directives (cards, tables, code-tabs, gallery) |
| 5-6 | Phase C | Specialized directives (includes, embeds, navigation, versioning) |
| 7-8 | Phase D | Integration, deprecation, documentation |

**Total: 9 weeks** (including Phase 0)

---

## Open Questions

1. **Role migration**: Include in this RFC or separate?
   - `glossary` directive blocked without `{term}` role
   - Cross-references (`{ref}`, `{doc}`) used by multiple directives
   - **Recommendation**: Separate RFC, gate `glossary` until complete

2. **Standalone Patitas?** Should Patitas be extractable as a standalone package?
   - Current: Icon import from Bengal acceptable
   - Future: Extract `bengal-icons` package if needed

3. **Rosettes integration**: Should syntax highlighting be part of this RFC?
   - `code-tabs` uses Rosettes for highlighting
   - **Recommendation**: Include as Phase B dependency

---

## Related Documents

- [RFC: Patitas Markdown Parser](rfc-patitas-markdown-parser.md) - Core parser design
- [bengal/directives/base.py](../../bengal/directives/base.py) - Current BengalDirective base
- [bengal/directives/registry.py](../../bengal/directives/registry.py) - Current directive registry

---

## Appendix A: Directive Migration Checklist

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

---

## Appendix B: Icon Dependencies

Directives that import from `bengal.directives._icons`:

| Module | Directives | Icon Usage |
|--------|------------|------------|
| `admonitions.py` | 10 types | Admonition type icons |
| `dropdown.py` | `dropdown`, `details` | Optional title icon |
| `button.py` | `button` | Button icon |
| `code_tabs.py` | `code-tabs` | Language icons |
| `cards/utils.py` | `card`, `cards` | Card icons |
| `icon.py` | `icon`, `svg-icon` | Direct icon rendering |

**Migration order**: Extract icon utilities in Phase 0/A before migrating these directives.

---

## Appendix C: Contract Relationships

```
steps ──requires──► step (child)
step ──requires──► steps (parent)

tab-set ──requires──► tab-item (child)
tab-item ──requires──► tab-set (parent)

cards ──requires──► card (child)
card ──requires──► cards (parent)
```

All contracts already exist in `patitas/directives/contracts.py`.
