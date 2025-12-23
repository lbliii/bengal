---
description: Bengal's core architecture - passive models, orchestrators for operations, composition over inheritance
alwaysApply: true
---

# Architecture Patterns

Bengal follows strict separation of concerns: **models are passive data containers**, **orchestrators handle all operations**.

**Works with**: `modules/types-as-contracts`, `modules/evidence-handling`

---

## The Model/Orchestrator Split

### Models (`bengal/core/`) - PASSIVE

Models are **data structures only**:

```python
# ✅ CORRECT - Models hold data, no I/O
@dataclass
class Page:
    source_path: Path
    content: str
    metadata: dict[str, Any]

    @property
    def title(self) -> str:
        return self.metadata.get("title", "Untitled")
```

Models **MUST NOT**:
- Log messages
- Perform file I/O
- Make network requests
- Have side effects
- Access global state

### Orchestrators (`bengal/orchestration/`) - ACTIVE

Orchestrators **handle all operations**:

```python
# ✅ CORRECT - Orchestrator handles I/O and logging
class RenderOrchestrator:
    @staticmethod
    def render_pages(site: Site) -> None:
        """Render all pages in the site."""
        logger.info(f"Rendering {len(site.pages)} pages")
        for page in site.pages:
            html = TemplateEngine.render(page)
            output_path = site.output_dir / page.url
            output_path.write_text(html)
```

---

## Delegation Pattern

Models delegate operations to orchestrators:

```python
# In bengal/core/site.py
class Site:
    def build(self) -> None:
        """Build the site (delegates to orchestrator)."""
        return BuildOrchestrator.build(self)

    def discover_content(self) -> None:
        """Discover content (delegates to orchestrator)."""
        return ContentOrchestrator.discover(self)
```

**Why?**
- Models remain testable without I/O mocking
- Operations are centralized and consistent
- Clear separation of data and behavior

---

## Subsystem Responsibilities

```
bengal/
├── core/              # Data models (no I/O, no logging)
│   ├── site.py        # Site container
│   ├── page/          # Page model (package - >400 lines)
│   ├── section.py     # Section/directory model
│   ├── asset/         # Asset model
│   └── theme/         # Theme resolution
│
├── orchestration/     # Build operations (all I/O here)
│   ├── build_orchestrator.py
│   ├── render_orchestrator.py
│   ├── content_orchestrator.py
│   └── asset_orchestrator.py
│
├── rendering/         # Template and content rendering
├── discovery/         # Content/asset discovery
├── cache/             # Caching infrastructure
├── health/            # Validation and health checks
└── cli/               # Command-line interface
```

---

## Composition Over Inheritance

Use mixins instead of deep inheritance:

```python
# ✅ CORRECT - Composition with focused mixins
@dataclass
class Page(
    PageMetadataMixin,      # Metadata access
    PageNavigationMixin,    # URL/navigation helpers
    PageComputedMixin,      # Computed properties
    PageRelationshipsMixin, # Parent/children/siblings
):
    """Page combines focused mixins."""
    core: PageCore
    content: str
    rendered_html: str | None = None
```

**Not this**:

```python
# ❌ WRONG - Deep inheritance
class BasePage: pass
class ContentPage(BasePage): pass
class BlogPage(ContentPage): pass
class ArticlePage(BlogPage): pass  # Too deep!
```

---

## Single Responsibility

Each class has **one clear purpose**:

| Class | Responsibility |
|-------|----------------|
| `Site` | Root data container for a build |
| `Page` | Represents one content file |
| `Section` | Represents content directory |
| `BuildOrchestrator` | Coordinates build phases |
| `RenderOrchestrator` | Handles page rendering |
| `ContentOrchestrator` | Discovers content |

---

## File Size Threshold (400 Lines)

When a file exceeds **400 lines**, convert to a package:

```
# Before (450 lines)
bengal/core/page.py

# After (converted to package)
bengal/core/page/
├── __init__.py          # Main Page class (~50 lines)
├── page_core.py         # PageCore (~200 lines)
├── metadata.py          # PageMetadataMixin (~80 lines)
├── navigation.py        # PageNavigationMixin (~60 lines)
├── computed.py          # PageComputedMixin (~100 lines)
└── proxy.py             # PageProxy (~150 lines)
```

---

## Common Patterns

### Strategy Pattern

```python
class ContentStrategy(ABC):
    @abstractmethod
    def get_template(self, page: Page) -> str: ...

class BlogStrategy(ContentStrategy):
    def get_template(self, page: Page) -> str:
        return 'blog/post.html'

class DocStrategy(ContentStrategy):
    def get_template(self, page: Page) -> str:
        return 'docs/page.html'
```

### Registry Pattern

```python
class ContentTypeRegistry:
    _strategies: dict[str, ContentStrategy] = {}

    @classmethod
    def register(cls, name: str, strategy: ContentStrategy) -> None:
        cls._strategies[name] = strategy

    @classmethod
    def get(cls, name: str) -> ContentStrategy:
        return cls._strategies[name]
```

### Builder Pattern

```python
builder = MenuBuilder('main')
builder.add_from_config(items)
builder.add_from_pages(pages)
menu = builder.build_hierarchy()
```

---

## Data Flow

### Explicit State Management

```python
# ✅ CORRECT - Pass state explicitly
def render_page(page: Page, context: BuildContext) -> str:
    return template.render(page=page, site=context.site)

# ❌ WRONG - Hidden global state
_current_site = None  # Global mutable state

def render_page(page: Page) -> str:
    global _current_site
    return template.render(page=page, site=_current_site)
```

### Single Source of Truth

- **Site** is the root data container
- **Cache** stores paths, not object references
- References reconstructed each build

---

## God Object Warning Signs

A class may be a "God object" if it has:

- More than **400 lines**
- More than **10 public methods**
- Imports from **>5 different modules**
- Does **multiple unrelated things**

**Solution**:
1. Extract mixins for different concerns
2. Delegate operations to specialized classes
3. Use composition instead of adding methods

---

## Validation Checklist

When reviewing code:

- [ ] **Models have no I/O** - No file operations in `bengal/core/`
- [ ] **Models don't log** - No `logger.info()` in models
- [ ] **Orchestrators handle operations** - All I/O in `bengal/orchestration/`
- [ ] **Composition over inheritance** - Mixins, not deep hierarchies
- [ ] **Single responsibility** - Each class does one thing
- [ ] **File size < 400 lines** - Convert to package if exceeded

---

## Quick Reference

| Pattern | Use When |
|---------|----------|
| Delegation | Model needs to trigger operation |
| Strategy | Multiple implementations of behavior |
| Registry | Dynamic type/handler lookup |
| Builder | Complex object construction |
| Mixin | Shared functionality across classes |

---

## Evidence

- `bengal/core/site.py` - Site delegates to orchestrators
- `bengal/core/page/__init__.py` - Page uses mixins
- `bengal/orchestration/build_orchestrator.py` - Orchestrator with I/O
- `architecture/design-principles.md` - Full design documentation
