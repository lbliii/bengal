
---
title: "graph"
type: cli-command
css_class: api-content
description: "📊 Analyze site structure and connectivity.  Builds a knowledge graph of your site to: - Find orphaned pages (no incoming links) - Identify hub pages (highly connected) - Underst..."
source_file: "bengal/bengal/cli/commands/graph.py"
source_line: 12
---

# graph

📊 Analyze site structure and connectivity.

Builds a knowledge graph of your site to:
- Find orphaned pages (no incoming links)
- Identify hub pages (highly connected)
- Understand content structure
- Generate interactive visualizations


## Usage

```bash
bengal graph [ARGUMENTS] [OPTIONS]
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

### --output

Generate interactive visualization to file (e.g., public/graph.html)

**Type:** `path`
**Default:** `Sentinel.UNSET`

### --stats

Show graph statistics (default: enabled)

**Type:** Flag (boolean)
**Default:** `True`

### --tree

Show site structure as tree visualization

**Type:** Flag (boolean)
**Default:** `False`



## Examples

```bash
# Show connectivity statistics
bengal graph
# Generate interactive visualization
bengal graph --output public/graph.html
```



## Help

```bash
bengal graph --help
```
