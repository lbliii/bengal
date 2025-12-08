---
title: "debug"
type: "cli-reference"
css_class: "api-content"
source_file: "bengal/cli/commands/debug.py"
description: "🔬 Debug and diagnostic commands for builds - incremental debugging, dependency visualization, content migration, and more."
weight: 50
---

# debug

**Type:** Command Group  
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/cli/commands/debug.py)

:::{badge} Command Group
:class: badge-secondary
:::

**Command:** `bengal debug`

🔬 Debug and diagnostic commands for builds.

This command group provides internal debugging and introspection tools for understanding how Bengal builds work, debugging issues, and analyzing site structure.

## Subcommands

| Command | Description |
|---------|-------------|
| [`incremental`](/cli/debug/incremental/) | Debug incremental build issues and cache state |
| [`delta`](/cli/debug/delta/) | Compare builds and explain changes |
| [`deps`](/cli/debug/deps/) | Visualize build dependencies |
| [`migrate`](/cli/debug/migrate/) | Preview and execute content migrations |
| [`sandbox`](/cli/debug/sandbox/) | Test shortcodes/directives in isolation |
| [`config-inspect`](/cli/debug/config-inspect/) | Advanced configuration inspection |

## Usage

```bash
bengal debug <subcommand> [OPTIONS]
```

## Quick Examples

```bash
# Debug why a page was rebuilt
bengal debug incremental --explain content/posts/my-post.md

# Compare current build to baseline
bengal debug delta --baseline

# Visualize dependencies for a page
bengal debug deps content/docs/guide.md

# Preview moving content
bengal debug migrate --move docs/old.md guides/new.md

# Test a directive in isolation
bengal debug sandbox '```{note}\nTest\n```'

# Compare config between environments
bengal debug config-inspect --compare-to production
```

## Related Commands

- [`bengal explain`](/cli/explain/) - Explain how a specific page is built
- [`bengal validate`](/cli/validate/) - Run health checks on site
- [`bengal config show`](/cli/config/show/) - Show configuration

