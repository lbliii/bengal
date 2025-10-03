---
title: "Configuration Options"
date: 2025-09-08
tags: ["configuration", "tutorial", "setup"]
categories: ["Configuration", "Tutorials"]
description: "All available configuration options in Bengal"
author: "Bengal Team"
---

# Configuration Options

Bengal is configured through `bengal.toml` in your site root.

## Basic Configuration

```toml
title = "My Site"
base_url = "https://example.com"
theme = "default"

[author]
name = "Your Name"
email = "you@example.com"
```

## Pagination

```toml
[pagination]
per_page = 10
```

## Build Options

```toml
[build]
output_dir = "public"
```

## Section-Specific Config

```toml
[sections.blog]
title = "Blog"
per_page = 5
```

