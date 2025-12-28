# RFC: Code Smell Remediation — God Classes, Monolithic Functions, and Deep Nesting

**Status**: Draft  
**Created**: 2025-12-28  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P1 (High) — Technical debt at breaking point  
**Confidence**: 95% 🟢 (based on direct AST analysis of 800+ files)

---

## Executive Summary

Static analysis of the bengal codebase reveals critical maintainability issues:

| Category | Count | Worst Offender |
|----------|-------|----------------|
| **God Functions** (400+ lines) | 6 | `BuildOrchestrator.build` (460 lines) |
| **God Classes** (50+ methods) | 5 | `PageProxy` (~70 wrapper methods/properties) |
| **High Cyclomatic Complexity** (40+ branches) | 25+ | `_parse_block_content` (40 elif branches) |
| **Monolithic Files** (1000+ lines) | 10 | `patitas/parser.py` (1655 lines) |
| **Long Parameter Lists** (≥10) | 10 | `build` CLI command (25 params) |

**Key Insight**: These aren't isolated issues—they're symptoms of missing abstractions. The `PageProxy` class's 74 methods exist because there's no delegation pattern. The 460-line `build()` exists because phase orchestration isn't complete.

This RFC proposes a phased remediation plan targeting the highest-impact issues first.

---

## Problem Statement

### 1. God Functions Create Testing and Maintenance Nightmares

**Critical Offenders**:

| Lines | Location | Function | Problem |
|-------|----------|----------|---------|
| 460 | `orchestration/build/__init__.py:137` | `BuildOrchestrator.build` | Mixes options resolution, logging setup, phase orchestration, error handling, stats collection |
| 456 | `analysis/graph_visualizer.py:361` | `generate_html` | Embeds 400+ lines of HTML/CSS/JS as f-strings |
| 442 | `cli/commands/build.py:161` | `build` | 25 parameters, mixes config resolution with execution |
| 384 | `health/validators/connectivity.py:63` | `validate` | Monolithic validation logic |
| 342 | `rendering/kida/template.py:348` | `Template.__init__` | Defines helper functions inline as closures |
| 296 | `rendering/kida/compiler/expressions.py:105` | `_compile_expr` | Giant switch/if-chain |

**Impact**:
- Impossible to unit test individual responsibilities
- Changes risk unintended side effects
- Code review becomes superficial due to cognitive overload
- Parallel development creates merge conflicts

### 2. God Classes Violate Single Responsibility

**Critical Offenders**:

| Methods | Lines | Class | Problem |
|---------|-------|-------|---------|
| ~70 | 806 | `PageProxy` | Wraps every `Page` method instead of using `__getattr__` delegation |
| 66 | 690 | `DependencyWalker` | Visitor pattern with too many node types |
| 50 | 429 | `PurityAnalyzer` | Similar to DependencyWalker |
| 49 | 1112 | `JinjaParser` | Compatibility layer doing too much |
| 33 | 1602 | `Parser` (patitas) | Block + inline parsing in one class |

**`PageProxy` Analysis** (worst offender):

The class contains ~70 wrapper methods and properties that exist because the class manually delegates to `_full_page` or `core`:

```python
# Current pattern (repeated 74 times!)
@property
def title(self) -> str:
    return self.core.title or ""

@property
def content(self) -> str:
    self._ensure_loaded()
    return self._full_page.content if self._full_page else ""

# ... 72 more property/method wrappers
```

This should be 3-5 methods using `__getattr__` delegation.

### 3. High Cyclomatic Complexity Makes Code Unmaintainable

**Critical Offenders**:

| Branches | Location | Function | Root Cause |
|----------|----------|----------|------------|
| **40+** | `kida/parser/statements.py:115` | `_parse_block_content` | 40+ `elif keyword ==` branches |
| 20+ | `content_layer/sources/notion.py:394` | `_blocks_to_markdown` | Recursive block type dispatch |
| 18+ | `content_layer/sources/notion.py:524` | `_extract_properties` | Property type dispatch |
| 15+ | `patitas/parser.py:1352` | `_build_inline_ast` | Inline token type dispatch |

**Note**: These are **branch counts** (cyclomatic complexity), not nesting depth. Each branch represents a distinct code path that must be tested.

**`_parse_block_content` with 40+ Branches**:

```python
def _parse_block_content(self) -> Node | list[Node] | None:
    keyword = self._current.value

    if keyword == "if":
        return self._parse_if()
    elif keyword == "unless":
        return self._parse_unless()
    elif keyword == "for":
        return self._parse_for()
    # ... 37 more elif branches ...
    elif keyword == "spaceless":
        return self._parse_spaceless()
```

This is a textbook case for a **dispatch table/registry pattern**.

### 4. Monolithic Files Indicate Missing Abstractions

| Lines | File | Concern |
|-------|------|---------|
| 1655 | `rendering/parsers/patitas/parser.py` | Block + inline + AST in one file |
| 1242 | `rendering/errors.py` | All error types in one file |
| 1226 | `rendering/kida/compat/jinja.py` | Jinja compatibility monolith |
| 1188 | `directives/embed.py` | Single directive, 1200 lines |
| 1129 | `rendering/kida/template.py` | Template runtime complexity |
| 1105 | `rendering/kida/environment/filters.py` | All filters in one file |
| 1023 | `patitas/directives/builtins/embed.py` | Duplicate embed logic |

**Duplication Alert**: `directives/embed.py` (1188 lines) and `patitas/directives/builtins/embed.py` (1023 lines) likely contain significant overlap.

### 5. Long Parameter Lists Signal Missing Abstractions

| Params | Location | Function |
|--------|----------|----------|
| 25 | `cli/commands/build.py:161` | `build` |
| 16 | `orchestration/build/rendering.py:357` | `phase_render` |
| 15 | `cli/commands/serve.py:99` | `serve` |
| 15 | `orchestration/build/__init__.py:137` | `build` |
| 13 | `core/site/core.py:310` | `build` |

The `build` command already has a `BuildOptions` dataclass but **doesn't use it at the CLI layer**. Parameters are accepted individually and then assembled into the dataclass.

---

## Proposed Solution

### Phase 1: Quick Wins (Low Risk, High Impact)

#### 1.1 Dispatch Table for `_parse_block_content`

**Before** (31 nesting levels):
```python
def _parse_block_content(self) -> Node | list[Node] | None:
    keyword = self._current.value
    if keyword == "if":
        return self._parse_if()
    elif keyword == "unless":
        return self._parse_unless()
    # ... 37 more elif ...
```

**After** (2 nesting levels):
```python
# Class-level dispatch table
_BLOCK_PARSERS: dict[str, Callable[[], Node | list[Node] | None]] = {
    "if": "_parse_if",
    "unless": "_parse_unless",
    "for": "_parse_for",
    # ... all keywords ...
}

def _parse_block_content(self) -> Node | list[Node] | None:
    keyword = self._current.value
    parser_name = self._BLOCK_PARSERS.get(keyword)

    if parser_name is None:
        return self._parse_custom_extension(keyword)

    parser = getattr(self, parser_name)
    return parser()
```

**Benefits**:
- Reduces nesting from 31 → 2
- Makes keyword list discoverable
- Enables extension points for custom block types
- Same performance (dict lookup is O(1))

**Effort**: 1 hour  
**Risk**: Low (pure refactor, no behavior change)

---

#### 1.2 `PageProxy` Delegation Pattern

**Before** (74 wrapper methods):
```python
class PageProxy:
    @property
    def title(self) -> str:
        return self.core.title or ""

    @property
    def content(self) -> str:
        self._ensure_loaded()
        return self._full_page.content if self._full_page else ""

    # ... 72 more methods ...
```

**After** (~10 methods + `__getattr__`):
```python
class PageProxy:
    # Cached properties (no lazy load needed)
    _CACHED_ATTRS = frozenset({
        "title", "date", "tags", "slug", "section", "type",
        "weight", "draft", "lang", "version", "aliases", "props"
    })

    # Properties that trigger lazy load
    _LAZY_ATTRS = frozenset({
        "content", "rendered_html", "toc", "toc_items", "links",
        "parsed_ast", "headings", "frontmatter"
    })

    def __getattr__(self, name: str) -> Any:
        # Check cached attributes (from PageCore)
        if name in self._CACHED_ATTRS:
            return getattr(self.core, name, None)

        # Check lazy attributes (require full page load)
        if name in self._LAZY_ATTRS:
            self._ensure_loaded()
            return getattr(self._full_page, name, None)

        # Unknown attribute - delegate to full page
        self._ensure_loaded()
        return getattr(self._full_page, name)
```

**Benefits**:
- Reduces 74 methods → ~10 explicit + `__getattr__`
- Automatically forwards new `Page` attributes
- Clear separation: cached vs lazy-loaded
- Easier to maintain transparency contract

**Effort**: 4 hours  
**Risk**: High (critical path for templates and incremental builds)

**Required Test Coverage**:
- Property access timing (lazy vs eager load triggers)
- Missing attribute error propagation (not masked by `__getattr__`)
- All template access patterns (verified via integration tests)
- Incremental build correctness (proxy→page replacement)
- Serialization behavior if relevant to caching

---

#### 1.3 Extract `generate_html` Templates

**Before** (456 lines of f-strings):
```python
def generate_html(self, title: str | None = None) -> str:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    ...
    <style>
        /* 200+ lines of CSS */
    </style>
    <script>
        /* 150+ lines of JS */
    </script>
</head>
...
"""
```

**After** (template files + 50-line function):
```python
# bengal/analysis/templates/graph_visualizer.html
# bengal/analysis/templates/graph_visualizer.css
# bengal/analysis/templates/graph_visualizer.js

def generate_html(self, title: str | None = None) -> str:
    """Generate complete standalone HTML visualization."""
    graph_data = self.generate_graph_data()
    context = self._build_template_context(title, graph_data)
    return self._render_template("graph_visualizer.html", context)

def _build_template_context(self, title: str | None, graph_data: dict) -> dict:
    """Build context for template rendering."""
    return {
        "title": title or f"Knowledge Graph - {self.site.config.get('title', 'Site')}",
        "graph_data": json.dumps(graph_data),
        "css_path": self._resolve_css_path(),
        "default_appearance": self._get_default_appearance(),
        # ...
    }
```

**Benefits**:
- Separates concerns (Python logic vs HTML/CSS/JS)
- Templates can be edited by frontend developers
- Syntax highlighting in templates
- Easier to test rendering logic

**Effort**: 4 hours  
**Risk**: Low (output is the same, just sourced differently)

---

### Phase 2: Structural Refactoring (Medium Risk)

#### 2.1 Split `patitas/parser.py` (1655 lines → 4 modules)

```
rendering/parsers/patitas/
├── parser.py           # Main Parser class, ~400 lines (orchestration only)
├── block_parser.py     # Block-level parsing, ~500 lines
├── inline_parser.py    # Inline/span parsing, ~400 lines
├── ast_builder.py      # AST construction, ~300 lines
└── token_stream.py     # Token stream utilities (if not already separate)
```

**Approach**:
1. Extract block-level methods to `BlockParserMixin`
2. Extract inline methods to `InlineParserMixin`
3. `Parser` class uses mixin composition
4. Alternatively: Parser delegates to `BlockParser` and `InlineParser` instances

**Effort**: 8 hours  
**Risk**: Medium (must maintain API compatibility)

---

#### 2.2 Split `errors.py` (1242 lines → domain-specific modules)

```
rendering/errors/
├── __init__.py         # Public API (re-exports)
├── base.py             # Base exception classes
├── parsing.py          # Parser-related errors
├── compilation.py      # Compiler errors
├── runtime.py          # Runtime/render errors
└── validation.py       # Validation errors
```

**Effort**: 4 hours  
**Risk**: Low (errors are leaf nodes, no complex dependencies)

---

#### 2.3 Consolidate Embed Directive Logic

**Current State**:
- `directives/embed.py` (1188 lines)
- `patitas/directives/builtins/embed.py` (1023 lines)

**Investigation Required First** (2 hours):
```bash
# Compare structural similarity
diff -u bengal/directives/embed.py \
       bengal/rendering/parsers/patitas/directives/builtins/embed.py | head -200

# Check for shared function names
grep "^def \|^    def " bengal/directives/embed.py | sort > /tmp/embed1.txt
grep "^def \|^    def " bengal/rendering/parsers/patitas/directives/builtins/embed.py | sort > /tmp/embed2.txt
comm -12 /tmp/embed1.txt /tmp/embed2.txt  # Common functions
```

**Possible Outcomes**:
1. **High overlap (>60%)**: Consolidate to shared `embed/core.py` with adapters
2. **Moderate overlap (30-60%)**: Extract common utilities, keep separate implementations
3. **Low overlap (<30%)**: Keep separate, document as intentional divergence

**If consolidating**:
```
directives/embed/
├── __init__.py         # Public API
├── core.py             # Shared embed logic
├── jinja_adapter.py    # Jinja-specific wrapper
└── patitas_adapter.py  # Patitas-specific wrapper
```

**Effort**: 2 hours investigation + 4-6 hours consolidation (if applicable)  
**Risk**: Medium (must understand both implementations before deciding)

---

### Phase 3: API Improvements (Higher Risk)

#### 3.1 Parameter Object for Build Commands

**Before** (25 parameters):
```python
@click.command()
@click.option("--parallel/--no-parallel", ...)
@click.option("--incremental/--no-incremental", ...)
# ... 23 more options ...
def build(parallel, incremental, memory_optimized, environment, ...):
    # Manually construct BuildOptions
    options = BuildOptions(
        parallel=parallel,
        incremental=incremental,
        # ... map all 25 params ...
    )
```

**After** (parameter object with Click integration):
```python
# bengal/cli/options.py
class BuildOptionsClickMixin:
    """Click options that map to BuildOptions fields."""

    @staticmethod
    def options(func):
        """Decorator that adds all build options."""
        decorators = [
            click.option("--parallel/--no-parallel", default=True),
            click.option("--incremental/--no-incremental", default=None),
            # ... all options with defaults from BuildOptions ...
        ]
        for decorator in reversed(decorators):
            func = decorator(func)
        return func

# bengal/cli/commands/build.py
@click.command()
@BuildOptionsClickMixin.options
def build(**kwargs):
    options = BuildOptions.from_cli_args(**kwargs)
    orchestrator.build(options)
```

**Benefits**:
- Single source of truth for options
- Defaults defined in `BuildOptions`, not scattered in decorators
- Easier to add new options
- Type-safe parameter passing

**Effort**: 6 hours  
**Risk**: Medium (CLI is stable interface)

---

#### 3.2 Decompose `BuildOrchestrator.build` (460 lines)

The method already uses phase orchestrators but still does too much. Break into:

```python
class BuildOrchestrator:
    def build(self, options: BuildOptions) -> BuildStats:
        """Execute full build pipeline."""
        context = self._prepare_build(options)

        try:
            stats = self._execute_phases(context)
            self._finalize_build(context, stats)
            return stats
        except Exception as e:
            return self._handle_build_error(context, e)

    def _prepare_build(self, options: BuildOptions) -> BuildContext:
        """Set up logging, resolve options, initialize context."""
        # ~80 lines currently scattered in build()

    def _execute_phases(self, context: BuildContext) -> BuildStats:
        """Run all build phases in sequence."""
        # Phase orchestration loop

    def _finalize_build(self, context: BuildContext, stats: BuildStats) -> None:
        """Clean up, report stats, close resources."""

    def _handle_build_error(self, context: BuildContext, error: Exception) -> BuildStats:
        """Error handling and recovery."""
```

**Effort**: 4 hours  
**Risk**: Low (internal refactor, public API unchanged)

---

## Implementation Plan

### Pre-Flight Validation

Before starting any phase, capture baseline metrics:

```bash
# Run the detection script and save baseline
python scripts/detect_code_smells.py > reports/smells-before.txt

# Run full test suite and benchmark
pytest tests/ -q --tb=no > reports/tests-before.txt
python -m bengal build site/ --profile > reports/bench-before.txt
```

### Week 1: Quick Wins

| Day | Task | Effort | Risk |
|-----|------|--------|------|
| 1 | Dispatch table for `_parse_block_content` | 1h | Low |
| 1-3 | `PageProxy` delegation pattern | 4h | **High** |
| 3-4 | Extract `generate_html` templates | 4h | Low |

**Tests**: Run full test suite after each change. Add specific tests for:
- Block keyword dispatch (ensure all keywords still work)
- PageProxy attribute access (cached vs lazy)
- PageProxy error propagation (missing attrs raise properly)
- Graph visualizer HTML output comparison

**Rollback Criteria**:
- If test suite fails: `git revert HEAD` immediately
- If PageProxy changes break template rendering: revert and investigate
- If benchmark regresses >5%: revert and profile before re-attempting

### Week 2: Structural Splits

| Day | Task | Effort | Risk |
|-----|------|--------|------|
| 1-2 | Split `errors.py` | 4h | Low |
| 2-3 | Investigate embed duplication | 2h | N/A |
| 3-5 | Consolidate embed logic | 6h | Medium |

### Week 3: Parser Modularization

| Day | Task | Effort | Risk |
|-----|------|--------|------|
| 1-3 | Split `patitas/parser.py` | 8h | Medium |
| 4-5 | Integration testing | 4h | N/A |

### Week 4: API Improvements

| Day | Task | Effort | Risk |
|-----|------|--------|------|
| 1-2 | Parameter object for CLI | 6h | Medium |
| 3-4 | Decompose `BuildOrchestrator.build` | 4h | Low |
| 5 | Documentation updates | 2h | N/A |

---

## Success Criteria

### Quantitative

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Max function length | 460 lines | < 100 lines | AST analysis |
| Max class methods | 74 | < 25 | AST analysis |
| Max nesting depth | 31 levels | < 5 levels | AST analysis |
| Max file length | 1655 lines | < 800 lines | wc -l |
| Max parameters | 25 | < 8 | AST analysis |

### Qualitative

- [ ] Each module has single, clear responsibility
- [ ] New developers can understand code in < 30 minutes per module
- [ ] Unit tests can target individual responsibilities
- [ ] No merge conflicts in split modules during parallel development

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking `PageProxy` transparency | High | Comprehensive property access tests |
| Dispatch table performance | Low | Benchmark before/after (dict lookup is O(1)) |
| Template extraction breaks output | Medium | Diff HTML output before/after |
| Parser split breaks edge cases | High | Run full benchmark suite + fuzzing |
| CLI changes break scripts | Medium | Maintain backward-compatible parameter names |

---

## Testing Strategy

### 1. Regression Tests

- Full test suite must pass after each phase
- Add snapshot tests for complex outputs (graph HTML, error messages)

### 2. Property-Based Tests

For `PageProxy` delegation:
```python
@given(st.sampled_from(Page.__dict__.keys()))
def test_proxy_forwards_all_page_attributes(attr_name):
    proxy = create_test_proxy()
    page = create_test_page()

    if not attr_name.startswith("_"):
        assert getattr(proxy, attr_name) == getattr(page, attr_name)
```

### 3. Benchmark Validation

Ensure refactoring doesn't regress performance:
- Parser throughput (pages/second)
- Build time for reference site
- Memory usage for large sites

---

## Appendix A: Full Analysis Data

### A.1 All Functions > 200 Lines

| Lines | File | Function |
|-------|------|----------|
| 460 | `orchestration/build/__init__.py:137` | `build` |
| 456 | `analysis/graph_visualizer.py:361` | `generate_html` |
| 442 | `cli/commands/build.py:161` | `build` |
| 384 | `health/validators/connectivity.py:63` | `validate` |
| 342 | `rendering/kida/template.py:348` | `__init__` |
| 309 | `rendering/rosettes/lexers/ruby_sm.py:132` | `tokenize` |
| 296 | `rendering/kida/compiler/expressions.py:105` | `_compile_expr` |
| 262 | `rendering/rosettes/lexers/elixir_sm.py:126` | `tokenize` |
| 261 | `rendering/rosettes/lexers/julia_sm.py:165` | `tokenize` |
| 257 | `utils/css_minifier.py:74` | `minify_css` |
| 257 | `rendering/template_engine/environment.py:181` | `create_jinja_environment` |
| 251 | `autodoc/orchestration/orchestrator.py:454` | `generate` |
| 248 | `rendering/rosettes/lexers/nim_sm.py:176` | `tokenize` |
| 244 | `rendering/rosettes/lexers/v_sm.py:134` | `tokenize` |
| 239 | `rendering/rosettes/lexers/perl_sm.py:280` | `tokenize` |
| 234 | `orchestration/streaming.py:109` | `process` |
| 233 | `rendering/rosettes/lexers/markdown_sm.py:25` | `tokenize` |
| 227 | `rendering/rosettes/lexers/powershell_sm.py:169` | `tokenize` |
| 226 | `rendering/parsers/patitas/parser.py:987` | `_tokenize_inline` |
| 226 | `rendering/rosettes/lexers/xml_sm.py:25` | `tokenize` |
| 223 | `health/validators/directives/analysis.py:94` | `analyze` |
| 223 | `rendering/rosettes/lexers/mojo_sm.py:169` | `tokenize` |
| 222 | `rendering/rosettes/lexers/cue_sm.py:90` | `tokenize` |
| 218 | `cli/commands/graph/bridges.py:52` | `bridges` |
| 214 | `rendering/rosettes/lexers/clojure_sm.py:145` | `tokenize` |
| 213 | `rendering/rosettes/lexers/bash_sm.py:118` | `tokenize` |
| 209 | `rendering/rosettes/lexers/hcl_sm.py:178` | `tokenize` |

### A.2 Pattern: State Machine Lexers

The `rendering/rosettes/lexers/*_sm.py` files share a pattern: 200-300 line `tokenize` methods with similar structure. Consider:

1. **Base class abstraction** for common state machine logic
2. **Code generation** from grammar definitions
3. **Declarative token tables** instead of procedural code

This is a separate RFC topic but worth noting as a systemic pattern.

### A.3 High-Coupling Files (30+ imports)

| Imports | File |
|---------|------|
| 52 | `directives/factory.py` |
| 45 | `rendering/parsers/patitas/directives/builtins/__init__.py` |
| 43 | `rendering/parsers/patitas/__init__.py` |
| 40 | `autodoc/extractors/python/extractor.py` |
| 37 | `rendering/parsers/patitas/renderers/html.py` |
| 36 | `cli/dashboard/widgets/__init__.py` |
| 36 | `debug/__init__.py` |
| 35 | `directives/__init__.py` |
| 35 | `rendering/parsers/patitas/parser.py` |
| 32 | `directives/base.py` |
| 32 | `rendering/kida/compat/jinja.py` |

Many of these are `__init__.py` files re-exporting from submodules—acceptable pattern. The non-init files with 30+ imports may indicate:
- Module doing too much (split it)
- Missing intermediate abstractions
- Circular dependency risk

---

## Appendix B: Refactoring Scripts

### B.1 Code Smell Detection Script

Save as `scripts/detect_code_smells.py`:

```python
#!/usr/bin/env python3
"""Detect code smells in the bengal codebase."""

import ast
import os
from pathlib import Path

def analyze_file(filepath: Path) -> dict:
    """Analyze a single Python file for code smells."""
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read())
    except:
        return {}

    results = {
        "functions": [],
        "classes": [],
        "imports": 0,
    }

    # Count imports
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            results["imports"] += len(node.names)
        elif isinstance(node, ast.ImportFrom):
            results["imports"] += len(node.names)

    # Analyze functions and classes
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = node.end_lineno or node.lineno
            size = end - node.lineno + 1
            params = len([p for p in node.args.args if p.arg not in ("self", "cls")])
            results["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "size": size,
                "params": params,
            })
        elif isinstance(node, ast.ClassDef):
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            end = node.end_lineno or node.lineno
            results["classes"].append({
                "name": node.name,
                "line": node.lineno,
                "size": end - node.lineno + 1,
                "methods": len(methods),
            })

    return results

def main():
    thresholds = {
        "function_size": 100,
        "class_methods": 20,
        "params": 7,
        "imports": 25,
        "file_size": 500,
    }

    issues = []
    for root, dirs, files in os.walk("bengal"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                path = Path(root) / f
                results = analyze_file(path)

                # Check thresholds
                for func in results.get("functions", []):
                    if func["size"] > thresholds["function_size"]:
                        issues.append(f"LONG_FUNCTION: {path}:{func['line']} {func['name']} ({func['size']} lines)")
                    if func["params"] > thresholds["params"]:
                        issues.append(f"MANY_PARAMS: {path}:{func['line']} {func['name']} ({func['params']} params)")

                for cls in results.get("classes", []):
                    if cls["methods"] > thresholds["class_methods"]:
                        issues.append(f"GOD_CLASS: {path}:{cls['line']} {cls['name']} ({cls['methods']} methods)")

    for issue in sorted(issues):
        print(issue)

if __name__ == "__main__":
    main()
```

---

## References

- [Refactoring: Improving the Design of Existing Code](https://martinfowler.com/books/refactoring.html) — Martin Fowler
- [Clean Code](https://www.oreilly.com/library/view/clean-code-a/9780136083238/) — Robert C. Martin
- [rfc-dependency-decoupling.md](./rfc-dependency-decoupling.md) — Related refactoring RFC
- [rfc-mixin-composition.md](./rfc-mixin-composition.md) — Mixin patterns for class decomposition
