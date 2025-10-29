
---
title: "autodoc-cli"
type: doc
description: "⌨️  Generate CLI documentation from Click/argparse/typer apps.  Extracts documentation from command-line interfaces to create comprehensive command reference documentation."
source_file: "bengal/bengal/cli/commands/autodoc.py"
source_line: 355
---

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
| `--app`, `-a` |`text` |- |CLI app module (e.g., bengal.cli:main) |
| `--clean` |Flag |`False` |Clean output directory before generating |
| `--config` |`path` |- |Path to config file (default: bengal.toml) |
| `--framework`, `-f` |`choice` |`click` |CLI framework (default: click) |
| `--include-hidden` |Flag |`False` |Include hidden commands |
| `--output`, `-o` |`path` |- |Output directory for generated docs (default: content/cli) |
| `--verbose`, `-v` |Flag |`False` |Show detailed progress |


## Examples

```bash
bengal autodoc-cli --app bengal.cli:main --output content/cli
```



## Help

```bash
bengal utils autodoc-cli --help
```