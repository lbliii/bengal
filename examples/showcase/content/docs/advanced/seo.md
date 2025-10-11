---
title: SEO and Metadata
description: Optimize your site for search engines
type: doc
weight: 4
tags: ["advanced", "seo", "optimization"]
toc: true
---

# SEO and Metadata

**Purpose**: Optimize your Bengal site for search engines.

## What You'll Learn

- Write effective titles and descriptions
- Use SEO-friendly frontmatter
- Optimize URLs and structure
- Generate sitemaps and RSS feeds

## Essential SEO Fields

### title

**Length:** 50-60 characters

```yaml
---
title: "Getting Started with Bengal SSG"  # 33 chars ✓
---
```

**Best practices:**
- Include target keywords
- Front-load important words
- Be descriptive and specific
- Match page content

### description

**Length:** 120-160 characters

```yaml
---
description: "Learn to build fast static sites with Bengal. Install, configure, and deploy your first site in under 10 minutes."  # 128 chars ✓
---
```

**Best practices:**
- Include target keywords naturally
- Compelling call-to-action
- Summarize page value
- Avoid keyword stuffing

## Complete SEO Frontmatter

```yaml
---
title: "Build Fast Static Sites with Bengal"
description: "Complete guide to creating lightning-fast static websites using Bengal SSG. Learn installation, configuration, and deployment."
date: 2025-10-11
author: "Jane Developer"
tags: ["static-sites", "bengal", "tutorial"]
keywords: ["static site generator", "fast websites", "Bengal SSG"]
canonical_url: "https://example.com/guides/bengal-guide/"
---
```

## URL Optimization

### Clean URLs

Bengal generates clean URLs automatically:

```
✅ Good:
/docs/getting-started/
/blog/python-tutorial/
/about/

❌ Avoid:
/docs/getting-started.html
/blog/post?id=123
/page1/
```

### Descriptive Slugs

Use descriptive filenames:

```
✅ Good filenames:
getting-started.md
python-web-development.md
deployment-guide.md

❌ Avoid:
page1.md
post.md
doc.md
```

## Content Optimization

### Headings

Use one H1 per page:

```markdown
# Main Title  (H1 - one per page)

## Section Heading  (H2)

### Subsection  (H3)
```

### Keywords

Include naturally in:
- Title and headings
- First paragraph
- Throughout content
- Image alt text
- Links

### Internal Links

Link related content:

```markdown
See our [installation guide](installation.md) for setup.
Learn about [deployment](deployment.md) options.
```

## Images

### Alt Text

Always include descriptive alt text:

```markdown
✅ Good:
![Python code editor showing Flask application](/assets/python-code.png)

❌ Poor:
![Image](/assets/image.png)
```

### File Names

Use descriptive names:

```
✅ Good:
python-tutorial-hero.jpg
flask-app-screenshot.png

❌ Avoid:
IMG_1234.jpg
screenshot.png
```

## Automatic Features

### Sitemap

Bengal generates `sitemap.xml` automatically:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2025-10-11</lastmod>
  </url>
  ...
</urlset>
```

Submit to:
- Google Search Console
- Bing Webmaster Tools

### RSS Feed

Auto-generated at `/rss.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>My Site</title>
    ...
  </channel>
</rss>
```

## Meta Tags

Bengal generates meta tags from frontmatter:

```html
<!-- From frontmatter -->
<title>Page Title | Site Name</title>
<meta name="description" content="Page description">
<meta name="keywords" content="keyword1, keyword2">
<meta name="author" content="Author Name">

<!-- Open Graph -->
<meta property="og:title" content="Page Title">
<meta property="og:description" content="Page description">
<meta property="og:image" content="/assets/hero.jpg">
```

## Performance

### Speed

Fast sites rank better:

- Use incremental builds
- Optimize images
- Minimize CSS/JS
- Enable caching

### Mobile

Ensure mobile-friendly:

- Responsive design (default theme)
- Touch-friendly navigation
- Fast mobile load times

## Best Practices

### Do's

✅ Write for humans first
✅ Use descriptive titles
✅ Include internal links
✅ Optimize images
✅ Submit sitemap
✅ Monitor performance

### Don'ts

❌ Keyword stuff
❌ Duplicate content
❌ Use generic descriptions
❌ Ignore mobile users
❌ Forget alt text
❌ Make slow sites

## Quick Checklist

**Every page should have:**

- [ ] Descriptive title (50-60 chars)
- [ ] Compelling description (120-160 chars)
- [ ] Target keywords (naturally)
- [ ] Clean URL
- [ ] Internal links
- [ ] Optimized images with alt text
- [ ] Proper heading structure

## Next Steps

- **[Publishing](drafts-and-publishing.md)** - Deploy your site
- **[Taxonomies](taxonomies.md)** - Organize content
- **[External Links](../writing/external-links.md)** - Link best practices

## Related

- [Frontmatter Guide](../writing/frontmatter-guide.md) - Metadata
- [Images and Assets](../writing/images-and-assets.md) - Media optimization
- [Blog Posts](../content-types/blog-posts.md) - Post metadata

