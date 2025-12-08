---
title: Snippets
description: Reusable content fragments for DRY documentation
draft: true
---

# Content Snippets

This directory contains reusable content fragments that can be included across multiple documentation pages.

## Usage

Include snippets in your content using:

```markdown
{{< include "_snippets/install/pip.md" >}}
```

## Directory Structure

- `install/` — Installation instructions for different package managers
- `prerequisites/` — Requirement snippets
- `config/` — Configuration example snippets
- `cli/` — CLI command reference snippets
- `warnings/` — Callout and warning snippets
- `support/` — Support information snippets

