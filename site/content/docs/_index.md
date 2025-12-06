---
title: ᗢ Documentation
weight: 5
draft: false
lang: en
icon: docs

# 1. Identity (What is it?)
type: doc

# 2. Mode (How does it look?)
# 'overview' sets the hero style and grid layout for top-level docs
variant: overview

# 3. Data (Props)
# Explicit props block (preferred for new model)
props:
  description: Complete documentation for Bengal
  category: documentation
  tags: [documentation, docs]
  keywords: [documentation, docs, guides, reference]
  menu:
    main:
      weight: 10

# 4. Cascade (Inheritance)
cascade:
  type: doc          # All children are docs
  variant: standard  # Default children to standard layout (not overview)
---

# Documentation

Bengal documentation organized by what you want to accomplish.

## Get Started

New to Bengal? Start here:

- **[Get Started](/docs/get-started/)** — Installation and quickstart guides
- **[Tutorials](/docs/tutorials/)** — Hands-on learning journeys

## Feature Dimensions

Learn about specific capabilities:

| Dimension | What You'll Learn |
|-----------|-------------------|
| **[Content](/docs/content/)** | Content authoring, collections, sources, reuse |
| **[Theming](/docs/theming/)** | Templates, assets, theme customization |
| **[Building](/docs/building/)** | Configuration, CLI, performance, deployment |
| **[Extending](/docs/extending/)** | Autodoc, analysis, validation, architecture |

## Reference

- **[About](/docs/about/)** — Philosophy, concepts, FAQ
- **[API Reference](/api/)** — Complete API documentation
- **[CLI Reference](/cli/)** — Command-line interface reference

## Quick Links

| I want to... | Go to... |
|--------------|----------|
| Install Bengal | [Installation](/docs/get-started/installation/) |
| Start writing content | [Writer Quickstart](/docs/get-started/quickstart-writer/) |
| Customize themes | [Themer Quickstart](/docs/get-started/quickstart-themer/) |
| Build a blog | [Build a Blog Tutorial](/docs/tutorials/build-a-blog/) |
| Deploy my site | [Deployment](/docs/building/deployment/) |
