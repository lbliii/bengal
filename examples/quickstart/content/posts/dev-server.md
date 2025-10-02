---
title: "Using the Development Server"
date: 2025-09-03
tags: ["development", "tutorial", "tools"]
description: "Working with Bengal's built-in dev server"
---

# Using the Development Server

Bengal includes a development server with hot reload for a great development experience.

## Starting the Server

```bash
bengal serve
```

The server starts at `http://localhost:8000` by default.

## Custom Port

```bash
bengal serve --port 3000
```

## Hot Reload

The server watches for changes and automatically:
- Rebuilds your site
- Refreshes your browser

Just edit your content and see changes instantly!

## Debugging

Use the `--verbose` flag for detailed build information:

```bash
bengal serve --verbose
```

