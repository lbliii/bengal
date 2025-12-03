---
title: Analysis
description: Site structure analysis tools
weight: 20
draft: false
lang: en
tags: [analysis, graph, links]
keywords: [analysis, graph, pagerank, links, structure]
category: guide
---

# Analysis

Analyze your site's structure to improve navigation and discoverability.

## Overview

Bengal provides analysis tools for:

- **Graph analysis** — Visualize content relationships
- **Link suggestions** — Find internal linking opportunities
- **Page rank** — Identify important pages
- **Path analysis** — Understand user journeys

## Quick Start

```bash
# Analyze site structure
bengal analyze graph

# Get link suggestions
bengal analyze links --suggestions

# Calculate page importance
bengal analyze pagerank
```

## Graph Analysis

Visualize how your content connects:

```bash
bengal analyze graph --output graph.html
```

Identifies:
- Orphan pages (no incoming links)
- Hub pages (many connections)
- Content clusters

## Link Suggestions

Find pages that should link to each other:

```bash
bengal analyze links --suggestions --min-score 0.7
```

Based on:
- Content similarity
- Taxonomy overlap
- Structural proximity

## In This Section

- **[Graph Analysis](/docs/extending/analysis/graph/)** — Content relationship visualization
- **[Link Suggestions](/docs/extending/analysis/link-suggestions/)** — Internal linking opportunities

