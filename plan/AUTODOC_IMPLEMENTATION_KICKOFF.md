# Autodoc Implementation: Kickoff Plan

**Date**: October 4, 2025  
**Status**: 🚀 STARTING  
**Goal**: Ship Python autodoc in 3-4 weeks

---

## What We Just Created

### ✅ Foundation (Just Now)

Created the core architecture:

```
bengal/autodoc/
├── __init__.py              ✅ Package initialization
├── base.py                  ✅ DocElement + Extractor base class
├── generator.py             ✅ DocumentationGenerator + TemplateCache
├── extractors/              ✅ Directory for extractors
├── templates/               ✅ Directory for built-in templates
│   ├── python/              ✅
│   ├── openapi/             ✅
│   └── cli/                 ✅
```

**What this gives us**:
- ✅ Unified `DocElement` data model (works for all doc types)
- ✅ `Extractor` interface (pluggable architecture)
- ✅ `DocumentationGenerator` (template rendering + caching)
- ✅ Template hierarchy system (user overrides built-in)
- ✅ Parallel generation ready

---

## Next Steps (Week 1)

### Day 1: Python Extractor Core (Today!)

**Goal**: Extract basic Python documentation via AST

**Tasks**:
1. Create `bengal/autodoc/extractors/python.py`
2. Implement `PythonExtractor` class
3. AST parsing for:
   - Modules (name, docstring)
   - Classes (name, docstring, methods)
   - Functions (name, signature, docstring)
4. Basic tests

**Deliverable**: Can extract basic Python API structure

---

### Day 2: Docstring Parsing

**Goal**: Parse Google/NumPy/Sphinx docstrings

**Tasks**:
1. Create `bengal/autodoc/docstring_parser.py`
2. Implement parsers:
   - `GoogleDocstringParser`
   - `NumpyDocstringParser`
   - `SphinxDocstringParser`
3. Extract:
   - Args/parameters
   - Returns
   - Raises
   - Examples
4. Tests for all three styles

**Deliverable**: Rich docstring data extraction

---

### Day 3: Template System

**Goal**: Generate markdown from extracted data

**Tasks**:
1. Create default templates:
   - `templates/python/module.md.jinja2`
   - `templates/python/class.md.jinja2`
   - `templates/python/function.md.jinja2`
2. Test template rendering
3. Create example customization
4. Documentation

**Deliverable**: Beautiful markdown output

---

### Day 4: CLI Integration

**Goal**: `bengal autodoc python` command works

**Tasks**:
1. Add autodoc commands to `bengal/cli.py`
2. Configuration loading from `bengal.toml`
3. Progress indicators
4. Error handling
5. Basic tests

**Deliverable**: Working CLI command

---

### Day 5: Testing & Polish

**Goal**: Solid foundation, self-test

**Tasks**:
1. Test on Bengal's own codebase
2. Generate Bengal API docs
3. Fix bugs
4. Performance testing
5. Documentation

**Deliverable**: Week 1 complete, basic autodoc working!

---

## Success Criteria (Week 1)

By end of week, we should be able to:

```bash
$ bengal autodoc python --source bengal --output content/api

📚 Extracting Python API...
   📄 Parsing bengal/core/site.py... ✓
   📄 Parsing bengal/core/page.py... ✓
   📄 Parsing bengal/core/section.py... ✓
   ... (23 modules)

🔨 Generating documentation...
   ✓ Generated 127 pages in 2.3s

✅ Done!
```

**Output**: Beautiful markdown files in `content/api/`

---

## Week 2-3 Preview

### Week 2: Advanced Features
- Cross-reference system
- Type hint extraction
- Inheritance documentation
- Source links
- Coverage reporting

### Week 3: Performance & Polish
- Incremental builds
- Caching system
- Parallel optimization
- Watch mode
- Sphinx migration tool

---

## Development Workflow

### 1. Make Changes
```bash
# Edit code
vim bengal/autodoc/extractors/python.py
```

### 2. Test Immediately
```bash
# Unit tests
pytest tests/unit/autodoc/test_python_extractor.py -v

# Integration test (on Bengal itself)
bengal autodoc python --source bengal --output content/api
```

### 3. Check Output
```bash
# View generated docs
ls content/api/
cat content/api/bengal/core/site.md
```

### 4. Iterate Fast
```bash
# Watch mode for templates
bengal autodoc python --watch
```

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/autodoc/test_python_extractor.py

def test_extract_simple_function():
    """Test extracting a simple function."""
    source = '''
def hello(name: str) -> str:
    """Say hello.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message
    """
    return f"Hello, {name}!"
'''
    
    extractor = PythonExtractor()
    elements = extractor.extract_from_string(source)
    
    assert len(elements) == 1
    func = elements[0]
    assert func.name == 'hello'
    assert func.element_type == 'function'
    assert 'name' in func.metadata['args']
```

### Integration Tests
```bash
# Use Bengal's own code as test case
bengal autodoc python --source bengal/core --output test-output
```

### Self-Documentation
```bash
# Generate Bengal's API docs (dogfooding!)
bengal autodoc python --source bengal --output content/api
bengal build
# Now we have API docs for Bengal!
```

---

## Quick Reference

### File Structure
```
bengal/autodoc/
├── base.py                  ← Data models + interfaces
├── generator.py             ← Template rendering
├── cache.py                 ← (Week 2) Caching
├── cross_refs.py            ← (Week 2) Cross-references
├── extractors/
│   ├── python.py           ← (Day 1) Python AST extraction
│   ├── openapi.py          ← (v0.5.0) OpenAPI extraction
│   └── cli.py              ← (v0.4.0) CLI extraction
├── docstring_parser.py     ← (Day 2) Docstring parsing
└── templates/
    └── python/
        ├── module.md.jinja2    ← (Day 3)
        ├── class.md.jinja2     ← (Day 3)
        └── function.md.jinja2  ← (Day 3)
```

### Configuration
```toml
# bengal.toml

[autodoc.python]
enabled = true
source_dirs = ["bengal"]
output_dir = "content/api"
docstring_style = "google"
```

### CLI Commands
```bash
# Basic
bengal autodoc python

# With options
bengal autodoc python --source src --output docs/api

# Watch mode
bengal autodoc python --watch

# Stats
bengal autodoc python --stats
```

---

## Debugging Tips

### Enable Verbose Output
```bash
bengal autodoc python --verbose --debug
```

### Test Single File
```bash
python -c "
from bengal.autodoc.extractors.python import PythonExtractor
from pathlib import Path

extractor = PythonExtractor()
elements = extractor.extract(Path('bengal/core/site.py'))
print(elements)
"
```

### Template Debugging
```bash
# Show which template would be used
bengal autodoc python --show-template class
```

---

## Performance Targets (Week 1)

- Extract 100 Python files: < 5 seconds
- Generate 100 pages: < 3 seconds
- Total: < 10 seconds for medium project

*We'll optimize more in Week 3*

---

## Questions to Answer This Week

- [ ] Does AST extraction work for Bengal's codebase?
- [ ] Are the generated docs readable?
- [ ] Is the template system flexible enough?
- [ ] Does the CLI feel intuitive?
- [ ] Are there any blockers?

---

## Success = Ship Week 1 Milestone

By Friday, we should have:
- ✅ Working Python extractor
- ✅ Basic template system
- ✅ CLI integration
- ✅ Self-documented (Bengal API docs generated)
- ✅ 50+ test passing
- ✅ < 10s to generate 100 pages

**Then we build on this foundation!**

---

## Let's Go! 🚀

**Start with**: `bengal/autodoc/extractors/python.py`

**First goal**: Extract a simple function from a string

**Test it**: Generate docs for `bengal/core/page.py`

**Win condition**: See beautiful markdown in `content/api/`

---

*Week 1, Day 1 begins NOW!*

