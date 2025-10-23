
---
title: "install"
type: cli-reference
css_class: api-content
description: "Install a theme via uv pip.  NAME may be a package or a slug. If a slug without prefix is provided, suggest canonical 'bengal-theme-<slug>'."
source_file: "bengal/bengal/cli/commands/theme.py"
source_line: 169
---

# install

Install a theme via uv pip.

NAME may be a package or a slug. If a slug without prefix is provided,
suggest canonical 'bengal-theme-<slug>'.


## Usage

```bash
bengal utils theme install [ARGUMENTS] [OPTIONS]
```

## Arguments

### name

**Type:** `text`
**Required:** Yes
**Default:** `Sentinel.UNSET`


## Options

### --force

Install even if name is non-canonical

**Type:** Flag (boolean)
**Default:** `False`





## Help

```bash
bengal utils theme install --help
```