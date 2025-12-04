
---
title: "template_context"
type: "python-module"
source_file: "bengal/bengal/rendering/template_context.py"
line_number: 1
description: "Template context wrappers for ergonomic URL handling. Wraps Page and Section objects so that .url automatically includes baseurl in templates, making it impossible to forget baseurl in href/src attrib..."
---

# template_context
**Type:** Module
**Source:** [View source](bengal/bengal/rendering/template_context.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›template_context

Template context wrappers for ergonomic URL handling.

Wraps Page and Section objects so that .url automatically includes baseurl
in templates, making it impossible to forget baseurl in href/src attributes.
Provides transparent delegation to wrapped objects while adding baseurl handling.

Key Concepts:
    - Auto-baseurl: Automatically applies baseurl to .url property
    - Transparent delegation: All other properties delegate to wrapped object
    - Multiple baseurl formats: Supports path, absolute, file, and S3 URLs
    - Template ergonomics: Simplifies template code by removing baseurl handling

Related Modules:
    - bengal.rendering.template_engine: Template engine that uses wrappers
    - bengal.core.page: Page objects being wrapped
    - bengal.core.section: Section objects being wrapped

See Also:
    - bengal/rendering/template_context.py:TemplatePageWrapper for page wrapper
    - bengal/rendering/template_context.py:TemplateSectionWrapper for section wrapper

## Classes




### `TemplatePageWrapper`


Wraps Page objects to auto-apply baseurl to .url in templates.

Provides transparent wrapper that automatically applies baseurl to page URLs,
making templates ergonomic. All other page properties delegate to the wrapped
page object, maintaining full compatibility.

Creation:
    Direct instantiation: TemplatePageWrapper(page, baseurl="")
        - Created by TemplateEngine for template context
        - Requires Page instance and optional baseurl



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `_page` | - | Wrapped Page object |
| `_baseurl` | - | Base URL from site config (can be empty, path-only, or absolute) |
| `Relationships` | - | - Uses: Page for wrapped page object - Used by: TemplateEngine for template context - Used in: Templates via template context Baseurl Formats Supported: - Path-only: `/bengal` → `/bengal/docs/page/` - Absolute: `https://example.com` → `https://example.com/docs/page/` - File protocol: `file:///path/to/site` → `file:///path/to/site/docs/page/` - S3: `s3://bucket/path` → `s3://bucket/path/docs/page/` |




:::{rubric} Properties
:class: rubric-properties
:::



#### `url` @property

```python
def url(self) -> str
```
URL with baseurl applied (for templates).

This is the property templates should use for href/src attributes.
It automatically includes baseurl, so theme developers don't need
to remember to use permalink or filters.

#### `permalink` @property

```python
def permalink(self) -> str
```
Alias for url (for backward compatibility).

Both url and permalink now return the same value (with baseurl).
This maintains compatibility with existing templates that use permalink.

#### `relative_url` @property

```python
def relative_url(self) -> str
```
Relative URL without baseurl (for comparisons).

Use this when you need the relative URL for comparisons or logic.
For display URLs, use .url (which includes baseurl).




## Methods



#### `url`
```python
def url(self) -> str
```


URL with baseurl applied (for templates).

This is the property templates should use for href/src attributes.
It automatically includes baseurl, so theme developers don't need
to remember to use permalink or filters.



**Returns**


`str`



#### `permalink`
```python
def permalink(self) -> str
```


Alias for url (for backward compatibility).

Both url and permalink now return the same value (with baseurl).
This maintains compatibility with existing templates that use permalink.



**Returns**


`str`



#### `relative_url`
```python
def relative_url(self) -> str
```


Relative URL without baseurl (for comparisons).

Use this when you need the relative URL for comparisons or logic.
For display URLs, use .url (which includes baseurl).



**Returns**


`str`



#### `__init__`
```python
def __init__(self, page: Any, baseurl: str = '')
```


Initialize wrapper.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Any` | - | Page object to wrap |
| `baseurl` | `str` | `''` | Base URL from site config (can be empty, path-only, or absolute) |








#### `__getattr__`
```python
def __getattr__(self, name: str) -> Any
```


Delegate all other attributes to wrapped page.

This makes the wrapper transparent - all page properties work as expected.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | *No description provided.* |







**Returns**


`Any`



#### `__repr__`
```python
def __repr__(self) -> str
```


String representation for debugging.



**Returns**


`str`




### `TemplateSectionWrapper`


Wraps Section objects to auto-apply baseurl to .url in templates.

Provides transparent wrapper that automatically applies baseurl to section URLs,
similar to TemplatePageWrapper. Also wraps pages and subsections when accessed
to ensure consistent baseurl handling throughout the section hierarchy.

Creation:
    Direct instantiation: TemplateSectionWrapper(section, baseurl="")
        - Created by TemplateEngine for template context
        - Requires Section instance and optional baseurl



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `_section` | - | Wrapped Section object |
| `_baseurl` | - | Base URL from site config |
| `Relationships` | - | - Uses: Section for wrapped section object - Used by: TemplateEngine for template context - Used in: Templates via template context - Wraps: Pages and subsections when accessed |




:::{rubric} Properties
:class: rubric-properties
:::



#### `url` @property

```python
def url(self) -> str
```
URL with baseurl applied (for templates).

#### `permalink` @property

```python
def permalink(self) -> str
```
Alias for url (for backward compatibility).

#### `relative_url` @property

```python
def relative_url(self) -> str
```
Relative URL without baseurl (for comparisons).

#### `pages` @property

```python
def pages(self) -> list
```
Return wrapped pages.

#### `subsections` @property

```python
def subsections(self) -> list
```
Return wrapped subsections.

#### `sorted_pages` @property

```python
def sorted_pages(self) -> list
```
Return wrapped sorted pages.

#### `sorted_subsections` @property

```python
def sorted_subsections(self) -> list
```
Return wrapped sorted subsections.

#### `index_page` @property

```python
def index_page(self) -> Any
```
Return wrapped index page.




## Methods



#### `url`
```python
def url(self) -> str
```


URL with baseurl applied (for templates).



**Returns**


`str`



#### `permalink`
```python
def permalink(self) -> str
```


Alias for url (for backward compatibility).



**Returns**


`str`



#### `relative_url`
```python
def relative_url(self) -> str
```


Relative URL without baseurl (for comparisons).



**Returns**


`str`



#### `pages`
```python
def pages(self) -> list
```


Return wrapped pages.



**Returns**


`list`



#### `subsections`
```python
def subsections(self) -> list
```


Return wrapped subsections.



**Returns**


`list`



#### `sorted_pages`
```python
def sorted_pages(self) -> list
```


Return wrapped sorted pages.



**Returns**


`list`



#### `sorted_subsections`
```python
def sorted_subsections(self) -> list
```


Return wrapped sorted subsections.



**Returns**


`list`



#### `index_page`
```python
def index_page(self) -> Any
```


Return wrapped index page.



**Returns**


`Any`



#### `__init__`
```python
def __init__(self, section: Any, baseurl: str = '')
```


Initialize wrapper.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Any` | - | Section object to wrap |
| `baseurl` | `str` | `''` | Base URL from site config |








#### `__getattr__`
```python
def __getattr__(self, name: str) -> Any
```


Delegate all other attributes to wrapped section.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | *No description provided.* |







**Returns**


`Any`



#### `__repr__`
```python
def __repr__(self) -> str
```


String representation for debugging.



**Returns**


`str`




### `TemplateSiteWrapper`


Wraps Site object to auto-wrap pages/sections when accessed from templates.

When templates access site.pages or site.sections, the pages/sections
are automatically wrapped so they have .relative_url and .url includes baseurl.






:::{rubric} Properties
:class: rubric-properties
:::



#### `pages` @property

```python
def pages(self) -> list
```
Return wrapped pages.

#### `sections` @property

```python
def sections(self) -> list
```
Return wrapped sections.

#### `regular_pages` @property

```python
def regular_pages(self) -> list
```
Return wrapped regular pages.




## Methods



#### `pages`
```python
def pages(self) -> list
```


Return wrapped pages.



**Returns**


`list`



#### `sections`
```python
def sections(self) -> list
```


Return wrapped sections.



**Returns**


`list`



#### `regular_pages`
```python
def regular_pages(self) -> list
```


Return wrapped regular pages.



**Returns**


`list`



#### `__init__`
```python
def __init__(self, site: Any, baseurl: str = '')
```


Initialize wrapper.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Any` | - | Site object to wrap |
| `baseurl` | `str` | `''` | Base URL from site config |








#### `__getattr__`
```python
def __getattr__(self, name: str) -> Any
```


Delegate all other attributes to wrapped site.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | *No description provided.* |







**Returns**


`Any`

## Functions



### `wrap_for_template`


```python
def wrap_for_template(obj: Any, baseurl: str = '') -> Any
```



Wrap Page or Section objects for template context.

This function automatically detects the object type and wraps it appropriately.
Other objects are returned unchanged.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `obj` | `Any` | - | Page, Section, SimpleNamespace (special pages), or other object |
| `baseurl` | `str` | `''` | Base URL from site config |







**Returns**


`Any` - Wrapped object (if Page/Section/SimpleNamespace with url) or original object



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/template_context.py`*
