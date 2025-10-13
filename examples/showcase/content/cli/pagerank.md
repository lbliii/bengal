
---
title: "pagerank"
type: cli-command
css_class: api-content
description: "🏆 Analyze page importance using PageRank algorithm.  Computes PageRank scores for all pages based on their link structure. Pages that are linked to by many important pages recei..."
source_file: "bengal/bengal/cli/commands/graph.py"
source_line: 221
---

# pagerank

🏆 Analyze page importance using PageRank algorithm.

Computes PageRank scores for all pages based on their link structure.
Pages that are linked to by many important pages receive high scores.

Use PageRank to:
- Identify your most important content
- Prioritize content updates
- Guide navigation and sitemap design
- Find underlinked valuable content


## Usage

```bash
bengal pagerank [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

### --config

Path to config file (default: bengal.toml)

**Type:** `path`
**Default:** `Sentinel.UNSET`

### --damping, -d

PageRank damping factor (default: 0.85)

**Type:** `float`
**Default:** `0.85`

### --format, -f

Output format (default: table)

**Type:** `choice`
**Default:** `table`

### --top-n, -n

Number of top pages to show (default: 20)

**Type:** `integer`
**Default:** `20`



## Examples

```bash
# Show top 20 most important pages
bengal pagerank
# Show top 50 pages
bengal pagerank --top-n 50
# Export scores as JSON
bengal pagerank --format json > pagerank.json
```



## Help

```bash
bengal pagerank --help
```
