---
title: YAML Edge Cases Test
description: Tests handling of YAML special values in frontmatter
tags:
- null
- ~
- true
- false
- 404
- 3.14
- 2024-01-01
- ""
- "   "
- valid-tag
- Another Valid Tag
keywords:
- null
- valid keyword
aliases:
- /old-url/
- null
- /another-alias/
weight: 10
---

# YAML Edge Cases

This file tests Bengal's handling of YAML special values in list fields.

## Expected Behavior

After sanitization:
- `tags` should contain: `["True", "False", "404", "3.14", "2024-01-01", "valid-tag", "Another Valid Tag"]`
- `null`, `~`, empty strings, and whitespace-only strings should be filtered out
- `keywords` should contain: `["valid keyword"]`
- `aliases` should contain: `["/old-url/", "/another-alias/"]`
