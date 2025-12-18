# RFC: Bengal Templates — A Python 3.14-Native Templating System

**Status**: Draft  
**Created**: 2025-12-18  
**Author**: AI Assistant  
**Subsystems**: `bengal/rendering/`, `bengal/themes/`

---

## Executive Summary

This RFC proposes **Bengal Templates**, a modern templating system built on Python 3.14's [PEP 750 Template Strings (t-strings)](https://www.python.org/downloads/release/python-3140/). By leveraging native Python syntax, type safety, and context-aware escaping, Bengal Templates can provide a superior developer experience compared to Jinja2 while eliminating an external dependency and enabling deeper IDE integration.

**Key benefits**:
- **Single language**: No context-switching between Python and Jinja syntax
- **Type-safe**: Full IDE autocompletion, refactoring, and error detection
- **Context-aware escaping**: Automatic HTML/CSS/JS/URL escaping based on context
- **Modern Python**: Async-first, pattern matching, deferred annotations
- **Zero new syntax**: Just Python with a builder API

---

## Problem Statement

### Current State: Jinja2

Bengal currently uses Jinja2 for templating. While Jinja2 is mature and capable, it has fundamental limitations:

1. **Separate DSL**: Jinja2 is a distinct language with its own syntax, requiring developers to context-switch between Python and template code.

2. **Limited Type Safety**: No IDE support for type checking template variables, filter arguments, or macro signatures.

3. **String-Based**: Templates are strings parsed at runtime, making refactoring fragile and errors hard to catch early.

4. **Manual Escaping**: Developers must remember to use `| escape` or `| safe` correctly, leading to XSS vulnerabilities or double-escaping bugs.

5. **Limited Expressions**: Jinja2's expression language is a subset of Python, causing frustration when familiar Python constructs don't work.

6. **External Dependency**: Jinja2 is a large dependency (~500KB) that Bengal must maintain compatibility with.

### Python 3.14 Opportunity

Python 3.14 (released October 2025) introduces [PEP 750: Template String Literals](https://www.python.org/downloads/release/python-3140/):

```python
# Traditional f-string: immediate evaluation, returns str
name = "world"
greeting = f"Hello, {name}!"  # → "Hello, world!"

# T-string: lazy template, returns Template object
template = t"Hello, {name}!"  # → Template(strings=["Hello, ", "!"],
                              #           values=[Interpolation(value="world", ...)])
```

T-strings enable:
- **Inspection before rendering**: See the template structure, not just the result
- **Custom processing**: Apply transformations, escaping, validation
- **Type preservation**: Values retain their types until rendering
- **Composition**: Build complex templates from smaller pieces

Combined with other 3.14 features:
- **PEP 649**: Deferred annotation evaluation (better type hints)
- **PEP 779**: Free-threaded Python (better async/parallel rendering)
- **Experimental JIT**: Significant performance potential

---

## Proposed Solution: Bengal Templates

### Design Goals

1. **Native Python**: Templates are Python functions returning `HTML` objects
2. **Type-Safe**: Full type hints, IDE integration, and mypy support
3. **Context-Aware**: Automatic escaping based on HTML/CSS/JS/URL context
4. **Component-Based**: First-class components with slots and composition
5. **Async-Native**: Built for async rendering from the ground up
6. **Zero Learning Curve**: If you know Python, you know Bengal Templates

### Core API

#### Basic Usage

```python
from bengal.templates import html, t

def greeting(name: str) -> HTML:
    """Simple template with auto-escaping."""
    return html[t"<h1>Hello, {name}!</h1>"]
    # name is automatically HTML-escaped
```

#### Element Builder

```python
from bengal.templates import html, div, h1, p, a, span

def article(title: str, content: str, author: str) -> HTML:
    """Element builder with type-safe attributes."""
    return html[
        div(class_="article")[
            h1(class_="article__title")[title],
            div(class_="article__content")[content],
            p(class_="article__meta")[
                "By ",
                span(class_="author")[author]
            ]
        ]
    ]
```

#### Control Flow (Native Python)

```python
from bengal.templates import html, ul, li, a

def nav(items: list[NavItem], current_slug: str) -> HTML:
    """Native Python control flow."""
    return html[
        ul(class_="nav")[
            li(class_="nav__item" + (" nav__item--active" if item.slug == current_slug else ""))[
                a(href=item.url)[item.title]
            ]
            for item in items
            if item.visible
        ]
    ]
```

#### Components

```python
from bengal.templates import component, children, HTML

@component
def card(title: str, variant: str = "default") -> HTML:
    """Reusable component with slots."""
    return html[
        div(class_=f"card card--{variant}")[
            div(class_="card__header")[
                h3[title]
            ],
            div(class_="card__body")[
                children()  # Slot for nested content
            ]
        ]
    ]

# Usage
def dashboard(posts: list[Post]) -> HTML:
    return html[
        card(title="Recent Posts", variant="highlighted")[
            post_list(posts)
        ]
    ]
```

#### Context-Aware Escaping

```python
from bengal.templates import html, css, js, url

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

#### Async Rendering

```python
from bengal.templates import html, await_

@component
async def user_card(user_id: int) -> HTML:
    """Native async support."""
    user = await fetch_user(user_id)
    return html[
        div(class_="user-card")[
            img(src=user.avatar, alt=user.name),
            span[user.name]
        ]
    ]

# Parallel rendering
async def user_grid(user_ids: list[int]) -> HTML:
    cards = await asyncio.gather(*[user_card(uid) for uid in user_ids])
    return html[
        div(class_="user-grid")[cards]
    ]
```

#### Pattern Matching

```python
from bengal.templates import html, span
from bengal.core import PageStatus

def status_badge(status: PageStatus) -> HTML:
    """Python 3.10+ pattern matching."""
    match status:
        case PageStatus.DRAFT:
            return html[span(class_="badge badge--draft")["Draft"]]
        case PageStatus.PUBLISHED:
            return html[span(class_="badge badge--published")["Published"]]
        case PageStatus.ARCHIVED:
            return html[span(class_="badge badge--archived")["Archived"]]
        case _:
            return html[span(class_="badge")["Unknown"]]
```

#### Raw/Unsafe Content

```python
from bengal.templates import html, raw

def content_block(page: Page) -> HTML:
    """Explicit unsafe content marking."""
    return html[
        article[
            h1[page.title],  # Escaped
            div(class_="content")[
                raw(page.content_html)  # Explicit: not escaped
            ]
        ]
    ]
```

---

## Implementation Architecture

### Module Structure

```
bengal/templates/
├── __init__.py          # Public API exports
├── core.py              # HTML class, rendering engine
├── elements.py          # Element factories (div, span, etc.)
├── components.py        # @component decorator, children()
├── contexts.py          # Context-aware escapers (html, css, js, url)
├── escaping.py          # Escaping implementations
├── types.py             # Type definitions, protocols
└── compat.py            # Jinja2 interop layer
```

### Core Types

```python
# bengal/templates/types.py
from __future__ import annotations
from typing import Protocol, runtime_checkable, Union, Sequence
from string.templatelib import Template

@runtime_checkable
class Renderable(Protocol):
    """Any object that can render to HTML."""
    def __html__(self) -> str: ...

# Content types
HTMLContent = Union[
    str,                    # Plain text (will be escaped)
    Template,               # T-string (context-aware escaping)
    Renderable,             # Objects with __html__
    Sequence["HTMLContent"], # Lists/tuples of content
    None,                   # Renders as empty string
]
```

### HTML Class

```python
# bengal/templates/core.py
from __future__ import annotations
from string.templatelib import Template, Interpolation
from .escaping import escape_html, escape_attr
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
        return self._value

    def __repr__(self) -> str:
        preview = self._value[:50] + "..." if len(self._value) > 50 else self._value
        return f"HTML({preview!r})"

    def __add__(self, other: HTML) -> HTML:
        if isinstance(other, HTML):
            return HTML(self._value + other._value)
        return NotImplemented

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
        """
        Render a t-string with context-aware escaping.

        Literal strings pass through unchanged.
        Interpolated values are HTML-escaped.
        """
        parts: list[str] = []

        for item in template:
            match item:
                case str() as literal:
                    # Literal HTML passes through
                    parts.append(literal)
                case Interpolation(value=value, conversion=conv, format_spec=spec):
                    # Apply conversion if specified
                    if conv == "r":
                        value = repr(value)
                    elif conv == "s":
                        value = str(value)
                    elif conv == "a":
                        value = ascii(value)

                    # Apply format spec if specified
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
# bengal/templates/elements.py
from __future__ import annotations
from typing import Any, overload
from types import GeneratorType
from .core import HTML, html
from .escaping import escape_attr

class Element:
    """
    HTML element factory with fluent API.

    Usage:
        div(class_="container", id="main")["Content"]
        a(href="/about")["About Us"]
    """

    __slots__ = ("_tag", "_attrs", "_void")

    # Void elements (self-closing, no children)
    VOID_ELEMENTS = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"
    })

    def __init__(self, tag: str, attrs: dict[str, Any] | None = None):
        self._tag = tag
        self._attrs = attrs or {}
        self._void = tag in self.VOID_ELEMENTS

    def __call__(self, **attrs: Any) -> Element:
        """
        Set attributes. Trailing underscores are stripped (for reserved words).
        None values are omitted. True renders as boolean attribute.

        Examples:
            div(class_="foo")      → <div class="foo">
            input(disabled=True)   → <input disabled>
            div(hidden=None)       → <div>
        """
        clean_attrs = {}
        for key, value in attrs.items():
            if value is None:
                continue
            # Strip trailing underscore (class_, for_, type_, etc.)
            clean_key = key.rstrip("_")
            clean_attrs[clean_key] = value

        return Element(self._tag, {**self._attrs, **clean_attrs})

    def __getitem__(self, children) -> HTML:
        """
        Set children and render to HTML.

        Examples:
            div["Hello"]
            ul[li["Item 1"], li["Item 2"]]
            div[item for item in items]
        """
        if self._void:
            raise ValueError(f"<{self._tag}> is a void element and cannot have children")

        # Build attribute string
        attr_parts = []
        for key, value in self._attrs.items():
            if value is True:
                attr_parts.append(key)  # Boolean attribute
            else:
                attr_parts.append(f'{key}="{escape_attr(str(value))}"')

        attr_str = " " + " ".join(attr_parts) if attr_parts else ""

        # Render children
        if isinstance(children, GeneratorType):
            children = list(children)

        if isinstance(children, (list, tuple)):
            content = "".join(html[c]._value for c in children)
        else:
            content = html[children]._value

        return HTML(f"<{self._tag}{attr_str}>{content}</{self._tag}>")

    def __html__(self) -> str:
        """Render void element or element with no children."""
        attr_parts = []
        for key, value in self._attrs.items():
            if value is True:
                attr_parts.append(key)
            else:
                attr_parts.append(f'{key}="{escape_attr(str(value))}"')

        attr_str = " " + " ".join(attr_parts) if attr_parts else ""

        if self._void:
            return f"<{self._tag}{attr_str}>"
        else:
            return f"<{self._tag}{attr_str}></{self._tag}>"


# Generate standard HTML elements
_STANDARD_ELEMENTS = [
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
    "option", "optgroup", "textarea", "datalist", "output", "progress",
    "meter",
    # Interactive
    "details", "summary", "dialog",
]

# Create element instances
def _create_elements() -> dict[str, Element]:
    return {name: Element(name) for name in _STANDARD_ELEMENTS}

_elements = _create_elements()

# Export as module attributes
div = _elements["div"]
span = _elements["span"]
a = _elements["a"]
p = _elements["p"]
h1 = _elements["h1"]
h2 = _elements["h2"]
h3 = _elements["h3"]
h4 = _elements["h4"]
h5 = _elements["h5"]
h6 = _elements["h6"]
ul = _elements["ul"]
ol = _elements["ol"]
li = _elements["li"]
img = _elements["img"]
# ... etc.

def __getattr__(name: str) -> Element:
    """Allow access to any element by name."""
    if name in _elements:
        return _elements[name]
    if name.startswith("_"):
        raise AttributeError(name)
    # Create custom element on demand
    return Element(name)
```

### Escaping

```python
# bengal/templates/escaping.py
"""Context-aware escaping functions."""

import html as html_module
import urllib.parse
import json
import re

def escape_html(value: str) -> str:
    """Escape for HTML text content."""
    return html_module.escape(value, quote=False)

def escape_attr(value: str) -> str:
    """Escape for HTML attribute values (assumes double quotes)."""
    return html_module.escape(value, quote=True)

def escape_css(value: str) -> str:
    """
    Escape for CSS context.
    Prevents CSS injection attacks.
    """
    # Remove potentially dangerous characters
    # Allow alphanumeric, hyphens, underscores, spaces, and common CSS chars
    if not re.match(r'^[\w\s\-#.,()%]+$', value):
        # Escape non-safe characters
        return re.sub(r'[^\w\s\-#.,()%]', lambda m: f'\\{ord(m.group()):x}', value)
    return value

def escape_js(value: str) -> str:
    """
    Escape for JavaScript string context.
    Prevents XSS via script injection.
    """
    # Use JSON encoding which handles all escaping
    return json.dumps(value)[1:-1]  # Strip quotes

def escape_url(value: str) -> str:
    """Escape for URL query parameters."""
    return urllib.parse.quote(value, safe='')

def escape_url_path(value: str) -> str:
    """Escape for URL path segments."""
    return urllib.parse.quote(value, safe='/')
```

### Context Managers

```python
# bengal/templates/contexts.py
"""Context-specific template processors."""

from __future__ import annotations
from string.templatelib import Template, Interpolation
from .escaping import escape_css, escape_js, escape_url
from .core import HTML

class ContextProcessor:
    """Base class for context-specific template processing."""

    def __class_getitem__(cls, content: str | Template) -> str:
        if isinstance(content, str):
            return content
        return cls._process_template(content)

    @classmethod
    def _process_template(cls, template: Template) -> str:
        raise NotImplementedError


class CSSContext(ContextProcessor):
    """CSS-safe template processing."""

    @classmethod
    def _process_template(cls, template: Template) -> str:
        parts = []
        for item in template:
            match item:
                case str() as literal:
                    parts.append(literal)
                case Interpolation(value=value):
                    parts.append(escape_css(str(value)))
        return "".join(parts)


class JSContext(ContextProcessor):
    """JavaScript-safe template processing."""

    @classmethod
    def _process_template(cls, template: Template) -> str:
        parts = []
        for item in template:
            match item:
                case str() as literal:
                    parts.append(literal)
                case Interpolation(value=value):
                    parts.append(escape_js(str(value)))
        return "".join(parts)


class URLContext(ContextProcessor):
    """URL-safe template processing."""

    @classmethod
    def _process_template(cls, template: Template) -> str:
        parts = []
        for item in template:
            match item:
                case str() as literal:
                    parts.append(literal)
                case Interpolation(value=value):
                    parts.append(escape_url(str(value)))
        return "".join(parts)


# Public instances
css = CSSContext
js = JSContext
url = URLContext
```

### Components

```python
# bengal/templates/components.py
"""Component system for reusable templates."""

from __future__ import annotations
from typing import Callable, TypeVar, ParamSpec, Any
from contextvars import ContextVar
from functools import wraps
from .core import HTML, html
from .types import HTMLContent

P = ParamSpec("P")
T = TypeVar("T")

# Context variable for tracking children during rendering
_children_stack: ContextVar[list[HTMLContent]] = ContextVar("children_stack", default=[])

def children() -> HTML:
    """
    Render the children passed to a component.

    Usage:
        @component
        def card(title: str):
            return html[
                div(class_="card")[
                    h3[title],
                    div(class_="card__body")[
                        children()
                    ]
                ]
            ]
    """
    stack = _children_stack.get()
    if not stack:
        return HTML("")
    return html[stack[-1]]


class Component:
    """
    Wrapper for component functions that enables child content.

    Created by @component decorator.
    """

    def __init__(self, func: Callable[P, HTML], args: tuple, kwargs: dict):
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def __getitem__(self, content: HTMLContent) -> HTML:
        """Render component with children."""
        stack = _children_stack.get().copy()
        stack.append(content)
        token = _children_stack.set(stack)
        try:
            return self._func(*self._args, **self._kwargs)
        finally:
            _children_stack.reset(token)

    def __html__(self) -> str:
        """Render component without children."""
        return self._func(*self._args, **self._kwargs).__html__()


def component(func: Callable[P, HTML]) -> Callable[P, Component]:
    """
    Decorator to create a reusable component.

    Components can accept children via the children() function.

    Usage:
        @component
        def alert(variant: str = "info"):
            return html[
                div(class_=f"alert alert--{variant}")[
                    children()
                ]
            ]

        # Use with children
        alert(variant="warning")["This is a warning!"]

        # Use without children
        alert(variant="success")
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Component:
        return Component(func, args, kwargs)

    return wrapper
```

### Raw Content Helper

```python
# bengal/templates/raw.py
"""Helper for including raw (unescaped) HTML content."""

from .core import HTML

def raw(content: str) -> HTML:
    """
    Mark content as raw HTML that should not be escaped.

    ⚠️ SECURITY WARNING: Only use with trusted content!

    Usage:
        from bengal.templates import html, raw

        def content_block(page: Page) -> HTML:
            return html[
                div(class_="content")[
                    raw(page.content_html)  # Already-rendered HTML
                ]
            ]
    """
    return HTML(content)
```

---

## Migration Strategy

### Phase 1: Parallel Systems (v0.x → v1.0)

Both Jinja2 and Bengal Templates coexist. Templates can be written in either system.

```python
# Jinja2 (existing)
def render_page_jinja(page: Page, site: Site) -> str:
    return jinja_env.get_template("page.html").render(page=page, site=site)

# Bengal Templates (new)
def render_page_bengal(page: Page, site: Site) -> HTML:
    return base_layout(site)[
        article_component(page)
    ]
```

### Phase 2: Interoperability (v1.0 → v1.x)

Bengal Templates can include Jinja2 output and vice versa.

```python
from bengal.templates import html, raw
from bengal.templates.compat import jinja_include

def hybrid_page(page: Page, site: Site) -> HTML:
    return html[
        header_component(site),  # Bengal Template
        raw(jinja_include("legacy/content.html", page=page)),  # Jinja2
        footer_component(site),  # Bengal Template
    ]
```

### Phase 3: Full Migration (v2.0+)

Jinja2 becomes optional/deprecated. Default themes ship with Bengal Templates.

```python
# Bengal Templates as the standard
def page_template(ctx: RenderContext) -> HTML:
    return html[
        doctype(),
        html(lang=ctx.site.language)[
            head_component(ctx),
            body[
                header_component(ctx),
                main[
                    ctx.page.render()  # Page content via Bengal Templates
                ],
                footer_component(ctx)
            ]
        ]
    ]
```

---

## Comparison: Jinja2 vs Bengal Templates

| Aspect | Jinja2 | Bengal Templates |
|--------|--------|------------------|
| **Syntax** | Custom DSL | Native Python |
| **Learning curve** | New syntax to learn | Just Python |
| **Type safety** | None | Full type hints |
| **IDE support** | Requires plugins | Native |
| **Autocompletion** | Limited | Full |
| **Refactoring** | Fragile | Standard Python |
| **Escaping** | Manual (`\| escape`, `\| safe`) | Context-aware automatic |
| **Control flow** | `{% for %}`, `{% if %}` | `for`, `if`, `match` |
| **Components** | Macros + includes | First-class `@component` |
| **Async** | Limited (extension) | Native |
| **Debugging** | Template errors | Python tracebacks |
| **Performance** | Compiled templates | JIT potential (3.14) |
| **Dependency** | ~500KB external | Zero (stdlib) |

### Code Comparison

**Navigation Component**

Jinja2:
```jinja2
<nav class="main-nav">
  <ul>
    {% for item in nav_items %}
      {% if item.visible %}
        <li class="nav__item{% if item.slug == current %} nav__item--active{% endif %}">
          <a href="{{ item.url | escape }}">{{ item.title | escape }}</a>
        </li>
      {% endif %}
    {% endfor %}
  </ul>
</nav>
```

Bengal Templates:
```python
def nav(items: list[NavItem], current: str) -> HTML:
    return html[
        nav(class_="main-nav")[
            ul[
                li(class_=f"nav__item{' nav__item--active' if item.slug == current else ''}")[
                    a(href=item.url)[item.title]
                ]
                for item in items
                if item.visible
            ]
        ]
    ]
```

**Blog Post Card**

Jinja2:
```jinja2
{% macro post_card(post, show_excerpt=true) %}
<article class="post-card">
  <h2 class="post-card__title">
    <a href="{{ post.url | escape }}">{{ post.title | escape }}</a>
  </h2>
  {% if show_excerpt and post.excerpt %}
    <p class="post-card__excerpt">{{ post.excerpt | escape }}</p>
  {% endif %}
  <footer class="post-card__meta">
    <time datetime="{{ post.date.isoformat() }}">
      {{ post.date.strftime('%B %d, %Y') }}
    </time>
  </footer>
</article>
{% endmacro %}
```

Bengal Templates:
```python
@component
def post_card(post: Post, show_excerpt: bool = True) -> HTML:
    return html[
        article(class_="post-card")[
            h2(class_="post-card__title")[
                a(href=post.url)[post.title]
            ],
            p(class_="post-card__excerpt")[post.excerpt]
                if show_excerpt and post.excerpt else None,
            footer(class_="post-card__meta")[
                time(datetime=post.date.isoformat())[
                    post.date.strftime("%B %d, %Y")
                ]
            ]
        ]
    ]
```

---

## Performance Considerations

### Advantages

1. **No Template Parsing**: Templates are compiled Python, no runtime parsing
2. **JIT Optimization**: Python 3.14's experimental JIT can optimize hot paths
3. **Type Specialization**: Type hints enable better optimization
4. **Reduced Allocations**: Builder pattern can minimize string allocations

### Benchmarks (Projected)

| Operation | Jinja2 | Bengal Templates | Improvement |
|-----------|--------|------------------|-------------|
| Simple render | 100μs | ~60μs | ~40% faster |
| Complex page | 500μs | ~300μs | ~40% faster |
| Memory per render | 50KB | ~30KB | ~40% less |

*Note: Actual benchmarks needed once implemented.*

### Optimization Strategies

1. **String interning**: Reuse common attribute strings
2. **Element caching**: Cache Element instances
3. **Lazy rendering**: Defer rendering until needed
4. **Streaming**: Support incremental output for large pages

---

## Security Analysis

### XSS Prevention

Bengal Templates provide **defense in depth**:

1. **Default escaping**: All interpolated values are escaped by default
2. **Context-aware**: Escaping adapts to HTML/CSS/JS/URL context
3. **Explicit unsafe**: `raw()` requires explicit opt-in
4. **Type safety**: IDE catches many issues at write-time

### Comparison to Jinja2

| Risk | Jinja2 | Bengal Templates |
|------|--------|------------------|
| Forgetting to escape | Common (must use `\| escape`) | Impossible (default) |
| Double escaping | Possible | Prevented by `HTML` type |
| Wrong context escaping | Manual | Automatic |
| Unsafe content | `\| safe` (easy to misuse) | `raw()` (explicit) |

---

## Open Questions

### Q1: Should we support JSX-like syntax?

```python
# Option A: Current proposal (element builder)
div(class_="foo")[span["Hello"]]

# Option B: JSX-inspired (hypothetical)
<div class="foo"><span>Hello</span></div>  # Not valid Python

# Option C: Tagged template alternative
html`<div class="foo"><span>Hello</span></div>`
```

**Recommendation**: Option A (element builder) keeps everything as valid Python.

### Q2: How to handle fragments (multiple root elements)?

```python
# Option A: List
html[[div["One"], div["Two"]]]

# Option B: Fragment helper
html[fragment[div["One"], div["Two"]]]

# Option C: Automatic flattening
html[div["One"], div["Two"]]  # Multiple args
```

**Recommendation**: Option A (lists) is most Pythonic.

### Q3: Should template functions return `HTML` or `str`?

```python
# Option A: Return HTML (proposed)
def greeting(name: str) -> HTML:
    return html[h1[f"Hello, {name}!"]]

# Option B: Return str
def greeting(name: str) -> str:
    return str(html[h1[f"Hello, {name}!"]])
```

**Recommendation**: Option A maintains type safety and enables composition.

### Q4: What about template inheritance?

Jinja2 has `{% extends %}` and `{% block %}`. Bengal Templates can use:

```python
# Composition (recommended)
def base_layout(site: Site):
    @component
    def layout():
        return html[
            doctype(),
            html(lang=site.language)[
                head_component(site),
                body[children()]
            ]
        ]
    return layout

# Usage
def page(ctx: RenderContext) -> HTML:
    return base_layout(ctx.site)[
        article[ctx.page.content]
    ]
```

**Recommendation**: Composition over inheritance. More explicit and type-safe.

---

## Implementation Plan

### Phase 1: Core (2-3 weeks)
- [ ] `HTML` class with `__class_getitem__`
- [ ] T-string rendering with HTML escaping
- [ ] Element factory with attribute handling
- [ ] Basic escaping functions

### Phase 2: Components (1-2 weeks)
- [ ] `@component` decorator
- [ ] `children()` context function
- [ ] Slot system for named children

### Phase 3: Contexts (1 week)
- [ ] CSS context escaping
- [ ] JS context escaping
- [ ] URL context escaping

### Phase 4: Integration (2-3 weeks)
- [ ] Bengal render context integration
- [ ] Jinja2 interop layer
- [ ] Default theme migration (one template)

### Phase 5: Documentation (1 week)
- [ ] API reference
- [ ] Migration guide
- [ ] Examples

### Phase 6: Optimization (Ongoing)
- [ ] Benchmarking suite
- [ ] Performance profiling
- [ ] JIT exploration

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Python 3.14 not adopted | High | Keep Jinja2 as fallback, design for graceful degradation |
| Performance regression | Medium | Benchmark early and often, optimize hot paths |
| Migration complexity | Medium | Provide interop layer, migrate incrementally |
| Learning curve | Low | Syntax is just Python, provide examples |
| T-string edge cases | Medium | Thorough testing, fallback to f-strings where needed |

---

## Success Criteria

1. **Type Safety**: Zero template-related runtime errors that could be caught by type checker
2. **Performance**: Equal or better than Jinja2 for common operations
3. **Migration**: Smooth path from Jinja2 with interop layer
4. **Adoption**: Default theme fully converted to Bengal Templates
5. **Developer Experience**: Positive feedback on IDE support and debugging

---

## References

- [PEP 750: Template String Literals](https://peps.python.org/pep-0750/)
- [Python 3.14.0 Release](https://www.python.org/downloads/release/python-3140/)
- [PEP 649: Deferred Evaluation of Annotations](https://peps.python.org/pep-0649/)
- [PEP 779: Free-threaded Python](https://peps.python.org/pep-0779/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [htpy](https://htpy.dev/) - Similar approach (pre-t-strings)
- [PyHTML](https://github.com/cenkalti/pyhtml) - Early Python HTML builder

---

## Appendix: Full API Reference

```python
# bengal/templates/__init__.py

# Core
from .core import HTML, html

# Elements (all standard HTML elements)
from .elements import (
    div, span, a, p, h1, h2, h3, h4, h5, h6,
    ul, ol, li, dl, dt, dd,
    table, thead, tbody, tr, th, td,
    form, input, button, select, option, textarea, label,
    img, video, audio, source,
    header, footer, main, nav, aside, section, article,
    # ... all standard elements
)

# Components
from .components import component, children

# Contexts
from .contexts import css, js, url

# Helpers
from .raw import raw

# Types
from .types import HTML, Renderable, HTMLContent

__all__ = [
    # Core
    "HTML", "html",
    # Elements
    "div", "span", "a", "p", "h1", "h2", "h3", "h4", "h5", "h6",
    # ... etc
    # Components
    "component", "children",
    # Contexts  
    "css", "js", "url",
    # Helpers
    "raw",
    # Types
    "Renderable", "HTMLContent",
]
```
