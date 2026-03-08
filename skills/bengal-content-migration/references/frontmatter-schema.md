# Bengal Frontmatter Schema

## Common Fields

| Field | Type | Description |
|-------|------|-------------|
| title | str | Page title |
| description | str | Meta description |
| date | str | ISO date: '2026-01-01' |
| draft | bool | Exclude from build |
| type | str | Content type: blog, doc |
| tags | list[str] | Tags for taxonomy |
| category | str | Category |
| params | dict | Custom fields (params.author, etc.) |

## Blog Post Example

```yaml
---
type: blog
title: "Post Title"
date: '2026-01-01'
tags: [python, bengal]
category: tutorial
description: Post description.
params:
  author: Jane
---
```

## Section Index (_index.md)

```yaml
---
type: blog
title: Posts
description: Blog posts
---
```

## Params for Custom Data

Custom frontmatter goes under `params`:

```yaml
params:
  author: Jane Doe
  author_links:
    - href: https://github.com/jane
      text: GitHub
  featured: true
```
