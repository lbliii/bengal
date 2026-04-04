---
title: AI-Native Output
nav_title: AI-Native
description: How Bengal makes your documentation discoverable, navigable, and policy-compliant for AI agents and RAG pipelines
weight: 42
icon: robot
tags:
- ai
- llm
- rag
- content signals
- machine discovery
keywords:
- ai native documentation
- llms.txt
- agent manifest
- content signals
- rag documentation
- ai training opt out
- machine readable docs
---

# AI-Native Output

When an AI agent visits your documentation site, it faces the same problem a human does: figuring out what exists, where to start, and what it's allowed to use. Bengal solves this by generating a complete set of machine-readable outputs alongside your HTML — not as an afterthought, but as a default part of every build.

## What Bengal Generates

Every `bengal build` produces these files automatically:

| File | Purpose | Audience |
|------|---------|----------|
| `llms.txt` | Curated site overview with navigation links | AI agents deciding where to look |
| `llm-full.txt` | Complete plain-text corpus | RAG pipelines ingesting full content |
| `agent.json` | Hierarchical site map with content hashes | Programmatic agent navigation |
| `{page}/index.json` | Per-page metadata, navigation, optional chunks | Fine-grained RAG retrieval |
| `{page}/index.txt` | Per-page plain text | Single-page LLM consumption |
| `index.json` | Searchable site index with facets | Client-side search, indexers |
| `robots.txt` | Content Signal directives | Crawlers respecting your policies |
| `.well-known/content-signals.json` | Machine-readable policy manifest | Automated compliance checks |

All formats respect your [Content Signals](#content-signals) policies. Denied pages simply don't get machine-readable files generated.

## Content Signals: Who Can Use What

Bengal implements the [Content Signals](https://contentsignals.org/) specification — a three-way policy that lets you control how automated systems interact with your content:

| Signal | Default | Controls |
|--------|---------|----------|
| `search` | `true` | Search engine indexing |
| `ai_input` | `true` | RAG, grounding, AI-generated answers |
| `ai_train` | `false` | Model training and fine-tuning |

The default posture is **privacy-first**: your docs are discoverable and citable by AI systems, but not available for training unless you opt in.

### The Cascade

Policies cascade through three levels (highest priority first):

1. **Page frontmatter** — overrides everything for that page
2. **Section `_index.md`** — inherited by all pages in the section
3. **Site config** — the default for all pages

```yaml
# docs/internal/_index.md — hide an entire section from AI
---
cascade:
  visibility:
    ai_input: false
    ai_train: false
---
```

```yaml
# A single page opting in to training
---
visibility:
  ai_train: true
---
```

### Enforcement

Content Signals are not advisory. Bengal enforces them at the file level:

- `ai_input: false` pages get no `index.json` or `index.txt`
- `ai_train: false` pages are excluded from `llm-full.txt`
- `search: false` pages are excluded from `index.json` site index
- Draft pages are excluded from all machine-readable outputs

The files simply don't exist on disk for denied pages.

## For RAG Pipelines

If you're feeding Bengal docs into a retrieval pipeline, the per-page JSON includes everything you need:

- **`content_hash`** (SHA-256) — skip re-indexing unchanged pages
- **`last_modified`** (ISO 8601) — freshness filtering
- **`chunks`** — heading-level content splits with individual hashes (enable with `include_chunks: true`)
- **`navigation.related`** — related pages for context expansion

The `changelog.json` file tracks per-build diffs (added, modified, removed pages), so incremental indexing pipelines can process only what changed.

## Configuration

With default features enabled, all AI-native formats are generated automatically. To customize:

```yaml
# config/_default/outputs.yaml
output_formats:
  per_page: ["json", "llm_txt"]
  site_wide: ["index_json", "llm_full", "llms_txt", "agent_manifest", "changelog"]
  options:
    include_chunks: true              # Heading-level RAG chunks
    excerpt_length: 200               # Search index excerpt length
    exclude_sections: ["internal"]    # Hide sections from machine output

# config/_default/site.yaml
content_signals:
  search: true
  ai_input: true
  ai_train: false
```

See [Output Formats](./output-formats.md) for the full configuration reference and [SEO & Discovery](./seo.md) for the broader discovery strategy.
