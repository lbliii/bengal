
---
title: "metadata"
type: "python-module"
source_file: "bengal/core/page/metadata.py"
line_number: 1
description: "Page Metadata Mixin - Basic properties and type checking."
---

# metadata
**Type:** Module
**Source:** [View source](bengal/core/page/metadata.py#L1)



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




#### `should_render_in_environment`

:::{div} api-badge-group
:::

```python
def should_render_in_environment(self, is_production: bool = False) -> bool
```


Check if page should be rendered in the given environment.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `is_production` | `bool` | `False` | True if building for production |







:::{rubric} Returns
:class: rubric-returns
:::


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
*Generated by Bengal autodoc from `bengal/core/page/metadata.py`*

