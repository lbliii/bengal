
---
title: "new"
type: cli-reference
css_class: api-content
description: "Create a new theme scaffold.  SLUG is the theme identifier used in config (e.g., [site].theme = SLUG)."
source_file: "bengal/bengal/cli/commands/theme.py"
source_line: 228
---

# new

Create a new theme scaffold.

SLUG is the theme identifier used in config (e.g., [site].theme = SLUG).


## Usage

```bash
bengal utils theme new [ARGUMENTS] [OPTIONS]
```

## Arguments

### slug

**Type:** `text`
**Required:** Yes
**Default:** `Sentinel.UNSET`


## Options

### --extends

Parent theme to extend

**Type:** `text`
**Default:** `default`

### --force

Overwrite existing directory if present

**Type:** Flag (boolean)
**Default:** `False`

### --mode

Scaffold locally under themes/ or an installable package

**Type:** `choice`
**Default:** `site`

### --output

Output directory (for site mode: site root; for package mode: parent dir)

**Type:** `directory`
**Default:** `.`





## Help

```bash
bengal utils theme new --help
```
