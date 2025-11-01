
---
title: "communities"
type: doc
description: "🔍 Discover topical communities in your content.  Uses the Louvain algorithm to find natural clusters of related pages. Communities represent topic areas or content groups based ..."
source_file: "bengal/bengal/cli/commands/graph/communities.py"
source_line: 16
---

🔍 Discover topical communities in your content.

Uses the Louvain algorithm to find natural clusters of related pages.
Communities represent topic areas or content groups based on link structure.

Use community detection to:
- Discover hidden content structure
- Organize content into logical groups
- Identify topic clusters
- Guide taxonomy creation


## Usage

```bash
bengal utils graph communities [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` |`path` |`Sentinel.UNSET` |Path to config file (default: bengal.toml) |
| `--format`, `-f` |`choice` |`table` |Output format (default: table) |
| `--min-size`, `-m` |`integer` |`2` |Minimum community size to show (default: 2) |
| `--resolution`, `-r` |`float` |`1.0` |Resolution parameter (higher = more communities, default: 1.0) |
| `--seed` |`integer` |`Sentinel.UNSET` |Random seed for reproducibility |
| `--top-n`, `-n` |`integer` |`10` |Number of communities to show (default: 10) |


## Examples

```bash
# Show top 10 communities
bengal communities
# Show only large communities (10+ pages)
bengal communities --min-size 10
# Find more granular communities
bengal communities --resolution 2.0
# Export as JSON
bengal communities --format json > communities.json
```



## Help

```bash
bengal utils graph communities --help
```
