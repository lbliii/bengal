---
title: Cards
description: Create visual card grids for features, links, and content organization
type: doc
weight: 6
tags: ["directives", "cards", "layout"]
toc: true
---

# Cards

**Purpose**: Create attractive card layouts for features, links, and visual content organization.

## What You'll Learn

- Create individual cards
- Build card grids
- Use icons and images
- Link cards to pages

## Basic Syntax

### Single Card

````markdown
```{card} Card Title
:icon: 🎯
:link: /page/

Card description with **markdown** support.
```
````

### Card Grid

````markdown
```{cards}
:columns: 3

```{card} First Card
:icon: ⚡
Content here
```

```{card} Second Card
:icon: 📝
More content
```

```{card} Third Card
:icon: 🔍
Even more
```
````

## Use Cases

### Feature Showcase

Highlight product or site features:

````markdown
```{cards}
:columns: 3

```{card} Fast Builds
:icon: ⚡

Incremental builds are 18-42x faster than full rebuilds.
```

```{card} Rich Content
:icon: 📝

Directives, shortcodes, and 75+ template functions.
```

```{card} SEO Ready
:icon: 🔍

Automatic sitemaps, RSS feeds, and metadata.
```
````

### Navigation Cards

Create visual navigation:

````markdown
```{cards}
:columns: 2

```{card} Getting Started
:icon: 🚀
:link: /docs/getting-started/

Learn the basics and create your first site.
```

```{card} Writing Guide
:icon: ✍️
:link: /docs/writing/

Master markdown and content creation.
```

```{card} Directives
:icon: 🎨
:link: /docs/directives/

Create rich content with callouts and tabs.
```

```{card} Deployment
:icon: 🌐
:link: /docs/deployment/

Deploy your site to production.
```
````

### Team or Author Cards

Showcase team members:

````markdown
```{cards}
:columns: 3

```{card} Jane Developer
:icon: 👩‍💻
:link: /team/jane/

Lead developer and architect.
```

```{card} John Writer
:icon: 👨‍💻
:link: /team/john/

Technical writer and documentation lead.
```

```{card} Sarah Designer
:icon: 👩‍🎨
:link: /team/sarah/

UX designer and theme creator.
```
````

## Card Options

### icon

Add emoji or text icon:

````markdown
```{card} Feature Name
:icon: 🎯

Icon appears at the top of the card.
```
````

**Icon types:**
- Emoji: ⚡ 📝 🔍 🎨 🚀
- Text: NEW, PRO, BETA
- Empty: Omit for no icon

### link

Make entire card clickable:

````markdown
```{card} Clickable Card
:link: /destination/

Click anywhere on card to navigate.
```
````

**Link types:**
- Internal: `/docs/page/`
- External: `https://example.com`
- Anchor: `/page/#section`

### columns

Control cards per row (grid only):

````markdown
```{cards}
:columns: 2    # 2 cards per row
...

```{cards}
:columns: 3    # 3 cards per row (default)
...

```{cards}
:columns: 4    # 4 cards per row
...
````

**Responsive:** Cards automatically stack on mobile.

## Grid Layouts

### Two Column

````markdown
```{cards}
:columns: 2

```{card} Left Card
Content
```

```{card} Right Card
Content
```
````

### Three Column (Default)

````markdown
```{cards}
:columns: 3

```{card} Card 1
Content
```

```{card} Card 2
Content
```

```{card} Card 3
Content
```
````

### Four Column

````markdown
```{cards}
:columns: 4

```{card} Card 1
...
```

```{card} Card 2
...
```

```{card} Card 3
...
```

```{card} Card 4
...
```
````

## Markdown Support

Cards support full markdown:

````markdown
```{card} Rich Content
:icon: 📝

You can use:

- **Bold** and *italic*
- `Inline code`
- [Links](https://example.com)

\`\`\`python
# Even code blocks!
print("Hello")
\`\`\`
```
````

## Common Patterns

### Documentation Sections

````markdown
## Documentation

```{cards}
:columns: 2

```{card} Writing Guide
:icon: ✍️
:link: /docs/writing/

Learn to create content with markdown, frontmatter, and directives.
```

```{card} Theme Development
:icon: 🎨
:link: /docs/themes/

Build custom themes with Jinja2 templates and CSS.
```

```{card} API Reference
:icon: 📚
:link: /api/

Complete API documentation for developers.
```

```{card} Deployment
:icon: 🚀
:link: /docs/deployment/

Deploy to Netlify, Vercel, GitHub Pages, and more.
```
````

### Resource Links

````markdown
## Helpful Resources

```{cards}
:columns: 3

```{card} Documentation
:icon: 📖
:link: /docs/

Complete guides and references
```

```{card} GitHub
:icon: 💻
:link: https://github.com/user/repo

Source code and issues
```

```{card} Community
:icon: 💬
:link: https://discord.gg/example

Join our Discord server
```
````

## Best Practices

### Use Consistent Length

Keep card content similar length:

````markdown
✅ Good (similar length):
```{cards}
:columns: 3

```{card} Feature A
Short description here.
```

```{card} Feature B
Short description here.
```

```{card} Feature C
Short description here.
```

❌ Poor (uneven length):
```{cards}
:columns: 3

```{card} Feature A
Very long description that goes on and on...
```

```{card} Feature B
Short.
```

```{card} Feature C
Medium length description here.
```
````

### Choose Appropriate Column Count

- **2 columns:** Detailed cards with more content
- **3 columns:** Balanced (default, recommended)
- **4 columns:** Brief cards, many items

### Use Meaningful Icons

````markdown
✅ Good icons:
- ⚡ Speed/Performance
- 📝 Writing/Content
- 🔍 Search/SEO
- 🎨 Design/Themes
- 🚀 Deployment/Launch

❌ Avoid:
- Random emoji
- Same icon for everything
- Too many different icons
````

## Quick Reference

**Single card:**
````markdown
```{card} Title
:icon: 🎯
:link: /page/

Content here
```
````

**Card grid:**
````markdown
```{cards}
:columns: 3

```{card} Card 1
...
```

```{card} Card 2
...
```
````

## Next Steps

- **[Buttons](buttons.md)** - Call-to-action buttons
- **[Tabs](tabs.md)** - Tabbed content
- **[Admonitions](admonitions.md)** - Callout boxes
- **[Kitchen Sink](../kitchen-sink.md)** - See cards in action

## Related

- [Directives Overview](index.md) - All directives
- [Quick Reference](quick-reference.md) - Syntax cheatsheet
- [Content Organization](../writing/content-organization.md) - Site structure

