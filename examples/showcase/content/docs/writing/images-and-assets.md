---
title: Images and Assets
description: Add images, media files, and downloads to your content
type: doc
weight: 8
tags: ["images", "assets", "media", "accessibility"]
toc: true
---

# Images and Assets

**Purpose**: Learn to add images and other media files to your Bengal content.

## What You'll Learn

- Add images to your content
- Organize assets properly
- Write accessible alt text
- Handle different image formats
- Include downloads and other assets

## Adding Images

Add images with markdown syntax:

```markdown
![Image description](/assets/images/photo.jpg)
```

**Format:** `![alt text](image path)`

**Example:**

```markdown
![Sunset over mountains with orange and purple sky](/assets/images/sunset.jpg)
```

## Asset Organization

Store assets in the `assets/` directory:

```
mysite/
├── content/           # Your markdown files
└── assets/           # Your media files
    ├── images/
    │   ├── photos/
    │   ├── diagrams/
    │   └── icons/
    ├── downloads/
    │   └── guides.pdf
    └── videos/
        └── tutorial.mp4
```

**Build output:**

Assets are copied to `public/assets/` during builds:

```
public/
└── assets/
    ├── images/
    ├── downloads/
    └── videos/
```

## Image Paths

### Absolute Paths (Recommended)

Reference from site root with `/`:

```markdown
![Logo](/assets/images/logo.png)
![Hero image](/assets/images/hero.jpg)
![Diagram](/assets/images/diagrams/flow.svg)
```

**Advantages:**
- Works from any page
- Clear and unambiguous
- Easy to remember

### Relative Paths

Reference relative to current file:

```markdown
![Local image](../../assets/images/photo.jpg)
```

**Use cases:**
- Page-specific images stored near content
- Avoid for most cases (absolute paths are clearer)

## Alt Text Best Practices

Alt text describes images for accessibility and SEO.

### Good Alt Text

```markdown
✅ Descriptive and specific:
![Bengal SSG logo with yellow tiger stripes on black background](/assets/logo.png)

![Bar chart showing 45% increase in site performance](/assets/chart.png)

![Code editor displaying Python function with syntax highlighting](/assets/code-screenshot.png)
```

### Poor Alt Text

```markdown
❌ Too vague or generic:
![Image](/assets/photo.jpg)
![Logo](/assets/logo.png)
![Screenshot](/assets/screen.png)
```

### Alt Text Guidelines

**Describe the content:**
```markdown
![Pie chart: 60% static, 25% dynamic, 15% hybrid](/assets/chart.png)
```

**Describe the function for functional images:**
```markdown
![Search icon](/assets/icons/search.svg)
![Close button](/assets/icons/close.svg)
```

**Keep it concise (under 125 characters):**
```markdown
![Three developers collaborating at a whiteboard](/assets/team.jpg)
```

**Don't say "image of" or "picture of":**
```markdown
❌ ![Image of a mountain](/assets/mountain.jpg)
✅ ![Snow-capped mountain peak against blue sky](/assets/mountain.jpg)
```

**Use empty alt for decorative images:**
```markdown
![](/assets/decorative-border.png)
```

```{tip} Accessibility Matters
Screen readers announce alt text to users who can't see images. Good alt text makes your content accessible to everyone.
```

## Image Formats

### Recommended Formats

| Format | Use Case | Notes |
|--------|----------|-------|
| **JPEG** | Photos, complex images | Good compression, no transparency |
| **PNG** | Screenshots, graphics | Transparency support, larger files |
| **SVG** | Logos, icons, diagrams | Scalable, small files, crisp at any size |
| **WebP** | Modern browsers | Better compression than JPEG/PNG |
| **GIF** | Simple animations | Large files, limited colors |

### Format Examples

```markdown
# Photos - use JPEG
![Sunset photograph](/assets/images/sunset.jpg)

# Screenshots - use PNG
![Terminal screenshot showing build output](/assets/images/terminal.png)

# Logos and icons - use SVG
![Bengal logo](/assets/images/logo.svg)

# Diagrams - use SVG
![System architecture diagram](/assets/diagrams/architecture.svg)
```

## Image Sizing

### Markdown Limitations

Standard markdown doesn't support size attributes:

```markdown
# This doesn't work in markdown:
![Image](/assets/photo.jpg){width=500px}
```

### HTML for Sizing

Use HTML for size control:

```html
<img src="/assets/images/photo.jpg" 
     alt="Descriptive alt text" 
     width="600" 
     height="400">
```

### Responsive Images

For responsive sizing, use CSS (handled by theme):

```html
<img src="/assets/images/hero.jpg" 
     alt="Hero image" 
     class="img-fluid">
```

```{tip} Image Optimization
Resize images before uploading. Don't rely on HTML/CSS to shrink large images - it wastes bandwidth.
```

## Advanced Image Features

### Image with Caption

Use HTML for captions:

```html
<figure>
  <img src="/assets/images/chart.png" 
       alt="Performance comparison chart">
  <figcaption>Figure 1: Build time comparison across SSGs</figcaption>
</figure>
```

### Image Links

Make images clickable:

```markdown
[![Click to enlarge](/assets/images/thumbnail.jpg)](/assets/images/full-size.jpg)
```

Format: `[![alt](thumbnail)](link)`

### Image in Admonition

Combine with directives:

````markdown
```{tip} Visual Guide
![Step-by-step screenshot](/assets/images/tutorial-step.png)

Follow the highlighted areas to complete the setup.
```
````

## Other Assets

### Downloadable Files

Link to downloads:

```markdown
Download the [user guide (PDF)](/assets/downloads/guide.pdf).

Get the [starter template (ZIP)](/assets/downloads/template.zip).
```

### Videos

Embed videos:

```html
<video width="640" height="360" controls>
  <source src="/assets/videos/tutorial.mp4" type="video/mp4">
  Your browser doesn't support video.
</video>
```

Or link to external video:

```markdown
Watch the [tutorial video](https://youtube.com/watch?v=example).
```

### Audio Files

```html
<audio controls>
  <source src="/assets/audio/podcast.mp3" type="audio/mpeg">
  Your browser doesn't support audio.
</audio>
```

## Asset Management

### File Naming

Use clear, descriptive names:

```
✅ Good:
/assets/images/homepage-hero.jpg
/assets/images/product-screenshot.png
/assets/downloads/installation-guide.pdf

❌ Avoid:
/assets/IMG_1234.jpg
/assets/screen1.png
/assets/file.pdf
```

### Directory Structure

Organize by type or section:

```
assets/
├── images/
│   ├── blog/          # Blog post images
│   ├── docs/          # Documentation images
│   └── shared/        # Shared across site
├── downloads/
│   ├── guides/
│   └── templates/
└── fonts/            # Custom fonts (if any)
```

### File Sizes

Keep file sizes reasonable:

- **Photos**: Under 500KB (compress first)
- **Screenshots**: Under 200KB
- **Icons/SVG**: Under 50KB
- **Downloads**: Mention size in link

```markdown
Download the [user guide (2.3 MB PDF)](/assets/downloads/guide.pdf).
```

## Image Optimization

### Before Upload

1. **Resize**: Don't upload 4000px images if displaying at 800px
2. **Compress**: Use tools like TinyPNG, ImageOptim
3. **Format**: Choose appropriate format (SVG for graphics, JPEG for photos)

### Tools

- **ImageOptim** - Mac app for image compression
- **TinyPNG** - Online PNG/JPEG compression
- **SVGO** - SVG optimizer
- **Squoosh** - Web app for image compression

## Common Patterns

### Hero Image

```markdown
---
title: My Blog Post
hero_image: /assets/images/blog/post-hero.jpg
---

# My Blog Post

Content starts here...
```

### Inline Diagrams

```markdown
## Architecture Overview

The system consists of three main components:

![System architecture showing frontend, API, and database](/assets/diagrams/architecture.svg)

Each component communicates via REST APIs.
```

### Screenshot Gallery

```markdown
## Interface Screenshots

![Main dashboard view](/assets/screenshots/dashboard.png)

![Settings panel](/assets/screenshots/settings.png)

![Report generation interface](/assets/screenshots/reports.png)
```

### Comparison Images

```markdown
## Before and After

**Before:**
![Old interface design](/assets/comparison/before.png)

**After:**
![New interface design](/assets/comparison/after.png)
```

## Troubleshooting

### Image Not Showing

```{warning} Common Issues
- **Wrong path**: Check file location and path
- **Case sensitivity**: `Photo.jpg` ≠ `photo.jpg`
- **Missing file**: Ensure file is in `assets/`
- **Build needed**: Run `bengal build` to copy assets
```

### Broken Images

Check:

1. File exists in `assets/`
2. Path is correct (start with `/assets/`)
3. File was copied to `public/assets/`
4. No typos in filename

## Best Practices Summary

```{success} Image Checklist
- ✅ Use descriptive alt text
- ✅ Organize in `assets/` directory
- ✅ Use absolute paths from root
- ✅ Choose appropriate format
- ✅ Optimize file size before upload
- ✅ Use descriptive filenames
- ✅ Test images in build
- ✅ Consider accessibility
```

## Quick Reference

| Task | Syntax |
|------|--------|
| Basic image | `![alt](/assets/images/photo.jpg)` |
| Image link | `[![alt](image)](link)` |
| HTML image | `<img src="path" alt="text">` |
| Download link | `[Title (PDF)](/assets/file.pdf)` |
| Video | `<video controls><source src="..."></video>` |

## Next Steps

Master images and assets, then explore:

- **[Content Types](../content-types/)** - Different page layouts
- **[Directives](../directives/)** - Rich content features
- **[Blog Posts](../content-types/blog-posts.md)** - Hero images and featured content
- **[SEO](../advanced/seo.md)** - Image optimization for search

## Related

- [Markdown Basics](markdown-basics.md) - Essential syntax
- [Internal Links](internal-links.md) - Link between pages
- [External Links](external-links.md) - Link to external resources

