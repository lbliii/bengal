
---
title: "profile"
type: cli-reference
css_class: api-content
description: "👤 Set your Bengal working profile / persona.  Profiles customize CLI behavior and output format based on your role:      dev       👨‍💻  Full debug output, performance metrics, a..."
source_file: "bengal/bengal/cli/commands/project.py"
source_line: 68
---

# profile

👤 Set your Bengal working profile / persona.

Profiles customize CLI behavior and output format based on your role:

    dev       👨‍💻  Full debug output, performance metrics, all commands
    themer    🎨  Focus on templates, themes, component preview
    writer    ✍️  Simple UX, focus on content, minimal tech details
    ai        🤖  Machine-readable output, JSON formats


## Usage

```bash
bengal project profile [ARGUMENTS]
```

## Arguments

### profile_name

**Type:** `text`
**Required:** No



## Examples

```bash
bengal project profile dev       # Switch to developer profile
bengal project profile writer    # Switch to content writer profile
```



## Help

```bash
bengal project profile --help
```
