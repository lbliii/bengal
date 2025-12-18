#!/usr/bin/env python3
"""
patitas prototype - Pythonic HTML templating

A minimal implementation to validate the "just Python" design philosophy.
Requires Python 3.10+ (3.14 for full t-string support).

Usage:
    python prototypes/patitas_prototype.py
"""

from __future__ import annotations

import html as html_module
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Type alias defined here for type checkers, actual runtime check below
    HTMLContent = str | "HTML" | "Element" | Sequence["HTMLContent"] | None | bool


# =============================================================================
# Core: HTML Container
# =============================================================================


@dataclass(slots=True)
class HTML:
    """
    Safe HTML container. Content is already escaped or trusted.

    Usage:
        html[div["Hello"]]
        html[t"<h1>{title}</h1>"]  # With Python 3.14 t-strings
    """

    _value: str

    def __str__(self) -> str:
        return self._value

    def __html__(self) -> str:
        """Jinja2/MarkupSafe compatibility."""
        return self._value

    def __repr__(self) -> str:
        preview = self._value[:50] + "..." if len(self._value) > 50 else self._value
        return f"HTML({preview!r})"

    def __add__(self, other: HTML) -> HTML:
        if isinstance(other, HTML):
            return HTML(self._value + other._value)
        return NotImplemented

    def __bool__(self) -> bool:
        return bool(self._value)

    @classmethod
    def __class_getitem__(cls, content: HTMLContent) -> HTML:
        """Enable html[...] syntax."""
        return cls(_render(content))


def _render(content: HTMLContent) -> str:
    """Render any content type to an HTML string."""
    match content:
        case None | False:
            return ""
        case True:
            return ""  # True alone renders nothing (used in conditionals)
        case HTML() as h:
            return h._value
        case Element() as el:
            return el._render()
        case str() as s:
            return _escape_html(s)
        case list() | tuple() as seq:
            return "".join(_render(item) for item in seq)
        case _:
            # Try __html__ protocol
            if hasattr(content, "__html__"):
                return content.__html__()
            raise TypeError(f"Cannot render {type(content).__name__} to HTML")


def _escape_html(value: str) -> str:
    """Escape HTML special characters."""
    return html_module.escape(value, quote=False)


def _escape_attr(value: str) -> str:
    """Escape HTML attribute values."""
    return html_module.escape(value, quote=True)


# Module-level instance for html[...] syntax
html = HTML


# =============================================================================
# Elements: Tag Factories
# =============================================================================

# Void elements (self-closing, no children)
VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


@dataclass
class Element:
    """
    HTML element with attributes and children.

    Usage:
        div(class_="card")["content"]
        a(href="/home")["Home"]
        img(src="photo.jpg", alt="A photo")  # Void element, no children
    """

    tag: str
    attrs: dict[str, Any]
    children: list[HTMLContent]

    def __getitem__(self, content: HTMLContent) -> Element:
        """Add children: div["content"] or div[child1, child2]."""
        if self.tag in VOID_ELEMENTS:
            raise TypeError(f"<{self.tag}> is a void element and cannot have children")

        if isinstance(content, tuple):
            # div[child1, child2] - multiple children
            self.children.extend(content)
        else:
            self.children.append(content)
        return self

    def _render(self) -> str:
        """Render element to HTML string."""
        # Build attributes
        attr_parts = []
        for key, value in self.attrs.items():
            if value is None or value is False:
                continue  # Skip None/False attributes
            if value is True:
                attr_parts.append(key)  # Boolean attribute: <input disabled>
            else:
                # Convert class_ to class, for_ to for, etc.
                attr_name = key.rstrip("_").replace("_", "-")
                attr_parts.append(f'{attr_name}="{_escape_attr(str(value))}"')

        # Build tag
        attrs_str = " " + " ".join(attr_parts) if attr_parts else ""

        if self.tag in VOID_ELEMENTS:
            return f"<{self.tag}{attrs_str}>"

        # Render children
        children_html = "".join(_render(child) for child in self.children)
        return f"<{self.tag}{attrs_str}>{children_html}</{self.tag}>"

    def __html__(self) -> str:
        return self._render()

    def __str__(self) -> str:
        return self._render()


class ElementFactory:
    """Factory for creating elements of a specific tag."""

    __slots__ = ("tag",)

    def __init__(self, tag: str):
        self.tag = tag

    def __call__(self, **attrs: Any) -> Element:
        """Create element with attributes: div(class_="card")"""
        return Element(self.tag, attrs, [])

    def __getitem__(self, content: HTMLContent) -> Element:
        """Create element with children directly: div["content"]"""
        el = Element(self.tag, {}, [])
        return el[content]

    def __repr__(self) -> str:
        return f"<{self.tag}>"


# Create element factories for common tags
# Document
html_elem = ElementFactory("html")
head = ElementFactory("head")
body = ElementFactory("body")
title = ElementFactory("title")
meta = ElementFactory("meta")
link = ElementFactory("link")
style = ElementFactory("style")
script = ElementFactory("script")

# Sections
header = ElementFactory("header")
footer = ElementFactory("footer")
main = ElementFactory("main")
nav = ElementFactory("nav")
aside = ElementFactory("aside")
section = ElementFactory("section")
article = ElementFactory("article")

# Headings
h1 = ElementFactory("h1")
h2 = ElementFactory("h2")
h3 = ElementFactory("h3")
h4 = ElementFactory("h4")
h5 = ElementFactory("h5")
h6 = ElementFactory("h6")

# Grouping
div = ElementFactory("div")
p = ElementFactory("p")
pre = ElementFactory("pre")
blockquote = ElementFactory("blockquote")
ol = ElementFactory("ol")
ul = ElementFactory("ul")
li = ElementFactory("li")
hr = ElementFactory("hr")

# Text
a = ElementFactory("a")
span = ElementFactory("span")
em = ElementFactory("em")
strong = ElementFactory("strong")
small = ElementFactory("small")
code = ElementFactory("code")
time_elem = ElementFactory("time")
br = ElementFactory("br")

# Embedded
img = ElementFactory("img")
video = ElementFactory("video")
audio = ElementFactory("audio")
source = ElementFactory("source")
iframe = ElementFactory("iframe")

# Tables
table = ElementFactory("table")
thead = ElementFactory("thead")
tbody = ElementFactory("tbody")
tr = ElementFactory("tr")
th = ElementFactory("th")
td = ElementFactory("td")

# Forms
form = ElementFactory("form")
label = ElementFactory("label")
input_ = ElementFactory("input")  # input is a Python builtin
button = ElementFactory("button")
select = ElementFactory("select")
option = ElementFactory("option")
textarea = ElementFactory("textarea")

# Interactive
details = ElementFactory("details")
summary = ElementFactory("summary")


# =============================================================================
# Utilities
# =============================================================================


def raw(content: str) -> HTML:
    """
    Mark content as already-safe HTML (bypass escaping).

    ⚠️ Only use with trusted content!

    Usage:
        raw("<strong>Already escaped</strong>")
        raw(markdown_to_html(page.content))
    """
    return HTML(content)


def doctype() -> HTML:
    """Generate HTML5 doctype."""
    return HTML("<!DOCTYPE html>")


def cx(*args: str | tuple[str, bool] | dict[str, bool] | None) -> str | None:
    """
    Build conditional class string (like clsx/classnames from JS).

    Usage:
        cx("card", ("card--featured", is_featured), ("card--draft", is_draft))
        cx("btn", {"btn-primary": primary, "btn-large": large})
    """
    classes: list[str] = []
    for arg in args:
        match arg:
            case str() as s:
                classes.append(s)
            case (cls, True):
                classes.append(cls)
            case (_, False) | None:
                pass
            case dict() as d:
                classes.extend(k for k, v in d.items() if v)
    return " ".join(classes) if classes else None


# =============================================================================
# Demo / Tests
# =============================================================================


def demo():
    """Demonstrate patitas features."""

    print("=" * 60)
    print("patitas prototype demo")
    print("=" * 60)

    # 1. Basic elements
    print("\n1. Basic elements:")
    result = div(class_="container")[
        h1["Hello, World!"],
        p["This is a paragraph."],
    ]
    print(result)

    # 2. Nested structure
    print("\n2. Nested structure:")
    result = html[
        doctype(),
        html_elem(lang="en")[
            head[
                title["My Page"],
                meta(charset="utf-8"),
                link(rel="stylesheet", href="/style.css"),
            ],
            body[
                header[nav[a(href="/")["Home"]]],
                main[
                    article[
                        h1["Article Title"],
                        p["Article content goes here."],
                    ]
                ],
                footer["© 2025"],
            ],
        ],
    ]
    print(result)

    # 3. Lists with comprehensions
    print("\n3. Lists with comprehensions:")
    items = ["Apple", "Banana", "Cherry"]
    result = ul(class_="fruit-list")[[li[item] for item in items]]
    print(result)

    # 4. Conditional rendering
    print("\n4. Conditional rendering:")
    is_featured = True
    is_draft = False
    result = article(
        class_=cx(
            "card",
            ("card--featured", is_featured),
            ("card--draft", is_draft),
        )
    )[
        h2["My Article"],
        is_featured and span(class_="badge")["Featured"],
        is_draft and span(class_="badge badge--warning")["Draft"],
    ]
    print(result)

    # 5. Escaping
    print("\n5. Auto-escaping:")
    user_input = '<script>alert("xss")</script>'
    result = div[p[f"User said: {user_input}"],]
    print(result)

    # 6. Raw content (pre-rendered HTML)
    print("\n6. Raw content:")
    markdown_html = "<p><strong>Bold</strong> and <em>italic</em></p>"
    result = div(class_="content")[raw(markdown_html)]
    print(result)

    # 7. Components as functions
    print("\n7. Components as functions:")

    def user_card(name: str, avatar: str, bio: str | None = None) -> HTML:
        """A user card component - just a function!"""
        return html[
            article(class_="user-card")[
                img(src=avatar, alt=f"{name}'s avatar", class_="avatar"),
                h3[name],
                bio and p(class_="bio")[bio],
            ]
        ]

    result = div(class_="user-grid")[
        user_card("Alice", "/alice.jpg", "Python developer"),
        user_card("Bob", "/bob.jpg"),  # No bio
    ]
    print(result)

    # 8. Layout as function with parameters
    print("\n8. Layouts as functions:")

    def base_layout(
        *,
        page_title: str,
        content: HTML,
        scripts: HTML | None = None,
    ) -> HTML:
        """Base layout - just a function with parameters!"""
        return html[
            doctype(),
            html_elem(lang="en")[
                head[
                    title[page_title],
                    link(rel="stylesheet", href="/style.css"),
                ],
                body[
                    header[nav[a(href="/")["Home"]]],
                    main[content],
                    footer["© 2025"],
                    scripts,
                ],
            ],
        ]

    page_content = html[
        article[
            h1["Blog Post"],
            p["This is my blog post."],
        ]
    ]

    result = base_layout(
        page_title="My Blog Post",
        content=page_content,
        scripts=html[script(src="/js/comments.js")],
    )
    print(result)

    # 9. Tables
    print("\n9. Tables:")
    data = [
        {"name": "Alice", "role": "Developer"},
        {"name": "Bob", "role": "Designer"},
    ]
    result = table(class_="data-table")[
        thead[tr[th["Name"], th["Role"]]],
        tbody[[tr[td[row["name"]], td[row["role"]]] for row in data]],
    ]
    print(result)

    # 10. Forms
    print("\n10. Forms:")
    result = form(action="/submit", method="post")[
        div(class_="form-group")[
            label(for_="email")["Email"],
            input_(type="email", id="email", name="email", required=True),
        ],
        div(class_="form-group")[
            label(for_="message")["Message"],
            textarea(id="message", name="message", rows=4)[""],
        ],
        button(type="submit")["Send"],
    ]
    print(result)

    print("\n" + "=" * 60)
    print("✅ All demos completed!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
