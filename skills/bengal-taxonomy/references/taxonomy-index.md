# Bengal Taxonomy Index Reference

## Index Types

| Index | Source | Key Format |
|-------|--------|------------|
| section | Content path | Section dir name (e.g., "posts") |
| author | params.author | Author string |
| category | category | Category string |
| date_range | date | "2026" or "2026-01" |

## Query Pattern

```kida
{% let pages = site.indexes.<index>.get('<key>') | resolve_pages %}
```

Always use `| resolve_pages` to convert path list to page objects.

## Performance

Index lookups are O(1). Prefer over `site.pages | where(...)` which is O(n).

## Author Index

Author comes from `params.author` in frontmatter. Ensure consistent spelling across posts.
