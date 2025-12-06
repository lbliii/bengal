
---
title: "metadata"
type: "python-module"
source_file: "bengal/bengal/core/page/metadata.py"
line_number: 1
description: "Page Metadata Mixin - Basic properties and type checking."
---

# metadata
**Type:** Module
**Source:** [View source](bengal/bengal/core/page/metadata.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[core](/api/bengal/core/) ›[page](/api/bengal/core/page/) ›metadata

Page Metadata Mixin - Basic properties and type checking.

## Classes




### `PageMetadataMixin`


Mixin providing metadata properties and type checking for pages.

This mixin handles:
- Basic properties: title, date, slug, url
- Type checking: is_home, is_section, is_page, kind
- Simple metadata: description, draft, keywords
- Component Model: type, variant, props
- TOC access: toc_items (lazy evaluation)






:::{rubric} Properties
:class: rubric-properties
:::



#### `title` @property

```python
def title(self) -> str
```
Get page title from metadata or generate intelligently from context.

For index pages (_index.md or index.md) without explicit titles,
uses the parent directory name humanized instead of showing "Index"
which is not user-friendly in menus, navigation, or page titles.

#### `date` @property

```python
def date(self) -> datetime | None
```
Get page date from metadata.

Uses bengal.utils.dates.parse_date for flexible date parsing.

#### `slug` @property

```python
def slug(self) -> str
```
Get URL slug for the page.

#### `relative_url` @property

```python
def relative_url(self) -> str
```
Get relative URL without baseurl (for comparisons).

This is the identity URL - use for comparisons, menu activation, etc.
Always returns a relative path without baseurl.

#### `url` @property

```python
def url(self) -> str
```
Get URL with baseurl applied (cached after first access).

This is the primary URL property for templates - automatically includes
baseurl when available. Use .relative_url for comparisons.

#### `permalink` @property

```python
def permalink(self) -> str
```
Alias for url (for backward compatibility).

Both url and permalink now return the same value (with baseurl).
Use .relative_url for comparisons.

#### `toc_items` @property

```python
def toc_items(self) -> list[dict[str, Any]]
```
Get structured TOC data (lazy evaluation).

Only extracts TOC structure when accessed by templates, saving
HTMLParser overhead for pages that don't use toc_items.

Important: This property does NOT cache empty results. This allows
toc_items to be accessed before parsing (during xref indexing) without
preventing extraction after parsing when page.toc is actually set.

#### `is_home` @property

```python
def is_home(self) -> bool
```
Check if this page is the home page.

#### `is_section` @property

```python
def is_section(self) -> bool
```
Check if this page is a section page.

#### `is_page` @property

```python
def is_page(self) -> bool
```
Check if this is a regular page (not a section).

#### `kind` @property

```python
def kind(self) -> str
```
Get the kind of page: 'home', 'section', or 'page'.

#### `type` @property

```python
def type(self) -> str | None
```
Get page type from core metadata (preferred) or frontmatter.

Component Model: Identity.

#### `description` @property

```python
def description(self) -> str
```
Get page description from core metadata (preferred) or frontmatter.

#### `variant` @property

```python
def variant(self) -> str | None
```
Get visual variant from core (preferred) or legacy layout/hero_style fields.

This normalizes 'layout' and 'hero_style' into the new Component Model 'variant'.

Component Model: Mode.

#### `props` @property

```python
def props(self) -> dict[str, Any]
```
Get page props (alias for metadata).

Component Model: Data.

#### `draft` @property

```python
def draft(self) -> bool
```
Check if page is marked as draft.

#### `keywords` @property

```python
def keywords(self) -> list[str]
```
Get page keywords from metadata.

#### `hidden` @property

```python
def hidden(self) -> bool
```
Check if page is hidden (unlisted).

Hidden pages:
- Are excluded from navigation menus
- Are excluded from site.pages queries (listings)
- Are excluded from sitemap.xml
- Get noindex,nofollow robots meta
- Still render and are accessible via direct URL

#### `visibility` @property

```python
def visibility(self) -> dict[str, Any]
```
Get visibility settings with defaults.

The visibility object provides granular control over page visibility:
- menu: Include in navigation menus (default: True)
- listings: Include in site.pages queries (default: True)
- sitemap: Include in sitemap.xml (default: True)
- robots: Robots meta directive (default: "index, follow")
- render: When to render - "always", "local", "never" (default: "always")
- search: Include in search index (default: True)
- rss: Include in RSS feeds (default: True)

If `hidden: true` is set, it expands to restrictive defaults.

#### `in_listings` @property

```python
def in_listings(self) -> bool
```
Check if page should appear in listings/queries.

Excludes drafts and pages with visibility.listings=False.

#### `in_sitemap` @property

```python
def in_sitemap(self) -> bool
```
Check if page should appear in sitemap.

Excludes drafts and pages with visibility.sitemap=False.

#### `in_search` @property

```python
def in_search(self) -> bool
```
Check if page should appear in search index.

Excludes drafts and pages with visibility.search=False.

#### `in_rss` @property

```python
def in_rss(self) -> bool
```
Check if page should appear in RSS feeds.

Excludes drafts and pages with visibility.rss=False.

#### `robots_meta` @property

```python
def robots_meta(self) -> str
```
Get robots meta content for this page.

#### `should_render` @property

```python
def should_render(self) -> bool
```
Check if page should be rendered based on visibility.render setting.

Note: This checks the render setting but doesn't know about environment.
Use should_render_in_environment() for environment-aware checks.




## Methods



#### `title`
```python
def title(self) -> str
```


Get page title from metadata or generate intelligently from context.

For index pages (_index.md or index.md) without explicit titles,
uses the parent directory name humanized instead of showing "Index"
which is not user-friendly in menus, navigation, or page titles.



**Returns**


`str`
:::{rubric} Examples
:class: rubric-examples
:::


```python
api/_index.md → "Api"
    docs/index.md → "Docs"
    data-designer/_index.md → "Data Designer"
    my_module/index.md → "My Module"
    about.md → "About"
```




#### `date`
```python
def date(self) -> datetime | None
```


Get page date from metadata.

Uses bengal.utils.dates.parse_date for flexible date parsing.



**Returns**


`datetime | None`



#### `slug`
```python
def slug(self) -> str
```


Get URL slug for the page.



**Returns**


`str`



#### `relative_url`
```python
def relative_url(self) -> str
```


Get relative URL without baseurl (for comparisons).

This is the identity URL - use for comparisons, menu activation, etc.
Always returns a relative path without baseurl.



**Returns**


`str`



#### `url`
```python
def url(self) -> str
```


Get URL with baseurl applied (cached after first access).

This is the primary URL property for templates - automatically includes
baseurl when available. Use .relative_url for comparisons.



**Returns**


`str` - URL path with baseurl prepended (if configured)



#### `permalink`
```python
def permalink(self) -> str
```


Alias for url (for backward compatibility).

Both url and permalink now return the same value (with baseurl).
Use .relative_url for comparisons.



**Returns**


`str`



#### `toc_items`
```python
def toc_items(self) -> list[dict[str, Any]]
```


Get structured TOC data (lazy evaluation).

Only extracts TOC structure when accessed by templates, saving
HTMLParser overhead for pages that don't use toc_items.

Important: This property does NOT cache empty results. This allows
toc_items to be accessed before parsing (during xref indexing) without
preventing extraction after parsing when page.toc is actually set.



**Returns**


`list[dict[str, Any]]` - List of TOC items with id, title, and level



#### `is_home`
```python
def is_home(self) -> bool
```


Check if this page is the home page.



**Returns**


`bool` - True if this is the home page
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% if page.is_home %}
      <h1>Welcome to the home page!</h1>
    {% endif %}
```




#### `is_section`
```python
def is_section(self) -> bool
```


Check if this page is a section page.



**Returns**


`bool` - True if this is a section (always False for Page, True for Section)
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% if page.is_section %}
      <h2>Section: {{ page.title }}</h2>
    {% endif %}
```




#### `is_page`
```python
def is_page(self) -> bool
```


Check if this is a regular page (not a section).



**Returns**


`bool` - True if this is a regular page
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% if page.is_page %}
      <article>{{ page.content }}</article>
    {% endif %}
```




#### `kind`
```python
def kind(self) -> str
```


Get the kind of page: 'home', 'section', or 'page'.



**Returns**


`str` - String indicating page kind
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% if page.kind == 'section' %}
      {# Render section template #}
    {% endif %}
```




#### `type`
```python
def type(self) -> str | None
```


Get page type from core metadata (preferred) or frontmatter.

Component Model: Identity.



**Returns**


`str | None` - Page type or None



#### `description`
```python
def description(self) -> str
```


Get page description from core metadata (preferred) or frontmatter.



**Returns**


`str` - Page description or empty string



#### `variant`
```python
def variant(self) -> str | None
```


Get visual variant from core (preferred) or legacy layout/hero_style fields.

This normalizes 'layout' and 'hero_style' into the new Component Model 'variant'.

Component Model: Mode.



**Returns**


`str | None` - Variant string or None



#### `props`
```python
def props(self) -> dict[str, Any]
```


Get page props (alias for metadata).

Component Model: Data.



**Returns**


`dict[str, Any]` - Page metadata dictionary



#### `draft`
```python
def draft(self) -> bool
```


Check if page is marked as draft.



**Returns**


`bool` - True if page is a draft



#### `keywords`
```python
def keywords(self) -> list[str]
```


Get page keywords from metadata.



**Returns**


`list[str]` - List of keywords



#### `hidden`
```python
def hidden(self) -> bool
```


Check if page is hidden (unlisted).

Hidden pages:
- Are excluded from navigation menus
- Are excluded from site.pages queries (listings)
- Are excluded from sitemap.xml
- Get noindex,nofollow robots meta
- Still render and are accessible via direct URL



**Returns**


`bool` - True if page is hidden
:::{rubric} Examples
:class: rubric-examples
:::


```python
```yaml
    ---
    title: Secret Page
    hidden: true
    ---
    ```
```




#### `visibility`
```python
def visibility(self) -> dict[str, Any]
```


Get visibility settings with defaults.

The visibility object provides granular control over page visibility:
- menu: Include in navigation menus (default: True)
- listings: Include in site.pages queries (default: True)
- sitemap: Include in sitemap.xml (default: True)
- robots: Robots meta directive (default: "index, follow")
- render: When to render - "always", "local", "never" (default: "always")
- search: Include in search index (default: True)
- rss: Include in RSS feeds (default: True)

If `hidden: true` is set, it expands to restrictive defaults.



**Returns**


`dict[str, Any]` - Dict with visibility settings
:::{rubric} Examples
:class: rubric-examples
:::


```python
```yaml
    ---
    title: Partially Hidden
    visibility:
        menu: false
        listings: true
        sitemap: true
    ---
    ```
```




#### `in_listings`
```python
def in_listings(self) -> bool
```


Check if page should appear in listings/queries.

Excludes drafts and pages with visibility.listings=False.



**Returns**


`bool` - True if page should appear in site.pages queries



#### `in_sitemap`
```python
def in_sitemap(self) -> bool
```


Check if page should appear in sitemap.

Excludes drafts and pages with visibility.sitemap=False.



**Returns**


`bool` - True if page should appear in sitemap.xml



#### `in_search`
```python
def in_search(self) -> bool
```


Check if page should appear in search index.

Excludes drafts and pages with visibility.search=False.



**Returns**


`bool` - True if page should appear in search index



#### `in_rss`
```python
def in_rss(self) -> bool
```


Check if page should appear in RSS feeds.

Excludes drafts and pages with visibility.rss=False.



**Returns**


`bool` - True if page should appear in RSS feeds



#### `robots_meta`
```python
def robots_meta(self) -> str
```


Get robots meta content for this page.



**Returns**


`str` - Robots directive string (e.g., "index, follow" or "noindex, nofollow")



#### `should_render`
```python
def should_render(self) -> bool
```


Check if page should be rendered based on visibility.render setting.

Note: This checks the render setting but doesn't know about environment.
Use should_render_in_environment() for environment-aware checks.



**Returns**


`bool` - True if render is not "never"




#### `should_render_in_environment`
```python
def should_render_in_environment(self, is_production: bool = False) -> bool
```


Check if page should be rendered in the given environment.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `is_production` | `bool` | `False` | True if building for production |







**Returns**


`bool` - True if page should be rendered in this environment
:::{rubric} Examples
:class: rubric-examples
:::


```python
```yaml
    ---
    visibility:
        render: local  # Only in dev server
    ---
    ```
```



---
*Generated by Bengal autodoc from `bengal/bengal/core/page/metadata.py`*
