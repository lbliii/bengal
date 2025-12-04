
---
title: "init"
type: "python-module"
source_file: "bengal/bengal/cli/commands/init.py"
line_number: 1
description: "Commands for initializing site structure. This module provides the \'bengal init\' command for quickly scaffolding site structure with sections and sample content. Features: - Create multiple sections a..."
---

# init
**Type:** Module
**Source:** [View source](bengal/bengal/cli/commands/init.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cli](/api/bengal/cli/) ›[commands](/api/bengal/cli/commands/) ›init

Commands for initializing site structure.

This module provides the 'bengal init' command for quickly scaffolding
site structure with sections and sample content.

Features:
- Create multiple sections at once
- Generate sample content with context-aware naming
- Preview changes with dry-run mode
- Smart name sanitization
- Staggered dates for blog posts

## Classes




### `FileOperation`


Represents a file operation (create/overwrite).



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `path` | - | Path to the file |
| `content` | - | Content to write |
| `is_overwrite` | - | Whether this overwrites an existing file |







## Methods



#### `__init__`
```python
def __init__(self, path: Path, content: str, is_overwrite: bool = False)
```


Initialize a file operation.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `path` | `Path` | - | Path to the file |
| `content` | `str` | - | Content to write |
| `is_overwrite` | `bool` | `False` | Whether this overwrites an existing file |








#### `execute`
```python
def execute(self) -> None
```


Execute the file operation (write to disk).



**Returns**


`None`



#### `size_bytes`
```python
def size_bytes(self) -> int
```


Get the content size in bytes.



**Returns**


`int` - Size of content when encoded as UTF-8

## Functions



### `slugify`


```python
def slugify(text: str) -> str
```



Convert text to URL-friendly slug.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | The text to convert to a slug |







**Returns**


`str` - URL-friendly slug with lowercase letters, numbers, and hyphens
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> slugify("Hello World")
    'hello-world'
    >>> slugify("My Blog Post!")
    'my-blog-post'
```





### `titleize`


```python
def titleize(slug: str) -> str
```



Convert slug to title case.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `slug` | `str` | - | The slug to convert (e.g., 'hello-world') |







**Returns**


`str` - Title-cased string (e.g., 'Hello World')




### `generate_section_index`


```python
def generate_section_index(section_name: str, weight: int) -> str
```



Generate content for a section _index.md file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section_name` | `str` | - | The section slug (e.g., 'blog') |
| `weight` | `int` | - | The section weight for menu ordering |







**Returns**


`str` - Markdown content for the section index file




### `generate_sample_page`


```python
def generate_sample_page(section_name: str, page_name: str, page_number: int, date: datetime | None = None) -> str
```



Generate content for a sample page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section_name` | `str` | - | The section slug this page belongs to |
| `page_name` | `str` | - | The page slug |
| `page_number` | `int` | - | Page number (currently unused, reserved for future use) |
| `date` | `datetime \| None` | - | Publication date (defaults to now) |







**Returns**


`str` - Markdown content for the sample page




### `get_sample_page_names`


```python
def get_sample_page_names(section_name: str, count: int) -> list[str]
```



Generate sample page names for a section.

Uses context-aware naming based on section type:
- 'blog' gets: welcome-post, getting-started, etc.
- 'projects'/'portfolio' get: project-alpha, project-beta, etc.
- 'docs'/'documentation' get: introduction, quickstart, etc.
- Others get generic: {section}-page-1, {section}-page-2, etc.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section_name` | `str` | - | The section slug |
| `count` | `int` | - | Number of page names to generate |







**Returns**


`list[str]` - List of page slugs (limited to requested count)




### `plan_init_operations`


```python
def plan_init_operations(content_dir: Path, sections: list[str], with_content: bool = False, pages_per_section: int = DEFAULT_PAGES_PER_SECTION, force: bool = False) -> tuple[list[FileOperation], list[str]]
```



Plan all file operations for initialization.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content_dir` | `Path` | - | Path to the content directory |
| `sections` | `list[str]` | - | List of section slugs to create |
| `with_content` | `bool` | `False` | Whether to generate sample pages |
| `pages_per_section` | `int` | `DEFAULT_PAGES_PER_SECTION` | Number of sample pages per section |
| `force` | `bool` | `False` | Whether to overwrite existing sections |







**Returns**


`tuple[list[FileOperation], list[str]]` - Tuple of (list of file operations, list of warning messages)




### `format_file_tree`


```python
def format_file_tree(operations: list[FileOperation], content_dir: Path) -> str
```



Format operations as a tree structure for preview.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `operations` | `list[FileOperation]` | - | List of file operations to format |
| `content_dir` | `Path` | - | Base content directory for relative paths |







**Returns**


`str` - Formatted tree structure as a string




### `init`


```python
def init(sections: tuple[str, ...], with_content: bool, pages_per_section: int, dry_run: bool, force: bool) -> None
```



🏗️  Initialize site structure with sections and pages.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `sections` | `tuple[str, ...]` | - | *No description provided.* |
| `with_content` | `bool` | - | *No description provided.* |
| `pages_per_section` | `int` | - | *No description provided.* |
| `dry_run` | `bool` | - | *No description provided.* |
| `force` | `bool` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal init --sections blog --sections projects --sections about

  bengal init --sections blog --with-content --pages-per-section 10

  bengal init --sections docs --sections guides --dry-run

  bengal init  # Uses default 'blog' section
```



---
*Generated by Bengal autodoc from `bengal/bengal/cli/commands/init.py`*
