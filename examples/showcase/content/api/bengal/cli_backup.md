
---
title: "bengal.cli_backup"
type: python-module
source_file: "../../bengal/cli_backup.py"
css_class: api-content
description: "Command-line interface for Bengal SSG."
---

# bengal.cli_backup

Command-line interface for Bengal SSG.

---

## Classes

### `BengalGroup`

**Inherits from:** `click.Group`
Custom Click group with typo detection and suggestions.




```{rubric} Methods
:class: rubric-methods
```
#### `resolve_command`
```python
def resolve_command(self, ctx, args)
```

Resolve command with fuzzy matching for typos.



```{rubric} Parameters
:class: rubric-parameters
```
- **`self`**
- **`ctx`**
- **`args`**












---


## Functions

### `main`
```python
def main() -> None
```

ᓚᘏᗢ Bengal SSG - A high-performance static site generator.




```{rubric} Returns
:class: rubric-returns
```
`None`










---
### `build`
```python
def build(parallel: bool, incremental: bool, memory_optimized: bool, profile: str, perf_profile: str, use_theme_dev: bool, use_dev: bool, verbose: bool, strict: bool, debug: bool, validate: bool, autodoc: bool, config: str, quiet: bool, full_output: bool, log_file: str, source: str) -> None
```

🔨 Build the static site.

Generates HTML files from your content, applies templates,
processes assets, and outputs a production-ready site.



```{rubric} Parameters
:class: rubric-parameters
```
````{dropdown} 17 parameters (click to expand)
:open: false

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `parallel` | `bool` | - | - |
| `incremental` | `bool` | - | - |
| `memory_optimized` | `bool` | - | - |
| `profile` | `str` | - | - |
| `perf_profile` | `str` | - | - |
| `use_theme_dev` | `bool` | - | - |
| `use_dev` | `bool` | - | - |
| `verbose` | `bool` | - | - |
| `strict` | `bool` | - | - |
| `debug` | `bool` | - | - |
| `validate` | `bool` | - | - |
| `autodoc` | `bool` | - | - |
| `config` | `str` | - | - |
| `quiet` | `bool` | - | - |
| `full_output` | `bool` | - | - |
| `log_file` | `str` | - | - |
| `source` | `str` | - | - |

````


```{rubric} Returns
:class: rubric-returns
```
`None`










---
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



```{rubric} Parameters
:class: rubric-parameters
```
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `show_stats` | `bool` | - | - |
| `tree` | `bool` | - | - |
| `output` | `str` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |


```{rubric} Returns
:class: rubric-returns
```
`None`







```{rubric} Examples
:class: rubric-examples
```
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



```{rubric} Parameters
:class: rubric-parameters
```
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_n` | `int` | - | - |
| `damping` | `float` | - | - |
| `format` | `str` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |


```{rubric} Returns
:class: rubric-returns
```
`None`







```{rubric} Examples
:class: rubric-examples
```
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



```{rubric} Parameters
:class: rubric-parameters
```
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `min_size` | `int` | - | - |
| `resolution` | `float` | - | - |
| `top_n` | `int` | - | - |
| `format` | `str` | - | - |
| `seed` | `int` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |


```{rubric} Returns
:class: rubric-returns
```
`None`







```{rubric} Examples
:class: rubric-examples
```
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



```{rubric} Parameters
:class: rubric-parameters
```
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_n` | `int` | - | - |
| `metric` | `str` | - | - |
| `format` | `str` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |


```{rubric} Returns
:class: rubric-returns
```
`None`







```{rubric} Examples
:class: rubric-examples
```
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



```{rubric} Parameters
:class: rubric-parameters
```
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_n` | `int` | - | - |
| `min_score` | `float` | - | - |
| `format` | `str` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |


```{rubric} Returns
:class: rubric-returns
```
`None`







```{rubric} Examples
:class: rubric-examples
```
```python
# Show top 50 link suggestions
```




---
### `serve`
```python
def serve(host: str, port: int, watch: bool, auto_port: bool, open_browser: bool, config: str, source: str) -> None
```

🚀 Start development server with hot reload.

Watches for changes in content, assets, and templates,
automatically rebuilding the site when files are modified.



```{rubric} Parameters
:class: rubric-parameters
```
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `host` | `str` | - | - |
| `port` | `int` | - | - |
| `watch` | `bool` | - | - |
| `auto_port` | `bool` | - | - |
| `open_browser` | `bool` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |


```{rubric} Returns
:class: rubric-returns
```
`None`










---
### `clean`
```python
def clean(force: bool, config: str, source: str) -> None
```

🧹 Clean the output directory.

Removes all generated files from the output directory.



```{rubric} Parameters
:class: rubric-parameters
```
- **`force`** (`bool`)
- **`config`** (`str`)
- **`source`** (`str`)


```{rubric} Returns
:class: rubric-returns
```
`None`










---
### `cleanup`
```python
def cleanup(force: bool, port: int, source: str) -> None
```

🔧 Clean up stale Bengal server processes.

Finds and terminates any stale 'bengal serve' processes that may be
holding ports or preventing new servers from starting.

This is useful if a previous server didn't shut down cleanly.



```{rubric} Parameters
:class: rubric-parameters
```
- **`force`** (`bool`)
- **`port`** (`int`)
- **`source`** (`str`)


```{rubric} Returns
:class: rubric-returns
```
`None`










---
### `new`
```python
def new() -> None
```

✨ Create new site, page, or section.




```{rubric} Returns
:class: rubric-returns
```
`None`










---
### `site`
```python
def site(name: str, theme: str) -> None
```

🏗️  Create a new Bengal site.



```{rubric} Parameters
:class: rubric-parameters
```
- **`name`** (`str`)
- **`theme`** (`str`)


```{rubric} Returns
:class: rubric-returns
```
`None`










---
### `page`
```python
def page(name: str, section: str) -> None
```

📄 Create a new page.



```{rubric} Parameters
:class: rubric-parameters
```
- **`name`** (`str`)
- **`section`** (`str`)


```{rubric} Returns
:class: rubric-returns
```
`None`










---
### `autodoc`
```python
def autodoc(source: tuple, output: str, clean: bool, parallel: bool, verbose: bool, stats: bool, config: str, python_only: bool, cli_only: bool) -> None
```

📚 Generate comprehensive API documentation (Python + CLI).

Automatically generates both Python API docs and CLI docs based on
your bengal.toml configuration. Use --python-only or --cli-only to
generate specific types.



```{rubric} Parameters
:class: rubric-parameters
```
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `source` | `tuple` | - | - |
| `output` | `str` | - | - |
| `clean` | `bool` | - | - |
| `parallel` | `bool` | - | - |
| `verbose` | `bool` | - | - |
| `stats` | `bool` | - | - |
| `config` | `str` | - | - |
| `python_only` | `bool` | - | - |
| `cli_only` | `bool` | - | - |


```{rubric} Returns
:class: rubric-returns
```
`None`







```{rubric} Examples
:class: rubric-examples
```
```python
bengal autodoc                    # Generate all configured docs
```




---
### `autodoc_cli`
```python
def autodoc_cli(app: str, framework: str, output: str, include_hidden: bool, clean: bool, verbose: bool, config: str) -> None
```

⌨️  Generate CLI documentation from Click/argparse/typer apps.

Extracts documentation from command-line interfaces to create
comprehensive command reference documentation.



```{rubric} Parameters
:class: rubric-parameters
```
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `app` | `str` | - | - |
| `framework` | `str` | - | - |
| `output` | `str` | - | - |
| `include_hidden` | `bool` | - | - |
| `clean` | `bool` | - | - |
| `verbose` | `bool` | - | - |
| `config` | `str` | - | - |


```{rubric} Returns
:class: rubric-returns
```
`None`







```{rubric} Examples
:class: rubric-examples
```
```python
bengal autodoc-cli --app bengal.cli:main --output content/cli
```




---
### `perf`
```python
def perf(last, format, compare)
```

Show performance metrics and trends.

Displays build performance metrics collected from previous builds.
Metrics are automatically saved to .bengal-metrics/ directory.



```{rubric} Parameters
:class: rubric-parameters
```
- **`last`**
- **`format`**
- **`compare`**









```{rubric} Examples
:class: rubric-examples
```
```python
bengal perf              # Show last 10 builds as table
```




---
