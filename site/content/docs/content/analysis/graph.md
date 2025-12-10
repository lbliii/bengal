---
title: Graph Analysis
description: Analyze your site's structure, improve internal linking, and optimize
  navigation
weight: 10
draft: false
lang: en
tags:
- analysis
- graph
- seo
- optimization
keywords:
- graph analysis
- pagerank
- community detection
- link suggestions
- seo
category: guide
---

# Graph Analysis

Bengal's graph analysis tools help you understand your site's structure, identify optimization opportunities, and improve internal linking.

## Overview

Bengal uses a **semantic link model** that understands different types of connections:

| Link Type | Weight | Description |
|-----------|--------|-------------|
| **Explicit** | 1.0 | Human-authored markdown links |
| **Menu** | 10.0 | Navigation menu items (high editorial intent) |
| **Taxonomy** | 1.0 | Shared tags/categories |
| **Related** | 0.75 | Algorithm-computed related posts |
| **Topical** | 0.5 | Section hierarchy (parent → child) |
| **Sequential** | 0.25 | Next/prev navigation |

This weighted approach provides **nuanced connectivity analysis** beyond simple orphan detection, eliminating false positives from structural links.

## Connectivity Levels

Pages are classified by their weighted connectivity score:

| Level | Score | Status | Action |
|-------|-------|--------|--------|
| 🟢 Well-Connected | ≥ 2.0 | Excellent | No action needed |
| 🟡 Adequately Linked | 1.0 - 2.0 | Good | Could add more links |
| 🟠 Lightly Linked | 0.25 - 1.0 | Fair | Should add explicit cross-references |
| 🔴 Isolated | < 0.25 | Needs attention | Add internal links |

## Quick Start

Get a unified analysis report:

```bash
bengal graph report
```

This shows:
- **Connectivity distribution** by level
- **Isolated pages** that need attention
- **Bridge pages** (navigation bottlenecks)
- **Actionable recommendations**

For CI pipelines:

```bash
bengal graph report --brief --ci --threshold-isolated 5
```

## Understanding the Analysis

### Semantic Link Types

Bengal tracks different types of links with semantic meaning:

| Link Type | Weight | Description |
|-----------|--------|-------------|
| **Explicit** | 1.0 | Human-authored `[text](url)` markdown links |
| **Menu** | 10.0 | Navigation menu items (deliberate prominence) |
| **Taxonomy** | 1.0 | Shared tags or categories |
| **Related** | 0.75 | Algorithm-computed related posts |
| **Topical** | 0.5 | Section hierarchy (parent `_index.md` → children) |
| **Sequential** | 0.25 | Next/prev navigation within section |

### Key Metrics

- **Connectivity score**: Weighted sum of all incoming links
- **Average score**: Mean connectivity score across all pages (aim for ≥1.0)
- **Isolated pages**: Pages with score < 0.25 (need attention)
- **Distribution**: Percentage of pages at each connectivity level
- **Hub pages**: Pages with many incoming links (important for navigation)

## Command Reference

### Unified Analysis Report

Get a comprehensive connectivity report:

```bash
bengal graph report
```

**Options**:
- `--brief`: Compact output for CI pipelines
- `--ci`: CI mode with exit codes
- `--threshold-isolated N`: Max isolated pages before failure (default: 5)
- `--threshold-lightly N`: Max lightly-linked before warning (default: 20)
- `--format FORMAT`: Output format - `console`, `json`, or `markdown`

### List Under-Linked Pages

Find pages by connectivity level:

```bash
# Show isolated pages (default)
bengal graph orphans

# Show lightly-linked pages
bengal graph orphans --level lightly

# Show both isolated and lightly-linked
bengal graph orphans --level all
```

**Options**:
- `--level LEVEL`: Filter by level - `isolated`, `lightly`, `adequately`, `all`
- `--format FORMAT`: Output format - `table`, `json`, `paths`
- `--sort FIELD`: Sort by `path`, `title`, or `score`
- `--limit N`: Limit results

### Analyze Site Structure

Get an overview of your site's connectivity:

```bash
bengal graph analyze
```

**Options**:
- `--tree`: Show site structure as a tree visualization
- `--output path/to/graph.html`: Generate interactive HTML visualization
- `--config PATH`: Path to config file (default: bengal.toml)

**Short aliases**:
```bash
bengal g report        # g → graph
bengal analyze         # Top-level alias
```

### PageRank Analysis

Identify your most important pages using Google's PageRank algorithm:

```bash
bengal utils graph pagerank --top-n 20
```

**Options**:
- `--top-n N`: Show top N pages (default: 20)
- `--damping FLOAT`: PageRank damping factor (default: 0.85)
- `--format FORMAT`: Output format - `table`, `json`, `csv`, or `summary`

### Community Detection

Discover topical clusters in your content:

```bash
bengal utils graph communities --top-n 10 --min-size 3
```

**Options**:
- `--min-size N`: Minimum community size to show (default: 2)
- `--resolution FLOAT`: Resolution parameter - higher = more communities (default: 1.0)
- `--top-n N`: Number of communities to show (default: 10)

### Bridge Pages Analysis

Find critical navigation pages:

```bash
bengal utils graph bridges --top-n 20
```

**Metrics**:
- **Betweenness**: Pages that connect different parts of the site (bridge pages)
- **Closeness**: Pages easy to reach from anywhere (accessible pages)

### Link Suggestions

Get smart recommendations for internal linking:

```bash
bengal utils graph suggest --top-n 50 --min-score 0.5
```

**Options**:
- `--top-n N`: Number of suggestions to show (default: 50)
- `--min-score FLOAT`: Minimum score threshold (default: 0.3)
- `--format FORMAT`: Output format - `table`, `json`, or `markdown`

## Common Workflows

### Improving Internal Linking

1. **Get connectivity report**:
   ```bash
   bengal graph report
   ```

2. **Find isolated pages** (highest priority):
   ```bash
   bengal graph orphans --level isolated
   ```

3. **Find lightly-linked pages** (could improve):
   ```bash
   bengal graph orphans --level lightly --format json > lightly-linked.json
   ```

4. **Get link suggestions**:
   ```bash
   bengal graph suggest --min-score 0.5 --format markdown > suggestions.md
   ```

5. **Prioritize by importance**:
   ```bash
   bengal graph pagerank --top-n 30 --format csv > important-pages.csv
   ```

### CI Integration

Add connectivity checks to your CI pipeline:

```bash
# Fail build if too many isolated pages
bengal graph report --ci --threshold-isolated 5

# Export JSON for artifact storage
bengal graph report --format json > connectivity-report.json
bengal graph orphans --format json > under-linked-pages.json
```

### Optimizing Navigation

1. **Find bridge pages**:
   ```bash
   bengal graph bridges --metric betweenness --top-n 10
   ```

2. **Ensure bridge pages are prominent** — Add to main navigation menus.

3. **Check accessibility**:
   ```bash
   bengal graph bridges --metric closeness --top-n 10
   ```

## Understanding Connectivity Levels

The `report` command classifies pages by weighted connectivity:

| Level | Indicator | Meaning | Action |
|-------|-----------|---------|--------|
| 🔴 Isolated | Score < 0.25 | No meaningful links | Add explicit cross-references |
| 🟠 Lightly Linked | Score 0.25-1.0 | Only structural links | Add internal links |
| 🟡 Adequately Linked | Score 1.0-2.0 | Some connections | Could add more |
| 🟢 Well-Connected | Score ≥ 2.0 | Multiple link types | No action needed |

### Why Use Weighted Scores?

Binary orphan detection causes **false positives**:
- Pages in section hierarchies have `topical` links from parent `_index.md`
- Pages with next/prev navigation have `sequential` links
- These count as connections but carry low editorial intent

Weighted scores give credit for structural links while highlighting pages that need **explicit human-authored links**.

### Additional Recommendations

| Recommendation | Meaning | Action |
|----------------|---------|--------|
| 🌉 Bridge Pages | Pages connecting site sections | Make prominent in menus |
| 🏆 Hub Pages | Pages with many incoming links | Keep updated and maintained |
| 📊 Low Average Score | Overall connectivity < 1.0 | Add more internal links site-wide |

## Best Practices

### Regular Analysis

Run analysis regularly to track improvements:

```bash
# Save connectivity report
bengal graph report --format json > analysis-$(date +%Y%m%d).json

# Track isolated pages over time
bengal graph orphans --format json > isolated-$(date +%Y%m%d).json

# PageRank for importance
bengal graph pagerank --format csv > pagerank-$(date +%Y%m%d).csv
```

### Focus on High-Impact Changes

1. **Fix isolated pages first** (🔴) — Highest priority
2. **Improve lightly-linked pages** (🟠) — Add explicit cross-references
3. **Link to high PageRank pages** — Maximum SEO benefit
4. **Improve bridge pages** — Better navigation
5. **Add internal links gradually** — Don't over-link

### CI/CD Integration

Add connectivity gates to your pipeline:

```yaml
# GitHub Actions example
- name: Check connectivity
  run: bengal graph report --ci --threshold-isolated 5
```

## See Also

- [Analysis System Architecture](/docs/reference/architecture/subsystems/analysis/) — Technical details and API usage
