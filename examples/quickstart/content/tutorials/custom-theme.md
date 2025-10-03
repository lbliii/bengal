---
title: "Creating a Custom Theme"
date: 2025-10-03
tags: ["tutorial", "theming", "customization", "advanced"]
categories: ["Tutorials", "Design"]
type: "tutorial"
description: "Build your own custom Bengal theme from scratch"
author: "Bengal Documentation Team"
difficulty: "Intermediate"
duration: "45 minutes"
---

# Creating a Custom Theme

Learn how to build a complete custom theme for Bengal SSG with templates, styles, and reusable components.

## What You'll Build

A complete custom theme with:

- ✅ Custom templates
- ✅ Unique design system
- ✅ Reusable components
- ✅ Responsive layout
- ✅ Dark mode support
- ✅ Custom CSS and JavaScript

## Prerequisites

- Basic HTML, CSS, and JavaScript knowledge
- Familiarity with Jinja2 templates (helpful but not required)
- A Bengal site to work with

## Theme Structure

A Bengal theme consists of:

```
themes/mytheme/
├── templates/          # Jinja2 templates
│   ├── base.html
│   ├── index.html
│   ├── page.html
│   ├── post.html
│   └── partials/
├── assets/             # Theme assets
│   ├── css/
│   ├── js/
│   └── images/
└── theme.toml          # Theme metadata (optional)
```

## Step 1: Create Theme Directory

```bash
mkdir -p themes/mytheme/templates/partials
mkdir -p themes/mytheme/assets/css
mkdir -p themes/mytheme/assets/js
```

## Step 2: Design System - CSS Variables

Create `themes/mytheme/assets/css/design-system.css`:

```css
:root {
  /* Colors */
  --color-primary: #2563eb;
  --color-secondary: #7c3aed;
  --color-accent: #f59e0b;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  
  /* Text colors */
  --color-text: #1f2937;
  --color-text-muted: #6b7280;
  --color-heading: #111827;
  
  /* Background colors */
  --color-bg: #ffffff;
  --color-bg-alt: #f9fafb;
  --color-bg-elevated: #ffffff;
  
  /* Border colors */
  --color-border: #e5e7eb;
  --color-border-hover: #d1d5db;
  
  /* Typography */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "SF Mono", Monaco, "Cascadia Code", monospace;
  
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;
  --font-size-4xl: 2.25rem;
  
  /* Spacing */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  
  /* Transitions */
  --transition-fast: 150ms ease-in-out;
  --transition-base: 200ms ease-in-out;
  --transition-slow: 300ms ease-in-out;
}

/* Dark mode */
[data-theme="dark"] {
  --color-text: #f9fafb;
  --color-text-muted: #d1d5db;
  --color-heading: #ffffff;
  --color-bg: #111827;
  --color-bg-alt: #1f2937;
  --color-bg-elevated: #374151;
  --color-border: #374151;
  --color-border-hover: #4b5563;
}
```

## Step 3: Base Layout Template

Create `themes/mytheme/templates/base.html`:

```jinja2
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}{{ page.title | default(site.title) }}{% endblock %}</title>
  
  <!-- Meta tags -->
  <meta name="description" content="{{ page.metadata.description | default(site.description) }}">
  {% if site.baseurl %}
    <link rel="canonical" href="{{ site.baseurl }}{{ url_for(page) }}">
  {% endif %}
  
  <!-- Stylesheets -->
  <link rel="stylesheet" href="{{ asset_url('css/design-system.css') }}">
  <link rel="stylesheet" href="{{ asset_url('css/components.css') }}">
  <link rel="stylesheet" href="{{ asset_url('css/layout.css') }}">
  
  {% block head %}{% endblock %}
</head>
<body>
  <!-- Header -->
  <header class="site-header">
    <div class="container">
      <div class="header-content">
        <div class="site-brand">
          <a href="/" class="site-title">{{ site.title }}</a>
          {% if site.description %}
            <p class="site-description">{{ site.description }}</p>
          {% endif %}
        </div>
        
        <nav class="site-nav">
          <a href="/" class="nav-link">Home</a>
          <a href="/docs/" class="nav-link">Docs</a>
          <a href="/tutorials/" class="nav-link">Tutorials</a>
          <a href="/about/" class="nav-link">About</a>
          <button class="theme-toggle" aria-label="Toggle theme">
            <span class="theme-icon">🌙</span>
          </button>
        </nav>
      </div>
    </div>
  </header>
  
  <!-- Main content -->
  <main class="site-main">
    <div class="container">
      {% block content %}{% endblock %}
    </div>
  </main>
  
  <!-- Footer -->
  <footer class="site-footer">
    <div class="container">
      <p>&copy; {{ "now" | dateformat("%Y") }} {{ site.title }}. All rights reserved.</p>
      <p>Built with <a href="https://github.com/bengal-ssg/bengal">Bengal SSG</a></p>
    </div>
  </footer>
  
  <!-- Scripts -->
  <script src="{{ asset_url('js/theme-toggle.js') }}"></script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

## Step 4: Post Template

Create `themes/mytheme/templates/post.html`:

```jinja2
{% extends "base.html" %}

{% block title %}{{ page.title }} - {{ site.title }}{% endblock %}

{% block content %}
<article class="post">
  <header class="post-header">
    <h1 class="post-title">{{ page.title }}</h1>
    
    <div class="post-meta">
      {% if page.date %}
        <time datetime="{{ page.date | dateformat('%Y-%m-%d') }}" class="post-date">
          {{ page.date | dateformat('%B %d, %Y') }}
        </time>
      {% endif %}
      
      {% if page.metadata.author %}
        <span class="post-author">by {{ page.metadata.author }}</span>
      {% endif %}
      
      {% if page.metadata.category %}
        <span class="post-category">in {{ page.metadata.category }}</span>
      {% endif %}
    </div>
    
    {% if page.tags %}
      <div class="post-tags">
        {% for tag in page.tags %}
          <a href="/tags/{{ tag }}/" class="tag">{{ tag }}</a>
        {% endfor %}
      </div>
    {% endif %}
  </header>
  
  <div class="post-content prose">
    {{ content }}
  </div>
  
  <footer class="post-footer">
    <div class="post-navigation">
      {% if page.metadata.previous %}
        <a href="{{ url_for(page.metadata.previous) }}" class="nav-prev">
          ← Previous: {{ page.metadata.previous.title }}
        </a>
      {% endif %}
      
      {% if page.metadata.next %}
        <a href="{{ url_for(page.metadata.next) }}" class="nav-next">
          Next: {{ page.metadata.next.title }} →
        </a>
      {% endif %}
    </div>
  </footer>
</article>
{% endblock %}
```

## Step 5: Component Styles

Create `themes/mytheme/assets/css/components.css`:

```css
/* Container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-4);
}

/* Button */
.btn {
  display: inline-block;
  padding: var(--space-2) var(--space-4);
  background: var(--color-primary);
  color: white;
  text-decoration: none;
  border-radius: 0.375rem;
  font-weight: 500;
  transition: background var(--transition-fast);
}

.btn:hover {
  background: var(--color-secondary);
}

/* Card */
.card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-base);
}

.card:hover {
  box-shadow: var(--shadow-md);
}

/* Tag */
.tag {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  background: var(--color-bg-alt);
  color: var(--color-text-muted);
  text-decoration: none;
  border-radius: 9999px;
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
}

.tag:hover {
  background: var(--color-primary);
  color: white;
}

/* Post styles */
.post-header {
  margin-bottom: var(--space-8);
  padding-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.post-title {
  font-size: var(--font-size-4xl);
  font-weight: 700;
  color: var(--color-heading);
  margin-bottom: var(--space-4);
  line-height: 1.2;
}

.post-meta {
  display: flex;
  gap: var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.post-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

/* Prose (content styles) */
.prose {
  font-size: var(--font-size-lg);
  line-height: 1.7;
  color: var(--color-text);
}

.prose h2 {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  margin-top: var(--space-12);
  margin-bottom: var(--space-4);
  color: var(--color-heading);
}

.prose h3 {
  font-size: var(--font-size-xl);
  font-weight: 600;
  margin-top: var(--space-8);
  margin-bottom: var(--space-3);
  color: var(--color-heading);
}

.prose p {
  margin-bottom: var(--space-4);
}

.prose code {
  background: var(--color-bg-alt);
  padding: 0.2em 0.4em;
  border-radius: 0.25rem;
  font-family: var(--font-mono);
  font-size: 0.9em;
}

.prose pre {
  background: var(--color-bg-alt);
  padding: var(--space-4);
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: var(--space-4) 0;
}

.prose pre code {
  background: none;
  padding: 0;
}

.prose a {
  color: var(--color-primary);
  text-decoration: underline;
}

.prose a:hover {
  color: var(--color-secondary);
}
```

## Step 6: Dark Mode Toggle

Create `themes/mytheme/assets/js/theme-toggle.js`:

```javascript
// Theme toggle functionality
(function() {
  const themeToggle = document.querySelector('.theme-toggle');
  const themeIcon = document.querySelector('.theme-icon');
  
  // Get saved theme or default to light
  const savedTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateIcon(savedTheme);
  
  // Toggle theme on click
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateIcon(newTheme);
  });
  
  function updateIcon(theme) {
    themeIcon.textContent = theme === 'light' ? '🌙' : '☀️';
  }
})();
```

## Step 7: Configure Your Theme

Update `bengal.toml`:

```toml
[site]
theme = "mytheme"  # Use your custom theme
```

Or keep theme files in root:

```toml
[build]
templates_dir = "templates"
assets_dir = "assets"
```

## Step 8: Test Your Theme

```bash
# Build with your theme
bengal build

# Preview
bengal serve
```

Visit `http://localhost:8000` to see your custom theme!

## Step 9: Add More Templates

Create additional templates as needed:

**Index page** (`templates/index.html`):
```jinja2
{% extends "base.html" %}

{% block content %}
<div class="hero">
  <h1>{{ page.title }}</h1>
  <p>{{ site.description }}</p>
</div>

<div class="recent-posts">
  <h2>Recent Posts</h2>
  {% for post in site.pages[:5] %}
    {% if post.metadata.type == 'post' %}
      {% include "partials/post-card.html" %}
    {% endif %}
  {% endfor %}
</div>
{% endblock %}
```

**Post card partial** (`templates/partials/post-card.html`):
```jinja2
<div class="card post-card">
  <h3><a href="{{ url_for(post) }}">{{ post.title }}</a></h3>
  <p class="post-meta">
    {{ post.date | dateformat('%B %d, %Y') }}
  </p>
  <p>{{ post.metadata.description }}</p>
  <a href="{{ url_for(post) }}" class="btn">Read more →</a>
</div>
```

## Step 10: Responsive Design

Add responsive styles to `components.css`:

```css
/* Mobile-first responsive design */
@media (max-width: 768px) {
  .site-header .header-content {
    flex-direction: column;
    gap: var(--space-4);
  }
  
  .site-nav {
    flex-direction: column;
    width: 100%;
  }
  
  .post-title {
    font-size: var(--font-size-3xl);
  }
  
  .prose {
    font-size: var(--font-size-base);
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .container {
    max-width: 960px;
  }
}

@media (min-width: 1025px) {
  .container {
    max-width: 1200px;
  }
}
```

## Theme Distribution

To share your theme:

1. **Create theme.toml**:
```toml
name = "mytheme"
description = "A custom Bengal theme"
author = "Your Name"
version = "1.0.0"
license = "MIT"
```

2. **Package your theme**:
```
themes/mytheme/
├── theme.toml
├── templates/
├── assets/
└── README.md
```

3. **Share on GitHub** or package manager

## Best Practices

### ✅ Do

- Use CSS custom properties for theming
- Create reusable partials
- Test on multiple screen sizes
- Provide dark mode
- Use semantic HTML
- Optimize images and assets

### ❌ Don't

- Hardcode colors and sizes
- Duplicate template code
- Ignore accessibility
- Skip responsive design
- Forget browser compatibility

## What You've Learned

- ✅ Theme structure and organization
- ✅ Creating custom templates
- ✅ Building a design system
- ✅ Implementing dark mode
- ✅ Making responsive layouts
- ✅ Packaging and sharing themes

## Next Steps

- Add animations and transitions
- Create more page templates
- Build reusable components
- Add accessibility features
- Optimize performance
- Share your theme!

## Learn More

- [Template System Reference](/docs/template-system/)
- [Understanding Themes](/posts/understanding-themes/)
- [Custom Templates Guide](/posts/custom-templates/)

Happy theming! 🎨

