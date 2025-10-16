
---
title: "init"
type: cli-command
css_class: api-content
description: "🏗️  Initialize site structure with sections and pages."
source_file: "bengal/bengal/cli/commands/init.py"
source_line: 360
---

# init

🏗️  Initialize site structure with sections and pages.


## Usage

```bash
bengal project init [OPTIONS]
```


## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` |Flag |`False` |Preview what would be created without creating files |
| `--force` |Flag |`False` |Overwrite existing sections and files |
| `--pages-per-section` |`integer` |`3` |Number of sample pages per section (with --with-content) |
| `--sections` |`text` |`Sentinel.UNSET` |Comma-separated section names (e.g., 'blog,projects,about') |
| `--with-content` |Flag |`False` |Generate sample content in each section |


## Examples

```bash
bengal init --sections "blog,projects,about"
bengal init --sections "blog" --with-content --pages-per-section 10
bengal init --sections "docs,guides" --dry-run
```



## Help

```bash
bengal project init --help
```
