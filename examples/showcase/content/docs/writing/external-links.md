---
title: External Links
description: Best practices for linking to external resources and websites
type: doc
weight: 7
tags: ["links", "external", "seo"]
toc: true
---

# External Links

**Purpose**: Learn best practices for linking to external websites and resources.

## What You'll Learn

- Create external links properly
- Handle link security and SEO
- Choose when to open in new tabs
- Write accessible link text
- Validate external links

## Basic External Links

Link to external websites with standard markdown:

```markdown
Visit the [Bengal website](https://bengal-ssg.org).
Learn more at [Python.org](https://www.python.org).
Read the [Jinja2 docs](https://jinja.palletsprojects.com/).
```

**Result:** Visit the [Bengal website](https://bengal-ssg.org).

## Opening in New Tabs

By default, links open in the same tab. To open in a new tab, use HTML:

```markdown
Visit <a href="https://bengal-ssg.org" target="_blank" rel="noopener noreferrer">Bengal's website</a>.
```

```{warning} Security Note
Always include `rel="noopener noreferrer"` with `target="_blank"` to prevent security vulnerabilities.
```

### When to Use New Tabs

**Open in new tab** (external site):
- External documentation
- Reference materials
- Social media profiles
- External tools/services

**Open in same tab** (default):
- Internal site pages
- Related articles on your site
- Most cases (let users decide)

```{tip} User Choice
Many users prefer to control how links open. Use `target="_blank"` sparingly, mainly for external resources when context switching is important.
```

## Link Security

### rel Attributes

For external links that open in new tabs:

```html
<a href="https://example.com"
   target="_blank"
   rel="noopener noreferrer">
  External Site
</a>
```

**What they do:**
- `noopener` - Prevents the new page from accessing `window.opener`
- `noreferrer` - Doesn't send referrer information

### Untrusted Links

For user-generated content or untrusted sources:

```html
<a href="https://untrusted.example.com"
   rel="nofollow noopener noreferrer">
  Untrusted Link
</a>
```

`nofollow` tells search engines not to pass SEO value to the linked site.

## Link Text Best Practices

### Descriptive Text

```markdown
✅ Good:
Read the [official Python tutorial](https://docs.python.org/3/tutorial/).
Learn more about [static site generators](https://jamstack.org/generators/).
See [GitHub's markdown guide](https://guides.github.com/features/mastering-markdown/).

❌ Avoid:
Click [here](https://docs.python.org) for Python docs.
Read more [here](https://jamstack.org).
[Link](https://github.com)
```

### Why It Matters

**Accessibility:**
- Screen readers read link text out of context
- "Click here" × 50 is confusing
- Descriptive text provides context

**SEO:**
- Search engines use link text for context
- Descriptive text improves relevance
- Generic text provides no SEO value

**Usability:**
- Users scan pages for keywords
- Descriptive links are easier to find
- Context helps users decide to click

## URL Formatting

### Protocol

Always include `https://`:

```markdown
✅ Correct:
[Example](https://example.com)

❌ Wrong:
[Example](example.com)
[Example](www.example.com)
```

### Trailing Slashes

Be consistent with trailing slashes:

```markdown
# Both work, but be consistent
[Docs](https://bengal-ssg.org/docs/)
[Docs](https://bengal-ssg.org/docs)
```

### Query Parameters

Encode special characters in URLs:

```markdown
[Search](https://example.com/search?q=static+sites&lang=en)
```

## Common External Link Patterns

### Documentation References

```markdown
Bengal uses [Jinja2](https://jinja.palletsprojects.com/) for templating and [Mistune](https://mistune.lepture.com/) for markdown parsing.

For deployment, see:
- [Netlify Docs](https://docs.netlify.com/)
- [Vercel Docs](https://vercel.com/docs)
- [GitHub Pages](https://pages.github.com/)
```

### Social Links

```markdown
## Connect With Me

- 🐦 Twitter: [@username](https://twitter.com/username)
- 💼 LinkedIn: [My Profile](https://linkedin.com/in/username)
- 🐙 GitHub: [@username](https://github.com/username)
```

### Resource Lists

```markdown
## Helpful Resources

- [MDN Web Docs](https://developer.mozilla.org/) - Web development reference
- [Can I Use](https://caniuse.com/) - Browser compatibility tables
- [Stack Overflow](https://stackoverflow.com/) - Programming Q&A
```

### Citations and References

```markdown
According to the [Jamstack survey](https://jamstack.org/survey/2024/), static sites are growing in popularity[^1].

[^1]: Jamstack Community Survey 2024
```

## SEO Considerations

### Linking to Authority Sites

Link to high-quality, authoritative sources:

```markdown
✅ Good:
According to [W3C specifications](https://www.w3.org/TR/html52/)...
As documented in [MDN](https://developer.mozilla.org/)...

❌ Poor:
Some random blog says... [link to spam site]
```

### Anchor Text Diversity

Vary your link text:

```markdown
# Don't repeat the same anchor text
Read the Python docs ↓

❌ Repetitive:
[Python documentation](https://docs.python.org)
[Python documentation](https://docs.python.org/tutorial/)
[Python documentation](https://docs.python.org/library/)

✅ Varied:
[Python documentation](https://docs.python.org)
[Python tutorial](https://docs.python.org/tutorial/)
[Python standard library](https://docs.python.org/library/)
```

### Link Context

Surround links with relevant context:

```markdown
✅ Good context:
Bengal supports Jinja2 templating. Learn more in the
[official Jinja2 documentation](https://jinja.palletsprojects.com/)
which covers filters, functions, and template inheritance.

❌ No context:
[Click here](https://jinja.palletsprojects.com/)
```

## Link Validation

### Manual Testing

Test external links periodically:

```bash
# Build and check health report
bengal build

# Look for link validation warnings
```

### Tools

Use link checking tools:

```bash
# Example: Use wget to check links
wget --spider --recursive --level=1 https://yoursite.com

# Or use online tools
# - W3C Link Checker
# - Broken Link Checker
```

### Handling Broken Links

When external sites change:

```markdown
✅ Update links:
- Check if page moved (redirects)
- Find new URL
- Update link in content

✅ Use Internet Archive:
[Original article](https://web.archive.org/web/*/example.com)

✅ Note unavailability:
> **Note:** Original source no longer available. Archived version: [...]
```

## Accessibility

### Link Purpose

Links should be clear from their text alone:

```markdown
✅ Clear purpose:
[Download Python 3.11](https://python.org/downloads/)
[Read the installation guide](https://docs.python.org/install/)

❌ Unclear:
[Click here](https://python.org)
Download [here](https://python.org)
```

### Visual Indicators

Ensure links are visually distinct:

- Different color from body text
- Underline on hover
- Clear focus state for keyboard navigation

(Handled by theme CSS, but worth noting for custom themes)

## Link Organization

### Resource Sections

Group related external links:

```markdown
## Learning Resources

### Official Documentation
- [Python Docs](https://docs.python.org/)
- [Jinja2 Docs](https://jinja.palletsprojects.com/)

### Tutorials
- [Real Python](https://realpython.com/)
- [Python Tutorial](https://www.python.org/about/gettingstarted/)

### Community
- [Python Discord](https://pythondiscord.com/)
- [r/Python](https://reddit.com/r/Python/)
```

### Inline vs Reference Style

**Inline** (most common):
```markdown
Visit the [Bengal website](https://bengal-ssg.org) for more info.
```

**Reference style** (for repeated links):
```markdown
Visit the [Bengal website][bengal] for docs.
Check out [Bengal][bengal] on GitHub.

[bengal]: https://bengal-ssg.org
```

## Examples

### Blog Post Citations

```markdown
# Static Sites are Growing

According to [Netlify's survey](https://netlify.com/blog/2024-survey),
78% of developers use static site generators.

The [Jamstack community](https://jamstack.org) defines modern web
architecture as...
```

### Documentation References

```markdown
## Template Syntax

Bengal uses Jinja2 for templates. Key features:

- **Variables**: See [Jinja2 variables](https://jinja.palletsprojects.com/templates/#variables)
- **Filters**: See [built-in filters](https://jinja.palletsprojects.com/templates/#list-of-builtin-filters)
- **Control**: See [control structures](https://jinja.palletsprojects.com/templates/#list-of-control-structures)
```

### Tutorial External Tools

```markdown
## Prerequisites

Install these tools before starting:

1. **Python 3.8+**: [Download Python](https://python.org/downloads/)
2. **Git**: [Install Git](https://git-scm.com/downloads)
3. **VS Code**: [Download VS Code](https://code.visualstudio.com/)
```

## Best Practices Summary

```{success} External Link Checklist
- ✅ Use descriptive link text
- ✅ Include `https://` protocol
- ✅ Add `rel="noopener noreferrer"` for new tabs
- ✅ Link to authoritative sources
- ✅ Validate links periodically
- ✅ Provide context around links
- ✅ Make links accessible
- ✅ Update broken links
```

## Quick Reference

| Scenario | Example |
|----------|---------|
| Basic link | `[Text](https://example.com)` |
| New tab | `<a href="https://example.com" target="_blank" rel="noopener noreferrer">Text</a>` |
| With title | `[Text](https://example.com "Hover text")` |
| Nofollow | `<a href="..." rel="nofollow">Text</a>` |

## Next Steps

Now you know how to link externally. Next:

- **[Images and Assets](images-and-assets.md)** - Add media to content
- **[Internal Links](internal-links.md)** - Cross-reference pages
- **[SEO](../advanced/seo.md)** - Optimize for search engines

## Related

- [Internal Links](internal-links.md) - Link between pages
- [Markdown Basics](markdown-basics.md) - Essential syntax
- [SEO Guide](../advanced/seo.md) - SEO best practices
