---
title: Template Dependency Tracking
description: Selective rebuilds when templates change — only affected pages rebuild
weight: 20
icon: git-branch
nav_title: Template Deps
tags:
- performance
- incremental
- templates
keywords:
- template dependency
- selective rebuild
- incremental build
- cache
category: explanation
---

# Template Dependency Tracking

When you edit a template, Bengal rebuilds only the pages that use it — not every page on the site. This is automatic and requires no configuration.

## How It Works

During each build, Bengal records which templates each page uses, including the full `extends` and `include` chain:

```
about.md → single.html → base.html, partials/nav.html, partials/footer.html
blog/post-1.md → blog/single.html → base.html, partials/nav.html
```

On the next build, if `partials/nav.html` changes, Bengal rebuilds every page that depends on it (directly or transitively). Pages that don't use `partials/nav.html` are skipped entirely.

## When It Applies

| Scenario | Behavior |
|----------|----------|
| Edit a content file | Normal incremental: only that page rebuilds |
| Edit a template | Selective: only pages using that template rebuild |
| Edit a base template | Broader selective: all pages extending it rebuild |
| First build (no cache) | Full build; dependencies recorded for next time |
| Cache miss | Falls back to full rebuild |

## Performance Impact

On a 1,000-page site where you edit a partial used by 50 pages:

- **Without** template deps: all 1,000 pages rebuild
- **With** template deps: only 50 pages rebuild

The dependency data is stored in the build cache alongside content hashes. The lookup is O(1) per template via a lazy reverse index.

## Interaction with Dev Server

Template dependency tracking works with `bengal serve`. When you save a template file, the dev server triggers a selective rebuild and hot-reloads only the affected pages.

## See Also

- [[docs/building/performance|Performance Overview]] — All optimization strategies
- [[docs/about/free-threading|Free-Threading]] — Parallel rendering
