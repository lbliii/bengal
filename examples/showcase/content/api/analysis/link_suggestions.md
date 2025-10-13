
---
title: "analysis.link_suggestions"
type: python-module
source_file: "bengal/analysis/link_suggestions.py"
css_class: api-content
description: "Link Suggestion Engine for Bengal SSG.  Provides smart cross-linking recommendations based on: - Topic similarity (shared tags, categories, keywords) - PageRank importance (prioritize linking to hi..."
---

# analysis.link_suggestions

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

---

## Classes

### `LinkSuggestion`


A suggested link between two pages.

Represents a recommendation to add a link from source page to target page
based on topic similarity, importance, and connectivity analysis.

Attributes:
    source: Page where the link should be added
    target: Page that should be linked to
    score: Recommendation score (0.0-1.0, higher is better)
    reasons: List of reasons why this link is suggested

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`source`** (`'Page'`)- **`target`** (`'Page'`)- **`score`** (`float`)- **`reasons`** (`list[str]`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `__repr__`
```python
def __repr__(self) -> str
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---

### `LinkSuggestionResults`


Results from link suggestion analysis.

Contains all link suggestions generated for the site, along with
statistics and methods for querying suggestions.

Attributes:
    suggestions: List of all link suggestions, sorted by score
    total_suggestions: Total number of suggestions generated

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`suggestions`** (`list[LinkSuggestion]`)- **`total_suggestions`** (`int`)- **`pages_analyzed`** (`int`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `get_suggestions_for_page`
```python
def get_suggestions_for_page(self, page: 'Page', limit: int = 10) -> list[LinkSuggestion]
```

Get link suggestions for a specific page.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page`** (`'Page'`) - Page to get suggestions for
- **`limit`** (`int`) = `10` - Maximum number of suggestions

:::{rubric} Returns
:class: rubric-returns
:::
`list[LinkSuggestion]` - List of LinkSuggestion objects sorted by score




---
#### `get_top_suggestions`
```python
def get_top_suggestions(self, limit: int = 50) -> list[LinkSuggestion]
```

Get top N suggestions across all pages.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`limit`** (`int`) = `50`

:::{rubric} Returns
:class: rubric-returns
:::
`list[LinkSuggestion]`




---
#### `get_suggestions_by_target`
```python
def get_suggestions_by_target(self, target: 'Page') -> list[LinkSuggestion]
```

Get all suggestions that point to a specific target page.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`target`** (`'Page'`)

:::{rubric} Returns
:class: rubric-returns
:::
`list[LinkSuggestion]`




---

### `LinkSuggestionEngine`


Generate smart link suggestions to improve site connectivity.

Uses multiple signals to recommend links:
1. Topic Similarity: Pages with shared tags/categories
2. PageRank: Prioritize linking to important pages
3. Navigation Value: Link to bridge pages
4. Link Gaps: Find underlinked valuable content




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, graph: 'KnowledgeGraph', min_score: float = 0.3, max_suggestions_per_page: int = 10)
```

Initialize link suggestion engine.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`graph`** (`'KnowledgeGraph'`) - KnowledgeGraph with page connections
- **`min_score`** (`float`) = `0.3` - Minimum score threshold for suggestions
- **`max_suggestions_per_page`** (`int`) = `10` - Maximum suggestions per page





---
#### `generate_suggestions`
```python
def generate_suggestions(self) -> LinkSuggestionResults
```

Generate link suggestions for all pages.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`LinkSuggestionResults` - LinkSuggestionResults with all suggestions




---


## Functions

### `suggest_links`
```python
def suggest_links(graph: 'KnowledgeGraph', min_score: float = 0.3, max_suggestions_per_page: int = 10) -> LinkSuggestionResults
```

Convenience function for link suggestions.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`graph`** (`'KnowledgeGraph'`) - KnowledgeGraph with page connections
- **`min_score`** (`float`) = `0.3` - Minimum score threshold
- **`max_suggestions_per_page`** (`int`) = `10` - Max suggestions per page

:::{rubric} Returns
:class: rubric-returns
:::
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
