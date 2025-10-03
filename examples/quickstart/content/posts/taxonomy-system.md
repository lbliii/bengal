---
title: "The Taxonomy System"
date: 2025-09-05
tags: ["taxonomy", "tags", "categories"]
categories: ["Features", "Organization"]
description: "Using tags and categories in Bengal"
author: "Bengal Team"
---

# The Taxonomy System

Taxonomies help organize and classify your content.

## Tags

Add tags to any page's frontmatter:

```yaml
---
title: "My Post"
tags: ["tutorial", "beginner"]
---
```

## Categories

Categories work similarly:

```yaml
---
title: "My Post"
category: "Tutorials"
---
```

## Taxonomy Pages

Bengal automatically creates:
- A page listing all tags
- Individual pages for each tag
- Same for categories

Visit `/tags/` to see all tags, or `/tags/tutorial/` to see all posts with that tag.

