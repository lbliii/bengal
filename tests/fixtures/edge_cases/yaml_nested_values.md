---
title: YAML Nested Values Test
description: Tests that nested lists/dicts in tags are filtered out
tags:
- valid-tag
- [nested, list, should, be, filtered]
- {key: value, also: filtered}
- another-valid-tag
keywords:
- valid
- [should, be, filtered]
---

# Nested Values Test

This file tests that nested structures (lists, dicts) in tag-like fields are filtered out.

## Expected Behavior

- `tags` should contain only: `["valid-tag", "another-valid-tag"]`
- `keywords` should contain only: `["valid"]`
- Nested lists and dicts should be silently filtered
