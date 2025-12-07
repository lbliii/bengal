
---
title: "page"
type: "python-module"
source_file: "bengal/core/page/__init__.py"
line_number: 1
description: "Page representation for content pages in Bengal SSG. This module provides the main Page class, which combines multiple mixins to provide a complete page interface while maintaining separation of conce..."
---

# page
**Type:** Module
**Source:** [View source](bengal/core/page/__init__.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[core](/api/bengal/core/) ›page

Page representation for content pages in Bengal SSG.

This module provides the main Page class, which combines multiple mixins
to provide a complete page interface while maintaining separation of concerns.
Pages represent markdown content files and provide metadata, navigation,
content processing, and template rendering capabilities.

Key Concepts:
    - Mixin architecture: Separated concerns via mixins (metadata, content, navigation)
    - Hashability: Pages hashable by source_path for set operations
    - AST-based content: Content represented as AST for efficient processing
    - Cacheable metadata: PageCore provides cacheable page metadata

Related Modules:
    - bengal.core.page.page_core: Cacheable page metadata
    - bengal.core.page.proxy: Lazy-loaded page placeholder
    - bengal.rendering.renderer: Page rendering logic
    - bengal.orchestration.content: Content discovery and page creation

See Also:
    - bengal/core/page/__init__.py:Page class for page representation
    - plan/active/rfc-content-ast-architecture.md: AST architecture RFC

## Classes




### `Page`


**Inherits from:**`PageMetadataMixin`,`PageNavigationMixin`,`PageComputedMixin`,`PageRelationshipsMixin`,`PageOperationsMixin`,`PageContentMixin`Represents a single content page.

HASHABILITY:
============
Pages are hashable based on their source_path, allowing them to be stored
in sets and used as dictionary keys. This enables:
- Fast membership tests (O(1) instead of O(n))
- Automatic deduplication with sets
- Set operations for page analysis
- Direct use as dictionary keys

Two pages with the same source_path are considered equal, even if their
content differs. The hash is stable throughout the page lifecycle because
source_path is immutable. Mutable fields (content, rendered_html, etc.)
do not affect the hash or equality.

BUILD LIFECYCLE:
================
Pages progress through distinct build phases. Properties have different
availability depending on the current phase:

1. Discovery (content_discovery.py)
   ✅ Available: source_path, content, metadata, title, slug, date
   ❌ Not available: toc, parsed_ast, toc_items, rendered_html

2. Parsing (pipeline.py)
   ✅ Available: All Stage 1 + toc, parsed_ast
   ✅ toc_items can be accessed (will extract from toc)

3. Rendering (pipeline.py)
   ✅ Available: All previous + rendered_html, output_path
   ✅ All properties fully populated

Note: Some properties like toc_items can be accessed early (returning [])
but won't cache empty results, allowing proper extraction after parsing.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`_global_missing_section_warnings`
: 

`_MAX_WARNING_KEYS`
: 

`source_path`
: Path to the source content file

`core`
: 

`content`
: Raw content (Markdown, etc.)

`metadata`
: Frontmatter metadata (title, date, tags, etc.)

`parsed_ast`
: Abstract Syntax Tree from parsed content

`rendered_html`
: Rendered HTML output

`output_path`
: Path where the rendered page will be written

`links`
: List of links found in the page

`tags`
: Tags associated with the page

`version`
: Version information for versioned content

`toc`
: Table of contents HTML (auto-generated from headings)

`related_posts`
: Related pages (pre-computed during build based on tag overlap)

`lang`
: 

`translation_key`
: 

`aliases`
: 

`_site`
: 

`_section_path`
: 

`_toc_items_cache`
: 

`_ast_cache`
: 

`_html_cache`
: 

`_plain_text_cache`
: 

`toc_items`
: Structured TOC data for custom rendering

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `relative_path` @property

```python
def relative_path(self) -> str
```
Get relative path string (alias for source_path as string).

Used by templates and filtering where a string path is expected.
This provides backward compatibility and convenience.

#### `_section` @property

```python
def _section(self) -> Any | None
```
Get the section this page belongs to (lazy lookup via path).

This property performs a path-based lookup in the site's section registry,
enabling stable section references across rebuilds when Section objects
are recreated.




## Methods



#### `__post_init__`

:::{div} api-badge-group
:::

```python
def __post_init__(self) -> None
```


Initialize computed fields and PageCore.



:::{rubric} Returns
:class: rubric-returns
:::


`None`




#### `normalize_core_paths`

:::{div} api-badge-group
:::

```python
def normalize_core_paths(self) -> None
```


Normalize PageCore paths to be relative (for cache consistency).

This should be called before caching to ensure all paths are relative
to the site root, preventing absolute path leakage into cache.

Note: Directly mutates self.core.source_path since dataclasses are mutable.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `__hash__`

:::{div} api-badge-group
:::

```python
def __hash__(self) -> int
```


Hash based on source_path for stable identity.

The hash is computed from the page's source_path, which is immutable
throughout the page lifecycle. This allows pages to be stored in sets
and used as dictionary keys.



:::{rubric} Returns
:class: rubric-returns
:::


`int` - Integer hash of the source path



#### `__eq__`

:::{div} api-badge-group
:::

```python
def __eq__(self, other: Any) -> bool
```


Pages are equal if they have the same source path.

Equality is based on source_path only, not on content or other
mutable fields. This means two Page objects representing the same
source file are considered equal, even if their processed content
differs.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `other` | `Any` | - | Object to compare with |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if other is a Page with the same source_path



#### `__repr__`

:::{div} api-badge-group
:::

```python
def __repr__(self) -> str
```


*No description provided.*



:::{rubric} Returns
:class: rubric-returns
:::


`str`



---
*Generated by Bengal autodoc from `bengal/core/page/__init__.py`*

