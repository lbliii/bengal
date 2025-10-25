---
title: "Hello World"
description: "My first post using Bengal with the new config directory structure"
date: 2025-01-15
tags: [introduction, bengal]
categories: [blog]
---

# Hello World!

This is my first post using Bengal with the new **config directory structure**.

## Why Use Config Directories?

Instead of one large config file, Bengal now supports splitting configuration into:

```
config/
├── _default/           # Base config
├── environments/       # local, preview, production
└── profiles/          # writer, theme-dev, dev
```

## Benefits

1. **Environment-specific settings** - Different URLs for local vs production
2. **Easy introspection** - `bengal config show --origin` shows where values come from
3. **Profile-based workflows** - Optimize for your use case
4. **Better organization** - Split concerns across files

## Example

To build for production:

```bash
bengal build --environment production
```

To develop locally with writer profile:

```bash
bengal serve --profile writer
```

Simple and powerful! 🚀

