# page_core

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/core/page/page_core.py

PageCore - Cacheable page metadata shared between Page, PageMetadata, and PageProxy.

This module defines PageCore, the single source of truth for all cacheable page
metadata. Any field added to PageCore automatically becomes available in:

- Page: via page.core.field or @property delegate (e.g., page.title)
- PageMetadata: IS PageCore (type alias in cache/page_discovery_cache.py)
- PageProxy: via proxy.field property (no lazy load needed for core fields)

This design prevents cache bugs by making it impossible to have mismatched field
definitions between Page, PageMetadata, and PageProxy. The compiler enforces that
all three representations stay in sync.

Architecture:
    PageCore = Cacheable fields only (title, date, tags, etc.)
    Page = PageCore + non-cacheable fields (content, rendered_html, toc, etc.)
    PageMetadata = PageCore (type alias for caching)
    PageProxy = Wraps PageCore (lazy loads only non-core fields)

What Goes in PageCore?
    ✅ DO include if:
    - Field comes from frontmatter (title, date, tags, slug, etc.)
    - Field is computed without full content parsing (url path components)
    - Field needs to be accessible in templates without lazy loading
    - Field is cascaded from section _index.md (type, layout, etc.)
    - Field is used for navigation (section reference as path)

    ❌ DO NOT include if:
    - Field requires full content parsing (toc, excerpt, meta_description)
    - Field is a build artifact (output_path, links, rendered_html)
    - Field changes every build (timestamp, render_time)
    - Field is computed from other non-cacheable fields

Example Usage:
    # Creating a PageCore
    from datetime import datetime

    core = PageCore(
        source_path="content/posts/my-post.md",  # String path for JSON compatibility
        title="My Post",
        date=datetime(2025, 10, 26),
        tags=["python", "web"],
        slug="my-post",
        type="doc",
    )

    # Using in Page (composition)
    from bengal.core.page import Page

    page = Page(
        core=core,
        content="# Hello World",
        rendered_html="<h1>Hello World</h1>",
    )

    # Accessing fields via property delegates
    assert page.title == "My Post"  # Property delegate
    assert page.core.title == "My Post"  # Direct access

    # Caching (PageMetadata = PageCore)
    from dataclasses import asdict
    import json

    metadata = page.core  # Already PageCore!
    json_str = json.dumps(asdict(metadata), default=str)

    # Loading from cache
    from bengal.core.page.proxy import PageProxy

    loaded_core = PageCore(**json.loads(json_str))
    proxy = PageProxy(core=loaded_core, loader=load_page_fn)

    # Accessing cached fields (no lazy load)
    assert proxy.title == "My Post"  # Direct from core

Adding New Fields:
    When adding a new cacheable field:

    1. Add to PageCore (this file):
        @dataclass
        class PageCore:
            # ... existing fields ...
            author: str | None = None  # NEW

    2. Add @property delegate to Page (bengal/core/page/__init__.py):
        @property
        def author(self) -> str | None:
            return self.core.author

    3. Add @property delegate to PageProxy (bengal/core/page/proxy.py):
        @property
        def author(self) -> str | None:
            return self._core.author

    That's it! Field is now available in Page, PageMetadata, and PageProxy.
    The compiler will catch any missing implementations.

See Also:
    - architecture/object-model.md - PageProxy & Cache Contract section
    - plan/active/rfc-cache-proxy-contract.md - Design rationale
    - CONTRIBUTING.md - Guidelines for adding fields

*Note: Template has undefined variables. This is fallback content.*
