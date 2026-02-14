---
title: Notebooks
nav_title: Notebooks
description: Native Jupyter notebook support — drop .ipynb into content and build
weight: 35
category: how-to
icon: book
---
# Notebooks in Bengal

Bengal renders Jupyter notebooks (`.ipynb`) natively. Drop a notebook into your content directory and it builds as a page—no conversion step, no extra tooling.

:::{tip}
**New to notebooks?** Follow the [[setup|Setup Guide]] for a step-by-step walkthrough—add your first notebook, configure Download/Binder/Colab, and override metadata.
:::

## How It Works

1. Add `analysis.ipynb` to `content/docs/` (or any content section)
2. Bengal discovers it via [[ext:patitas:|Patitas]] `parse_notebook` (zero dependencies, stdlib JSON)
3. Cells become Markdown: markdown cells as-is, code cells as fenced blocks, outputs as HTML
4. The page uses the `notebook/single.html` template with download badge, kernel info, and optional Binder/Colab links (Colab auto-generated when `repo_url` is set)

## Example Notebooks

The notebooks below are live examples—they live in this docs site and render as pages.

:::{cards}
:columns: 2

:::{card} Hello Notebook
:icon: rocket
:link: ./hello-notebook

Minimal demo: one markdown cell, one code cell with output.
:::{/card}

:::{card} Content Features
:icon: layers
:link: ./content-features

Markdown, code, math ($E=mc^2$), and outputs—the full pipeline.
:::{/card}

:::{/cards}

## What Gets Rendered

| Cell Type | Result |
|-----------|--------|
| Markdown | Rendered as Markdown (headings, lists, **bold**, math, etc.) |
| Code | Fenced code block with syntax highlighting (Rosettes) |
| Code output (stream) | `<div class="nb-output"><pre>...</pre></div>` — compact styling |
| Code output (execute_result) | Text as `nb-output`, images as `nb-output--image`, HTML as `nb-output--html` |
| Code output (error) | `<div class="nb-output nb-output--error"><pre class="notebook-error">...</pre></div>` |

## Metadata

Notebook metadata flows into page frontmatter:

- **title** — from `notebook.metadata.title` or filename stem
- **type** — `notebook` (for template selection)
- **notebook.kernel_name** — e.g. `python3`
- **notebook.cell_count** — number of cells

Override in notebook metadata (Jupyter Book / JupyterLab conventions) or via cascade from section `_index.md`.

## Requirements

- **nbformat 4 or 5** — Modern notebooks only
- **No nbformat dependency** — Patitas parses JSON with stdlib; Bengal has zero extra deps for notebooks

::::{seealso}
- [[docs/content/authoring/code-blocks|Code Blocks]] — Syntax highlighting for code cells
- [[docs/content/authoring/math|Math and LaTeX]] — Inline and block equations in markdown cells
- [[ext:patitas:README|Patitas]] — The parser that powers notebook conversion
::::
