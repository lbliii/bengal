
---
title: "bengal_streams"
type: "python-module"
source_file: "bengal/bengal/pipeline/bengal_streams.py"
line_number: 1
description: "Bengal-specific stream adapters for the reactive dataflow pipeline. This module bridges the generic pipeline primitives with Bengal\'s domain: - ContentDiscoveryStream: Discovers content files - PageSt..."
---

# bengal_streams
**Type:** Module
**Source:** [View source](bengal/bengal/pipeline/bengal_streams.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[pipeline](/api/bengal/pipeline/) ›bengal_streams

Bengal-specific stream adapters for the reactive dataflow pipeline.

This module bridges the generic pipeline primitives with Bengal's domain:
- ContentDiscoveryStream: Discovers content files
- PageStream: Creates Page objects from parsed content
- RenderStream: Renders pages with templates

These adapters wrap existing Bengal classes (ContentDiscovery, Page, etc.)
making them work with the reactive pipeline infrastructure.

Related:
    - bengal/pipeline/core.py - Base Stream class
    - bengal/pipeline/build.py - Build pipeline factory
    - bengal/discovery/content_discovery.py - Wrapped by ContentDiscoveryStream

## Classes




### `ParsedContent`


Intermediate representation of parsed content file.

Bridges ContentDiscovery output with Page creation.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `source_path` | - | Path to the source file |
| `content` | - | Raw markdown content (after frontmatter) |
| `metadata` | - | Frontmatter metadata dict |
| `content_hash` | - | Hash of file contents for cache invalidation |










### `ContentDiscoveryStream`


**Inherits from:**`Stream[ParsedContent]`Stream that discovers and parses content files.

Wraps bengal.discovery.ContentDiscovery to emit ParsedContent items
that can flow through the pipeline.









## Methods



#### `__init__`
```python
def __init__(self, content_dir: Path) -> None
```


Initialize content discovery stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content_dir` | `Path` | - | Root directory to discover content in |







**Returns**


`None`




### `RenderedPage`


A page that has been rendered to HTML.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `page` | - | Original Page object |
| `html` | - | Rendered HTML content |
| `output_path` | - | Relative path for output file |










### `FileChangeStream`


**Inherits from:**`Stream[Path]`Stream that emits changed files for incremental builds.

Used by the dev server and watch mode to emit files that have changed
since the last build.









## Methods



#### `__init__`
```python
def __init__(self, changed_files: list[Path]) -> None
```


Initialize file change stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `changed_files` | `list[Path]` | - | List of paths that have changed |







**Returns**


`None`

## Functions



### `create_content_stream`


```python
def create_content_stream(site: Site) -> Stream[ParsedContent]
```



Create a content discovery stream for a site.

Factory function that creates a properly configured ContentDiscoveryStream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Site` | - | Bengal Site instance |







**Returns**


`Stream[ParsedContent]` - Stream of ParsedContent items




### `create_page_stream`


```python
def create_page_stream(content_stream: Stream[ParsedContent], site: Site) -> Stream[Page]
```



Create a stream that transforms ParsedContent into Page objects.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content_stream` | `Stream[ParsedContent]` | - | Upstream stream of ParsedContent |
| `site` | `Site` | - | Bengal Site instance for Page creation |







**Returns**


`Stream[Page]` - Stream of Page objects




### `create_render_stream`


```python
def create_render_stream(page_stream: Stream[Page], site: Site, navigation: Any = None) -> Stream[RenderedPage]
```



Create a stream that renders Page objects to HTML.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_stream` | `Stream[Page]` | - | Upstream stream of Page objects |
| `site` | `Site` | - | Bengal Site instance |
| `navigation` | `Any` | - | Pre-built navigation (if available) |







**Returns**


`Stream[RenderedPage]` - Stream of RenderedPage objects




### `write_output`


```python
def write_output(site: Site, rendered: RenderedPage) -> None
```



Write rendered page to disk.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Site` | - | Bengal Site instance |
| `rendered` | `RenderedPage` | - | RenderedPage to write |







**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/bengal/pipeline/bengal_streams.py`*

