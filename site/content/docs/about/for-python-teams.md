---
title: For Python Teams
description: Why Bengal is the natural documentation choice for teams already working in Python
weight: 8
icon: python
tags:
- python
- teams
- documentation
- jupyter
- autodoc
keywords:
- python documentation generator
- python static site generator
- python docs toolchain
- jupyter documentation
- autodoc python
- mkdocs alternative
- sphinx alternative
---

# For Python Teams

If your codebase is Python and your team thinks in Python, your documentation toolchain should be Python too. Bengal is built for this: same language end to end, same package manager, same debugging tools, same CI runner.

## One Language, One Toolchain

Most Python documentation setups involve hidden dependencies on other ecosystems:

| Tool | Python? | But also... |
|------|---------|-------------|
| Sphinx | Yes | reStructuredText DSL, Make/Tox wrappers, extension debugging is archaeology |
| MkDocs | Yes | Jinja2 GIL contention at scale, limited programmatic content |
| Docusaurus | No | Node.js, npm, React, MDX |
| Astro | No | Node.js, npm, Vite |

Bengal's stack is pure Python at every layer:

| Layer | Library | What it replaces |
|-------|---------|-----------------|
| Markdown parsing | [Patitas](https://github.com/lbliii/patitas) | mistune, markdown-it, MyST-Parser |
| Syntax highlighting | [Rosettes](https://github.com/lbliii/rosettes) | Pygments (3.75x faster, O(n) guaranteed) |
| Templates | [Kida](https://github.com/lbliii/kida) | Jinja2 (1.81x faster under concurrency) |
| Dev server | [Pounce](https://github.com/lbliii/pounce) | livereload, mkdocs serve |

Every library is readable Python source you can `breakpoint()` into. No compiled extensions in the critical path. No JavaScript toolchains to maintain.

## Jupyter Notebooks as Pages

Bengal renders `.ipynb` files as first-class pages — code cells, outputs, and Markdown cells become documentation without export steps:

```
content/
  tutorials/
    data-pipeline.ipynb    # Rendered as /tutorials/data-pipeline/
    model-training.ipynb   # Rendered as /tutorials/model-training/
```

Notebooks get the same treatment as Markdown pages: frontmatter, table of contents, syntax highlighting, search indexing, and navigation. Add Binder and Colab launch links from config.

## Autodoc for Python APIs

Generate API reference from your source code, CLI tools, and OpenAPI specs:

```yaml
# config/_default/content.yaml
autodoc:
  enabled: true
  sources:
    - type: python
      module: mypackage
      paths: ["src/mypackage"]
    - type: cli
      module: mypackage.cli
    - type: openapi
      path: openapi.yaml
```

Bengal parses your Python AST directly — no import-time side effects, no `autodoc_mock_imports`, no `sys.path` manipulation. The parsed AST is cached between builds.

## Free-Threading Performance

Bengal is designed for Python 3.14t. On free-threaded builds, page rendering achieves true parallelism:

| Configuration | 1,000 pages | Relative |
|---------------|-------------|----------|
| Python 3.14 (GIL enabled) | ~3.5s | 1.0x |
| Python 3.14t (GIL disabled) | ~2.0s | 1.75x |

```bash
uv python install 3.14t
uv run --python=3.14t bengal build
```

This works because every layer — Patitas, Rosettes, Kida — was written from scratch for thread safety. No GIL assumptions, no shared mutable state in the hot path. See [Free-Threading](./free-threading) and [Benchmarks](./benchmarks) for details.

## AI-Native by Default

Your docs are consumed by AI agents as much as by humans. Bengal generates machine-readable output automatically:

- **`llms.txt`** — curated site overview for AI agents ([spec](https://llmstxt.org/))
- **`agent.json`** — hierarchical navigation manifest with content hashes
- **Per-page JSON** — metadata, plain text, optional heading-level chunks for RAG
- **Content Signals** — per-page/section control over search, AI input, and training ([spec](https://contentsignals.org/))

See [AI-Native Output](/docs/building/ai-native-output/) for the full story.

## Getting Started

```bash
pip install bengal
bengal new site my-project-docs --template docs
cd my-project-docs
bengal serve
```

The docs template creates a ready-to-use structure with getting-started, guides, and reference sections. Add your content, configure autodoc, and deploy.

:::{seealso}
- [Benchmarks](./benchmarks) — measured build times and scaling curves
- [Free-Threading](./free-threading) — how Bengal uses Python 3.14t
- [The Bengal Ecosystem](./ecosystem) — the full b-stack architecture
- [AI-Native Output](/docs/building/ai-native-output/) — machine-readable output formats
:::
