---
title: Start Writing
description: Create your first site and start writing content
weight: 40
type: doc
draft: false
lang: en
tags: [onboarding, writing, quickstart]
keywords: [writing, content, markdown, frontmatter]
category: onboarding
---

# Writer Quickstart

Get from zero to published content in 5 minutes. This guide is for content creators who want to focus on writing.

## Prerequisites

- [Bengal installed](/docs/getting-started/installation/)
- Basic knowledge of Markdown

## Start

::::{steps}
1. **Create Your Site**

   Use the interactive wizard to create a site:

   ```bash
   bengal new site myblog
   ```

   Choose a preset that matches your goal:

   ```bash
   » 📝 Blog          - Personal or professional blog
     📚 Documentation - Technical docs or guides
     💼 Portfolio     - Showcase your work
     🏢 Business      - Company or product site
     📄 Resume        - Professional resume/CV site
   ```

   ```{tip}
   Choose **Blog** if you're unsure. It's a great starting point.
   ```

   ```bash
   cd myblog
   ```

2. **Start the Dev Server**

   Launch the development server with hot reload:

   ```bash
   bengal site serve
   ```

   Open **http://localhost:5173/** in your browser. You'll see your new site!

   :::{note}
   The dev server automatically rebuilds when you save changes. Keep it running while you work.
   :::

3. **Create Your First Post**

   ```bash
   bengal new page my-first-post --section blog
   ```

   This creates `content/blog/my-first-post.md`. Open it and edit:

   ```markdown
   ---
   title: My First Post
   date: 2025-10-26
   tags: [welcome, tutorial]
   description: Getting started with Bengal
   ---

   # My First Post

   Welcome to my new blog! This is my first post using Bengal.

   ## Why I Chose Bengal

   - Fast builds with parallel processing
   - Simple Markdown-based workflow
   - Customizable themes and templates
   - No complicated build tooling

   ## What's Next?

   I'm excited to share more content about:

   1. Python development
   2. Web performance
   3. Static site generators

   Stay tuned!
   ```

   **Save the file.** The dev server automatically rebuilds and your new post appears!

4. **Customize Your Site**

   Edit `bengal.toml` to personalize your site:

   ```toml
   [site]
   title = "My Awesome Blog"
   description = "Thoughts on code, design, and life"
   baseurl = "https://myblog.com"  # Your future domain
   author = "Your Name"
   language = "en"
   ```

5. **Add More Content**

   ### Create Regular Pages

   ```bash
   # About page
   bengal new page about

   # Contact page
   bengal new page contact
   ```

   ### Organize with Sections

   ```bash
   # Create a guides section
   bengal new page getting-started --section guides
   bengal new page advanced-tips --section guides
   ```

   ### Use Frontmatter

   Control how pages appear with frontmatter metadata:

   ```yaml
   ---
   title: Advanced Python Tips
   date: 2025-10-26
   tags: [python, advanced]
   description: Take your Python skills to the next level
   weight: 10               # Lower numbers appear first
   draft: false             # Set to true to hide during builds
   keywords: [python, advanced, tutorial]
   ---
   ```

   **Common frontmatter keys:**
   - `title` - Page title (required)
   - `date` - Publication date for sorting
   - `tags` - Tags for taxonomy pages (e.g., `[python, web]`)
   - `weight` - Sort order (lower numbers appear first)
   - `draft` - Set to `true` to hide during builds
   - `description` - SEO description

   For a complete reference of all supported frontmatter keys, see the [Frontmatter Reference](/api/core/page/) documentation.

6. **Build for Production**

   When you're ready to publish:

   ```bash
   # Clean previous builds
   bengal site clean

   # Build the site
   bengal site build
   ```

   Your complete site is in the `public/` directory, ready to deploy!

7. **Deploy Your Site**

   Deploy the `public/` directory to any static hosting:

   **Netlify:**
   1. Push your code to GitHub
   2. Connect to Netlify
   3. Build command: `bengal site build`
   4. Publish directory: `public`

   **GitHub Pages:**
   ```bash
   git subtree push --prefix public origin gh-pages
   ```

   **Vercel, Cloudflare Pages:** Similar to Netlify - point to `public/`
::::

## Writing Tips

### Markdown Basics

Bengal supports standard Markdown syntax:

```markdown
# Heading 1
## Heading 2
### Heading 3

**bold text**
*italic text*

[link text](https://example.com)

![image alt text](../images/photo.jpg)

- Bullet list
- Another item

1. Numbered list
2. Another item

`inline code`

```python
# Code block
def hello():
    print("Hello, World!")
```
```

For advanced Markdown features, see the [Markdown Guide](/docs/about/concepts/templating/).

### Add Images

Place images in `assets/images/`:

```markdown
![My Photo](../assets/images/photo.jpg)
```

### Link Between Pages

```markdown
Check out my [about page](../about/)
Read my [first post](../blog/my-first-post/)
```

### Use Tags and Categories

```yaml
---
title: My Post
tags: [python, tutorial, beginner]
category: programming
---
```

Tags and categories automatically create archive pages!

## Troubleshooting

### Common Issues

**Dev server won't start:**
- Check if port 5173 is already in use: `lsof -i :5173`
- Try a different port: `bengal site serve --port 8080`

**Pages not appearing:**
- Verify frontmatter has a `title` field
- Check if `draft: true` is set (remove or set to `false`)
- Ensure file is in `content/` directory or a subdirectory

**Markdown not rendering correctly:**
- Check for proper frontmatter delimiters (`---` at start and end)
- Verify YAML syntax (no tabs, proper indentation)
- Check for special characters that need escaping

**Build errors:**
- Run `bengal site build --verbose` for detailed error messages
- Check `bengal.toml` for syntax errors
- Verify all required fields in frontmatter

## Next Steps

**Learn More:**
- **[Configuration Guide](/docs/about/concepts/configuration/)** - Explore all config options
- **[Theming Guide](/docs/getting-started/themer-quickstart/)** - Change your site's appearance
- **[Content Organization](/docs/about/concepts/content-organization/)** - Advanced content features

**Get Inspired:**
- Check `site/content/` for example posts
- Browse [Bengal themes](/themes/)
- Read the [full documentation](/docs/)

**Need Help?**
- Join discussions on [GitHub](https://github.com/lbliii/bengal)
- Check out example sites in the repo

Happy writing! 🎉
