
---
title: "analyze"
type: cli-reference
css_class: api-content
description: "📊 Analyze site structure and connectivity."
source_file: "bengal/bengal/cli/commands/graph/__main__.py"
source_line: 27
---

# analyze

📊 Analyze site structure and connectivity.


## Usage

```bash
bengal utils graph analyze [ARGUMENTS] [OPTIONS]
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

### --output

Generate interactive visualization to file (e.g., public/graph.html)

**Type:** `path`

### --stats

Show graph statistics (default: enabled)

**Type:** Flag (boolean)
**Default:** `True`

### --tree

Show site structure as tree visualization

**Type:** Flag (boolean)
**Default:** `False`





## Help

```bash
bengal utils graph analyze --help
```
