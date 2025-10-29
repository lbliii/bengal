
---
title: "autodoc"
type: doc
description: "📚 Generate comprehensive API documentation (Python + CLI).  Automatically generates both Python API docs and CLI docs based on your bengal.toml configuration. Use --python-only ..."
source_file: "bengal/bengal/cli/commands/autodoc.py"
source_line: 17
---

📚 Generate comprehensive API documentation (Python + CLI).

Automatically generates both Python API docs and CLI docs based on
your bengal.toml configuration. Use --python-only or --cli-only to
generate specific types.


## Usage

```bash
bengal utils autodoc [OPTIONS]
```


## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--clean` |Flag |`False` |Clean output directory before generating |
| `--cli-only` |Flag |`False` |Only generate CLI docs (skip Python API docs) |
| `--config` |`path` |- |Path to config file (default: bengal.toml) |
| `--output`, `-o` |`path` |- |Output directory for generated docs (default: from config or content/api) |
| `--parallel` |Flag |`True` |Use parallel processing (default: enabled) |
| `--python-only` |Flag |`False` |Only generate Python API docs (skip CLI docs) |
| `--source`, `-s` |`path` |- |Source directory to document (can specify multiple) |
| `--stats` |Flag |`False` |Show performance statistics |
| `--verbose`, `-v` |Flag |`False` |Show detailed progress |


## Examples

```bash
bengal autodoc                    # Generate all configured docs
bengal autodoc --python-only      # Python API docs only
bengal autodoc --cli-only         # CLI docs only
bengal autodoc --source src       # Override Python source
```



## Help

```bash
bengal utils autodoc --help
```