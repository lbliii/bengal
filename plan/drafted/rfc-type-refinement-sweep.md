# RFC: Type Refinement Sweep

**Status**: Draft
**Created**: 2025-01-24
**Author**: AI Assistant
**Subsystem**: Cross-cutting (all packages)
**Confidence**: 90% 🟢 (verified via comprehensive codebase scan)
**Priority**: P1 (High) — Developer experience, IDE support, bug prevention
**Estimated Effort**: 5-7 days

---

## Executive Summary

This RFC proposes a systematic refinement of type annotations across the Bengal codebase to replace 541 `Any` usages and 806 `dict[str, Any]` patterns with precise types. This enables better IDE autocomplete, catches bugs at type-check time, and improves code maintainability.

**Key Metrics**:

| Pattern | Count | Files | Impact |
|---------|-------|-------|--------|
| `: Any` annotations | 541 | 193 | 🔴 High — loses all type checking |
| `dict[str, Any]` | 806 | 282 | 🟠 Medium — partial type info only |
| `-> Any` returns | 127 | 63 | 🔴 High — propagates untyped values |
| Existing `TypedDict` | 27 | 4 | 🟢 Good foundation to expand |
| Existing `Protocol` | 7 | 5 | 🟢 Good foundation to expand |

**Current State**: Bengal has **excellent typing infrastructure** with 594 files using `from __future__ import annotations` and 270 files using `TYPE_CHECKING` imports. The codebase is ready for type refinement.

**Impact**:
- **IDE Experience**: Autocomplete for config, frontmatter, context objects
- **Bug Prevention**: Catch type mismatches during development
- **Documentation**: Types serve as inline documentation
- **Refactoring Safety**: Confident refactoring with type checker support

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Existing Patterns to Expand](#existing-patterns-to-expand)
3. [High-Impact Type Refinements](#high-impact-type-refinements)
4. [Proposed TypedDict Definitions](#proposed-typeddict-definitions)
5. [Protocol Definitions](#protocol-definitions)
6. [Migration Strategy](#migration-strategy)
7. [File-by-File Priority](#file-by-file-priority)

---

## Current State Assessment

### Type Infrastructure ✅

Bengal has strong typing foundations:

```python
# 594 files use future annotations (99%+ coverage)
from __future__ import annotations

# 270 files use TYPE_CHECKING guards
if TYPE_CHECKING:
    from bengal.core import Site, Page

# mypy configured with strict options
[tool.mypy]
python_version = "3.14"
disallow_untyped_defs = true
strict_optional = true
disallow_any_generics = true
```

### Problematic Patterns

#### Pattern 1: `Any` as Escape Hatch (541 occurrences)

```python
# ❌ Loses all type information
def __init__(self, template_engine: Any, build_stats: Any = None) -> None:

# ❌ Return type `Any` propagates untyped values
def get(self, key: str, default: Any = None) -> Any:

# ❌ Generic catch-all parameters
def plugin_documentation_directives(md: Any) -> None:
```

#### Pattern 2: Stringly-Typed Dicts (806 occurrences)

```python
# ❌ No IDE support for valid keys or value types
def _add_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:

# ❌ Config structure unknown to type checker
DEFAULTS: dict[str, Any] = {
    "title": "Bengal Site",
    "baseurl": "",
    ...
}

# ❌ Frontmatter structure opaque
def from_dict(cls, data: dict[str, Any]) -> Frontmatter:
```

---

## Existing Patterns to Expand

### Pattern 1: AST TypedDict — EXCELLENT ✅

**Location**: `bengal/rendering/ast_types.py`

```python
class HeadingNode(TypedDict):
    """Heading (h1-h6)."""
    type: Literal["heading"]
    level: int
    children: list[ASTNode]
    attrs: NotRequired[dict[str, str]]

# Discriminated union of all node types
type ASTNode = (
    TextNode | CodeSpanNode | HeadingNode | ParagraphNode | ...
)
```

**Why This Works**:
- `Literal` types enable exhaustive switch handling
- `NotRequired` for optional fields
- Type alias for union (Python 3.12+ syntax)
- Type guards for runtime narrowing

### Pattern 2: CSS Manifest TypedDict — GOOD ✅

**Location**: `bengal/orchestration/css_manifest_types.py`

```python
class CSSManifest(TypedDict, total=False):
    """Schema for CSS manifest structure."""
    core: list[str]
    shared: list[str]
    type_map: dict[str, list[str]]
    feature_map: dict[str, list[str]]
    palettes: list[str]
    version: int
```

**Why This Works**:
- `total=False` makes all fields optional
- Nested structure with typed values
- Clear documentation

### Pattern 3: Frontmatter Dataclass — HYBRID ✅

**Location**: `bengal/core/page/frontmatter.py`

```python
@dataclass
class Frontmatter:
    """Typed frontmatter with dict-style access for template compatibility."""
    title: str = ""
    date: datetime | None = None
    tags: list[str] = field(default_factory=list)
    draft: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Dict-style access: fm["title"]."""
        ...
```

**Why This Works**:
- Explicit types for known fields
- `extra` dict for unknown fields
- Dict compatibility for templates

---

## High-Impact Type Refinements

### Category 1: Site Configuration

**Current** (`bengal/config/defaults.py`):

```python
DEFAULTS: dict[str, Any] = {
    "title": "Bengal Site",
    "baseurl": "",
    "output_dir": "public",
    "parallel": {"max_workers": 0},
    ...
}
```

**Proposed** — Create `SiteConfig` TypedDict:

```python
# bengal/config/types.py (NEW FILE)

class ParallelConfig(TypedDict, total=False):
    """Parallel build configuration."""
    max_workers: int
    chunk_size: int

class ContentConfig(TypedDict, total=False):
    """Content processing configuration."""
    excerpt_length: int
    auto_excerpt: bool
    toc_depth: int
    anchor_links: bool

class OutputConfig(TypedDict, total=False):
    """Output formatting configuration."""
    pretty_urls: bool
    trailing_slash: bool
    minify_html: bool

class SiteConfig(TypedDict, total=False):
    """Complete site configuration schema."""
    # Site metadata
    title: str
    baseurl: str
    description: str
    author: str
    language: str

    # Build settings
    output_dir: str
    parallel: ParallelConfig
    incremental: bool

    # Content
    content: ContentConfig

    # Output
    output: OutputConfig

    # Features
    rss: bool | RSSConfig
    sitemap: bool | SitemapConfig
    search: bool | SearchConfig
```

**Impact**:
- IDE autocomplete for all config keys
- Type errors for invalid config values
- Self-documenting configuration

---

### Category 2: Template Context

**Current** (`bengal/rendering/template_context.py`):

```python
def __init__(self, page: Any, baseurl: str = ""):
    self._page = page
```

**Proposed** — Use Protocol for template-compatible objects:

```python
# bengal/rendering/protocols.py (NEW FILE)

from typing import Protocol, runtime_checkable

@runtime_checkable
class TemplatePageProtocol(Protocol):
    """Protocol for objects usable as pages in templates."""
    @property
    def title(self) -> str: ...
    @property
    def href(self) -> str: ...
    @property
    def _path(self) -> str: ...
    @property
    def content(self) -> str: ...
    @property
    def frontmatter(self) -> Frontmatter: ...

class TemplatePageWrapper:
    def __init__(self, page: TemplatePageProtocol, baseurl: str = ""):
        self._page = page
```

---

### Category 3: Directive Parsing

**Current** (`bengal/directives/base.py`):

```python
def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
    ...

def render(self, renderer: Any, text: str, **attrs: Any) -> str:
    ...
```

**Proposed** — Define directive types:

```python
# bengal/directives/types.py (NEW FILE)

class DirectiveAttrs(TypedDict, total=False):
    """Common directive attributes."""
    class_: str  # CSS class
    id: str      # HTML id
    title: str   # Title/caption

class DirectiveParseResult(TypedDict):
    """Result of directive parsing."""
    type: str
    raw: str
    attrs: DirectiveAttrs
    children: list[ASTNode] | None

class CodeBlockAttrs(DirectiveAttrs):
    """Code block directive attributes."""
    language: str
    filename: str | None
    linenos: bool
    hl_lines: list[int]
    start_line: int

class AdmonitionAttrs(DirectiveAttrs):
    """Admonition directive attributes."""
    type: Literal["note", "warning", "tip", "danger", "info"]
    collapsible: bool
    open: bool
```

---

### Category 4: Build Statistics

**Current** (scattered across files):

```python
build_stats: Any = None
```

**Proposed** — Define build stats types:

```python
# bengal/orchestration/types.py (NEW FILE)

class PhaseStats(TypedDict):
    """Statistics for a build phase."""
    duration_ms: float
    count: int
    errors: int

class BuildStats(TypedDict, total=False):
    """Complete build statistics."""
    total_duration_ms: float
    pages_rendered: int
    pages_cached: int
    assets_copied: int

    # Phase breakdown
    discovery: PhaseStats
    rendering: PhaseStats
    postprocess: PhaseStats
    output: PhaseStats

    # Cache stats
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
```

---

### Category 5: Health Validator Results

**Current** (`bengal/health/report.py`):

```python
metadata: dict[str, Any] | None = None
```

**Proposed** — Define validator result types:

```python
# bengal/health/types.py (NEW FILE)

class ValidatorIssue(TypedDict):
    """Single validation issue."""
    severity: Literal["error", "warning", "info"]
    message: str
    file: str | None
    line: int | None
    code: str  # Issue code like "LINK001"

class ValidatorResult(TypedDict):
    """Result from a health validator."""
    validator: str
    passed: bool
    issues: list[ValidatorIssue]
    duration_ms: float
    metadata: NotRequired[dict[str, str | int | bool]]

class HealthReport(TypedDict):
    """Complete health check report."""
    total_validators: int
    passed: int
    failed: int
    warnings: int
    results: list[ValidatorResult]
```

---

## Proposed TypedDict Definitions

### Priority 1: Create New Type Files

| File | Purpose | TypedDicts |
|------|---------|------------|
| `bengal/config/types.py` | Site configuration | `SiteConfig`, `ParallelConfig`, `ContentConfig`, etc. |
| `bengal/rendering/types.py` | Rendering context | `TemplateContext`, `RenderResult` |
| `bengal/directives/types.py` | Directive parsing | `DirectiveAttrs`, `DirectiveParseResult` |
| `bengal/orchestration/types.py` | Build stats | `BuildStats`, `PhaseStats` |
| `bengal/health/types.py` | Validation | `ValidatorResult`, `ValidatorIssue` |
| `bengal/content_layer/types.py` | Content sources | `ContentEntry`, `SourceConfig` |

### Priority 2: Expand Existing Type Files

| File | Add |
|------|-----|
| `bengal/rendering/ast_types.py` | `DirectiveNode`, `TableNode` |
| `bengal/orchestration/css_manifest_types.py` | Export to `__all__` |

---

## Protocol Definitions

### New Protocols to Define

```python
# bengal/core/protocols.py (NEW FILE)

from typing import Protocol, runtime_checkable

@runtime_checkable
class PageLike(Protocol):
    """Protocol for page-like objects."""
    @property
    def title(self) -> str: ...
    @property
    def href(self) -> str: ...
    @property
    def content(self) -> str: ...
    @property
    def frontmatter(self) -> Frontmatter: ...

@runtime_checkable
class SectionLike(Protocol):
    """Protocol for section-like objects."""
    @property
    def title(self) -> str: ...
    @property
    def pages(self) -> list[PageLike]: ...
    @property
    def children(self) -> list[SectionLike]: ...

@runtime_checkable
class SiteLike(Protocol):
    """Protocol for site-like objects."""
    @property
    def config(self) -> SiteConfig: ...
    @property
    def pages(self) -> list[PageLike]: ...
    @property
    def sections(self) -> list[SectionLike]: ...
```

### Benefits

1. **Decoupling**: Functions accept protocols instead of concrete types
2. **Testing**: Easy to create mock objects
3. **Runtime checking**: `isinstance(obj, PageLike)` works

---

## Migration Strategy

### Phase 1: Create Type Definition Files (Day 1-2)

1. Create `bengal/config/types.py` with `SiteConfig` hierarchy
2. Create `bengal/orchestration/types.py` with `BuildStats`
3. Create `bengal/directives/types.py` with directive attributes
4. Create `bengal/health/types.py` with validator results
5. Create `bengal/core/protocols.py` with core protocols

### Phase 2: High-Traffic Path Refinement (Day 2-4)

Replace `Any` in most-accessed code paths:

| File | Current Any Count | Changes |
|------|-------------------|---------|
| `core/site/core.py` | 6 | Replace with `SiteConfig`, `QueryRegistry` |
| `directives/base.py` | 9 | Replace with `DirectiveAttrs`, `MistuneState` |
| `rendering/pipeline/core.py` | 5 | Replace with `BuildStats`, `DependencyTracker` |
| `orchestration/render.py` | 12 | Replace with typed context |
| `rendering/template_functions/navigation/scaffold.py` | 7 | Replace with `NavNode` types |

### Phase 3: Dict-to-TypedDict Conversion (Day 4-6)

Target files with highest `dict[str, Any]` usage:

| File | Pattern Count | Action |
|------|---------------|--------|
| `health/autofix.py` | 10 | Create `FixAction`, `DirectiveInfo` TypedDicts |
| `postprocess/output_formats/index_generator.py` | 9 | Create `PageSummary`, `SiteData` TypedDicts |
| `core/site/core.py` | 19 | Use `SiteConfig` type |
| `autodoc/orchestration/section_builders.py` | 10 | Create `AutodocSection` TypedDict |

### Phase 4: Return Type Refinement (Day 6-7)

Replace `-> Any` with specific types:

```python
# Before
def get(self, key: str, default: Any = None) -> Any:

# After (with overloads for common cases)
@overload
def get(self, key: Literal["title"], default: str = "") -> str: ...
@overload
def get(self, key: Literal["draft"], default: bool = False) -> bool: ...
@overload
def get(self, key: str, default: T) -> T: ...
def get(self, key: str, default: Any = None) -> Any:
    ...
```

---

## File-by-File Priority

### Tier 1: Critical Path (Days 1-2)

| File | Any Count | Priority |
|------|-----------|----------|
| `bengal/core/site/core.py` | 6 | P0 — Core site object |
| `bengal/config/defaults.py` | 7 | P0 — Config structure |
| `bengal/rendering/pipeline/core.py` | 5 | P0 — Render pipeline |
| `bengal/directives/base.py` | 9 | P0 — All directives extend |

### Tier 2: High Impact (Days 3-4)

| File | Any Count | Priority |
|------|-----------|----------|
| `bengal/orchestration/render.py` | 12 | P1 — Orchestration |
| `bengal/rendering/template_functions/navigation/scaffold.py` | 7 | P1 — Nav system |
| `bengal/health/autofix.py` | 10 | P1 — Autofix system |
| `bengal/directives/navigation.py` | 9 | P1 — Navigation directive |

### Tier 3: Secondary (Days 5-6)

| File | Any Count | Priority |
|------|-----------|----------|
| `bengal/directives/embed.py` | 12 | P2 |
| `bengal/autodoc/extractors/cli.py` | 6 | P2 |
| `bengal/rendering/template_functions/seo.py` | 7 | P2 |
| `bengal/content_layer/sources/notion.py` | 8 | P2 |

### Tier 4: Cleanup (Day 7)

Address remaining scattered `Any` usages with lower impact.

---

## Type Checking Integration

### mypy Configuration Updates

```toml
# pyproject.toml additions

[tool.mypy]
python_version = "3.14"
warn_return_any = true        # Already enabled ✅
warn_unused_configs = true    # Already enabled ✅
disallow_untyped_defs = true  # Already enabled ✅
strict_optional = true        # Already enabled ✅
disallow_any_generics = true  # Already enabled ✅
disallow_incomplete_defs = true  # Already enabled ✅

# NEW: Enable for gradual migration
warn_unreachable = true
enable_error_code = ["truthy-bool", "ignore-without-code"]

# Per-file overrides for gradual migration
[[tool.mypy.overrides]]
module = "bengal.directives.*"
disallow_any_explicit = true  # Enforce no explicit Any after migration
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml addition

- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.11.0
  hooks:
  - id: mypy
    args: [--strict, --ignore-missing-imports]
    additional_dependencies:
      - types-pyyaml
      - types-psutil
      - types-pygments
```

---

## Testing Strategy

### 1. Type Coverage Metrics

```bash
# Track type coverage over time
mypy bengal/ --txt-report mypy-report.txt

# Expected progression:
# Day 0: ~60% typed
# Day 7: ~85% typed
# Target: >90% typed
```

### 2. Runtime Protocol Checks

```python
# tests/test_type_protocols.py

def test_page_implements_protocol():
    """Verify Page implements PageLike protocol."""
    from bengal.core import Page
    from bengal.core.protocols import PageLike

    page = Page(...)
    assert isinstance(page, PageLike)

def test_site_config_validates():
    """Verify config matches SiteConfig TypedDict."""
    from bengal.config.types import SiteConfig

    config: SiteConfig = {
        "title": "Test Site",
        "baseurl": "/test/",
    }
    # TypedDict validates at type-check time
```

### 3. TypedDict Validation Tests

```python
def test_build_stats_structure():
    """Verify build stats match TypedDict."""
    from bengal.orchestration.types import BuildStats

    stats: BuildStats = {
        "total_duration_ms": 1234.5,
        "pages_rendered": 100,
        "cache_hits": 80,
    }
    assert stats["pages_rendered"] == 100
```

---

## Migration Checklist

### Pre-Implementation

- [ ] Review all 541 `Any` usages, categorize by domain
- [ ] Identify common dict structures for TypedDict candidates
- [ ] Create type definition files skeleton
- [ ] Update mypy configuration for gradual migration

### Phase 1: Type Definitions

- [ ] Create `bengal/config/types.py` with `SiteConfig`
- [ ] Create `bengal/orchestration/types.py` with `BuildStats`
- [ ] Create `bengal/directives/types.py` with directive types
- [ ] Create `bengal/health/types.py` with validator types
- [ ] Create `bengal/core/protocols.py` with core protocols
- [ ] Expand `bengal/rendering/ast_types.py`

### Phase 2: Critical Path Migration

- [ ] `core/site/core.py` — Replace 6 Any usages
- [ ] `config/defaults.py` — Type DEFAULTS dict
- [ ] `rendering/pipeline/core.py` — Replace 5 Any usages
- [ ] `directives/base.py` — Replace 9 Any usages

### Phase 3: High Impact Migration

- [ ] `orchestration/render.py` — Replace 12 Any usages
- [ ] `rendering/template_functions/navigation/scaffold.py` — Replace 7 Any usages
- [ ] `health/autofix.py` — Convert 10 dict[str, Any] to TypedDict
- [ ] `directives/navigation.py` — Replace 9 Any usages

### Phase 4: Secondary Migration

- [ ] `directives/embed.py` — Replace 12 Any usages
- [ ] `autodoc/extractors/cli.py` — Replace 6 Any usages
- [ ] `rendering/template_functions/seo.py` — Replace 7 Any usages

### Verification

- [ ] mypy passes with `--strict`
- [ ] No new `Any` in critical path files
- [ ] Type coverage > 85%
- [ ] All protocol tests pass
- [ ] IDE autocomplete works for config, frontmatter, context

---

## Appendix: Complete Any Audit

<details>
<summary>📊 Top 20 Files by Any Count (click to expand)</summary>

| Rank | File | Any Count |
|------|------|-----------|
| 1 | `orchestration/render.py` | 12 |
| 2 | `directives/embed.py` | 12 |
| 3 | `health/autofix.py` | 10 |
| 4 | `rendering/template_functions/navigation/models.py` | 10 |
| 5 | `directives/base.py` | 9 |
| 6 | `directives/navigation.py` | 9 |
| 7 | `rendering/pipeline/autodoc_renderer.py` | 9 |
| 8 | `content_layer/sources/notion.py` | 8 |
| 9 | `rendering/template_functions/seo.py` | 7 |
| 10 | `rendering/template_functions/navigation/scaffold.py` | 7 |
| 11 | `config/defaults.py` | 7 |
| 12 | `core/site/core.py` | 6 |
| 13 | `autodoc/extractors/cli.py` | 6 |
| 14 | `health/health_check.py` | 6 |
| 15 | `directives/glossary.py` | 6 |
| 16 | `directives/versioning.py` | 6 |
| 17 | `directives/steps.py` | 6 |
| 18 | `rendering/template_engine/environment.py` | 5 |
| 19 | `rendering/pipeline/core.py` | 5 |
| 20 | `orchestration/postprocess.py` | 5 |

</details>

<details>
<summary>📊 Top 20 Files by dict[str, Any] Count (click to expand)</summary>

| Rank | File | Pattern Count |
|------|------|---------------|
| 1 | `core/site/core.py` | 19 |
| 2 | `cache/build_cache/core.py` | 14 |
| 3 | `analysis/community_detection.py` | 13 |
| 4 | `health/report.py` | 12 |
| 5 | `themes/config.py` | 11 |
| 6 | `postprocess/output_formats/index_generator.py` | 9 |
| 7 | `rendering/engines/jinja.py` | 9 |
| 8 | `analysis/path_analysis.py` | 11 |
| 9 | `autodoc/orchestration/section_builders.py` | 10 |
| 10 | `health/autofix.py` | 10 |
| 11 | `analysis/graph_builder.py` | 9 |
| 12 | `debug/config_inspector.py` | 9 |
| 13 | `content_layer/sources/notion.py` | 8 |
| 14 | `health/validators/directives/checkers.py` | 8 |
| 15 | `content_layer/loaders.py` | 7 |
| 16 | `autodoc/orchestration/orchestrator.py` | 7 |
| 17 | `cache/build_cache/file_tracking.py` | 7 |
| 18 | `analysis/knowledge_graph.py` | 7 |
| 19 | `rendering/template_functions/i18n.py` | 7 |
| 20 | `collections/validator.py` | 5 |

</details>

---

## References

- [PEP 589 – TypedDict](https://peps.python.org/pep-0589/)
- [PEP 544 – Protocols](https://peps.python.org/pep-0544/)
- [PEP 673 – Self Type](https://peps.python.org/pep-0673/)
- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- `bengal/rendering/ast_types.py` — Existing TypedDict patterns
- `bengal/orchestration/css_manifest_types.py` — Existing TypedDict patterns
- `bengal/core/page/frontmatter.py` — Hybrid dataclass pattern
