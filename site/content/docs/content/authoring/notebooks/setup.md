---
title: Notebook Setup Guide
description: Step-by-step guide to adding Jupyter notebooks to your Bengal site
weight: 5
---

# Notebook Setup Guide

This guide walks you through adding Jupyter notebooks to your Bengal site as an end user. No conversion tools, no extra dependencies—just drop `.ipynb` files and build.

:::{steps}
:::{step} Create or Export a Notebook
Create a notebook in Jupyter Lab, Jupyter Notebook, or VS Code. Save it as `.ipynb` (nbformat 4 or 5).

**Example:** `analysis.ipynb` with a markdown cell and a Python code cell.
:::{/step}

:::{step} Add It to Your Content
Copy the notebook into any content directory. Bengal treats it like a Markdown page.

```
content/
  docs/
    tutorials/
      analysis.ipynb    ← Add here
```

Or nest it in a section:

```
content/
  docs/
    guides/
      _index.md
      getting-started.ipynb
      advanced.ipynb
```

The notebook will appear in the sidebar nav alongside other pages in that section.
:::{/step}

:::{step} Build
```bash
bengal build
```

That's it. Bengal discovers the notebook, parses it via Patitas (stdlib JSON, no nbformat), and renders it as a page with:

- **Left sidebar** — Same doc navigation as your other pages
- **Page hero** — Breadcrumbs, title, metadata (kernel, cell count)
- **Content** — Markdown cells as prose, code cells as fenced blocks with syntax highlighting, outputs as HTML
- **Right sidebar** — Table of contents (from markdown headings), contextual graph
- **Download button** — Links to the `.ipynb` file (auto-generated)
- **Share** — LLM text, AI assistants
:::{/step}

:::{step} (Optional) Add Binder or Colab
To let readers run your notebook in the cloud:

**Binder** — Add `binder_url` in section cascade or notebook frontmatter:

```yaml
# Section cascade in content/docs/notebooks/_index.md
---
binder_url: https://mybinder.org/v2/gh/your-org/your-repo/main?filepath=content/docs/notebooks/
---
```

**Colab (auto-generated)** — Add `repo_url` to `[params]` in `bengal.toml` (or `config/_default/params.yaml`):

```toml
[params]
repo_url = "https://github.com/your-org/your-repo"
colab_branch = "main"   # optional, default: main
colab_path_prefix = "site"   # when site lives in repo subdirectory (e.g. site/content/...)
```

The Colab button will appear on every notebook page. Override per-page with `colab_url` in frontmatter if needed.
:::{/step}

:::{step} (Optional) Override Metadata
Notebook metadata (kernel, title, etc.) flows from the `.ipynb` file. Override via frontmatter in a companion `_index.md` or in the notebook's own metadata (Jupyter conventions).

| Field | Source | Override |
|-------|--------|----------|
| title | `notebook.metadata.title` or filename | `title:` in frontmatter |
| description | — | `description:` in frontmatter |
| download_url | Auto from source | `download_url:` (rare) |
| binder_url | — | `binder_url:` in cascade |
| colab_url | Auto from `repo_url` + `colab_branch` | `colab_url:` in cascade (overrides) |
:::{/step}
:::{/steps}

---

## What You Get

| Output | Purpose |
|--------|---------|
| HTML page | Rendered notebook with doc layout |
| `index.txt` | LLM-friendly plain text (for AI, RAG) |
| `index.json` | Structured data (search index) |
| `.ipynb` copy | Download link for readers |

Notebooks are included in search, sitemaps, and the site index—same as regular docs.

---

## Troubleshooting

**Download button missing?** The `.ipynb` is copied to output automatically. If the button doesn't appear, check that the page has a valid `source_path` (e.g. the notebook was discovered from your content dir).

**Binder not showing?** Add `binder_url` in your section cascade or notebook frontmatter.

**Colab not showing?** Add `repo_url` to `[params]` in `bengal.toml` or `config/_default/params.yaml` for auto-generation, or set `colab_url` explicitly in frontmatter/cascade.

**CI/CD:** In GitHub Actions, `repo_url` and `colab_branch` are inferred automatically. Override with `BENGALxPARAMSxREPO_URL` or `BENGALxPARAMSxCOLAB_BRANCH` env vars (Hugo-style).

**Wrong nav order?** Use `weight` in frontmatter (lower = higher in nav). Same as Markdown pages.

---

::::{seealso}
- [[docs/content/authoring/notebooks|Notebooks overview]] — What gets rendered, metadata, examples
- [[docs/content/authoring/code-blocks|Code Blocks]] — Syntax highlighting for code cells
- [[ext:patitas:README|Patitas]] — The parser that powers notebook conversion
::::
