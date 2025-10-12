# Site Templates Refactoring Plan

## Current State

**File**: `bengal/cli/site_templates.py` (1,143 lines)

### Problems

1. **Monolithic**: Single 1.1k line file containing all template definitions
2. **Content as Code**: Large markdown/YAML content embedded as Python strings
3. **Hard to Maintain**: Adding/editing templates requires scrolling through huge string literals
4. **Not Extensible**: Difficult to add custom templates or override defaults
5. **Poor Separation**: Template content mixed with template logic
6. **Testing Difficulty**: Hard to test individual templates in isolation

### Current Templates

- **default**: Basic site structure (21 lines)
- **blog**: Blog with posts, tags, categories (137 lines)
- **docs**: Technical documentation (327 lines)
- **portfolio**: Portfolio with projects showcase (547 lines)
- **resume**: Professional resume/CV with structured data (832 lines!)
- **landing**: Landing page for products/services (1,072 lines)

## Proposed Modular Architecture

### Directory Structure

```
bengal/cli/templates/
├── __init__.py                    # Template registry and loader
├── base.py                        # Base classes and utilities
├── registry.py                    # Template discovery and management
│
├── default/
│   ├── __init__.py
│   ├── template.py                # Template definition
│   └── pages/
│       └── index.md               # Actual markdown file
│
├── blog/
│   ├── __init__.py
│   ├── template.py
│   └── pages/
│       ├── index.md
│       ├── about.md
│       └── posts/
│           ├── first-post.md
│           └── second-post.md
│
├── docs/
│   ├── __init__.py
│   ├── template.py
│   └── pages/
│       ├── index.md
│       ├── getting-started/
│       │   ├── index.md
│       │   ├── installation.md
│       │   └── quickstart.md
│       ├── guides/
│       │   └── index.md
│       └── api/
│           └── index.md
│
├── portfolio/
│   ├── __init__.py
│   ├── template.py
│   └── pages/
│       ├── index.md
│       ├── about.md
│       ├── contact.md
│       └── projects/
│           ├── index.md
│           ├── project-1.md
│           └── project-2.md
│
├── resume/
│   ├── __init__.py
│   ├── template.py
│   ├── pages/
│   │   └── _index.md
│   └── data/
│       └── resume.yaml            # Actual YAML file
│
└── landing/
    ├── __init__.py
    ├── template.py
    └── pages/
        ├── index.md
        ├── privacy.md
        └── terms.md
```

### New Code Structure

#### 1. Base Classes (`bengal/cli/templates/base.py`)

```python
"""Base classes for site templates."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class TemplateFile:
    """Represents a file to be created from a template."""

    relative_path: str  # Relative path from content/data directory
    content: str
    target_dir: str = "content"  # "content", "data", "templates", etc.


@dataclass
class SiteTemplate:
    """Base class for site templates."""

    id: str
    name: str
    description: str
    files: list[TemplateFile] = field(default_factory=list)
    additional_dirs: list[str] = field(default_factory=list)

    def get_files(self) -> list[TemplateFile]:
        """Get all files for this template."""
        return self.files

    def get_additional_dirs(self) -> list[str]:
        """Get additional directories to create."""
        return self.additional_dirs


class TemplateProvider(Protocol):
    """Protocol for template providers."""

    @classmethod
    def get_template(cls) -> SiteTemplate:
        """Return the site template."""
        ...
```

#### 2. Template Registry (`bengal/cli/templates/registry.py`)

```python
"""Template registry and discovery."""

from pathlib import Path
from typing import Dict, Optional
import importlib
import pkgutil

from .base import SiteTemplate, TemplateProvider


class TemplateRegistry:
    """Registry for discovering and managing site templates."""

    def __init__(self):
        self._templates: Dict[str, SiteTemplate] = {}
        self._discover_templates()

    def _discover_templates(self) -> None:
        """Discover all available templates."""
        templates_dir = Path(__file__).parent

        for item in templates_dir.iterdir():
            if not item.is_dir() or item.name.startswith('_'):
                continue

            # Try to import the template module
            try:
                module = importlib.import_module(f".{item.name}.template", package="bengal.cli.templates")
                if hasattr(module, 'TEMPLATE'):
                    template = module.TEMPLATE
                    self._templates[template.id] = template
            except (ImportError, AttributeError) as e:
                # Skip directories that don't contain templates
                continue

    def get(self, template_id: str) -> Optional[SiteTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list(self) -> list[tuple[str, str, str]]:
        """List all templates (id, name, description)."""
        return [
            (t.id, t.name, t.description)
            for t in self._templates.values()
        ]

    def exists(self, template_id: str) -> bool:
        """Check if a template exists."""
        return template_id in self._templates


# Global registry instance
_registry = TemplateRegistry()


def get_template(template_id: str) -> Optional[SiteTemplate]:
    """Get a template by ID."""
    return _registry.get(template_id)


def list_templates() -> list[tuple[str, str, str]]:
    """List all available templates."""
    return _registry.list()


def register_template(template: SiteTemplate) -> None:
    """Register a custom template."""
    _registry._templates[template.id] = template
```

#### 3. Template Module Example (`bengal/cli/templates/blog/template.py`)

```python
"""Blog template definition."""

from pathlib import Path
from ..base import SiteTemplate, TemplateFile


def _load_template_file(relative_path: str) -> str:
    """Load a template file from the pages directory."""
    template_dir = Path(__file__).parent
    file_path = template_dir / "pages" / relative_path

    with open(file_path, 'r') as f:
        return f.read()


def _create_blog_template() -> SiteTemplate:
    """Create the blog site template."""

    files = [
        TemplateFile(
            relative_path="index.md",
            content=_load_template_file("index.md"),
            target_dir="content"
        ),
        TemplateFile(
            relative_path="about.md",
            content=_load_template_file("about.md"),
            target_dir="content"
        ),
        TemplateFile(
            relative_path="posts/first-post.md",
            content=_load_template_file("posts/first-post.md"),
            target_dir="content"
        ),
        TemplateFile(
            relative_path="posts/second-post.md",
            content=_load_template_file("posts/second-post.md"),
            target_dir="content"
        ),
    ]

    return SiteTemplate(
        id="blog",
        name="Blog",
        description="A blog with posts, tags, and categories",
        files=files,
        additional_dirs=["content/posts", "content/drafts"]
    )


# Export the template
TEMPLATE = _create_blog_template()
```

#### 4. Resume Template with Data (`bengal/cli/templates/resume/template.py`)

```python
"""Resume template definition."""

from pathlib import Path
from ..base import SiteTemplate, TemplateFile


def _load_file(filename: str, subdir: str = "pages") -> str:
    """Load a file from the template directory."""
    template_dir = Path(__file__).parent
    file_path = template_dir / subdir / filename

    with open(file_path, 'r') as f:
        return f.read()


def _create_resume_template() -> SiteTemplate:
    """Create the resume site template."""

    files = [
        TemplateFile(
            relative_path="_index.md",
            content=_load_file("_index.md"),
            target_dir="content"
        ),
        TemplateFile(
            relative_path="resume.yaml",
            content=_load_file("resume.yaml", subdir="data"),
            target_dir="data"
        ),
    ]

    return SiteTemplate(
        id="resume",
        name="Resume",
        description="Professional resume/CV site with structured data",
        files=files,
        additional_dirs=["data"]
    )


# Export the template
TEMPLATE = _create_resume_template()
```

#### 5. Updated Site Templates Module (`bengal/cli/site_templates.py`)

```python
"""
Site templates - DEPRECATED

This module maintains backward compatibility.
Use bengal.cli.templates instead.
"""

import warnings
from bengal.cli.templates.base import SiteTemplate as SiteTemplateBase
from bengal.cli.templates.registry import get_template, list_templates


# Backward compatibility
SiteTemplate = SiteTemplateBase


def __getattr__(name: str):
    """Provide backward compatibility for old imports."""
    if name == "TEMPLATES":
        warnings.warn(
            "Accessing TEMPLATES directly is deprecated. Use get_template() or list_templates() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return {tid: get_template(tid) for tid, _, _ in list_templates()}

    if name.endswith("_TEMPLATE"):
        template_id = name[:-9].lower()  # Remove '_TEMPLATE' suffix
        template = get_template(template_id)
        if template:
            warnings.warn(
                f"Accessing {name} directly is deprecated. Use get_template('{template_id}') instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return template

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

## Benefits

### 1. **Maintainability**
- Each template is self-contained in its own directory
- Content files are actual markdown/YAML files, not Python strings
- Easy to edit content without touching Python code

### 2. **Extensibility**
- Users can add custom templates by dropping a directory
- Plugin system could register additional templates
- Templates can be distributed as packages

### 3. **Testability**
- Each template module can be tested independently
- Content files can be validated separately
- Mock templates for testing

### 4. **Better Developer Experience**
- Syntax highlighting for markdown/YAML files
- Easy to preview content changes
- Clear separation of concerns

### 5. **Dynamic Variables**
- Can use Jinja2 templates for content files
- Variables like `{date}`, `{title}`, etc. can be rendered at generation time

### 6. **Versioning**
- Templates can have version metadata
- Can support template migrations
- Easier to deprecate old templates

## Migration Strategy

### Phase 1: Create New Structure (No Breaking Changes)
1. Create `bengal/cli/templates/` directory structure
2. Implement base classes and registry
3. Migrate each template to its own module
4. Keep old `site_templates.py` with deprecation warnings
5. All tests should pass with no changes

### Phase 2: Update Consumers
1. Update `bengal/cli/commands/new.py` to use new registry
2. Update `bengal/cli/commands/init.py` to use new registry
3. Add deprecation warnings for direct imports

### Phase 3: Cleanup (Breaking Change)
1. Remove deprecated `site_templates.py` in next major version
2. Update documentation
3. Add migration guide

## Advanced Features (Future)

### 1. Template Inheritance
```python
# bengal/cli/templates/blog-minimal/template.py
from ..blog.template import TEMPLATE as BLOG_TEMPLATE

TEMPLATE = BLOG_TEMPLATE.copy()
TEMPLATE.id = "blog-minimal"
TEMPLATE.name = "Minimal Blog"
TEMPLATE.files = TEMPLATE.files[:2]  # Only index and about
```

### 2. Template Composition
```python
# Mix and match components from different templates
from ..components import header_page, footer_page, contact_form

files = [
    header_page,
    contact_form,
    footer_page
]
```

### 3. User-Defined Templates
```yaml
# ~/.bengal/templates/my-template/template.yaml
id: my-custom
name: My Custom Template
description: My personal site structure

files:
  - path: index.md
    source: index.md
  - path: about.md
    source: about.md

directories:
  - content/blog
  - content/projects
```

### 4. Template Variables
```markdown
<!-- bengal/cli/templates/blog/pages/index.md -->
---
title: {{site.title | default("My Blog")}}
description: Welcome to my blog
---

# Welcome to {{site.title}}

Created on: {{generated_date}}
```

## Implementation Checklist

- [ ] Create `bengal/cli/templates/` package structure
- [ ] Implement `base.py` with core classes
- [ ] Implement `registry.py` with auto-discovery
- [ ] Migrate `default` template
- [ ] Migrate `blog` template
- [ ] Migrate `docs` template
- [ ] Migrate `portfolio` template
- [ ] Migrate `resume` template (with data file support)
- [ ] Migrate `landing` template
- [ ] Add backward compatibility layer in `site_templates.py`
- [ ] Update `new.py` to use new registry
- [ ] Update `init.py` to use new registry
- [ ] Add tests for template registry
- [ ] Add tests for each template
- [ ] Update documentation
- [ ] Add template development guide

## File Size Comparison

### Before
- `site_templates.py`: **1,143 lines** (monolithic)

### After
```
bengal/cli/templates/
  base.py:               ~80 lines
  registry.py:           ~90 lines

  default/template.py:   ~30 lines
  default/pages/*:       ~30 lines

  blog/template.py:      ~40 lines
  blog/pages/*:          ~150 lines

  docs/template.py:      ~50 lines
  docs/pages/*:          ~180 lines

  portfolio/template.py: ~50 lines
  portfolio/pages/*:     ~220 lines

  resume/template.py:    ~40 lines
  resume/pages/*:        ~20 lines
  resume/data/*:         ~250 lines

  landing/template.py:   ~50 lines
  landing/pages/*:       ~200 lines
```

**Total**: Same content, but organized into ~30 smaller, focused files averaging 30-50 lines each.

## Notes

- This refactor maintains 100% backward compatibility in Phase 1 & 2
- Breaking changes only in Phase 3 (major version bump)
- Opens door for community-contributed templates
- Makes Bengal more "themeable" and customizable
- Aligns with modern static site generator architecture (Hugo, Jekyll, etc.)
