# RFC: Stubbed Link Functionality

**Priority**: P2 (Medium)  

## Summary

Add a `stub_link()` template function that allows writers to create placeholder links for planned future content without triggering broken link warnings.

## Problem

Documentation writers often need to:
1. **Plan content structure** - Reference pages that don't exist yet while planning site architecture
2. **Progressive development** - Build pages incrementally while maintaining visible linkage plans
3. **Draft documentation** - Show intended navigation before all target pages are complete
4. **Team coordination** - Communicate planned content connections to collaborators

Currently, this results in broken link warnings during builds, forcing writers to either:
- Remove planned links (losing visibility into intended structure)
- Disable link validation globally (losing protection against real broken links)
- Use placeholder text without link markup (losing semantic intent)

## Design

### Template Function: `stub_link()`

Add a new template function that generates visually distinct placeholder links:

```jinja2
{# Basic usage #}
{{ stub_link('/docs/advanced/plugins/', 'Plugin Development') }}

{# With optional status/notes #}
{{ stub_link('/docs/api/v2/', 'API v2 Reference', status='planned') }}
{{ stub_link('/tutorials/deployment/', 'Deployment Guide', status='in-progress') }}
```

### Rendered Output

Stub links render as styled `<span>` elements (not `<a>` links), avoiding link validation:

```html
<span class="stub-link"
      data-target="/docs/advanced/plugins/"
      data-status="planned"
      title="Planned: /docs/advanced/plugins/">
  Plugin Development
</span>
```

### Visual Styling

Default theme includes CSS for stub links:

```css
.stub-link {
  color: var(--color-text-muted);
  border-bottom: 1px dashed var(--color-border);
  cursor: help;
}

.stub-link[data-status="in-progress"] {
  border-bottom-color: var(--color-warning);
}

.stub-link::after {
  content: " ↗";
  font-size: 0.75em;
  opacity: 0.6;
}
```

### Optional: Markdown Syntax

For convenience in content files, support a shorthand:

```markdown
<!-- Standard markdown won't work (would create broken link) -->
<!-- [Plugin Guide](/docs/plugins/) -->

<!-- Use Jinja2 syntax in content -->
Check out the {{ stub_link('/docs/plugins/', 'Plugin Guide') }} for more.
```

### Stub Link Tracking

The Site object collects stub links during rendering for optional reporting:

```python
# site.stub_links after build:
[
    StubLink(
        target="/docs/advanced/plugins/",
        text="Plugin Development",
        status="planned",
        source_page="/docs/getting-started/",
        source_line=42
    ),
    ...
]
```

Build stats can report:
```
📊 Build Summary
  Pages: 42
  Stub links: 7 (planned: 5, in-progress: 2)
```

## Implementation

### 1. New Template Function Module

Create `bengal/rendering/template_functions/stubs.py`:

```python
"""
Stub link functions for planned/placeholder content.

Provides functions for creating visually distinct placeholder links
that won't trigger broken link validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from markupsafe import Markup

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment
    from bengal.core.site import Site

logger = get_logger(__name__)


@dataclass
class StubLink:
    """Record of a stub link for tracking."""
    target: str
    text: str
    status: str
    source_page: str | None = None


def register(env: Environment, site: Site) -> None:
    """Register stub link functions with Jinja2 environment."""

    def stub_link_with_context(
        target: str,
        text: str | None = None,
        status: str = "planned"
    ) -> Markup:
        return stub_link(target, text, status, site)

    env.globals["stub_link"] = stub_link_with_context
    env.globals["planned_link"] = stub_link_with_context  # Alias


def stub_link(
    target: str,
    text: str | None = None,
    status: str = "planned",
    site: Site | None = None
) -> Markup:
    """
    Generate a placeholder link for planned content.

    Creates a visually distinct span (not an <a> link) that indicates
    planned future content without triggering broken link warnings.

    Args:
        target: Target path for the future page
        text: Display text (defaults to target path)
        status: Status indicator ('planned', 'in-progress', 'draft')
        site: Site instance for tracking (optional)

    Returns:
        Safe HTML span element with stub link styling

    Examples:
        {{ stub_link('/docs/plugins/', 'Plugin Guide') }}
        {{ stub_link('/api/v2/', 'API v2', status='in-progress') }}
    """
    display_text = text or target

    # Track stub link if site available
    if site is not None:
        if not hasattr(site, '_stub_links'):
            site._stub_links = []
        site._stub_links.append(StubLink(
            target=target,
            text=display_text,
            status=status,
        ))

    logger.debug(
        "stub_link_rendered",
        target=target,
        text=display_text,
        status=status,
    )

    # Escape for safe HTML
    from html import escape
    safe_target = escape(target)
    safe_text = escape(display_text)
    safe_status = escape(status)

    return Markup(
        f'<span class="stub-link" '
        f'data-target="{safe_target}" '
        f'data-status="{safe_status}" '
        f'title="Planned: {safe_target}">'
        f'{safe_text}'
        f'</span>'
    )
```

### 2. Register in Template Functions

Update `bengal/rendering/template_functions/__init__.py`:

```python
from . import (
    ...
    stubs,  # Add new module
)

def register_all(env: Environment, site: Site) -> None:
    ...
    # Phase 4: Cross-reference functions
    crossref.register(env, site)
    stubs.register(env, site)  # Add registration
```

### 3. Default Theme CSS

Add to `bengal/themes/default/assets/css/components/`:

```css
/* _stub-links.css */

.stub-link {
  color: var(--color-text-muted, #6b7280);
  border-bottom: 1px dashed var(--color-border, #d1d5db);
  cursor: help;
  text-decoration: none;
}

.stub-link:hover {
  background-color: var(--color-bg-subtle, #f9fafb);
}

.stub-link[data-status="in-progress"] {
  border-bottom-color: var(--color-warning, #f59e0b);
}

.stub-link[data-status="draft"] {
  border-bottom-color: var(--color-info, #3b82f6);
}

/* Visual indicator for stub links */
.stub-link::after {
  content: " ↗";
  font-size: 0.75em;
  opacity: 0.6;
}
```

### 4. Build Stats Integration (Optional)

Add stub link reporting to build stats:

```python
# In build_stats.py

def _format_stub_links(self, site: Site) -> None:
    """Report stub links in build summary."""
    stub_links = getattr(site, '_stub_links', [])
    if stub_links:
        by_status = {}
        for link in stub_links:
            by_status.setdefault(link.status, []).append(link)

        status_parts = [f"{k}: {len(v)}" for k, v in by_status.items()]
        cli.info(f"📝 Stub links: {len(stub_links)} ({', '.join(status_parts)})")
```

## Alternatives Considered

### 1. Special URL Scheme (`stub://`)

```markdown
[Plugin Guide](stub:///docs/plugins/)
```

**Rejected**: Would require modifying the link validator to recognize special schemes, and markdown processors might not handle custom schemes well.

### 2. Front Matter Declaration

```yaml
---
stub_links:
  - /docs/plugins/
  - /api/v2/
---
```

**Rejected**: Less discoverable, doesn't support inline link text, harder to maintain as content evolves.

### 3. HTML Comments

```markdown
[Plugin Guide](#stub:/docs/plugins/)
<!-- TODO: /docs/plugins/ -->
```

**Rejected**: Link would still be created (with broken fragment), comments lose semantic meaning.

## Testing

### Unit Tests

```python
def test_stub_link_basic():
    """Test basic stub link generation."""
    result = stub_link("/docs/plugins/", "Plugin Guide")
    assert 'class="stub-link"' in result
    assert 'data-target="/docs/plugins/"' in result
    assert ">Plugin Guide<" in result

def test_stub_link_status():
    """Test stub link with custom status."""
    result = stub_link("/api/", "API", status="in-progress")
    assert 'data-status="in-progress"' in result

def test_stub_link_tracking():
    """Test stub links are tracked on site."""
    site = MagicMock()
    stub_link("/docs/", "Docs", site=site)
    assert len(site._stub_links) == 1
    assert site._stub_links[0].target == "/docs/"
```

### Integration Tests

```python
def test_stub_link_not_validated(test_site):
    """Stub links should not trigger broken link warnings."""
    # Page with stub link to non-existent target
    page = create_test_page(
        content='{{ stub_link("/nonexistent/", "Future Page") }}'
    )

    # Build should succeed without broken link warnings
    build_site(test_site)

    # Link validator should not report this as broken
    validator = LinkValidator()
    broken = validator.validate_site(test_site)
    assert len(broken) == 0
```

## Migration

No migration needed - this is a new additive feature.

## Documentation

1. Add to template function reference: `stub_link(target, text, status)`
2. Add "Planning Content" guide with examples
3. Document CSS customization options

## Success Criteria

- [ ] `stub_link()` function renders placeholder spans
- [ ] Stub links don't trigger broken link validation
- [ ] Default theme includes stub link styles
- [ ] Build stats optionally report stub links
- [ ] Unit and integration tests pass

## Timeline

- **Phase 1** (1 hour): Core template function + tests
- **Phase 2** (30 min): CSS styling in default theme
- **Phase 3** (30 min): Build stats integration
- **Phase 4** (30 min): Documentation

Total: ~2.5 hours

## Open Questions

1. Should stub links support linking to anchors? (`stub_link('/docs/api/#auth')`)
2. Should there be a CLI command to list all stub links? (`bengal list-stubs`)
3. Should stub links auto-convert to real links when target pages are created?
