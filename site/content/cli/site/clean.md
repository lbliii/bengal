
---
title: "clean"
type: cli-reference
css_class: api-content
description: "🧹 Clean generated files and stale processes.  By default, removes only the output directory (public/).  Options:   --cache         Also remove build cache   --all           Remo..."
source_file: "bengal/bengal/cli/commands/clean.py"
source_line: 16
---

# clean

🧹 Clean generated files and stale processes.

By default, removes only the output directory (public/).

Options:
  --cache         Also remove build cache
  --all           Remove both output and cache
  --stale-server  Clean up stale 'bengal serve' processes


## Usage

```bash
bengal site clean [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--cache` |Flag |`False` |Also remove build cache (.bengal/ directory) |
| `--all` |Flag |`False` |Remove everything (output + cache) |
| `--config` |`path` |- |Path to config file (default: bengal.toml) |
| `--force`, `-f` |Flag |`False` |Skip confirmation prompt |
| `--stale-server` |Flag |`False` |Clean up stale 'bengal serve' processes |


## Examples

```bash
bengal clean                  # Clean output only
bengal clean --cache          # Clean output and cache
bengal clean --stale-server   # Clean up stale server processes
```



## Help

```bash
bengal site clean --help
```
