
---
title: "site"
type: cli-reference
css_class: api-content
description: "🏗️  Create a new Bengal site with optional structure initialization."
source_file: "bengal/bengal/cli/commands/new.py"
source_line: 206
---

# site

🏗️  Create a new Bengal site with optional structure initialization.


## Usage

```bash
bengal new site [ARGUMENTS] [OPTIONS]
```

## Arguments

### name

**Type:** `text`
**Required:** No
**Default:** `Sentinel.UNSET`


## Options

### --init-preset

Initialize with preset (blog, docs, portfolio, business, resume) without prompting

**Type:** `text`
**Default:** `Sentinel.UNSET`

### --no-init

Skip structure initialization wizard

**Type:** Flag (boolean)
**Default:** `False`

### --template

Site template (default, blog, docs, portfolio, resume, landing)

**Type:** `text`
**Default:** `default`

### --theme

Theme to use

**Type:** `text`
**Default:** `default`





## Help

```bash
bengal new site --help
```