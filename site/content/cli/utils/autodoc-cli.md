
---
title: "autodoc-cli"
type: cli-reference
css_class: api-content
description: "⌨️  Generate CLI documentation from Click/argparse/typer apps.  Extracts documentation from command-line interfaces to create comprehensive command reference documentation."
source_file: "bengal/bengal/cli/commands/autodoc.py"
source_line: 356
---

# autodoc-cli

⌨️  Generate CLI documentation from Click/argparse/typer apps.

Extracts documentation from command-line interfaces to create
comprehensive command reference documentation.


## Usage

```bash
bengal utils autodoc-cli [OPTIONS]
```


## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--app`, `-a` |`text` |`Sentinel.UNSET` |CLI app module (e.g., bengal.cli:main) |
| `--clean` |Flag |`False` |Clean output directory before generating |
| `--config` |`path` |`Sentinel.UNSET` |Path to config file (default: bengal.toml) |
| `--framework`, `-f` |`choice` |`click` |CLI framework (default: click) |
| `--include-hidden` |Flag |`False` |Include hidden commands |
| `--output`, `-o` |`path` |`Sentinel.UNSET` |Output directory for generated docs (default: content/cli) |
| `--verbose`, `-v` |Flag |`False` |Show detailed progress |


## Examples

```bash
bengal autodoc-cli --app bengal.cli:main --output content/cli
```



## Help

```bash
bengal utils autodoc-cli --help
```
