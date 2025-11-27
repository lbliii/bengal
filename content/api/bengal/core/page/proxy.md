
---
title: "proxy"
type: "python-module"
source_file: "bengal/bengal/core/page/proxy.py"
line_number: 1
description: "PageProxy - Lazy-loaded page placeholder for incremental builds. A PageProxy holds minimal page metadata (title, date, tags, etc.) loaded from the PageDiscoveryCache and defers loading full page conte..."
---

# proxy
**Type:** Module
**Source:** [View source](bengal/bengal/core/page/proxy.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[core](/api/bengal/core/) ›[page](/api/bengal/core/page/) ›proxy

PageProxy - Lazy-loaded page placeholder for incremental builds.

A PageProxy holds minimal page metadata (title, date, tags, etc.) loaded from
the PageDiscoveryCache and defers loading full page content until needed.

This enables incremental builds to skip disk I/O and parsing for unchanged
pages while maintaining transparent access (code doesn't know it's lazy).

Architecture:
- Metadata loaded immediately from cache (fast)
- Full content loaded on first access to .content or other lazy properties
- Transparent to callers - behaves like a normal Page object
- Falls back to eager load if cascades or complex operations detected

## Classes




### `PageProxy`


Lazy-loaded page placeholder.

Holds page metadata from cache and defers loading full content until
accessed. Transparent to callers - implements Page-like interface.

LIFECYCLE IN INCREMENTAL BUILDS:
---------------------------------
1. **Discovery** (content_discovery.py):
   - Created from cached metadata for unchanged pages
   - Has: title, date, tags, slug, _section, _site, output_path
   - Does NOT have: content, rendered_html (lazy-loaded on demand)

2. **Filtering** (incremental.py):
   - PageProxy objects pass through find_work_early() unchanged
   - Only modified pages become full Page objects for rendering

3. **Rendering** (render.py):
   - Modified pages rendered as full Page objects
   - PageProxy objects skipped (already have cached output)

4. **Update** (build.py Phase 8.4):
   - Freshly rendered Page objects REPLACE their PageProxy counterparts
   - site.pages becomes: mix of fresh Page (rebuilt) + PageProxy (cached)

5. **Postprocessing** (postprocess.py):
   - Iterates over site.pages (now updated with fresh Pages)
   - ⚠️ CRITICAL: PageProxy must implement ALL properties/methods used:
     * output_path (for finding where to write .txt/.json)
     * url, permalink (for generating index.json)
     * title, date, tags (for content in output files)

TRANSPARENCY CONTRACT:
----------------------
PageProxy must be transparent to:
- **Templates**: Implements .url, .permalink, .title, etc.
- **Postprocessing**: Implements .output_path, metadata access
- **Navigation**: Implements .prev, .next (via lazy load)

⚠️ When adding new Page properties used by templates/postprocessing,
MUST also add to PageProxy or handle in _ensure_loaded().

Usage:
    # Create from cached metadata
    page = PageProxy(
        source_path=Path("content/post.md"),
        metadata=cached_metadata,
        loader=load_page_from_disk,  # Callable that loads full page
    )

    # Access metadata (instant, from cache)
    print(page.title)  # "My Post"
    print(page.tags)   # ["python", "web"]

    # Access full content (triggers lazy load)
    print(page.content)  # Loads from disk and parses

    # After first access, it's fully loaded
    assert page._lazy_loaded  # True






:::{rubric} Properties
:class: rubric-properties
:::



#### `title` @property

```python
def title(self) -> str
```
Get page title from cached metadata.

#### `date` @property

```python
def date(self) -> datetime | None
```
Get page date from cached metadata (parsed from ISO string).

#### `tags` @property

```python
def tags(self) -> list[str]
```
Get page tags from cached metadata.

#### `slug` @property

```python
def slug(self) -> str | None
```
Get URL slug from cached metadata.

#### `weight` @property

```python
def weight(self) -> int | None
```
Get sort weight from cached metadata.

#### `lang` @property

```python
def lang(self) -> str | None
```
Get language code from cached metadata.

#### `type` @property

```python
def type(self) -> str | None
```
Get page type from cached metadata (cascaded).

#### `section` @property

```python
def section(self) -> str | None
```
Get section path from cached metadata.

#### `relative_path` @property

```python
def relative_path(self) -> str
```
Get relative path string (alias for source_path as string).

#### `content` @property

```python
def content(self) -> str
```
Get page content (lazy-loaded from disk).

#### `metadata` @property

```python
def metadata(self) -> dict[str, Any]
```
Get metadata dict from cache (no lazy load).

Returns cached metadata including cascaded fields like 'type'.
This allows templates to check page.metadata.get("type") without
triggering a full page load.

#### `rendered_html` @property

```python
def rendered_html(self) -> str
```
Get rendered HTML (lazy-loaded).

#### `links` @property

```python
def links(self) -> list[str]
```
Get extracted links (lazy-loaded).

#### `version` @property

```python
def version(self) -> str | None
```
Get version (lazy-loaded).

#### `toc` @property

```python
def toc(self) -> str | None
```
Get table of contents (lazy-loaded).

#### `toc_items` @property

```python
def toc_items(self) -> list[dict[str, Any]]
```
Get TOC items (lazy-loaded).

#### `output_path` @property

```python
def output_path(self) -> Path | None
```
Get output path (lazy-loaded).

#### `parsed_ast` @property

```python
def parsed_ast(self) -> Any
```
Get parsed AST (lazy-loaded).

#### `related_posts` @property

```python
def related_posts(self) -> list
```
Get related posts (lazy-loaded).

#### `translation_key` @property

```python
def translation_key(self) -> str | None
```
Get translation key.

#### `url` @property

```python
def url(self) -> str
```
Get the URL path for the page (lazy-loaded, cached after first access).

#### `relative_url` @property

```python
def relative_url(self) -> str
```
Get the relative URL (without baseurl) for the page (lazy-loaded, cached after first access).

#### `permalink` @property

```python
def permalink(self) -> str
```
Get the permalink (URL with baseurl) for the page (lazy-loaded, cached after first access).

#### `meta_description` @property

```python
def meta_description(self) -> str
```
Get meta description (lazy-loaded from full page).

#### `reading_time` @property

```python
def reading_time(self) -> str
```
Get reading time estimate (lazy-loaded from full page).

#### `excerpt` @property

```python
def excerpt(self) -> str
```
Get content excerpt (lazy-loaded from full page).

#### `keywords` @property

```python
def keywords(self) -> list[str]
```
Get keywords (lazy-loaded from full page).

#### `parent` @property

```python
def parent(self) -> Any
```
Get the parent section of this page.

Returns parent section without forcing full page load (uses _section).

#### `ancestors` @property

```python
def ancestors(self) -> list[Any]
```
Get all ancestor sections of this page.

Returns list of ancestor sections from immediate parent to root
without forcing full page load (uses _section property).

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

#### `description` @property

```python
def description(self) -> str
```
Get page description from metadata.

#### `draft` @property

```python
def draft(self) -> bool
```
Check if page is marked as draft.

#### `next` @property

```python
def next(self) -> Page | None
```
Get next page in site collection.

#### `prev` @property

```python
def prev(self) -> Page | None
```
Get previous page in site collection.

#### `next_in_section` @property

```python
def next_in_section(self) -> Page | None
```
Get next page in same section.

#### `prev_in_section` @property

```python
def prev_in_section(self) -> Page | None
```
Get previous page in same section.

#### `_section` @property

```python
def _section(self) -> Any | None
```
Get the section this page belongs to (lazy lookup via path).

If the page is loaded, delegates to the full page's _section property.
Otherwise, performs path-based lookup via site registry without forcing load.




## Methods



#### `title`
```python
def title(self) -> str
```


Get page title from cached metadata.



**Returns**


`str`



#### `date`
```python
def date(self) -> datetime | None
```


Get page date from cached metadata (parsed from ISO string).



**Returns**


`datetime | None`



#### `tags`
```python
def tags(self) -> list[str]
```


Get page tags from cached metadata.



**Returns**


`list[str]`



#### `slug`
```python
def slug(self) -> str | None
```


Get URL slug from cached metadata.



**Returns**


`str | None`



#### `weight`
```python
def weight(self) -> int | None
```


Get sort weight from cached metadata.



**Returns**


`int | None`



#### `lang`
```python
def lang(self) -> str | None
```


Get language code from cached metadata.



**Returns**


`str | None`



#### `type`
```python
def type(self) -> str | None
```


Get page type from cached metadata (cascaded).



**Returns**


`str | None`



#### `section`
```python
def section(self) -> str | None
```


Get section path from cached metadata.



**Returns**


`str | None`



#### `relative_path`
```python
def relative_path(self) -> str
```


Get relative path string (alias for source_path as string).



**Returns**


`str`



#### `content`
```python
def content(self) -> str
```


Get page content (lazy-loaded from disk).



**Returns**


`str`



#### `metadata`
```python
def metadata(self) -> dict[str, Any]
```


Get metadata dict from cache (no lazy load).

Returns cached metadata including cascaded fields like 'type'.
This allows templates to check page.metadata.get("type") without
triggering a full page load.



**Returns**


`dict[str, Any]`



#### `rendered_html`
```python
def rendered_html(self) -> str
```


Get rendered HTML (lazy-loaded).



**Returns**


`str`



#### `links`
```python
def links(self) -> list[str]
```


Get extracted links (lazy-loaded).



**Returns**


`list[str]`



#### `version`
```python
def version(self) -> str | None
```


Get version (lazy-loaded).



**Returns**


`str | None`



#### `toc`
```python
def toc(self) -> str | None
```


Get table of contents (lazy-loaded).



**Returns**


`str | None`



#### `toc_items`
```python
def toc_items(self) -> list[dict[str, Any]]
```


Get TOC items (lazy-loaded).



**Returns**


`list[dict[str, Any]]`



#### `output_path`
```python
def output_path(self) -> Path | None
```


Get output path (lazy-loaded).



**Returns**


`Path | None`



#### `parsed_ast`
```python
def parsed_ast(self) -> Any
```


Get parsed AST (lazy-loaded).



**Returns**


`Any`



#### `related_posts`
```python
def related_posts(self) -> list
```


Get related posts (lazy-loaded).



**Returns**


`list`



#### `translation_key`
```python
def translation_key(self) -> str | None
```


Get translation key.



**Returns**


`str | None`



#### `url`
```python
def url(self) -> str
```


Get the URL path for the page (lazy-loaded, cached after first access).



**Returns**


`str`



#### `relative_url`
```python
def relative_url(self) -> str
```


Get the relative URL (without baseurl) for the page (lazy-loaded, cached after first access).



**Returns**


`str`



#### `permalink`
```python
def permalink(self) -> str
```


Get the permalink (URL with baseurl) for the page (lazy-loaded, cached after first access).



**Returns**


`str`



#### `meta_description`
```python
def meta_description(self) -> str
```


Get meta description (lazy-loaded from full page).



**Returns**


`str`



#### `reading_time`
```python
def reading_time(self) -> str
```


Get reading time estimate (lazy-loaded from full page).



**Returns**


`str`



#### `excerpt`
```python
def excerpt(self) -> str
```


Get content excerpt (lazy-loaded from full page).



**Returns**


`str`



#### `keywords`
```python
def keywords(self) -> list[str]
```


Get keywords (lazy-loaded from full page).



**Returns**


`list[str]`



#### `parent`
```python
def parent(self) -> Any
```


Get the parent section of this page.

Returns parent section without forcing full page load (uses _section).



**Returns**


`Any`



#### `ancestors`
```python
def ancestors(self) -> list[Any]
```


Get all ancestor sections of this page.

Returns list of ancestor sections from immediate parent to root
without forcing full page load (uses _section property).



**Returns**


`list[Any]`



#### `is_home`
```python
def is_home(self) -> bool
```


Check if this page is the home page.



**Returns**


`bool`



#### `is_section`
```python
def is_section(self) -> bool
```


Check if this page is a section page.



**Returns**


`bool`



#### `is_page`
```python
def is_page(self) -> bool
```


Check if this is a regular page (not a section).



**Returns**


`bool`



#### `kind`
```python
def kind(self) -> str
```


Get the kind of page: 'home', 'section', or 'page'.



**Returns**


`str`



#### `description`
```python
def description(self) -> str
```


Get page description from metadata.



**Returns**


`str`



#### `draft`
```python
def draft(self) -> bool
```


Check if page is marked as draft.



**Returns**


`bool`



#### `next`
```python
def next(self) -> Page | None
```


Get next page in site collection.



**Returns**


`Page | None`



#### `prev`
```python
def prev(self) -> Page | None
```


Get previous page in site collection.



**Returns**


`Page | None`



#### `next_in_section`
```python
def next_in_section(self) -> Page | None
```


Get next page in same section.



**Returns**


`Page | None`



#### `prev_in_section`
```python
def prev_in_section(self) -> Page | None
```


Get previous page in same section.



**Returns**


`Page | None`




#### `__init__`
```python
def __init__(self, source_path: Path, metadata: PageCore, loader: callable)
```


Initialize PageProxy with PageCore metadata and loader.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source content file |
| `metadata` | `PageCore` | - | PageCore with cached page metadata (title, date, tags, etc.) |
| `loader` | `callable` | - | Callable that loads full Page(source_path) -> Page |










#### `rendered_html`
```python
def rendered_html(self, value: str) -> None
```


Set rendered HTML.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `value` | `str` | - | *No description provided.* |







**Returns**


`None`



#### `toc`
```python
def toc(self, value: str | None) -> None
```


Set table of contents.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `value` | `str \| None` | - | *No description provided.* |







**Returns**


`None`



#### `output_path`
```python
def output_path(self, value: Path | None) -> None
```


Set output path.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `value` | `Path \| None` | - | *No description provided.* |







**Returns**


`None`



#### `parsed_ast`
```python
def parsed_ast(self, value: Any) -> None
```


Set parsed AST.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `value` | `Any` | - | *No description provided.* |







**Returns**


`None`



#### `related_posts`
```python
def related_posts(self, value: list) -> None
```


Set related posts.

In incremental mode, allow setting on proxy without forcing a full load.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `value` | `list` | - | *No description provided.* |







**Returns**


`None`



#### `extract_links`
```python
def extract_links(self) -> None
```


Extract links from content.



**Returns**


`None`




#### `__hash__`
```python
def __hash__(self) -> int
```


Hash based on source_path (same as Page).



**Returns**


`int`



#### `__eq__`
```python
def __eq__(self, other: Any) -> bool
```


Equality based on source_path.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `other` | `Any` | - | *No description provided.* |







**Returns**


`bool`



#### `__repr__`
```python
def __repr__(self) -> str
```


String representation.



**Returns**


`str`



#### `__str__`
```python
def __str__(self) -> str
```


String conversion.



**Returns**


`str`



#### `get_load_status`
```python
def get_load_status(self) -> dict[str, Any]
```


Get debugging info about proxy state.



**Returns**


`dict[str, Any]`



#### `from_page` @classmethod
```python
def from_page(cls, page: Page, metadata: Any) -> PageProxy
```


Create proxy from full page (for testing).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | *No description provided.* |
| `metadata` | `Any` | - | *No description provided.* |







**Returns**


`PageProxy`



---
*Generated by Bengal autodoc from `bengal/bengal/core/page/proxy.py`*
