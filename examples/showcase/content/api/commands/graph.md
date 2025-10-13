
---
title: "commands.graph"
type: python-module
source_file: "bengal/cli/commands/graph.py"
css_class: api-content
description: "Graph analysis and knowledge graph commands."
---

# commands.graph

Graph analysis and knowledge graph commands.

---


## Functions

### `graph`
```python
def graph(show_stats: bool, tree: bool, output: str, config: str, source: str) -> None
```

📊 Analyze site structure and connectivity.

Builds a knowledge graph of your site to:
- Find orphaned pages (no incoming links)
- Identify hub pages (highly connected)
- Understand content structure
- Generate interactive visualizations



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `show_stats` | `bool` | - | - |
| `tree` | `bool` | - | - |
| `output` | `str` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Show connectivity statistics
```


---
### `pagerank`
```python
def pagerank(top_n: int, damping: float, format: str, config: str, source: str) -> None
```

🏆 Analyze page importance using PageRank algorithm.

Computes PageRank scores for all pages based on their link structure.
Pages that are linked to by many important pages receive high scores.

Use PageRank to:
- Identify your most important content
- Prioritize content updates
- Guide navigation and sitemap design
- Find underlinked valuable content



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_n` | `int` | - | - |
| `damping` | `float` | - | - |
| `format` | `str` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Show top 20 most important pages
```


---
### `communities`
```python
def communities(min_size: int, resolution: float, top_n: int, format: str, seed: int, config: str, source: str) -> None
```

🔍 Discover topical communities in your content.

Uses the Louvain algorithm to find natural clusters of related pages.
Communities represent topic areas or content groups based on link structure.

Use community detection to:
- Discover hidden content structure
- Organize content into logical groups
- Identify topic clusters
- Guide taxonomy creation



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `min_size` | `int` | - | - |
| `resolution` | `float` | - | - |
| `top_n` | `int` | - | - |
| `format` | `str` | - | - |
| `seed` | `int` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Show top 10 communities
```


---
### `bridges`
```python
def bridges(top_n: int, metric: str, format: str, config: str, source: str) -> None
```

🌉 Identify bridge pages and navigation bottlenecks.

Analyzes navigation paths to find:
- Bridge pages (high betweenness): Pages that connect different parts of the site
- Accessible pages (high closeness): Pages easy to reach from anywhere
- Navigation bottlenecks: Critical pages for site navigation

Use path analysis to:
- Optimize navigation structure
- Identify critical pages
- Improve content discoverability
- Find navigation gaps



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_n` | `int` | - | - |
| `metric` | `str` | - | - |
| `format` | `str` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Show top 20 bridge pages
```


---
### `suggest`
```python
def suggest(top_n: int, min_score: float, format: str, config: str, source: str) -> None
```

💡 Generate smart link suggestions to improve internal linking.

Analyzes your content to recommend links based on:
- Topic similarity (shared tags/categories)
- Page importance (PageRank scores)
- Navigation value (bridge pages)
- Link gaps (underlinked content)

Use link suggestions to:
- Improve internal linking structure
- Boost SEO through better connectivity
- Increase content discoverability
- Fill navigation gaps



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_n` | `int` | - | - |
| `min_score` | `float` | - | - |
| `format` | `str` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Show top 50 link suggestions
```


---
