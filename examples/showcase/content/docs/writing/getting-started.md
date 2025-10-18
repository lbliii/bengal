---
title: Getting Started with Writing
description: Create your first page in Bengal SSG
type: doc
weight: 1
tags: ["getting-started", "beginner", "tutorial"]
toc: true
---

# Getting Started with Writing

**Purpose**: Create your first Bengal page and preview it locally in under 5 minutes.

## What You'll Learn

- Create a new markdown file
- Add essential frontmatter
- Write basic content
- Preview your page locally

## Prerequisites

You should have Bengal installed and a site initialized. If not:

```bash
# Install Bengal
pip install -e .

# Create a new site
bengal new site mysite
cd mysite
```

## Create Your First Page

### Step 1: Create the File

Create a new markdown file in your `content/` directory:

```bash
# Create a simple page
touch content/my-first-page.md

# Or create a page in a section
mkdir -p content/blog
touch content/blog/welcome.md
```

### Step 2: Add Frontmatter

Open the file and add frontmatter at the top:

```yaml
---
title: My First Page
description: This is my first page in Bengal
date: 2025-10-11
tags: ["introduction", "first-post"]
---
```

**Essential fields:**
- `title` - Page title (required)
- `description` - Short summary for SEO
- `date` - Publication date
- `tags` - Categories for organization

### Step 3: Write Content

Below the frontmatter, write your content using markdown:

```markdown
---
title: My First Page
description: This is my first page in Bengal
date: 2025-10-11
---

# Welcome to My Site

This is my first page! I can write content using **markdown**.

## What I'll Write About

Here are some topics I plan to cover:

- Web development
- Static site generators
- Content creation

Check out my [about page](/about/) to learn more.
```

### Step 4: Preview Locally

Build and preview your site:

```bash
# Build the site
bengal site build

# Start the development server
bengal site serve
```

Open your browser to `http://localhost:5173` and navigate to your new page!

## Your Page Structure

Here's what a complete page looks like:

```markdown
---
title: Page Title Here
description: A brief summary of the page
date: 2025-10-11
tags: ["tag1", "tag2"]
draft: false
---

# Page Title Here

Opening paragraph that introduces the topic.

## First Section

Content for the first section with **bold** and *italic* text.

### Subsection

More detailed information here.

## Second Section

Another section with a list:

- Item one
- Item two
- Item three

## Conclusion

Wrap up your thoughts here.
```

## Development Workflow

```{tip} Live Reload
Use `bengal site serve` for automatic rebuilds when you save files. Your browser will refresh automatically!
```

The typical workflow:

1. **Edit** - Make changes to your markdown files
2. **Save** - File watcher detects changes
3. **Auto-rebuild** - Bengal rebuilds affected pages
4. **Preview** - Browser refreshes automatically

## Common Mistakes

```{warning} Common Issues
Avoid these beginner mistakes:
```

- **Missing frontmatter delimiters**: Must have `---` before and after
- **Invalid YAML**: Check indentation and syntax
- **Wrong file location**: Pages must be in `content/` directory
- **Missing title**: Always include a title in frontmatter

## Quick Tips

```{success} Pro Tips
- Use descriptive filenames: `how-to-install.md` not `page1.md`
- Keep titles under 60 characters for SEO
- Write descriptions between 120-160 characters
- Use tags consistently across your content
```

## Next Steps

Now that you have your first page, learn more:

- **[Markdown Basics](markdown-basics.md)** - Learn essential markdown syntax
- **[Frontmatter Guide](frontmatter-guide.md)** - Master page metadata
- **[Content Organization](content-organization.md)** - Structure your site
- **[Internal Links](internal-links.md)** - Link pages together

## Example: Blog Post

Here's a complete example of a blog post:

```markdown
---
title: Getting Started with Python
description: A beginner's guide to Python programming
date: 2025-10-11
author: Jane Developer
tags: ["python", "tutorial", "beginner"]
type: post
---

# Getting Started with Python

Python is a versatile programming language perfect for beginners.

## Why Learn Python?

Python is popular because:

1. **Easy to read** - Clear, simple syntax
2. **Versatile** - Web, data science, automation
3. **Great community** - Tons of resources

## Your First Program

Let's write a simple program:

\`\`\`python
print("Hello, World!")
\`\`\`

When you run this, it prints: Hello, World!

## Next Steps

Now try writing your own programs!
```

## Related Guides

- [Markdown Basics](markdown-basics.md) - Essential markdown syntax
- [Content Organization](content-organization.md) - Site structure
- [Blog Posts](../content-types/blog-posts.md) - Writing blog content
