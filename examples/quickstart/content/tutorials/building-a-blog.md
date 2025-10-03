---
title: "Building a Blog with Bengal"
date: 2025-10-03
tags: ["tutorial", "beginner", "blog"]
categories: ["Tutorials"]
type: "tutorial"
description: "Step-by-step guide to creating a full-featured blog with Bengal SSG"
author: "Bengal Documentation Team"
difficulty: "Beginner"
duration: "30 minutes"
---

# Building a Blog with Bengal

Learn how to create a full-featured blog from scratch using Bengal SSG.

## What You'll Build

By the end of this tutorial, you'll have:

- ✅ A complete blog with multiple posts
- ✅ Homepage with recent posts
- ✅ Individual post pages
- ✅ Tag system for organization
- ✅ Archive page for all posts
- ✅ RSS feed for subscribers
- ✅ Sitemap for SEO

## Prerequisites

- Bengal SSG installed (`pip install bengal-ssg`)
- Basic knowledge of Markdown
- Text editor of your choice

## Step 1: Create a New Site

Create a new directory for your blog:

```bash
# Create and navigate to project directory
mkdir my-blog
cd my-blog

# Create necessary directories
mkdir -p content/posts
mkdir -p assets/images
```

## Step 2: Create Configuration

Create `bengal.toml`:

```toml
[site]
title = "My Tech Blog"
baseurl = "https://myblog.example.com"
description = "Thoughts on software development and technology"
author = "Your Name"

[build]
output_dir = "public"
parallel = true
incremental = true

[assets]
minify = true
optimize = true
fingerprint = true

[features]
generate_sitemap = true
generate_rss = true
validate_links = true

[pagination]
items_per_page = 10
```

## Step 3: Create Homepage

Create `content/index.md`:

```markdown
---
title: "Welcome to My Tech Blog"
type: index
---

# Welcome to My Tech Blog

Hi! I'm a software developer sharing my thoughts on technology,
programming, and software development.

## Recent Posts

Check out my latest posts below or browse by [tags](/tags/).

## About Me

I'm passionate about building great software and sharing what I learn
along the way. [Learn more about me](/about/).
```

## Step 4: Create About Page

Create `content/about.md`:

```markdown
---
title: "About Me"
type: page
---

# About Me

I'm a software developer with a passion for clean code, performance
optimization, and developer tools.

## What I Write About

- Software architecture
- Performance optimization
- Developer tools
- Best practices
- Technology trends

## Get In Touch

- GitHub: [@yourusername](https://github.com/yourusername)
- Twitter: [@yourusername](https://twitter.com/yourusername)
- Email: your.email@example.com
```

## Step 5: Create Your First Post

Create `content/posts/my-first-post.md`:

```markdown
---
title: "My First Blog Post"
date: 2025-10-01
tags: ["meta", "introduction"]
categories: ["Blog"]
description: "Welcome to my new blog built with Bengal SSG"
author: "Your Name"
---

# My First Blog Post

Welcome to my new blog! I'm excited to start sharing my thoughts on
software development and technology.

## Why I Started This Blog

I wanted a platform to:

- Share what I'm learning
- Document my projects
- Connect with other developers
- Give back to the community

## What to Expect

I'll be writing about:

- Software architecture and design patterns
- Performance optimization techniques
- Tools that improve developer productivity
- Lessons learned from real projects

## About the Tech Stack

This blog is built with [Bengal SSG](https://github.com/bengal-ssg/bengal),
a high-performance static site generator written in Python.

Why Bengal?

- ⚡ Lightning fast builds with incremental builds
- 🚀 Parallel processing for speed
- 📝 Simple Markdown-based content
- 🎨 Flexible Jinja2 templates
- 🔧 Easy to customize

## Stay Updated

Subscribe to the [RSS feed](/feed.xml) to get notified of new posts!
```

## Step 6: Add More Posts

Create `content/posts/understanding-static-sites.md`:

```markdown
---
title: "Understanding Static Site Generators"
date: 2025-10-02
tags: ["static-sites", "jamstack", "tutorial"]
categories: ["Tutorials", "Web Development"]
description: "What are static site generators and why should you use them?"
author: "Your Name"
---

# Understanding Static Site Generators

Static site generators (SSGs) have become increasingly popular for blogs,
documentation, and marketing sites. Let's explore why.

## What is a Static Site?

A static site consists of pre-generated HTML files that are served directly
to users. Unlike dynamic sites, there's no server-side processing for each
request.

### Benefits of Static Sites

1. **Performance**: Pre-generated HTML is incredibly fast
2. **Security**: No database or server-side code to hack
3. **Scalability**: Easy to serve from CDNs
4. **Cost**: Can host for free on many platforms

## How SSGs Work

```
Markdown Files → SSG → HTML Files → Deploy
```

The process:

1. Write content in Markdown
2. Run the build command
3. SSG generates HTML files
4. Deploy to any static host

## Popular SSGs

| SSG | Language | Best For |
|-----|----------|----------|
| Bengal | Python | Performance, flexibility |
| Hugo | Go | Speed, documentation |
| Jekyll | Ruby | GitHub Pages integration |
| Gatsby | JavaScript | React sites |

## When to Use SSGs

✅ **Perfect for:**
- Blogs and personal sites
- Documentation
- Marketing sites
- Portfolios

❌ **Not ideal for:**
- Real-time applications
- User-generated content
- Complex web apps

## Conclusion

Static site generators offer an excellent balance of simplicity, performance,
and developer experience. They're perfect for content-focused sites like blogs.

Want to build your own? Check out [Bengal SSG](https://github.com/bengal-ssg/bengal)!
```

## Step 7: Add a Technical Post

Create `content/posts/incremental-builds-explained.md`:

```markdown
---
title: "How Incremental Builds Work"
date: 2025-10-03
tags: ["performance", "builds", "technical"]
categories: ["Technical"]
description: "Deep dive into incremental build systems"
author: "Your Name"
---

# How Incremental Builds Work

Incremental builds are a game-changer for static site generators.
Let's explore how they provide 18-42x faster rebuilds.

## The Problem

Traditional static site generators rebuild everything on every change.
For a 1000-page site, this can take minutes—frustrating during development.

## The Solution

Incremental builds only rebuild what changed:

1. **Track file hashes** - Detect changes via SHA256 hashing
2. **Build dependency graph** - Know what depends on what
3. **Selective rebuilding** - Only rebuild affected files
4. **Cache results** - Store between builds

## Performance Impact

Real results from Bengal's incremental builds:

| Site Size | Full Build | Incremental | Speedup |
|-----------|-----------|-------------|---------|
| 10 pages | 0.223s | 0.012s | 18.6x |
| 50 pages | 0.839s | 0.020s | 41.6x |
| 100 pages | 1.688s | 0.047s | 35.6x |

## Implementation Details

### File Hashing

```python
import hashlib

def hash_file(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()
```

### Dependency Tracking

When page A includes template B:
- Record: A depends on B
- If B changes: rebuild A
- If A changes: rebuild A only

### Cache Storage

```json
{
  "files": {
    "content/post.md": {
      "hash": "abc123...",
      "dependencies": ["templates/post.html"]
    }
  }
}
```

## Best Practices

✅ **Use for development** - Fast iteration  
✅ **Use verbose mode** - Understand dependencies  
❌ **Don't use for CI/CD** - Clean builds are safer

## Conclusion

Incremental builds dramatically improve developer experience. They're
essential for working with large sites.

Learn more: [Incremental Builds Documentation](/docs/incremental-builds/)
```

## Step 8: Build Your Site

Now build your blog:

```bash
# First build (creates cache)
bengal build --incremental --verbose

# The output directory now contains your site
ls public/
```

You should see:
```
public/
├── index.html
├── about/
│   └── index.html
├── posts/
│   ├── my-first-post/
│   ├── understanding-static-sites/
│   └── incremental-builds-explained/
├── tags/
│   ├── meta/
│   ├── tutorial/
│   └── ...
├── feed.xml
└── sitemap.xml
```

## Step 9: Preview Your Site

Start the development server:

```bash
bengal serve
```

Visit `http://localhost:8000` to see your blog!

The dev server automatically rebuilds when you make changes.

## Step 10: Add Custom Styles (Optional)

Create `assets/css/custom.css`:

```css
/* Custom blog styles */
:root {
    --primary-color: #0066cc;
    --text-color: #333;
}

.blog-header {
    background: var(--primary-color);
    color: white;
    padding: 2rem;
    text-align: center;
}

.post-meta {
    color: #666;
    font-size: 0.9rem;
    margin-bottom: 2rem;
}

.post-tags {
    margin-top: 2rem;
}

.tag {
    background: #f0f0f0;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    margin-right: 0.5rem;
    text-decoration: none;
}
```

## Step 11: Customize Templates (Optional)

Create `templates/post.html` to override the default:

```jinja2
{{ '{% extends "base.html" %}' }}

{{ '{% block content %}' }}
<article class="blog-post">
  <header>
    <h1>{{ '{{ page.title }}' }}</h1>
    <div class="post-meta">
      <time datetime="{{ '{{ page.date | dateformat' }}('%Y-%m-%d') }}">
        {{ '{{ page.date | dateformat' }}('%B %d, %Y') }}
      </time>
      {{ '{% if page.metadata.author %}' }}
        <span> • By {{ '{{ page.metadata.author }}' }}</span>
      {{ '{% endif %}' }}
    </div>
  </header>

  <div class="post-content">
    {{ '{{ content }}' }}
  </div>

  {{ '{% if page.tags %}' }}
    <footer class="post-tags">
      <strong>Tags:</strong>
      {{ '{% for tag in page.tags %}' }}
        <a href="/tags/{{ '{{ tag }}' }}/" class="tag">{{ '{{ tag }}' }}</a>
      {{ '{% endfor %}' }}
    </footer>
  {{ '{% endif %}' }}
</article>
{{ '{% endblock %}' }}
```

## Step 12: Deploy Your Blog

Build for production:

```bash
# Clean build for production
bengal clean
bengal build --parallel

# The public/ directory is ready to deploy
```

### Deployment Options

**Netlify**:
```bash
# Deploy with Netlify CLI
netlify deploy --prod --dir=public
```

**GitHub Pages**:
```bash
# Push public/ to gh-pages branch
git subtree push --prefix public origin gh-pages
```

**Any Static Host**:
- Upload `public/` directory
- Point domain to the files

## What You've Learned

Congratulations! You now know how to:

- ✅ Set up a Bengal site
- ✅ Configure your blog
- ✅ Write posts in Markdown
- ✅ Use tags for organization
- ✅ Build and preview locally
- ✅ Customize styles and templates
- ✅ Deploy to production

## Next Steps

Now that you have a working blog:

1. **Add more content** - Write regularly
2. **Customize the design** - Make it your own
3. **Add analytics** - Track your visitors
4. **Share your posts** - On social media
5. **Engage with readers** - Add comments (Disqus, utterances)

## Learn More

- [Creating a Custom Theme](/tutorials/custom-theme/)
- [Template System Reference](/docs/template-system/)
- [Configuration Reference](/docs/configuration-reference/)
- [Performance Optimization](/guides/performance-optimization/)

## Troubleshooting

**Build fails**: Check syntax in `bengal.toml`  
**Pages not showing**: Verify file paths and frontmatter  
**Styles not loading**: Check asset_url() usage in templates

Happy blogging! 🎉

