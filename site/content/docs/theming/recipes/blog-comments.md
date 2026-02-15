---
title: Blog Comments
description: Configure and integrate comments (Giscus, Disqus, Utterances) on blog posts
weight: 95
draft: false
lang: en
tags:
- cookbook
- blog
- comments
keywords:
- comments
- giscus
- disqus
- utterances
category: cookbook
---

# Blog Comments

The default theme's blog template includes a comments section placeholder. This recipe shows how to configure it and integrate a third-party comments provider.

## Configuration

### Show or Hide Comments

Control visibility via `params.comments` in frontmatter:

**Per post:**

```yaml
---
title: My Post
params:
  comments: false   # Hide comments on this post
---
```

**Site-wide (cascade):**

Add to `content/_default/content.yaml` or section `_index.md`:

```yaml
cascade:
  params:
    comments: false   # Disable comments for all posts in this section
```

**Default:** Comments section is shown when `params.comments` is `true` or omitted.

### Integration Point

The blog single template renders:

```html
<div id="comments" data-comments-target></div>
```

Your comments provider script should inject into this element. Override `blog/single.html` or add a script in your layout's footer/head.

## Integrate a Provider

### Giscus (GitHub Discussions)

1. Enable Discussions on your repo
2. Install [giscus](https://giscus.app/)
3. Add the script to your base layout or a partial:

```html
<script src="https://giscus.app/client.js"
  data-repo="owner/repo"
  data-repo-id="..."
  data-category="..."
  data-category-id="..."
  data-mapping="pathname"
  data-strict="0"
  data-reactions-enabled="1"
  data-emit-metadata="0"
  data-input-position="bottom"
  data-theme="light"
  data-lang="en"
  crossorigin="anonymous"
  async>
</script>
```

The script auto-mounts into the first `data-giscus` container. Add `data-giscus` to the comments div in your override, or ensure the script runs after the `#comments` element exists.

### Utterances (GitHub Issues)

Similar to Giscus but uses GitHub Issues. Add the Utterances script and point it at `#comments`.

### Disqus

Add the Disqus embed script and set `disqus_config.page.url` to the current page. Mount into `#comments`.

## Override the Template

To replace the placeholder entirely, copy `bengal/themes/default/templates/blog/single.html` to your project's `templates/blog/single.html` and modify the comments block. Replace the placeholder `<p>` with your provider's embed code or a conditional that injects the right script based on `params.comments_provider`.
