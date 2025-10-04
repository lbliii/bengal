---
title: "bengal.cli"
layout: api-reference
type: python-module
source_file: "../../bengal/cli.py"
---

# bengal.cli

Command-line interface for Bengal SSG.

**Source:** `../../bengal/cli.py`

---


## Functions

### main

```python
def main() -> None
```

🐯 Bengal SSG - A high-performance static site generator.

Fast & fierce static site generation with personality!


**Returns:** `None`





---
### build

```python
def build(parallel: bool, incremental: bool, verbose: bool, strict: bool, debug: bool, validate: bool, config: str, quiet: bool, source: str) -> None
```

🔨 Build the static site.

Generates HTML files from your content, applies templates,
processes assets, and outputs a production-ready site.

**Parameters:**

- **parallel** (`bool`)
- **incremental** (`bool`)
- **verbose** (`bool`)
- **strict** (`bool`)
- **debug** (`bool`)
- **validate** (`bool`)
- **config** (`str`)
- **quiet** (`bool`)
- **source** (`str`)

**Returns:** `None`





---
### serve

```python
def serve(host: str, port: int, watch: bool, auto_port: bool, open_browser: bool, config: str, source: str) -> None
```

🚀 Start development server with hot reload.

Watches for changes in content, assets, and templates,
automatically rebuilding the site when files are modified.

**Parameters:**

- **host** (`str`)
- **port** (`int`)
- **watch** (`bool`)
- **auto_port** (`bool`)
- **open_browser** (`bool`)
- **config** (`str`)
- **source** (`str`)

**Returns:** `None`





---
### clean

```python
def clean(force: bool, config: str, source: str) -> None
```

🧹 Clean the output directory.

Removes all generated files from the output directory.

**Parameters:**

- **force** (`bool`)
- **config** (`str`)
- **source** (`str`)

**Returns:** `None`





---
### cleanup

```python
def cleanup(force: bool, port: int, source: str) -> None
```

🔧 Clean up stale Bengal server processes.

Finds and terminates any stale 'bengal serve' processes that may be
holding ports or preventing new servers from starting.

This is useful if a previous server didn't shut down cleanly.

**Parameters:**

- **force** (`bool`)
- **port** (`int`)
- **source** (`str`)

**Returns:** `None`





---
### new

```python
def new() -> None
```

✨ Create new site, page, or section.


**Returns:** `None`





---
### site

```python
def site(name: str, theme: str) -> None
```

🏗️  Create a new Bengal site.

**Parameters:**

- **name** (`str`)
- **theme** (`str`)

**Returns:** `None`





---
### page

```python
def page(name: str, section: str) -> None
```

📄 Create a new page.

**Parameters:**

- **name** (`str`)
- **section** (`str`)

**Returns:** `None`





---
### autodoc

```python
def autodoc(source: tuple, output: str, clean: bool, parallel: bool, verbose: bool, stats: bool, config: str) -> None
```

📚 Generate API documentation from Python source code.

Extracts documentation via AST parsing (no imports needed!).
Fast, reliable, and works even with complex dependencies.

**Parameters:**

- **source** (`tuple`)
- **output** (`str`)
- **clean** (`bool`)
- **parallel** (`bool`)
- **verbose** (`bool`)
- **stats** (`bool`)
- **config** (`str`)

**Returns:** `None`


**Examples:**

bengal autodoc --source src/mylib --output content/api




---
