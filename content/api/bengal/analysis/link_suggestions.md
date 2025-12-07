
---
title: "link_suggestions"
type: "python-module"
source_file: "bengal/analysis/link_suggestions.py"
line_number: 1
description: "Link Suggestion Engine for Bengal SSG. Provides smart cross-linking recommendations based on: - Topic similarity (shared tags, categories, keywords) - PageRank importance (prioritize linking to high-v..."
---

# link_suggestions
**Type:** Module
**Source:** [View source](bengal/analysis/link_suggestions.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[analysis](/api/bengal/analysis/) ›link_suggestions

Link Suggestion Engine for Bengal SSG.

Provides smart cross-linking recommendations based on:
- Topic similarity (shared tags, categories, keywords)
- PageRank importance (prioritize linking to high-value pages)
- Navigation patterns (betweenness, closeness)
- Current link structure (avoid over-linking, find gaps)

Helps improve:
- Internal linking structure
- SEO through better site connectivity
- Content discoverability
- User navigation

## Classes




### `LinkSuggestion`


A suggested link between two pages.

Represents a recommendation to add a link from source page to target page
based on topic similarity, importance, and connectivity analysis.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`source`
: Page where the link should be added

`target`
: Page that should be linked to

`score`
: Recommendation score (0.0-1.0, higher is better)

`reasons`
: List of reasons why this link is suggested

:::







## Methods



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




### `LinkSuggestionResults`


Results from link suggestion analysis.

Contains all link suggestions generated for the site, along with
statistics and methods for querying suggestions.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`suggestions`
: List of all link suggestions, sorted by score

`total_suggestions`
: Total number of suggestions generated

`pages_analyzed`
: 

:::







## Methods



#### `get_suggestions_for_page`

:::{div} api-badge-group
:::

```python
def get_suggestions_for_page(self, page: Page, limit: int = 10) -> list[LinkSuggestion]
```


Get link suggestions for a specific page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page to get suggestions for |
| `limit` | `int` | `10` | Maximum number of suggestions |







:::{rubric} Returns
:class: rubric-returns
:::


`list[LinkSuggestion]` - List of LinkSuggestion objects sorted by score



#### `get_top_suggestions`

:::{div} api-badge-group
:::

```python
def get_top_suggestions(self, limit: int = 50) -> list[LinkSuggestion]
```


Get top N suggestions across all pages.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `limit` | `int` | `50` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[LinkSuggestion]`



#### `get_suggestions_by_target`

:::{div} api-badge-group
:::

```python
def get_suggestions_by_target(self, target: Page) -> list[LinkSuggestion]
```


Get all suggestions that point to a specific target page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `target` | `Page` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[LinkSuggestion]`




### `LinkSuggestionEngine`


Generate smart link suggestions to improve site connectivity.

Uses multiple signals to recommend links:
1. Topic Similarity: Pages with shared tags/categories
2. PageRank: Prioritize linking to important pages
3. Navigation Value: Link to bridge pages
4. Link Gaps: Find underlinked valuable content









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, graph: KnowledgeGraph, min_score: float = 0.3, max_suggestions_per_page: int = 10)
```


Initialize link suggestion engine.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `graph` | `KnowledgeGraph` | - | KnowledgeGraph with page connections |
| `min_score` | `float` | `0.3` | Minimum score threshold for suggestions |
| `max_suggestions_per_page` | `int` | `10` | Maximum suggestions per page |








#### `generate_suggestions`

:::{div} api-badge-group
:::

```python
def generate_suggestions(self) -> LinkSuggestionResults
```


Generate link suggestions for all pages.



:::{rubric} Returns
:class: rubric-returns
:::


`LinkSuggestionResults` - LinkSuggestionResults with all suggestions

## Functions



### `suggest_links`


```python
def suggest_links(graph: KnowledgeGraph, min_score: float = 0.3, max_suggestions_per_page: int = 10) -> LinkSuggestionResults
```



Convenience function for link suggestions.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `graph` | `KnowledgeGraph` | - | KnowledgeGraph with page connections |
| `min_score` | `float` | `0.3` | Minimum score threshold |
| `max_suggestions_per_page` | `int` | `10` | Max suggestions per page |







**Returns**


`LinkSuggestionResults` - LinkSuggestionResults with all suggestions
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = suggest_links(graph)
    >>> for suggestion in results.get_top_suggestions(20):
    ...     print(f"{suggestion.source.title} -> {suggestion.target.title}")
```



---
*Generated by Bengal autodoc from `bengal/analysis/link_suggestions.py`*

