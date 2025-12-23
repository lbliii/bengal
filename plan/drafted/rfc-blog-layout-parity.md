# RFC: Blog Layout Quality Parity

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-23  
**Subsystems**: themes/default, templates/blog, css/components

---

## Executive Summary

Elevate the blog layout (`type: blog`) to the same polish, quality, and style as the documentation layout (`type: doc`), while keeping it tailored for the unique needs of blog content. The goal is not to replicate docs features, but to apply the same design system rigor and UX polish to blog-specific patterns.

---

## Problem Statement

The current blog layout is functional but lacks the refinement of the docs layout:

| Aspect | Docs Layout | Blog Layout | Gap |
|--------|------------|-------------|-----|
| Hero section | Animated blob backgrounds, magnetic titles | Plain centered text | Visual impact |
| Navigation | Sidebar with hierarchy, active states | Top nav only | Content discovery |
| Typography | Custom fonts, refined spacing | System defaults | Brand identity |
| Reading experience | TOC, progress indicator, smooth scrolling | Basic TOC on posts | Engagement |
| Content discovery | Graph visualization, related content | Basic "related posts" | Exploration |
| Mobile experience | Refined responsive, touch targets | Basic responsive | Polish |

**Core issue**: Blog users expect the same level of care applied to their reading experience as docs users get. Currently, blogs feel like an afterthought.

---

## Goals

### Must Have
1. **Visual parity** with docs layout (same design tokens, motion, polish)
2. **Blog-tailored navigation** that aids content discovery (not docs-style hierarchy)
3. **Refined reading experience** optimized for long-form content consumption
4. **Mobile-first responsive** design with excellent touch targets

### Should Have
5. **Author-centric features** (richer profiles, attribution)
6. **Series/collection support** for multi-part content
7. **Archive browsing** that feels modern, not a boring list

### Nice to Have
8. **Comments integration** (placeholder for external systems)
9. **Newsletter integration** (configurable signup forms)
10. **Reading statistics** (estimated time, word count, progress)

### Non-Goals
- Replicating docs sidebar navigation (wrong pattern for blogs)
- Version selector (blogs don't have versions)
- API reference styling (not applicable)
- Three-column layout (too dense for blog reading)

---

## What Makes a Good Blog Layout?

### 1. Content-First Reading Experience

**The article is the hero.** Unlike docs where navigation aids task completion, blogs prioritize immersive reading:

```
┌─────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────┐  │
│  │                    Header Bar                     │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Hero / Featured Image                │  │
│  │         Title, Author, Date, Reading Time         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│           ┌───────────────────────────┐                 │
│           │                           │  ← Optimal     │
│           │      Article Content      │    reading     │
│           │        (65-75 chars)      │    width       │
│           │                           │                 │
│           └───────────────────────────┘                 │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │                Author Bio + Share                 │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Related / Next Posts                 │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Key principles**:
- Optimal line length (65-75 characters) for comfortable reading
- Generous whitespace around content
- Minimal distractions in the reading zone
- TOC is optional, sticky, and unobtrusive

### 2. Discovery-Optimized Home/List Pages

**Help readers find interesting content.** Blog homepages should showcase and curate:

```
┌─────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────┐  │
│  │              Hero / Brand Statement               │  │
│  │         (animated blob background)                │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Featured Post (large card, full-width)            ││
│  │  ┌─────────────────────────────────────────────┐   ││
│  │  │  Title, Excerpt, Tags, Date, Reading Time   │   ││
│  │  └─────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │
│  │  Recent #1    │ │  Recent #2    │ │  Recent #3    │  │
│  │  Post Card    │ │  Post Card    │ │  Post Card    │  │
│  └───────────────┘ └───────────────┘ └───────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │     Explore: Tags | Categories | Archive          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Key principles**:
- Featured/pinned content gets prominence
- Visual hierarchy guides attention (large → small)
- Multiple entry points (tags, categories, search)
- Pagination or infinite scroll for archives

### 3. Author as First-Class Citizen

**Blogs are personal.** Author identity matters more than in docs:

- Prominent author attribution on posts
- Rich author bio with photo, links, social
- Author archive pages with all their posts
- Multi-author support for team blogs

### 4. Temporal Content Organization

**Blogs are time-based.** Unlike docs (organized by topic), blogs organize by:

- Recency (latest posts first)
- Archives (by year/month)
- Series (multi-part content)
- Categories/Tags (topical grouping)

---

## Design Decisions

### Decision 1: Hero Section Treatment

**Options**:

A. **Blob background (recommended)**: Use existing `hero--blob-background` class for animated, polished hero sections on blog home and list pages.

B. **Featured image hero**: Large featured image with overlay text for posts that have cover images.

C. **Minimal hero**: Clean, typography-focused hero (current approach).

**Recommendation**: Option A for home/list pages, Option B for single posts with images, Option C fallback.

**Rationale**: Blob backgrounds provide visual parity with docs home without requiring users to add images. Featured images let authors customize when desired.

### Decision 2: Blog Navigation Pattern

**Options**:

A. **Contextual sidebar (not recommended)**: Docs-style left sidebar with categories/tags.
   - Cons: Too dense for reading, wrong mental model for blogs

B. **Inline exploration zones (recommended)**: Dedicated sections within content flow for discovery.
   - Explore bar below hero: Categories | Tags | Archive
   - Related posts at article end
   - Tag cloud in footer

C. **Floating action menu**: Compact floating button that reveals navigation.
   - Cons: Adds interaction cost, hides discoverability

**Recommendation**: Option B with optional contextual TOC for long posts.

**Rationale**: Blogs should feel spacious and reading-focused. Sidebars work for docs because users are hunting for specific info. Blog readers are browsing/exploring—inline exploration zones fit this better.

### Decision 3: Post Card Design

**Options**:

A. **Image-forward cards**: Large featured images, compact text below.
   - Good for image-heavy blogs

B. **Text-forward cards (recommended)**: Title/excerpt prominent, image optional thumbnail.
   - Works with or without images
   - Faster scanning

C. **Hybrid cards**: Large featured card for first post, text-forward for rest.

**Recommendation**: Option C (hybrid) with Option B as default.

**Rationale**: Featured posts deserve prominence. Most cards should prioritize scannable text since not all posts have great images.

### Decision 4: Typography and Fonts

**Options**:

A. **Inherit docs fonts**: Use same `fonts.yaml` configuration.
   - Pro: Consistency across site
   - Con: Blogs may want different personality

B. **Blog-specific fonts (recommended)**: Allow independent font configuration.
   - Pro: Blogs can have distinct voice
   - Con: Slightly more config

C. **System fonts only**: Fast, no configuration.
   - Con: Generic feel

**Recommendation**: Option B with docs fonts as sensible default.

**Rationale**: Blogs often have stronger brand identity than docs. Allow customization while defaulting to polished fonts.

### Decision 5: Reading Progress Indicator

**Options**:

A. **Top progress bar (recommended)**: Thin bar at top showing scroll progress.
   - Non-intrusive, familiar pattern

B. **Side progress indicator**: Vertical bar in margin.
   - More novel, can show TOC position

C. **None**: Keep it simple.

**Recommendation**: Option A, enabled via theme feature flag.

**Rationale**: Progress indicators increase engagement on long-form content. Top bar is least intrusive.

---

## Technical Approach

### Phase 1: Visual Polish (Estimated: 4-6 hours)

**1.1 Blob Background Support**

Add blob background variant to blog hero:

```html
<!-- blog/home.html -->
<header class="blog-home-hero hero--blob-background">
  <div class="hero__blobs">
    <div class="hero__blob hero__blob--1"></div>
    <div class="hero__blob hero__blob--2"></div>
    <div class="hero__blob hero__blob--3"></div>
    <div class="hero__blob hero__blob--4"></div>
  </div>
  <div class="blog-home-hero-content">
    <!-- existing content -->
  </div>
</header>
```

**Evidence**: `hero.css:294-362` has complete blob implementation.

**1.2 Typography Refinements**

Ensure blog uses semantic type tokens:

```css
/* blog.css additions */
.blog-post-content {
  font-family: var(--font-body);
  font-size: var(--text-body);
  line-height: var(--leading-relaxed);
  max-width: 70ch; /* Optimal reading width */
  margin-inline: auto;
}

.blog-post-header h1 {
  font-family: var(--font-heading);
  font-size: var(--text-4xl);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-tight);
}
```

**1.3 Card Polish**

Apply gradient borders and fluid backgrounds consistently:

```css
/* Already exists, ensure consistent application */
.blog-post-card.gradient-border.fluid-combined {
  /* Uses existing utility classes */
}
```

### Phase 2: Reading Experience (Estimated: 4-6 hours)

**2.1 Reading Progress Bar**

Add CSS for progress indicator:

```css
/* blog.css */
.reading-progress {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  width: 0%;
  background: linear-gradient(
    90deg,
    var(--color-primary),
    var(--color-secondary)
  );
  z-index: var(--z-sticky);
  transition: width 50ms linear;
  pointer-events: none;
}

/* Hide on short content */
.reading-progress[data-short="true"] {
  display: none;
}
```

Add to `interactive.js`:

```javascript
// Reading progress for blog posts
function initReadingProgress() {
  const article = document.querySelector('.blog-post-content');
  const progressBar = document.querySelector('.reading-progress');
  if (!article || !progressBar) return;

  // Only show for long content
  if (article.offsetHeight < window.innerHeight * 2) {
    progressBar.dataset.short = 'true';
    return;
  }

  window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    const articleTop = article.offsetTop;
    const articleHeight = article.offsetHeight;
    const viewportHeight = window.innerHeight;

    const progress = Math.min(1, Math.max(0,
      (scrolled - articleTop + viewportHeight * 0.5) / articleHeight
    ));

    progressBar.style.width = `${progress * 100}%`;
  }, { passive: true });
}
```

**2.2 Sticky TOC Refinement**

Improve TOC behavior on blog posts:

```css
/* blog.css */
.blog-sidebar {
  position: sticky;
  top: calc(var(--header-height) + var(--space-6));
  max-height: calc(100vh - var(--header-height) - var(--space-12));
  overflow-y: auto;
}

.blog-sidebar .toc {
  padding: var(--space-4);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
}
```

**2.3 Smooth Scroll to Anchors**

Ensure heading links scroll smoothly:

```css
html {
  scroll-behavior: smooth;
  scroll-padding-top: calc(var(--header-height) + var(--space-4));
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }
}
```

### Phase 3: Content Discovery (Estimated: 6-8 hours)

**3.1 Explore Bar Component**

New component for inline navigation:

```html
<!-- partials/blog-explore.html -->
<nav class="blog-explore" aria-label="Explore content">
  <div class="blog-explore-inner">
    {% if site.taxonomies.categories %}
    <div class="blog-explore-group">
      <span class="blog-explore-label">Categories</span>
      <div class="blog-explore-items">
        {% for cat in site.taxonomies.categories | limit(5) %}
        <a href="{{ cat.href }}" class="blog-explore-chip">{{ cat.name }}</a>
        {% endfor %}
        {% if site.taxonomies.categories | length > 5 %}
        <a href="/categories/" class="blog-explore-more">+{{ site.taxonomies.categories | length - 5 }} more</a>
        {% endif %}
      </div>
    </div>
    {% endif %}

    {% if site.taxonomies.tags %}
    <div class="blog-explore-group">
      <span class="blog-explore-label">Popular Tags</span>
      <div class="blog-explore-items">
        {{ tag_list(site.taxonomies.tags | sort_by('count', reverse=true) | limit(8)) }}
      </div>
    </div>
    {% endif %}

    <div class="blog-explore-group">
      <span class="blog-explore-label">Browse</span>
      <div class="blog-explore-items">
        <a href="/archive/" class="blog-explore-chip">📅 Archive</a>
        <a href="/authors/" class="blog-explore-chip">👤 Authors</a>
      </div>
    </div>
  </div>
</nav>
```

```css
/* blog.css */
.blog-explore {
  padding: var(--space-6) 0;
  border-block: 1px solid var(--color-border-subtle);
  margin-block: var(--space-8);
}

.blog-explore-inner {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-6);
  justify-content: center;
}

.blog-explore-group {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.blog-explore-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.blog-explore-items {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.blog-explore-chip {
  padding: var(--space-1) var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.blog-explore-chip:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
}
```

**3.2 Featured Post Card**

Large card for hero post:

```html
<!-- partials/blog-featured-card.html -->
<article class="blog-featured-hero gradient-border-strong fluid-bg">
  {% if post.metadata.get('image') %}
  <div class="blog-featured-hero-image">
    <img src="{{ post.metadata.get('image') }}" alt="{{ post.title }}" loading="lazy">
  </div>
  {% endif %}
  <div class="blog-featured-hero-content">
    <div class="blog-featured-hero-meta">
      {% if post.date %}
      <time datetime="{{ post.date | date_iso }}">{{ post.date | dateformat('%B %d, %Y') }}</time>
      {% endif %}
      <span class="reading-time">{{ icon('clock', size=14) }} {{ reading_time }} min read</span>
    </div>
    <h2 class="blog-featured-hero-title">
      <a href="{{ post.href }}">{{ post.title }}</a>
    </h2>
    {% if post.metadata.get('description') or post.excerpt %}
    <p class="blog-featured-hero-excerpt">
      {{ post.metadata.get('description') | default(post.excerpt) | truncate(200) }}
    </p>
    {% endif %}
    {% if post.tags %}
    <div class="blog-featured-hero-tags">
      {{ tag_list(post.tags | limit(4)) }}
    </div>
    {% endif %}
  </div>
</article>
```

**3.3 Related Posts with Contextual Graph (Optional)**

For blogs that want the graph visualization:

```html
<!-- blog/single.html addition -->
{% if site.features.graph and related %}
<div class="blog-related-graph">
  <div class="graph-contextual" data-page-url="{{ page.href }}">
    <div class="graph-contextual-container graph-loading" style="min-height: 180px;"></div>
  </div>
</div>
{% endif %}
```

### Phase 4: Author Experience (Estimated: 3-4 hours)

**4.1 Enhanced Author Card**

```html
<!-- partials/blog-author-card.html -->
<div class="blog-author-card">
  <div class="blog-author-card-header">
    {% if author.avatar %}
    <img src="{{ author.avatar }}" alt="{{ author.name }}" class="blog-author-avatar">
    {% else %}
    <div class="blog-author-avatar blog-author-avatar--placeholder">
      {{ author.name | first | upper }}
    </div>
    {% endif %}
    <div class="blog-author-info">
      <a href="{{ author.href }}" class="blog-author-name">{{ author.name }}</a>
      {% if author.title %}
      <span class="blog-author-title">{{ author.title }}</span>
      {% endif %}
    </div>
  </div>
  {% if author.bio %}
  <p class="blog-author-bio">{{ author.bio | truncate(150) }}</p>
  {% endif %}
  {% if author.links %}
  <div class="blog-author-links">
    {% for link in author.links %}
    <a href="{{ link.url }}" class="blog-author-link" target="_blank" rel="noopener">
      {{ icon(link.type | default('external'), size=16) }}
    </a>
    {% endfor %}
  </div>
  {% endif %}
</div>
```

**4.2 Author Page Template Enhancement**

```html
<!-- author/single.html -->
{% extends "base.html" %}

{% block content %}
<div class="author-page">
  <header class="author-page-header">
    <div class="author-page-profile">
      {% if author.avatar %}
      <img src="{{ author.avatar }}" alt="{{ author.name }}" class="author-page-avatar">
      {% endif %}
      <div class="author-page-info">
        <h1 class="author-page-name">{{ author.name }}</h1>
        {% if author.title %}
        <p class="author-page-title">{{ author.title }}</p>
        {% endif %}
        {% if author.links %}
        <div class="author-page-links">
          {% for link in author.links %}
          <a href="{{ link.url }}" target="_blank" rel="noopener" title="{{ link.text }}">
            {{ icon(link.type, size=20) }}
          </a>
          {% endfor %}
        </div>
        {% endif %}
      </div>
    </div>
    {% if author.bio %}
    <div class="author-page-bio prose">
      {{ author.bio | markdown | safe }}
    </div>
    {% endif %}
  </header>

  <section class="author-page-posts">
    <h2>Articles by {{ author.name }}</h2>
    <p class="author-page-count">{{ author.pages | length }} post{{ 's' if author.pages | length != 1 }}</p>
    <div class="blog-post-list">
      {% for post in author.pages | sort_by('date', reverse=true) %}
      {% include 'partials/blog-post-card.html' %}
      {% endfor %}
    </div>
  </section>
</div>
{% endblock %}
```

### Phase 5: Configuration & Polish (Estimated: 2-3 hours)

**5.1 Blog-Specific Feature Flags**

Add to theme.yaml options:

```yaml
# theme.yaml
theme:
  features:
    # Blog-specific
    - blog.reading_progress      # Show reading progress bar
    - blog.explore_bar           # Show category/tag exploration bar
    - blog.featured_posts        # Enable featured post highlighting
    - blog.author_cards          # Show author cards on posts
    - blog.related_graph         # Show contextual graph for related posts
```

**5.2 Update Example Site**

Ensure `example-sites/milos-blog` demonstrates all features:

```yaml
# milos-blog/config/_default/theme.yaml
theme:
  name: default
  default_appearance: dark
  default_palette: snow-lynx
  features:
    - navigation.breadcrumbs
    - navigation.toc
    - navigation.toc.sticky
    - navigation.prev_next
    - navigation.back_to_top
    - content.code.copy
    - content.lightbox
    - content.reading_time
    - content.author
    - content.excerpts
    - search.suggest
    - search.highlight
    - footer.social
    - accessibility.skip_link
    # Blog-specific
    - blog.reading_progress
    - blog.explore_bar
    - blog.featured_posts
    - blog.author_cards
```

---

## File Changes Summary

### New Files
| File | Purpose |
|------|---------|
| `templates/partials/blog-explore.html` | Inline exploration bar |
| `templates/partials/blog-author-card.html` | Reusable author card |
| `templates/partials/blog-featured-card.html` | Featured post hero card |

### Modified Files
| File | Changes |
|------|---------|
| `templates/blog/home.html` | Blob background, explore bar, featured post |
| `templates/blog/list.html` | Explore bar, better card layout |
| `templates/blog/single.html` | Reading progress, refined TOC, author card |
| `templates/author/single.html` | Complete redesign for richer profiles |
| `css/components/blog.css` | All new styles (~200-300 lines added) |
| `js/enhancements/interactive.js` | Reading progress indicator |

### Config Changes
| File | Changes |
|------|---------|
| `themes/default/theme.yaml` | Document blog feature flags |
| `example-sites/milos-blog/config/_default/theme.yaml` | Enable new features |

---

## Testing Strategy

### Visual Testing
- [ ] Blog home with blob background in light/dark modes
- [ ] Blog home with 0, 1, 3, 10 posts
- [ ] Blog list with pagination
- [ ] Single post with/without TOC
- [ ] Single post with/without featured image
- [ ] Single post with/without author
- [ ] Author page with 0, 1, many posts
- [ ] Mobile responsive (320px, 768px, 1024px breakpoints)

### Functional Testing
- [ ] Reading progress updates on scroll
- [ ] Reading progress hidden on short posts
- [ ] TOC sticky behavior
- [ ] Explore bar links work
- [ ] Gradient borders render correctly
- [ ] Blob animations respect reduced-motion

### Cross-Browser
- [ ] Chrome, Firefox, Safari (latest)
- [ ] Mobile Safari, Chrome Android

---

## Migration Path

**For existing blog sites**: All changes are additive. Existing blogs get improvements automatically. Feature flags allow opting out of specific enhancements.

**Breaking changes**: None expected.

---

## Open Questions

1. **Should we support a "magazine" layout variant?** (Multiple columns of cards, more visual)

2. **Should explore bar be in header on mobile?** (Currently inline, could move to hamburger)

3. **Should we add "series" as a first-class content type?** (Multi-part posts linked together)

4. **Should author data come from `data/authors.yaml` or individual files?** (Currently supports both via collections)

---

## Success Criteria

- [ ] milos-blog visually indistinguishable in polish from site/ docs
- [ ] Reading experience optimized for long-form content
- [ ] Content discovery intuitive without sidebar
- [ ] Author identity prominent without being intrusive
- [ ] Mobile experience excellent
- [ ] Performance: No layout shift, fast paint

---

## Estimated Effort

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 1 | Visual Polish | 4-6 hours |
| Phase 2 | Reading Experience | 4-6 hours |
| Phase 3 | Content Discovery | 6-8 hours |
| Phase 4 | Author Experience | 3-4 hours |
| Phase 5 | Config & Polish | 2-3 hours |
| **Total** | | **19-27 hours** |

---

## Appendix: Design Inspiration

**Reading Experience**:
- Medium.com: Clean reading, progress indicator, author focus
- Substack: Newsletter-style, author-centric
- Ghost: Modern, typography-focused

**Content Discovery**:
- CSS-Tricks: Inline exploration, featured content
- Smashing Magazine: Rich cards, categorization
- A List Apart: Clean hierarchy, archive browsing

**Visual Polish**:
- Vercel Blog: Minimal, high-quality imagery
- Linear Changelog: Animated touches, dark mode excellence
- Stripe Blog: Typography-forward, refined spacing
