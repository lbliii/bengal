---
title: Navigation and Menus
description: Configure site menus and navigation structure
type: doc
weight: 3
tags: ["advanced", "navigation", "menus"]
toc: true
---

# Navigation and Menus

**Purpose**: Configure site menus for easy navigation.

## What You'll Learn

- Configure menus in `bengal.toml`
- Add pages to menus via frontmatter
- Create nested menus
- Control menu ordering

## Menu Configuration

Configure menus in `bengal.toml`:

```toml
[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Docs"
url = "/docs/"
weight = 10

[[menu.main]]
name = "Blog"
url = "/blog/"
weight = 20
```

## Menu from Frontmatter

Add pages to menus via frontmatter:

```yaml
---
title: About
menu:
  main:
    weight: 30
---
```

**Or with custom name:**

```yaml
---
title: Documentation
menu:
  main:
    name: "Docs"
    weight: 10
---
```

## Menu Types

### Main Menu

Primary navigation:

```toml
[[menu.main]]
name = "Documentation"
url = "/docs/"
weight = 10
```

### Footer Menu

Footer links:

```toml
[[menu.footer]]
name = "Privacy"
url = "/privacy/"
weight = 10

[[menu.footer]]
name = "Terms"
url = "/terms/"
weight = 20
```

### Custom Menus

Create any menu:

```toml
[[menu.social]]
name = "GitHub"
url = "https://github.com/user/repo"
weight = 10
```

## Menu Ordering

### Weight

Lower weights appear first:

```toml
[[menu.main]]
name = "Home"
weight = 1      # First

[[menu.main]]
name = "Docs"
weight = 10     # Second

[[menu.main]]
name = "Blog"
weight = 20     # Third
```

## Nested Menus

Create dropdown menus:

```toml
[[menu.main]]
name = "Documentation"
url = "/docs/"
weight = 10

[[menu.main]]
name = "Getting Started"
url = "/docs/getting-started/"
parent = "Documentation"
weight = 1

[[menu.main]]
name = "Guides"
url = "/docs/guides/"
parent = "Documentation"
weight = 10
```

## Complete Example

```toml
# bengal.toml

# Main navigation
[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Documentation"
url = "/docs/"
weight = 10

[[menu.main]]
name = "Guides"
url = "/docs/guides/"
parent = "Documentation"
weight = 1

[[menu.main]]
name = "API Reference"
url = "/docs/api/"
parent = "Documentation"
weight = 10

[[menu.main]]
name = "Blog"
url = "/blog/"
weight = 20

[[menu.main]]
name = "About"
url = "/about/"
weight = 30

# Footer menu
[[menu.footer]]
name = "Privacy Policy"
url = "/privacy/"
weight = 10

[[menu.footer]]
name = "Terms of Service"
url = "/terms/"
weight = 20

# Social links
[[menu.social]]
name = "GitHub"
url = "https://github.com/user/repo"
weight = 10

[[menu.social]]
name = "Twitter"
url = "https://twitter.com/user"
weight = 20
```

## Best Practices

### Keep Menus Short

```toml
✅ Good (5-7 items):
- Home
- Docs
- Blog
- About
- Contact

❌ Too many (10+ items):
(Overwhelming for users)
```

### Use Clear Names

```toml
✅ Clear:
name = "Documentation"
name = "Getting Started"
name = "API Reference"

❌ Vague:
name = "Docs"
name = "Start"
name = "API"
```

### Logical Order

```toml
✅ Good flow:
1. Home
2. Products
3. Documentation
4. Blog
5. About

❌ Random:
1. Blog
2. About
3. Home
4. Products
```

## Next Steps

- **[SEO](seo.md)** - Search optimization
- **[Taxonomies](taxonomies.md)** - Tags and categories
- **[Content Organization](../writing/content-organization.md)** - Structure

## Related

- [Frontmatter Guide](../writing/frontmatter-guide.md)  - Metadata
- [Internal Links](../writing/internal-links.md) - Cross-references
