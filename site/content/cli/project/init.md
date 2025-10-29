
---
title: "init"
type: doc
description: "🏗️  Initialize site structure with sections and pages."
source_file: "bengal/bengal/cli/commands/init.py"
source_line: 365
---

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
| `--sections`, `-s` |`text` |`('blog',)` |Content sections to create (e.g., blog posts about). Default: blog |
| `--with-content` |Flag |`False` |Generate sample content in each section |


## Examples

```bash
bengal init --sections blog --sections projects --sections about
bengal init --sections blog --with-content --pages-per-section 10
bengal init --sections docs --sections guides --dry-run
bengal init  # Uses default 'blog' section
```



## Help

```bash
bengal project init --help
```