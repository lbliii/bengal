# RFC: templit — A Standalone Python 3.14-Native HTML Templating Library

**Status**: Draft
**Created**: 2025-12-18
**Author**: AI Assistant
**Subsystems**: Standalone package + `bengal/rendering/` integration

---

## Executive Summary

This RFC proposes **templit** (pronounced "temp-lit"), a standalone Python 3.14-native HTML templating library built on [PEP 750 Template Strings (t-strings)](https://www.python.org/downloads/release/python-3140/). Designed as a **general-purpose library** that anyone can use, templit will also serve as Bengal's next-generation templating system via an optional dependency.

**Distribution Strategy**:
```bash
# Standalone usage (any Python project)
pip install templit

# Bengal with templit support
pip install bengal[templates]
```

**Key benefits**:
- **Standalone package**: Use in any Python project, not just Bengal
- **Zero dependencies**: Only Python 3.14+ stdlib required
- **Type-safe**: Full IDE autocompletion, refactoring, and mypy support
- **Context-aware escaping**: Automatic HTML/CSS/JS/URL escaping
- **Modern Python**: Async-first, pattern matching, native syntax

---

## Why a Standalone Package?

### Benefits of Independence

1. **Broader Adoption**: Developers can use templit in Flask, FastAPI, Django, or any Python project
2. **Faster Iteration**: templit can evolve independently of Bengal's release cycle
3. **Community Contributions**: Lower barrier for external contributors
4. **Ecosystem Growth**: Other static site generators could adopt templit
5. **Focused Scope**: Clean separation between HTML generation and site building

### Relationship to Bengal

```
┌─────────────────────────────────────────────────────────┐
│                     templit (PyPI)                      │
│  A general-purpose Python 3.14 HTML templating library  │
└─────────────────────────────────────────────────────────┘
                            │
                            │ optional dependency
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    bengal[templates]                    │
│        Bengal SSG with templit integration layer        │
└─────────────────────────────────────────────────────────┘
```

---

## SSG Requirements Analysis (Rethought)

Based on Bengal's 80+ Jinja2 templates, here's a **radically simpler** approach that embraces Python rather than recreating Jinja2.

### Design Philosophy: "It's Just Python"

The best templating solution isn't a new DSL—it's **leveraging Python's existing strengths**:

1. **Functions are templates** - No special "template function" concept needed
2. **Imports are includes** - No `{% include %}`, just `from partials import nav`
3. **Parameters are context** - No global context registry, just function arguments
4. **Modules are namespaces** - No macro libraries, just Python modules

### 1. Template Functions → Just Import Them

**Jinja2 Problem**: Global function registry, magic availability

```jinja2
{{ icon('search', size=16) }}
{{ canonical_url(page.url) }}
```

**Better Solution**: Explicit imports, dependency injection

```python
# bengal/theme/helpers.py
def icon(name: str, size: int = 16) -> HTML:
    return raw(f'<svg class="icon icon-{name}" width="{size}" height="{size}">...</svg>')

def canonical_url(url: str, site: Site) -> str:
    return f"{site.baseurl}{url.rstrip('/')}"

# In your template
from bengal.theme.helpers import icon, canonical_url

def nav_link(item: NavItem, site: Site) -> HTML:
    return a(href=canonical_url(item.url, site))[
        icon(item.icon, size=16),
        item.name
    ]
```

**Why better?**
- IDE understands imports → full autocomplete, go-to-definition
- Explicit dependencies → easier testing, no hidden state
- Type-checked → errors caught before runtime

### 2. Filters → Just Functions (Composition)

**Jinja2 Problem**: Special filter syntax, hard to compose

```jinja2
{{ page.date | dateformat('%B %d, %Y') }}
{{ page.content | strip_html | excerpt(150) }}
```

**Better Solution**: Regular function calls or `>>` composition operator

```python
# Option A: Regular function calls (most explicit)
def article_meta(page: Page) -> HTML:
    return div(class_="meta")[
        time[dateformat(page.date, '%B %d, %Y')],
        p[excerpt(strip_html(page.content), 150)]
    ]

# Option B: Composition operator for pipelines
from templit import F  # Functional composition helper

# F wraps a value for method-style chaining
def article_meta(page: Page) -> HTML:
    return div(class_="meta")[
        time[F(page.date).dateformat('%B %d, %Y').value],
        p[F(page.content).strip_html().excerpt(150).value]
    ]

# Option C: Pipeline operator (Python 3.14 style, if PEP accepted)
# page.date |> dateformat('%B %d, %Y')  # Hypothetical
```

**Recommended**: Option A. It's the most Pythonic—just call functions. Filters are a solution to Jinja2's limited expression syntax, which we don't have.

### 3. Template Inheritance → Higher-Order Functions

**Jinja2 Problem**: `{% extends %}` + `{% block %}` creates implicit coupling

```jinja2
{% extends "base.html" %}
{% block content %}...{% endblock %}
{% block scripts %}...{% endblock %}
```

**Better Solution**: Functions that accept content as parameters

```python
# layouts.py
def base_layout(
    site: Site,
    *,  # Force keyword arguments for clarity
    title: str = "",
    head: HTML | None = None,
    scripts: HTML | None = None,
    content: HTML,
) -> HTML:
    return html[
        doctype(),
        html_elem(lang=site.language)[
            head_elem[
                title_elem[title or site.title],
                link(rel="stylesheet", href=site.asset_url('style.css')),
                head,  # None renders as empty
            ],
            body[
                site_header(site),
                main[content],
                site_footer(site),
                scripts,
            ]
        ]
    ]

# Usage - crystal clear what's happening
def blog_page(page: Page, site: Site) -> HTML:
    return base_layout(
        site,
        title=page.title,
        head=html[meta(name="author", content=page.author)],
        scripts=html[script(src="/js/comments.js")],
        content=html[
            article(class_="blog-post")[
                h1[page.title],
                raw(page.content_html)
            ]
        ]
    )
```

**Why better?**
- All dependencies explicit in function signature
- IDE shows you exactly what a layout accepts
- No inheritance hierarchy to trace
- Easy to test in isolation

### 4. Partials/Includes → Just Functions

**Jinja2 Problem**: String-based includes, unclear dependencies

```jinja2
{% include 'partials/page-hero.html' %}
```

**Better Solution**: Import and call functions

```python
# partials/hero.py
def page_hero(page: Page, variant: str = "default") -> HTML:
    return header(class_=f"hero hero--{variant}")[
        h1[page.title],
        page.description and p(class_="lead")[page.description]
    ]

# page.py
from partials.hero import page_hero

def doc_page(page: Page, site: Site) -> HTML:
    return div[
        page_hero(page, variant="compact"),  # Just a function call
        article[raw(page.content)]
    ]
```

**Literally nothing new to learn** - it's just Python imports.

### 5. Macros → Just Functions (Already Solved)

Macros in Jinja2 exist because you can't define functions in templates. In Python, you just... define functions.

```python
def article_card(article: Page, show_excerpt: bool = True) -> HTML:
    return article_elem(class_="card")[
        h2[a(href=article.url)[article.title]],
        show_excerpt and p[article.excerpt]
    ]

# Usage
div(class_="grid")[
    article_card(post) for post in posts
]
```

### 6. Conditionals → Python's `and`/`or` + `None` Handling

**Jinja2 Problem**: Verbose `{% if %}` blocks

```jinja2
{% if page.date %}<time>{{ page.date }}</time>{% endif %}
```

**Better Solution**: templit ignores `None` and `False` in children

```python
# None and False are filtered out automatically
def meta(page: Page) -> HTML:
    return div(class_="meta")[
        page.date and time[format_date(page.date)],  # Renders nothing if no date
        page.author and span[page.author],
        page.featured and span(class_="badge")["Featured"],
    ]
```

**For complex conditionals**, use helper:

```python
from templit import when

def meta(page: Page) -> HTML:
    return div[
        when(page.date)[time[format_date(page.date)]],
        when(page.draft, then=span["Draft"], else_=span["Published"]),
    ]
```

### 7. Loops → Comprehensions (Already Perfect)

Python comprehensions are already better than Jinja2 loops:

```python
ul(class_="nav")[
    li(class_="active" if item.active else None)[
        a(href=item.url)[item.name]
    ]
    for item in items
    if item.visible  # Built-in filtering!
]
```

### 8. Context/Globals → Dataclass or NamedTuple

**Jinja2 Problem**: Implicit globals like `site`, `page`, `config`

**Better Solution**: Explicit render context

```python
from dataclasses import dataclass

@dataclass
class RenderContext:
    """Everything a template might need."""
    site: Site
    page: Page
    config: Config

    # Computed helpers
    @property
    def asset_url(self) -> Callable[[str], str]:
        return lambda path: f"{self.site.baseurl}/assets/{path}"

    @property
    def canonical_url(self) -> Callable[[str], str]:
        return lambda url: f"{self.site.baseurl}{url}"

# Templates receive context explicitly
def page_template(ctx: RenderContext) -> HTML:
    return base_layout(ctx)[
        article[
            h1[ctx.page.title],
            raw(ctx.page.content)
        ]
    ]
```

**Or even simpler** - just pass what you need:

```python
def page_template(page: Page, site: Site) -> HTML:
    return base_layout(site)[
        article[h1[page.title], raw(page.content)]
    ]
```

### 9. Class Building → `cx()` Helper (Inspired by clsx/classnames)

```python
from templit import cx

def card(page: Page) -> HTML:
    return article(
        class_=cx(
            "card",                           # Always included
            ("card--featured", page.featured),  # Tuple: (class, condition)
            ("card--draft", page.draft),
            {"card--large": page.is_large},   # Dict style also works
        )
    )[...]

# cx() implementation
def cx(*args) -> str:
    """Conditional class builder (like clsx/classnames from JS)."""
    classes = []
    for arg in args:
        if isinstance(arg, str):
            classes.append(arg)
        elif isinstance(arg, tuple) and len(arg) == 2:
            cls, condition = arg
            if condition:
                classes.append(cls)
        elif isinstance(arg, dict):
            for cls, condition in arg.items():
                if condition:
                    classes.append(cls)
    return " ".join(classes) or None
```

### 10. Fragments (Multiple Roots) → Lists

```python
# Just return a list - templit flattens automatically
def meta_tags(page: Page) -> list[HTML]:
    return [
        meta(name="description", content=page.description),
        meta(property="og:title", content=page.title),
        meta(property="og:type", content="article"),
    ]

# Used inline
head[
    title[page.title],
    *meta_tags(page),  # Spread into head children
    link(rel="stylesheet", href="/style.css"),
]
```

---

## Revised Summary: Simplicity Wins

| Jinja2 Concept | templit Approach | Why Better |
|----------------|------------------|------------|
| Template globals | **Python imports** | IDE support, explicit deps |
| Filters | **Function calls** | No new syntax to learn |
| `{% extends %}` | **Function parameters** | Clear contracts, testable |
| `{% block %}` | **Named parameters** | Type-checked, discoverable |
| `{% include %}` | **Function calls** | It's just Python |
| `{% macro %}` | **Functions** | Already perfect |
| `{% if %}` | **`and`/`or` + None filtering** | More concise |
| `{% for %}` | **Comprehensions** | Already perfect |
| Context | **Dataclass or params** | Explicit, type-safe |
| Class building | **`cx()` helper** | Familiar from JS ecosystem |

**The pattern**: Don't invent new concepts. Use Python's existing tools.

---

## Package Design

### Package Name: `templit`

**Why "templit"?**
- **Template + lit**: References both templates and Python's t-string literals
- **Short and memorable**: Easy to type, easy to remember
- **Available**: Not taken on PyPI (as of writing)
- **Neutral**: No tie to Bengal, frameworks, or specific use cases

**Alternative names considered**:
- `thtml` - Too cryptic
- `pyhtml` - Already exists
- `htpy` - Already exists
- `taglib` - Java connotations
- `markuply` - Bit awkward

### Package Structure

```
templit/
├── pyproject.toml
├── README.md
├── LICENSE (MIT)
├── docs/
│   ├── getting-started.md
│   ├── api-reference.md
│   ├── components.md
│   ├── escaping.md
│   └── examples/
└── src/
    └── templit/
        ├── __init__.py        # Public API exports
        ├── py.typed           # PEP 561 marker
        ├── core.py            # HTML class, rendering engine
        ├── elements.py        # Element factories (div, span, etc.)
        ├── components.py      # @component decorator, children()
        ├── contexts.py        # Context-aware escapers (html, css, js, url)
        ├── escaping.py        # Escaping implementations
        ├── types.py           # Type definitions, protocols
        └── _compat.py         # Python version compatibility
```

### pyproject.toml

```toml
[project]
name = "templit"
version = "0.1.0"
description = "A Python 3.14-native HTML templating library using t-strings"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.14"
authors = [
    { name = "Bengal Contributors", email = "..." }
]
keywords = [
    "html",
    "templates",
    "t-strings",
    "pep750",
    "type-safe",
    "components",
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.14",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    "Topic :: Text Processing :: Markup :: HTML",
    "Typing :: Typed",
]

[project.urls]
Homepage = "https://github.com/bengal-ssg/templit"
Documentation = "https://templit.dev"
Repository = "https://github.com/bengal-ssg/templit"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "mypy>=1.10",
    "ruff>=0.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Core API

### Basic Usage

```python
from templit import html, div, h1, p, a

# Simple element
greeting = h1["Hello, World!"]

# Nested elements
card = div(class_="card")[
    h1["Welcome"],
    p["This is a card component."],
    a(href="/about")["Learn more"]
]

# Render to string
print(str(card))
# <div class="card"><h1>Welcome</h1><p>This is a card component.</p><a href="/about">Learn more</a></div>
```

### T-String Integration (Python 3.14+)

```python
from templit import html, t

def greeting(name: str) -> HTML:
    """T-strings enable context-aware escaping."""
    return html[t"<h1>Hello, {name}!</h1>"]
    # name is automatically HTML-escaped

# Malicious input is safely escaped
greeting("<script>alert('xss')</script>")
# → <h1>Hello, &lt;script&gt;alert('xss')&lt;/script&gt;!</h1>
```

### Element Builder

```python
from templit import div, h1, p, span, ul, li, a

def article(title: str, content: str, author: str) -> HTML:
    """Element builder with type-safe attributes."""
    return div(class_="article")[
        h1(class_="article__title")[title],
        div(class_="article__content")[content],
        p(class_="article__meta")[
            "By ",
            span(class_="author")[author]
        ]
    ]

def nav(items: list[NavItem], current: str) -> HTML:
    """Native Python control flow."""
    return ul(class_="nav")[
        li(class_="nav__item" + (" active" if item.slug == current else ""))[
            a(href=item.url)[item.title]
        ]
        for item in items
        if item.visible
    ]
```

### Components

```python
from templit import component, children, HTML, div, h3

@component
def card(title: str, variant: str = "default") -> HTML:
    """Reusable component with slots."""
    return div(class_=f"card card--{variant}")[
        div(class_="card__header")[
            h3[title]
        ],
        div(class_="card__body")[
            children()  # Slot for nested content
        ]
    ]

# Usage with children
card(title="Recent Posts", variant="highlighted")[
    post_list(posts)
]

# Usage without children
card(title="Empty Card")
```

### Context-Aware Escaping

```python
from templit import html, css, js, url, head, style, script, body, a

def page(title: str, theme_color: str, query: str, user_data: dict) -> HTML:
    """Each context has appropriate escaping."""
    return html[
        head[
            title[title],  # HTML-escaped
            style[
                css[t"body {{ background: {theme_color}; }}"]  # CSS-escaped
            ],
            script[
                js[t"const userData = {json.dumps(user_data)};"]  # JS-escaped
            ]
        ],
        body[
            a(href=url[t"/search?q={query}"])["Search"]  # URL-escaped
        ]
    ]
```

### Async Support

```python
from templit import component, HTML, div, img, span
import asyncio

@component
async def user_card(user_id: int) -> HTML:
    """Native async support."""
    user = await fetch_user(user_id)
    return div(class_="user-card")[
        img(src=user.avatar, alt=user.name),
        span[user.name]
    ]

# Parallel rendering
async def user_grid(user_ids: list[int]) -> HTML:
    cards = await asyncio.gather(*[user_card(uid) for uid in user_ids])
    return div(class_="user-grid")[cards]
```

### Raw Content

```python
from templit import html, raw, div

def content_block(html_content: str) -> HTML:
    """Explicit unsafe content marking."""
    return div(class_="content")[
        raw(html_content)  # ⚠️ Not escaped - use only with trusted content
    ]
```

### Slots (Named Children)

```python
from templit import component, children, slot, HTML

@component
def base_layout(title: str = ""):
    """Layout with named slots for head and scripts."""
    return html[
        head[
            title[title] if title else None,
            slot('head'),  # Named slot for custom head content
        ],
        body[
            main[children()],  # Default slot for main content
            slot('scripts'),   # Named slot for custom scripts
        ]
    ]

# Usage with .slots()
def blog_page(page: Page) -> HTML:
    return base_layout(title=page.title).slots(
        head=html[meta(name="author", content=page.author)],
        scripts=html[script(src="/js/blog.js")]
    )[
        article[raw(page.content_html)]
    ]
```

### Filters (Pipeable Transformations)

```python
from templit import pipe, filter

# Built-in filters
from templit.filters import dateformat, time_ago, excerpt, strip_html

def article_meta(page: Page) -> HTML:
    return div(class_="meta")[
        time[pipe(page.date, dateformat, '%B %d, %Y')],
        span[f"{pipe(page.content, strip_html, excerpt, 150)}"],
        span[pipe(page.date, time_ago)]
    ]

# Custom filters
@filter
def reading_time(content: str, wpm: int = 200) -> str:
    words = len(content.split())
    minutes = max(1, round(words / wpm))
    return f"{minutes} min read"

# Use in templates
span[pipe(page.content, reading_time)]
```

### Utility Helpers

```python
from templit import classes, attrs

def card(page: Page) -> HTML:
    return article(
        # Build conditional class string
        class_=classes(
            "card",
            page.featured and "card--featured",
            page.draft and "card--draft",
        ),
        # Build conditional attributes
        **attrs(
            data_id=page.id,
            data_category=page.category if page.category else None,
        )
    )[
        h2[page.title],
        p[page.excerpt]
    ]
```

---

## Bengal Integration Layer

### pyproject.toml (Bengal)

```toml
[project]
name = "bengal"
# ...

[project.optional-dependencies]
templates = ["templit>=0.1.0"]
all = ["templit>=0.1.0", "...other extras..."]
```

### Installation

```bash
# Standard Bengal (Jinja2 only)
pip install bengal

# Bengal with templit support
pip install bengal[templates]

# Or with uv
uv add bengal[templates]
```

### Integration Module (Minimal)

The integration layer is intentionally thin—it just provides Bengal-specific helpers
while letting you use templit directly:

```python
# bengal/rendering/templates.py
"""Bengal helpers for templit templates (optional)."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from templit import HTML
    from bengal.core import Page, Site

# Only import templit if available (optional dependency)
try:
    from templit import html, raw
    from templit.elements import meta, link, title as title_elem
    TEMPLIT_AVAILABLE = True
except ImportError:
    TEMPLIT_AVAILABLE = False


def check_templit() -> None:
    """Raise helpful error if templit not installed."""
    if not TEMPLIT_AVAILABLE:
        raise ImportError(
            "templit is not installed. Install with: pip install bengal[templates]"
        )


# --- Bengal-specific helpers (not magic globals, just functions) ---

def meta_tags(page: "Page") -> "HTML":
    """Generate standard meta tags for a page."""
    check_templit()
    return html[
        meta(charset="utf-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1"),
        title_elem[page.title],
        page.description and meta(name="description", content=page.description),
        page.canonical_url and link(rel="canonical", href=page.canonical_url),
    ]


def stylesheets(site: "Site") -> "HTML":
    """Generate stylesheet links for theme."""
    check_templit()
    return html[
        link(rel="stylesheet", href=url)
        for url in site.theme_stylesheets
    ]


def asset_url(path: str, site: "Site") -> str:
    """Build full URL for a static asset."""
    return f"{site.baseurl.rstrip('/')}/assets/{path.lstrip('/')}"


def canonical_url(path: str, site: "Site") -> str:
    """Build canonical URL for a page."""
    return f"{site.baseurl.rstrip('/')}/{path.lstrip('/')}"
```

**That's it.** No registries, no context managers, no magic. Just functions you import.

### Usage in Bengal Themes

```python
# themes/modern/templates/page.py
"""Page template using templit."""

# Standard templit imports
from templit import html, raw
from templit.elements import (
    doctype, html as html_elem, head, body, main, article, h1,
    header, footer, nav, a, ul, li, div
)

# Bengal helpers (optional, just convenience functions)
from bengal.rendering.templates import meta_tags, stylesheets, asset_url
from bengal.core import Page, Site


def base_layout(
    site: Site,
    *,
    title: str = "",
    content: "HTML",
) -> "HTML":
    """Base HTML structure. Just a function, not magic."""
    return html[
        doctype(),
        html_elem(lang=site.language)[
            head[
                meta_tags(site.current_page),
                stylesheets(site),
            ],
            body[
                site_header(site),
                main[content],
                site_footer(site),
            ]
        ]
    ]


def site_header(site: Site) -> "HTML":
    """Site header navigation."""
    return header(class_="site-header")[
        nav(class_="main-nav")[
            a(href="/", class_="logo")[site.title],
            ul(class_="nav-links")[
                li[a(href=item.url)[item.title]]
                for item in site.navigation
            ]
        ]
    ]


def site_footer(site: Site) -> "HTML":
    """Site footer."""
    return footer(class_="site-footer")[
        f"© {site.copyright_year} {site.author}"
    ]


def page_template(page: Page, site: Site) -> "HTML":
    """Main page template. This is what Bengal calls."""
    return base_layout(
        site,
        title=page.title,
        content=html[
            article(class_="page-content")[
                h1[page.title],
                div(class_="content")[raw(page.content_html)]
            ]
        ]
    )


# That's it. No @component decorators required, no slots,
# no children() magic. Just functions calling functions.
```

### Hybrid Jinja2 + templit (Migration Path)

```python
# Gradual migration: use templit for new components, keep Jinja2 for existing

from templit import html, raw
from templit.elements import header, footer
from bengal.rendering import jinja_env

def hybrid_page(page: Page, site: Site) -> HTML:
    """Mix new templit components with existing Jinja2 templates."""
    return html[
        # New templit header
        site_header(site),

        # Existing Jinja2 content (just render and wrap with raw())
        raw(jinja_env.get_template("content.html").render(page=page)),

        # New templit footer
        site_footer(site),
    ]
```

---

## Implementation Details

### Core Types

```python
# src/templit/types.py
from __future__ import annotations
from typing import Protocol, runtime_checkable, Union, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from string.templatelib import Template

@runtime_checkable
class Renderable(Protocol):
    """Any object that can render to HTML."""
    def __html__(self) -> str: ...

# Content types that can be rendered
HTMLContent = Union[
    str,                      # Plain text (will be escaped)
    "Template",               # T-string (context-aware escaping)
    Renderable,               # Objects with __html__
    Sequence["HTMLContent"],  # Lists/tuples of content
    None,                     # Renders as empty string
]
```

### HTML Class

```python
# src/templit/core.py
from __future__ import annotations
from string.templatelib import Template, Interpolation
from .escaping import escape_html
from .types import HTMLContent, Renderable

class HTML:
    """
    Safe HTML container with builder syntax.

    Usage:
        html[t"<h1>{title}</h1>"]
        html[div(class_="foo")["content"]]
    """

    __slots__ = ("_value",)

    def __init__(self, value: str):
        self._value = value

    def __str__(self) -> str:
        return self._value

    def __html__(self) -> str:
        """Jinja2/Markupsafe compatibility."""
        return self._value

    def __repr__(self) -> str:
        preview = self._value[:50] + "..." if len(self._value) > 50 else self._value
        return f"HTML({preview!r})"

    def __add__(self, other: HTML) -> HTML:
        if isinstance(other, HTML):
            return HTML(self._value + other._value)
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HTML):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    @classmethod
    def __class_getitem__(cls, content: HTMLContent) -> HTML:
        """Enable html[...] syntax."""
        return cls._render(content)

    @classmethod
    def _render(cls, content: HTMLContent) -> HTML:
        """Render any content type to HTML."""
        match content:
            case None:
                return cls("")
            case HTML() as h:
                return h
            case str() as s:
                return cls(escape_html(s))
            case Template() as t:
                return cls._render_template(t)
            case list() | tuple() as seq:
                parts = [cls._render(item)._value for item in seq]
                return cls("".join(parts))
            case _ if isinstance(content, Renderable):
                return cls(content.__html__())
            case _:
                raise TypeError(f"Cannot render {type(content).__name__} to HTML")

    @classmethod
    def _render_template(cls, template: Template) -> HTML:
        """Render a t-string with context-aware escaping."""
        parts: list[str] = []

        for item in template:
            match item:
                case str() as literal:
                    parts.append(literal)
                case Interpolation(value=value, conversion=conv, format_spec=spec):
                    # Apply conversion
                    if conv == "r":
                        value = repr(value)
                    elif conv == "s":
                        value = str(value)
                    elif conv == "a":
                        value = ascii(value)

                    # Apply format spec
                    if spec:
                        value = format(value, spec)

                    # Render and escape
                    rendered = cls._render(value)
                    parts.append(rendered._value)

        return cls("".join(parts))


# Module-level instance for html[...] syntax
html = HTML
```

### Element Factory

```python
# src/templit/elements.py
from __future__ import annotations
from typing import Any
from types import GeneratorType
from .core import HTML, html
from .escaping import escape_attr

class Element:
    """
    HTML element factory with fluent API.

    Usage:
        div(class_="container", id="main")["Content"]
        a(href="/about")["About Us"]
        img(src="/logo.png", alt="Logo")  # void element
    """

    __slots__ = ("_tag", "_attrs", "_void")

    VOID_ELEMENTS = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"
    })

    def __init__(self, tag: str, attrs: dict[str, Any] | None = None):
        self._tag = tag
        self._attrs = attrs or {}
        self._void = tag in self.VOID_ELEMENTS

    def __call__(self, **attrs: Any) -> Element:
        """Set attributes. Trailing underscores stripped for reserved words."""
        clean_attrs = {}
        for key, value in attrs.items():
            if value is None:
                continue
            clean_key = key.rstrip("_")
            clean_attrs[clean_key] = value

        return Element(self._tag, {**self._attrs, **clean_attrs})

    def __getitem__(self, children) -> HTML:
        """Set children and render to HTML."""
        if self._void:
            raise ValueError(f"<{self._tag}> is a void element and cannot have children")

        attr_str = self._render_attrs()

        if isinstance(children, GeneratorType):
            children = list(children)

        if isinstance(children, (list, tuple)):
            content = "".join(html[c]._value for c in children)
        else:
            content = html[children]._value

        return HTML(f"<{self._tag}{attr_str}>{content}</{self._tag}>")

    def __html__(self) -> str:
        """Render element (void or empty)."""
        attr_str = self._render_attrs()
        if self._void:
            return f"<{self._tag}{attr_str}>"
        return f"<{self._tag}{attr_str}></{self._tag}>"

    def _render_attrs(self) -> str:
        if not self._attrs:
            return ""
        parts = []
        for key, value in self._attrs.items():
            if value is True:
                parts.append(key)
            else:
                parts.append(f'{key}="{escape_attr(str(value))}"')
        return " " + " ".join(parts)


# Pre-defined elements
_ELEMENTS = [
    # Document
    "html", "head", "body", "title", "meta", "link", "style", "script",
    # Sections
    "header", "footer", "main", "nav", "aside", "section", "article",
    # Headings
    "h1", "h2", "h3", "h4", "h5", "h6",
    # Grouping
    "div", "p", "pre", "blockquote", "ol", "ul", "li", "dl", "dt", "dd",
    "figure", "figcaption", "hr",
    # Text
    "a", "span", "em", "strong", "small", "s", "cite", "q", "code",
    "sub", "sup", "mark", "time", "abbr",
    # Embedded
    "img", "video", "audio", "source", "iframe", "embed", "object",
    # Tables
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "colgroup", "col",
    # Forms
    "form", "fieldset", "legend", "label", "input", "button", "select",
    "option", "optgroup", "textarea", "datalist", "output", "progress", "meter",
    # Interactive
    "details", "summary", "dialog",
]

_element_cache = {name: Element(name) for name in _ELEMENTS}

# Export common elements directly
div = _element_cache["div"]
span = _element_cache["span"]
a = _element_cache["a"]
p = _element_cache["p"]
h1 = _element_cache["h1"]
h2 = _element_cache["h2"]
h3 = _element_cache["h3"]
h4 = _element_cache["h4"]
h5 = _element_cache["h5"]
h6 = _element_cache["h6"]
ul = _element_cache["ul"]
ol = _element_cache["ol"]
li = _element_cache["li"]
img = _element_cache["img"]
# ... all others exported in __init__.py

def __getattr__(name: str) -> Element:
    """Dynamic element access for any tag name."""
    if name in _element_cache:
        return _element_cache[name]
    if name.startswith("_"):
        raise AttributeError(name)
    return Element(name)  # Custom elements
```

### Component System

```python
# src/templit/components.py
from __future__ import annotations
from typing import Callable, TypeVar, ParamSpec
from contextvars import ContextVar
from functools import wraps
from .core import HTML, html
from .types import HTMLContent

P = ParamSpec("P")

_children_stack: ContextVar[list[HTMLContent]] = ContextVar("children_stack", default=[])

def children() -> HTML:
    """
    Render children passed to a component.

    Usage:
        @component
        def wrapper():
            return div(class_="wrapper")[children()]

        wrapper()["Content here"]
    """
    stack = _children_stack.get()
    if not stack:
        return HTML("")
    return html[stack[-1]]


class Component:
    """Wrapper enabling child content for component functions."""

    __slots__ = ("_func", "_args", "_kwargs")

    def __init__(self, func: Callable[..., HTML], args: tuple, kwargs: dict):
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def __getitem__(self, content: HTMLContent) -> HTML:
        """Render with children."""
        stack = _children_stack.get().copy()
        stack.append(content)
        token = _children_stack.set(stack)
        try:
            return self._func(*self._args, **self._kwargs)
        finally:
            _children_stack.reset(token)

    def __html__(self) -> str:
        """Render without children."""
        return self._func(*self._args, **self._kwargs).__html__()

    def __str__(self) -> str:
        return self.__html__()


def component(func: Callable[P, HTML]) -> Callable[P, Component]:
    """
    Decorator to create a reusable component with optional children.

    Usage:
        @component
        def alert(variant: str = "info") -> HTML:
            return div(class_=f"alert alert--{variant}")[children()]

        # With children
        alert(variant="warning")["Warning message!"]

        # Without children (empty)
        alert()
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Component:
        return Component(func, args, kwargs)

    return wrapper
```

### Escaping Functions

```python
# src/templit/escaping.py
"""Context-aware escaping for XSS prevention."""

import html as html_module
import urllib.parse
import json
import re

def escape_html(value: str) -> str:
    """Escape for HTML text content."""
    return html_module.escape(value, quote=False)

def escape_attr(value: str) -> str:
    """Escape for HTML attribute values."""
    return html_module.escape(value, quote=True)

def escape_css(value: str) -> str:
    """Escape for CSS context."""
    if re.match(r'^[\w\s\-#.,()%]+$', value):
        return value
    return re.sub(r'[^\w\s\-#.,()%]', lambda m: f'\\{ord(m.group()):x}', value)

def escape_js(value: str) -> str:
    """Escape for JavaScript string context."""
    return json.dumps(value)[1:-1]

def escape_url(value: str) -> str:
    """Escape for URL query parameters."""
    return urllib.parse.quote(value, safe='')

def escape_url_path(value: str) -> str:
    """Escape for URL path segments."""
    return urllib.parse.quote(value, safe='/')
```

### Context Processors

```python
# src/templit/contexts.py
"""Context-specific t-string processors."""

from __future__ import annotations
from string.templatelib import Template, Interpolation
from .escaping import escape_css, escape_js, escape_url

class _ContextProcessor:
    """Base for context-specific template processing."""

    _escape_func: Callable[[str], str]

    def __class_getitem__(cls, content: str | Template) -> str:
        if isinstance(content, str):
            return content
        return cls._process(content)

    @classmethod
    def _process(cls, template: Template) -> str:
        parts = []
        for item in template:
            match item:
                case str() as literal:
                    parts.append(literal)
                case Interpolation(value=value):
                    parts.append(cls._escape_func(str(value)))
        return "".join(parts)


class css(_ContextProcessor):
    """CSS-safe t-string processing."""
    _escape_func = staticmethod(escape_css)


class js(_ContextProcessor):
    """JavaScript-safe t-string processing."""
    _escape_func = staticmethod(escape_js)


class url(_ContextProcessor):
    """URL-safe t-string processing."""
    _escape_func = staticmethod(escape_url)
```

### Public API

```python
# src/templit/__init__.py
"""
templit - A Python 3.14-native HTML templating library using t-strings.

Usage:
    from templit import html, div, h1, p, a, component, children

    @component
    def card(title: str) -> HTML:
        return div(class_="card")[
            h1[title],
            div(class_="card__body")[children()]
        ]

    card(title="Hello")[p["World!"]]
"""

from .core import HTML, html
from .components import component, children
from .contexts import css, js, url
from .raw import raw
from .types import Renderable, HTMLContent

# Elements - explicit exports for IDE support
from .elements import (
    # Document
    html as html_elem, head, body, title, meta, link, style, script,
    # Sections
    header, footer, main, nav, aside, section, article,
    # Headings
    h1, h2, h3, h4, h5, h6,
    # Grouping
    div, p, pre, blockquote, ol, ul, li, dl, dt, dd,
    figure, figcaption, hr,
    # Text
    a, span, em, strong, small, s, cite, q, code,
    sub, sup, mark, time, abbr,
    # Embedded
    img, video, audio, source, iframe, embed, object,
    # Tables
    table, thead, tbody, tfoot, tr, th, td, caption, colgroup, col,
    # Forms
    form, fieldset, legend, label, input, button, select,
    option, optgroup, textarea, datalist, output, progress, meter,
    # Interactive
    details, summary, dialog,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "HTML", "html",
    # Components
    "component", "children",
    # Contexts
    "css", "js", "url",
    # Helpers
    "raw",
    # Types
    "Renderable", "HTMLContent",
    # Elements
    "html_elem", "head", "body", "title", "meta", "link", "style", "script",
    "header", "footer", "main", "nav", "aside", "section", "article",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "div", "p", "pre", "blockquote", "ol", "ul", "li", "dl", "dt", "dd",
    "figure", "figcaption", "hr",
    "a", "span", "em", "strong", "small", "s", "cite", "q", "code",
    "sub", "sup", "mark", "time", "abbr",
    "img", "video", "audio", "source", "iframe", "embed", "object",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col",
    "form", "fieldset", "legend", "label", "input", "button", "select",
    "option", "optgroup", "textarea", "datalist", "output", "progress", "meter",
    "details", "summary", "dialog",
    # Version
    "__version__",
]
```

---

## Framework Integrations

### Flask

```python
from flask import Flask
from templit import html, div, h1, p, component, children

app = Flask(__name__)

@component
def layout(title: str):
    return html[
        head[title[title]],
        body[children()]
    ]

@app.route("/")
def index():
    return str(layout(title="Home")[
        div(class_="container")[
            h1["Welcome"],
            p["This is a Flask app using templit."]
        ]
    ])
```

### FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from templit import html, div, h1, ul, li

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index():
    items = await get_items()
    return str(div[
        h1["Items"],
        ul[li[item.name] for item in items]
    ])
```

### Django (Template Tag)

```python
# templatetags/templit_tags.py
from django import template
from django.utils.safestring import mark_safe
from templit import HTML

register = template.Library()

@register.simple_tag
def templit(component_func, *args, **kwargs):
    """Render a templit component in Django templates."""
    result = component_func(*args, **kwargs)
    if isinstance(result, HTML):
        return mark_safe(str(result))
    return result
```

---

## Comparison: templit vs Alternatives

| Feature | templit | Jinja2 | htpy | PyHTML |
|---------|---------|--------|------|--------|
| Python version | 3.14+ | 3.7+ | 3.8+ | 3.6+ |
| T-string support | ✅ Native | ❌ | ❌ | ❌ |
| Type hints | ✅ Full | ❌ | ✅ Partial | ❌ |
| Syntax | Native Python | Custom DSL | Python | Python |
| Auto-escaping | Context-aware | Global | Manual | Manual |
| Components | First-class | Macros | Functions | Functions |
| Async | Native | Extension | ❌ | ❌ |
| Dependencies | Zero | MarkupSafe | None | None |
| IDE support | Native | Plugin | Good | Limited |

---

## Implementation Plan

### Phase 1: templit Core (4-6 weeks)

**Week 1-2: Foundation**
- [ ] Project scaffolding (pyproject.toml, CI/CD)
- [ ] `HTML` class with `__class_getitem__`
- [ ] Basic escaping functions
- [ ] Initial test suite

**Week 3-4: Elements & Components**
- [ ] Element factory with all HTML elements
- [ ] `@component` decorator
- [ ] `children()` function
- [ ] Context processors (css, js, url)

**Week 5-6: Polish**
- [ ] Full type hints (py.typed)
- [ ] Documentation site
- [ ] PyPI release (0.1.0)

### Phase 2: Bengal Integration (2-3 weeks)

- [ ] Add `bengal[templates]` optional dependency
- [ ] Create `bengal.rendering.templit_integration`
- [ ] Bengal-specific components (page_meta, etc.)
- [ ] Hybrid Jinja2/templit support
- [ ] Migrate one default theme template

### Phase 3: Ecosystem (Ongoing)

- [ ] Framework integration examples
- [ ] Community feedback incorporation
- [ ] Performance optimization
- [ ] Additional context processors

---

## Open Questions

### Q1: Repository location?

**Options**:
- A) Monorepo: `bengal/packages/templit/`
- B) Separate repo: `github.com/bengal-ssg/templit`
- C) Separate org: `github.com/templit/templit`

**Recommendation**: Option B - Separate repo under Bengal org. Maintains clear ownership while allowing independent development.

### Q2: Should templit work on Python < 3.14?

**Options**:
- A) 3.14+ only (full t-string support)
- B) 3.10+ with degraded t-string support (f-strings only)
- C) Dual-mode: auto-detect and use best available

**Recommendation**: Option A for initial release. T-strings are the core value proposition. Consider backport library later if demand exists.

### Q3: Package naming for html element conflict?

The `html` builder and `<html>` element share a name.

**Options**:
- A) `html` = builder, `html_elem` = element (current proposal)
- B) `markup` = builder, `html` = element
- C) `h` = builder shorthand, `html` = element

**Recommendation**: Option A. The builder `html[...]` is used more frequently than the `<html>` element.

---

## Success Criteria

### templit (Standalone)

1. **Adoption**: 100+ GitHub stars within 3 months
2. **Quality**: 95%+ test coverage, zero type errors
3. **Performance**: Faster than Jinja2 for equivalent templates
4. **Documentation**: Complete API reference + getting started guide

### Bengal Integration

1. **Seamless**: `pip install bengal[templates]` just works
2. **Migration**: Clear path from Jinja2 to templit
3. **Hybrid**: Jinja2 and templit can coexist
4. **Default**: One default theme template uses templit

---

## References

- [PEP 750: Template String Literals](https://peps.python.org/pep-0750/)
- [Python 3.14.0 Release](https://www.python.org/downloads/release/python-3140/)
- [htpy](https://htpy.dev/) - Similar approach (pre-t-strings)
- [dominate](https://github.com/Knio/dominate) - Python HTML generation
- [MarkupSafe](https://markupsafe.palletsprojects.com/) - Jinja2's escaping library
