# RFC Viability Analysis: Autodoc Alias Detection and Inherited Member Controls

**Date**: 2025-10-19  
**RFC**: rfc-autodoc-alias-inherited.md  
**Status**: ✅ VIABLE with recommendations  

## Executive Summary

The proposed RFC for alias detection and inherited member controls is **highly viable** and well-aligned with Bengal's architecture. The implementation is straightforward, aligns with existing patterns, and can be delivered incrementally with minimal risk. Key findings:

- ✅ **Architecture fit**: Perfectly aligned with existing AST-only extraction approach
- ✅ **Performance**: Expected overhead <2% when disabled, <5% when enabled
- ✅ **Extensibility**: Leverages existing DocElement metadata patterns
- ✅ **Testing**: Can reuse existing test infrastructure
- ⚠️ **Complexity**: Moderate (alias detection is simple; inherited resolution requires careful handling)
- ✅ **Value**: High - closes significant parity gap with Sphinx

## Current Architecture Assessment

### Strengths Supporting This RFC

1. **Metadata-Driven Design**
   - `DocElement.metadata` is already a flexible dict accepting arbitrary keys
   - Adding `alias_of`, `inherited_from`, `synthetic` fits naturally
   - No schema changes or migrations needed

2. **AST-Only Extraction**
   - RFC proposes AST-only alias detection (`ast.Assign` with `ast.Name` values)
   - Perfectly aligned with current `PythonExtractor` approach (no imports, no runtime)
   - Already handles base class strings via `ast.unparse(base)` in `_extract_class` (lines 160-162)

3. **Template System**
   - Jinja2 templates already support conditional rendering and filters
   - `module.md.jinja2` template is well-structured with sections and macros
   - Adding "Alias of" badges and "Inherited members" sections is straightforward

4. **Configuration System**
   - `bengal/autodoc/config.py` uses simple dict-merge pattern for config
   - Default values are clearly defined (lines 24-49)
   - Per-type configuration already exists conceptually (python vs cli vs openapi)

5. **Testing Infrastructure**
   - Unit tests use `tmp_path` fixtures and in-memory Python source (lines 10-263 in test_python_extractor.py)
   - Easy to add tests for alias and inheritance scenarios
   - Existing patterns for metadata validation

### Gaps and Challenges

1. **No Class Index Yet**
   - RFC requires in-memory index: `qualified_name -> class DocElement`
   - Current extractor processes files one at a time; no cross-file index
   - **Solution**: Build index during `_extract_directory()` after all files extracted

2. **Limited Cross-Module Resolution**
   - Current system doesn't track where symbols are defined across modules
   - Alias resolution to external libraries (e.g., `np = numpy`) won't work
   - RFC acknowledges this as non-goal (section "Non-goals")

3. **No Override Detection**
   - RFC requires detecting if derived class overrides a method to avoid duplicates
   - Current extractor doesn't track this
   - **Solution**: Simple name-based check in children list before adding inherited member

4. **Template Needs Enhancement**
   - Current `module.md.jinja2` has no alias or inherited member support
   - Need to add conditional rendering blocks
   - Minor effort; template is well-organized

## Detailed Viability Analysis

### 1. Alias Detection (Module Scope)

**Proposal**: Detect `alias = original` patterns via AST.

**Implementation Path**:
```python
def _extract_module_aliases(self, tree: ast.Module) -> dict[str, str]:
    """Extract simple assignment aliases: alias = original"""
    aliases = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            # Pattern: alias = original
            if len(node.targets) == 1:
                target = node.targets[0]
                value = node.value

                # target is ast.Name and value is ast.Name or ast.Attribute
                if isinstance(target, ast.Name) and isinstance(value, (ast.Name, ast.Attribute)):
                    alias_name = target.id
                    original_name = ast.unparse(value)
                    aliases[alias_name] = original_name

    return aliases
```

**Viability**: ✅ **HIGH**
- Uses existing AST infrastructure
- Simple pattern matching (10-15 lines)
- No imports or runtime introspection needed
- Can be tested in isolation

**Edge Cases**:
- Multiple assignment: `a = b = func` → Skip (not simple alias)
- Dynamic assignment: `alias = getattr(module, name)` → Skip (outside scope)
- Cross-module aliases: `pub = other_mod.internal` → Works if `other_mod` is in corpus

**Risk**: LOW. Worst case: we miss some aliases (conservative false negative). No false positives expected.

### 2. Inherited Members (Class Scope)

**Proposal**: Build class index and synthesize inherited members with metadata.

**Implementation Path**:

```python
def _extract_directory(self, directory: Path) -> list[DocElement]:
    """Extract from all Python files in directory."""
    elements = []

    # Extract all files
    for py_file in directory.rglob("*.py"):
        if self._should_skip(py_file):
            continue
        try:
            file_elements = self._extract_file(py_file)
            elements.extend(file_elements)
        except Exception as e:
            print(f"  ⚠️  Error extracting {py_file}: {e}")

    # Build class index for inheritance resolution
    class_index = self._build_class_index(elements)

    # Synthesize inherited members if enabled
    if self.config.get('include_inherited', False):
        self._add_inherited_members(elements, class_index)

    return elements

def _build_class_index(self, elements: list[DocElement]) -> dict[str, DocElement]:
    """Build qualified_name -> class DocElement index."""
    index = {}

    def visit(elem: DocElement):
        if elem.element_type == "class":
            index[elem.qualified_name] = elem
        for child in elem.children:
            visit(child)

    for elem in elements:
        visit(elem)

    return index

def _add_inherited_members(
    self, elements: list[DocElement], class_index: dict[str, DocElement]
):
    """Add inherited members to classes based on config."""

    def visit(elem: DocElement):
        if elem.element_type == "class":
            self._synthesize_inherited_for_class(elem, class_index)
        for child in elem.children:
            visit(child)

    for elem in elements:
        visit(elem)

def _synthesize_inherited_for_class(
    self, cls: DocElement, class_index: dict[str, DocElement]
):
    """Add inherited members to a single class."""
    bases = cls.metadata.get("bases", [])

    # Get own member names for collision detection
    own_members = {child.name for child in cls.children}

    for base_name in bases:
        # Resolve base class (simple qualified name lookup)
        base_cls = class_index.get(base_name)

        if not base_cls:
            continue  # Base not in corpus (e.g., stdlib)

        # Copy members from base
        for member in base_cls.children:
            # Skip if derived class overrides
            if member.name in own_members:
                continue

            # Skip private members unless explicitly included
            if member.name.startswith('_') and not self.config.get('include_private', False):
                continue

            # Create synthetic inherited member (shallow copy)
            inherited = DocElement(
                name=member.name,
                qualified_name=f"{cls.qualified_name}.{member.name}",
                description=f"Inherited from {base_cls.qualified_name}",
                element_type=member.element_type,
                source_file=member.source_file,
                line_number=member.line_number,
                metadata={
                    **member.metadata,
                    "inherited_from": base_cls.qualified_name,
                    "synthetic": True,
                },
            )

            cls.children.append(inherited)
```

**Viability**: ✅ **MEDIUM-HIGH**
- Requires new class index (not complex, ~30 lines)
- Inheritance resolution is AST-based (bases already extracted)
- No MRO computation needed (linear base list is sufficient for MVP)
- Synthetic DocElements fit existing model

**Challenges**:
1. **Nested classes**: Need recursive traversal (already done in CLI extractor, line 28 in `cli.py`)
2. **Multiple inheritance**: Process bases in order; stop on first definition
3. **Cross-module bases**: Only works if base is in documented corpus
4. **Generic bases**: `class Foo(Generic[T])` → unparse gives `"Generic[T]"`, won't match index

**Risk**: MEDIUM
- False negatives: Will miss inherited members from stdlib/third-party (expected)
- False positives: Minimal; collision detection prevents duplicates
- Performance: O(classes × bases × members) → ~1000 classes × 2 bases × 10 methods = 20K ops (negligible)

### 3. Configuration Integration

**Proposal**: Add `include_inherited`, `include_inherited_by_type`, `alias_strategy` to `[autodoc.python]`.

**Current Config Pattern** (from `config.py` lines 24-38):
```python
default_config = {
    "python": {
        "enabled": True,
        "include_private": False,
        "include_special": False,
        # ... more keys
    }
}
```

**New Config** (RFC lines 25-44):
```toml
[autodoc.python]
include_inherited = false
include_inherited_by_type = { class = false, exception = false }
alias_strategy = "canonical"
```

**Implementation**:
```python
default_config = {
    "python": {
        # Existing
        "enabled": True,
        "include_private": False,
        "include_special": False,

        # New
        "include_inherited": False,
        "include_inherited_by_type": {
            "class": False,
            "exception": False,
        },
        "alias_strategy": "canonical",  # canonical | duplicate | list-only
    }
}
```

**Viability**: ✅ **HIGH**
- Trivial to add (3 lines)
- Config merge already handles nested dicts (line 67 in `config.py`)
- Defaults are conservative (off) → no breaking changes

**Risk**: LOW. Pure additive change.

### 4. Template Updates

**Proposal**: Add alias badges and inherited member sections.

**Current Template Structure** (from `module.md.jinja2`):
- Frontmatter (lines 125-131)
- Module description (lines 133-139)
- Classes section (lines 143-245)
  - Attributes dropdown (lines 165-167)
  - Properties section (lines 169-185)
  - Methods section (lines 187-242)
- Functions section (lines 247-299)

**Needed Additions**:

1. **Alias Badge** (after class name, line ~147):
```jinja2
### `{{ cls.name }}`
{% if cls.metadata.alias_of %}
  ```{badge} Alias of {{ cls.metadata.alias_of }}
  :color: info
  ```
{% endif %}
```

2. **Inherited Members Section** (after own methods, line ~242):
```jinja2
{% set inherited = cls.children | selectattr('metadata.synthetic', 'equalto', true) | list %}
{% if inherited %}
::::{dropdown} Inherited members ({{ inherited | length }})
:open: false

{% for base in inherited | groupby('metadata.inherited_from') %}
##### From `{{ base.grouper }}`
{% for member in base.list %}
- `{{ member.name }}` → [{{ base.grouper }}.{{ member.name }}](link)
{% endfor %}
{% endfor %}

::::
{% endif %}
```

**Viability**: ✅ **HIGH**
- Template is well-structured with existing dropdowns and badges
- Jinja2 `selectattr` and `groupby` filters support the needed logic
- No breaking changes; sections only appear when data present

**Risk**: LOW. Template changes are isolated and backward-compatible.

### 5. Testing Strategy

**Proposal**: Unit tests for alias extraction, inherited synthesis, config merge.

**Existing Test Patterns** (from `test_python_extractor.py`):
- Use `tmp_path` fixtures
- Write Python source with `dedent()`
- Call `extractor.extract(source)`
- Assert on `element.name`, `element.metadata`, `element.children`

**New Tests Needed**:

1. **Alias Detection**:
```python
def test_extract_simple_alias(tmp_path):
    source = tmp_path / "test.py"
    source.write_text(dedent("""
        def original_func():
            '''The real function.'''
            pass

        # Simple alias
        alias_func = original_func
    """))

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    module = elements[0]
    children_names = [c.name for c in module.children]

    assert "original_func" in children_names
    assert "alias_func" in children_names

    alias = next(c for c in module.children if c.name == "alias_func")
    assert alias.metadata.get("alias_of") == "original_func"
```

2. **Inherited Members**:
```python
def test_extract_inherited_members_when_enabled(tmp_path):
    source = tmp_path / "test.py"
    source.write_text(dedent("""
        class Base:
            def base_method(self):
                '''Base method.'''
                pass

        class Derived(Base):
            def own_method(self):
                '''Own method.'''
                pass
    """))

    extractor = PythonExtractor(config={"include_inherited": True})
    elements = extractor.extract(source)

    module = elements[0]
    derived = next(c for c in module.children if c.name == "Derived")

    method_names = [m.name for m in derived.children]
    assert "own_method" in method_names
    assert "base_method" in method_names

    inherited = next(m for m in derived.children if m.name == "base_method")
    assert inherited.metadata.get("synthetic") is True
    assert inherited.metadata.get("inherited_from") == "Base"
```

3. **Override Detection**:
```python
def test_inherited_skips_overridden_members(tmp_path):
    # Similar to above, but Derived overrides base_method
    # Assert only one base_method in children (the override)
```

**Viability**: ✅ **HIGH**
- Existing test infrastructure supports all needed scenarios
- Can test alias detection and inheritance independently
- Config mocking is straightforward

**Effort**: ~1-2 days for comprehensive test suite (6-10 test cases)

**Risk**: LOW

### 6. Performance Impact

**Expected Overhead**:

| Operation                  | Current | With Aliases | With Inheritance |
|---------------------------|---------|--------------|------------------|
| Parse + Extract           | ~0.2s/file | +0.01s (~5%) | +0.01s (~5%)     |
| Directory extraction      | O(files) | O(files)     | O(files) + O(classes) |
| Class index building      | N/A     | N/A          | O(classes) = ~0.01s for 100 classes |
| Inherited synthesis       | N/A     | N/A          | O(classes × bases × members) = ~0.05s for 1000 classes |
| **Total overhead**        | -       | <1%          | <5%              |

**Measurements** (hypothetical, based on typical codebases):
- 100 files, 10 classes/file, 3 bases/class, 10 methods/class
- Index building: 1000 classes × 1 insert = 1000 ops → <10ms
- Inherited synthesis: 1000 classes × 3 bases × 10 methods = 30K ops → ~50ms

**When disabled** (default): Zero overhead (config check is O(1))

**Viability**: ✅ **HIGH**
- RFC target <5% overhead aligns with estimates
- Disabled by default → no impact on existing users
- Potential optimization: cache base class lookups, skip stdlib bases early

**Risk**: LOW

## Implementation Roadmap

### Phase 1: Alias Detection (MVP)
**Effort**: 3-5 days  
**Risk**: LOW

1. Add `_extract_module_aliases()` to `PythonExtractor`
2. Emit alias `DocElement` with `metadata.alias_of`
3. Update `module.md.jinja2` to show alias badges
4. Add configuration key `alias_strategy = "canonical"`
5. Unit tests (3-4 test cases)
6. Documentation update

**Deliverable**: Aliases appear in docs with "Alias of X" indicator

### Phase 2: Inherited Members (Core)
**Effort**: 5-7 days  
**Risk**: MEDIUM

1. Add `_build_class_index()` to `PythonExtractor`
2. Implement `_add_inherited_members()` with collision detection
3. Add configuration keys: `include_inherited`, `include_inherited_by_type`
4. Update `module.md.jinja2` with inherited members section
5. Unit tests (5-7 test cases)
6. Integration tests with multi-file scenarios
7. Documentation update

**Deliverable**: Inherited members listed in class docs (off by default)

### Phase 3: Polish & Optimization
**Effort**: 2-3 days  
**Risk**: LOW

1. Add "Also known as" section to canonical elements (list aliases)
2. Performance profiling and optimization
3. Edge case handling (nested classes, generics)
4. Enhanced documentation with examples
5. Showcase site integration

**Deliverable**: Production-ready feature with docs and examples

### Total Effort: 10-15 days
**Calendar Time**: 2-3 weeks (with testing and review)

## Risk Assessment

| Risk                              | Probability | Impact | Mitigation                                |
|-----------------------------------|-------------|--------|-------------------------------------------|
| Cross-module alias resolution     | HIGH        | LOW    | Document limitation; focus on same-module |
| Generic base class matching       | MEDIUM      | LOW    | Strip type params before lookup           |
| Performance on large codebases    | LOW         | MEDIUM | Profile with bengal's own codebase (160+ files) |
| Template breaking changes         | LOW         | HIGH   | Only add sections; don't modify existing  |
| Config merge conflicts            | LOW         | LOW    | Per-type config is dict, not nested       |
| Inherited member duplication      | LOW         | MEDIUM | Robust collision detection                |

**Overall Risk**: LOW-MEDIUM

## Recommendations

### ✅ PROCEED with modifications:

1. **Start with Alias Detection** (Phase 1)
   - Simplest, highest value
   - No cross-file dependencies
   - Can ship independently

2. **Defer Advanced Alias Strategies**
   - RFC proposes `alias_strategy = "canonical" | "duplicate" | "list-only"`
   - Start with "canonical" only; add others if demanded
   - Reduces initial complexity

3. **Limit Inherited to Single Inheritance Initially**
   - Skip multiple inheritance edge cases in MVP
   - Simplifies collision detection
   - Most Python code uses single inheritance

4. **Add Performance Benchmarks**
   - Measure extraction time on bengal's own codebase (~50 modules)
   - Add to `benchmarks/` directory
   - Set threshold: <5% overhead

5. **Provide Clear Documentation on Limitations**
   - "Only works for classes in documented corpus"
   - "No runtime MRO resolution"
   - "Stdlib bases not resolved"

6. **Consider Config Helper**
   - Common pattern: "show inherited for all public classes"
   - Add preset: `include_inherited_preset = "public-classes"`

### 🔄 Recommended Config Changes

From RFC:
```toml
include_inherited_by_type = { class = false, exception = false }
```

To simpler:
```toml
include_inherited = false  # Global toggle
# Per-type is overkill for MVP; add later if needed
```

### 📋 Testing Checklist

- [ ] Alias: simple assignment `a = b`
- [ ] Alias: attribute assignment `a = mod.b`
- [ ] Alias: skip complex assignments `a = b = c`
- [ ] Inherited: single base class
- [ ] Inherited: multiple bases (linear resolution)
- [ ] Inherited: override detection
- [ ] Inherited: private member filtering
- [ ] Inherited: base not in corpus (graceful skip)
- [ ] Config: merge precedence
- [ ] Config: disabled by default
- [ ] Template: alias badge rendering
- [ ] Template: inherited section grouping
- [ ] Template: empty state (no aliases/inherited)
- [ ] Performance: <5% overhead when enabled
- [ ] Performance: 0% overhead when disabled

## Conclusion

**RECOMMENDATION**: ✅ **APPROVE RFC with minor modifications**

The RFC is well-designed, fits Bengal's architecture perfectly, and addresses real user needs. Implementation is straightforward with moderate effort and low risk. The proposed features close a significant gap with Sphinx while maintaining Bengal's AST-only robustness and performance.

**Key Success Factors**:
- Incremental rollout (aliases first, inheritance second)
- Conservative defaults (disabled by default)
- Clear documentation of limitations
- Comprehensive testing including edge cases
- Performance benchmarking

**Next Steps**:
1. Author reviews this analysis
2. Approve RFC with recommended modifications
3. Create implementation issues/tasks
4. Begin Phase 1 (Alias Detection)

---

**Analysis by**: AI Assistant  
**Reviewed by**: _Pending_  
**Approved**: _Pending_
