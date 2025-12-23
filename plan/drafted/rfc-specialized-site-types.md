# RFC: Specialized Site Types & Theme Extensibility

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-23  
**Subsystems**: content_types, themes/default/templates, core, config

---

## Executive Summary

Create an **extensible content type ecosystem** where Bengal provides built-in strategies for common site types, themes declare which types they support, and themers can create custom types for specialized use cases.

**Built-in Strategies (Bengal Core)**:
- `PortfolioStrategy` - Project showcase with featured projects, technology tags
- `ProductStrategy` - Product catalog with pricing, JSON-LD structured data
- `LandingStrategy` - Marketing pages with hero, features, testimonials, pricing
- `WikiStrategy` - Interconnected knowledge base with backlinks, categories
- `RecipeStrategy` - Cookbook with structured data, cook times, ingredients

**Theme Contract**:
- Themes declare supported content types in `theme.yaml`
- Graceful fallback when theme doesn't support a type
- Clear documentation for themers on what data is available

**Extensibility**:
- Themers can create custom strategies via `register_strategy()`
- Custom types work identically to built-in types
- No Bengal core changes needed for custom types

---

## Problem Statement

### Gap 1: Missing Strategies for Common Site Types

Bengal has CLI scaffolding templates but no content strategies for specialized sites:

| Site Type | CLI Scaffold | Content Strategy | Theme Templates | Gap |
|-----------|--------------|------------------|-----------------|-----|
| Portfolio | ✅ `--template portfolio` | ❌ Missing | ❌ Missing | No sorting, no templates |
| Product | ✅ `--template product` | ❌ Missing | ⚠️ JSON-LD only | No catalog logic |
| Resume | ❌ None | ❌ Missing | ✅ Exists | Templates orphaned |
| Landing | ❌ None | ❌ Missing | ❌ Missing | No support |
| Wiki | ❌ None | ❌ Missing | ❌ Missing | No support |
| Recipe | ❌ None | ❌ Missing | ❌ Missing | No support |

### Gap 2: No Theme Contract for Content Types

Themes can't declare what types they support:
- No way to know if a theme has `portfolio/list.html`
- No graceful degradation when templates are missing
- Users get silent fallback to generic templates

### Gap 3: Custom Type Creation Undocumented

`register_strategy()` exists but:
- No documentation for themers
- No examples of theme-specific types
- No guidance on when to create custom types

---

## Goals

### Must Have
1. **Content strategies** for portfolio, product, landing, wiki, recipe
2. **Theme contract** - themes declare supported types in `theme.yaml`
3. **Graceful fallback** with warnings when theme doesn't support a type
4. **Documentation** for creating custom content types

### Should Have
5. **JSON-LD structured data** for SEO (Product, Recipe, Person)
6. **Data file support** (e.g., `data/products.yaml`, `data/recipes.yaml`)
7. **Template conveniences** specific to each type

### Nice to Have
8. **CLI scaffolds** for new types (`bengal new site --template wiki`)
9. **Variant support** within types
10. **Print styles** for resume and recipes

### Non-Goals
- Shopping cart or checkout (static site limitation)
- User accounts or authentication
- Real-time wiki editing
- Dynamic inventory management

---

## Architecture: The Themer Mental Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Bengal Content Type Registry                       │
│                                                                          │
│   Built-in (Core):   blog, doc, tutorial, changelog, track, page        │
│   Built-in (New):    portfolio, product, landing, wiki, recipe          │
│   Custom (Themer):   event, faq, testimonial, team-member, etc.         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Theme Examples                                 │
├──────────────┬────────────────┬─────────────────┬───────────────────────┤
│ minimal-blog │ developer-folio│ recipe-starter  │ default (Bengal)      │
├──────────────┼────────────────┼─────────────────┼───────────────────────┤
│ ✅ blog      │ ✅ portfolio   │ ✅ recipe       │ ✅ blog               │
│ ✅ page      │ ✅ blog        │ ✅ blog         │ ✅ doc                │
│              │ ✅ resume      │ ✅ page         │ ✅ tutorial           │
│              │ ✅ page        │                 │ ✅ changelog          │
│              │                │                 │ ✅ portfolio          │
│              │                │                 │ ✅ landing            │
│              │                │                 │ ✅ wiki               │
│              │                │                 │ ✅ recipe             │
│              │                │                 │ ✅ product            │
│              │                │                 │ ✅ resume             │
│              │                │                 │ ✅ autodoc-*          │
└──────────────┴────────────────┴─────────────────┴───────────────────────┘
```

**Key Insight**: Themes specialize. A food blogger doesn't need `autodoc-python`. A developer portfolio doesn't need `recipe`. The default Bengal theme supports everything, but specialized themes focus on their niche.

---

## Theme Contract

### Theme Type Declaration

Themes declare supported content types in `theme.yaml`:

```yaml
# themes/minimal-blog/theme.yaml
name: minimal-blog
version: 1.0.0

# Declare what content types this theme supports
content_types:
  supported:
    - blog
    - page
  # Optional: declare partial support
  partial:
    - doc  # Has templates but not sidebar

# Or for a full-featured theme:
# themes/default/theme.yaml
content_types:
  supported:
    - blog
    - doc
    - tutorial
    - changelog
    - track
    - portfolio
    - product
    - landing
    - wiki
    - recipe
    - resume
    - autodoc-python
    - autodoc-cli
```

### Graceful Fallback Behavior

When a user sets `type: portfolio` but theme doesn't support it:

```
1. PortfolioStrategy handles sorting ✅ (featured first, etc.)
2. Template lookup: portfolio/list.html → NOT FOUND
3. Fallback chain: list.html → index.html ✅
4. Warning logged:
   ⚠️ Theme 'minimal-blog' doesn't have templates for 'portfolio'
   Using fallback template. Consider:
   - Switching to a theme that supports portfolio
   - Creating templates/portfolio/list.html in your site
```

### Template Lookup Order

For `type: portfolio`, list page:
```
1. themes/{theme}/templates/portfolio/list.html  (type-specific)
2. site/templates/portfolio/list.html            (site override)
3. themes/{theme}/templates/list.html            (generic list)
4. themes/{theme}/templates/index.html           (ultimate fallback)
```

### Theme Validation (Optional)

`bengal health` can warn about missing templates:

```
$ bengal health --check-theme

Theme Compatibility Report: minimal-blog
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Content types in use:
  ✅ blog      - Full support (home, list, single)
  ✅ page      - Full support
  ⚠️ portfolio - No templates (using fallback)

Recommendation: Create templates/portfolio/ or switch theme
```

---

## Custom Strategy Guide (For Themers)

### Creating a Custom Content Type

Themers can create custom strategies for specialized use cases:

```python
# In your theme's __init__.py or a plugin

from bengal.content_types import ContentTypeStrategy, register_strategy

class EventStrategy(ContentTypeStrategy):
    """
    Custom strategy for event/conference sites.

    Sorts by event date (upcoming first, past events last).
    """
    default_template = "event/list.html"
    allows_pagination = True

    def sort_pages(self, pages):
        from datetime import datetime
        now = datetime.now()

        def sort_key(p):
            event_date = p.metadata.get("event_date")
            if not event_date:
                return (2, datetime.min)  # No date = sort last

            is_past = event_date < now
            return (1 if is_past else 0, event_date)

        return sorted(pages, key=sort_key)

    def detect_from_section(self, section):
        return section.name.lower() in ("events", "conferences", "meetups")

# Register during theme initialization
register_strategy("event", EventStrategy())
```

### When to Create Custom Types

| Scenario | Recommendation |
|----------|----------------|
| Different sorting logic | ✅ Create custom strategy |
| Different template | ❌ Use `layout:` frontmatter |
| Different URL pattern | ✅ Create custom strategy |
| Domain-specific metadata | ✅ Create custom strategy |
| Just visual differences | ❌ Use `variant:` frontmatter |

### Custom Type Checklist

- [ ] Strategy class extends `ContentTypeStrategy`
- [ ] `default_template` points to your templates
- [ ] `sort_pages()` implements your sorting logic
- [ ] `detect_from_section()` enables auto-detection
- [ ] Templates exist in `templates/{type}/`
- [ ] Type registered via `register_strategy()`
- [ ] Type declared in `theme.yaml` `content_types.supported`

---

## Detailed Design

### 1. Portfolio Support

#### 1.1 PortfolioStrategy

```python
# bengal/content_types/strategies.py

class PortfolioStrategy(ContentTypeStrategy):
    """
    Strategy for portfolio/project showcase content.

    Optimized for visual project displays where featured items get
    prominence and projects can be filtered by technology/category.

    Auto-Detection:
        Detected when section name matches portfolio patterns
        (``portfolio``, ``projects``, ``work``, ``showcase``).

    Sorting:
        1. Featured projects first (frontmatter: ``featured: true``)
        2. Then by date (newest first)
        3. Then by weight (for manual ordering)

    Templates:
        - List: ``portfolio/list.html`` (grid with filtering)
        - Single: ``portfolio/single.html`` (project detail)

    Frontmatter Support:
        - ``featured``: Boolean, shows in hero section
        - ``image``: Cover image for grid card
        - ``technologies``: List of tech tags for filtering
        - ``demo_url``: Link to live demo
        - ``github_url``: Link to source code
        - ``client``: Client name (for freelance work)
        - ``role``: Your role in the project
        - ``duration``: Project duration

    Class Attributes:
        default_template: ``"portfolio/list.html"``
        allows_pagination: ``True``
    """

    default_template = "portfolio/list.html"
    allows_pagination = True

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort projects: featured first, then by date, then by weight.
        """
        from datetime import datetime

        def sort_key(p: Page):
            is_featured = p.metadata.get("featured", False)
            date = p.date if p.date else datetime.min
            weight = p.metadata.get("weight", 999999)
            return (not is_featured, date, weight)

        return sorted(pages, key=sort_key, reverse=True)

    def detect_from_section(self, section: Section) -> bool:
        """Detect portfolio sections by common naming patterns."""
        name = section.name.lower()
        return name in ("portfolio", "projects", "work", "showcase", "gallery")

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Portfolio-specific template selection."""
        if page is None:
            return self.default_template

        is_section_index = page.source_path.stem == "_index"

        if is_section_index:
            return "portfolio/list.html"
        else:
            return "portfolio/single.html"
```

#### 1.2 Portfolio Templates

**`portfolio/list.html`** - Grid layout with filtering:

```html
{% extends "base.html" %}

{% block content %}
<div class="portfolio-container">
    {# Hero Section #}
    <header class="portfolio-header hero--blob-background">
        <div class="hero__blobs" aria-hidden="true">
            <div class="hero__blob hero__blob--1"></div>
            <div class="hero__blob hero__blob--2"></div>
        </div>
        <div class="portfolio-header-content">
            <h1 class="portfolio-title">{{ section.title | default('Portfolio') }}</h1>
            {% if section.description %}
            <p class="portfolio-lead">{{ section.description }}</p>
            {% endif %}
        </div>
    </header>

    {# Technology Filter #}
    {% set all_technologies = posts | map(attribute='metadata.technologies') | flatten | unique | sort %}
    {% if all_technologies %}
    <nav class="portfolio-filters" aria-label="Filter projects">
        <button class="portfolio-filter-btn active" data-filter="all">All</button>
        {% for tech in all_technologies | limit(10) %}
        <button class="portfolio-filter-btn" data-filter="{{ tech | slugify }}">{{ tech }}</button>
        {% endfor %}
    </nav>
    {% endif %}

    {# Featured Projects #}
    {% set featured = posts | where('featured', true) %}
    {% if featured %}
    <section class="portfolio-featured">
        <h2 class="portfolio-section-title">Featured Work</h2>
        <div class="portfolio-grid portfolio-grid--featured">
            {% for project in featured %}
            {% include 'partials/portfolio-card.html' with context %}
            {% endfor %}
        </div>
    </section>
    {% endif %}

    {# All Projects Grid #}
    {% set regular = posts | where_not('featured', true) %}
    <section class="portfolio-all">
        {% if featured %}<h2 class="portfolio-section-title">All Projects</h2>{% endif %}
        <div class="portfolio-grid">
            {% for project in regular %}
            {% include 'partials/portfolio-card.html' with context %}
            {% endfor %}
        </div>
    </section>

    {# Pagination #}
    {% if total_pages and total_pages > 1 %}
    {{ pagination(current_page, total_pages, base_url) }}
    {% endif %}
</div>
{% endblock %}
```

**`partials/portfolio-card.html`** - Reusable project card:

```html
<article class="portfolio-card gradient-border fluid-combined"
         data-technologies="{{ (project.metadata.get('technologies', []) | map('slugify') | join(' ')) }}">
    {# Cover Image #}
    {% if project.metadata.get('image') %}
    <div class="portfolio-card-image">
        <img src="{{ project.metadata.get('image') }}"
             alt="{{ project.title }}"
             loading="lazy">
        {% if project.metadata.get('featured') %}
        <span class="portfolio-badge portfolio-badge--featured">Featured</span>
        {% endif %}
    </div>
    {% endif %}

    {# Card Content #}
    <div class="portfolio-card-content">
        <h3 class="portfolio-card-title">
            <a href="{{ project.href }}">{{ project.title }}</a>
        </h3>

        {% if project.metadata.get('client') %}
        <p class="portfolio-card-client">{{ project.metadata.get('client') }}</p>
        {% endif %}

        {% if project.description or project.excerpt %}
        <p class="portfolio-card-excerpt">
            {{ project.description | default(project.excerpt) | truncate(120) }}
        </p>
        {% endif %}

        {# Technologies #}
        {% if project.metadata.get('technologies') %}
        <div class="portfolio-card-tech">
            {% for tech in project.metadata.get('technologies') | limit(4) %}
            <span class="tech-tag">{{ tech }}</span>
            {% endfor %}
            {% if project.metadata.get('technologies') | length > 4 %}
            <span class="tech-tag tech-tag--more">+{{ project.metadata.get('technologies') | length - 4 }}</span>
            {% endif %}
        </div>
        {% endif %}

        {# Links #}
        <div class="portfolio-card-links">
            <a href="{{ project.href }}" class="portfolio-link portfolio-link--primary">
                View Details {{ icon('arrow-right', size=14) }}
            </a>
            {% if project.metadata.get('demo_url') %}
            <a href="{{ project.metadata.get('demo_url') }}" class="portfolio-link" target="_blank" rel="noopener">
                {{ icon('external', size=14) }} Demo
            </a>
            {% endif %}
            {% if project.metadata.get('github_url') %}
            <a href="{{ project.metadata.get('github_url') }}" class="portfolio-link" target="_blank" rel="noopener">
                {{ icon('github-logo', size=14) }} Code
            </a>
            {% endif %}
        </div>
    </div>
</article>
```

**`portfolio/single.html`** - Project detail page:

```html
{% extends "base.html" %}
{% from 'partials/navigation-components.html' import breadcrumbs, page_navigation %}

{% block content %}
<article class="portfolio-single">
    {% include 'partials/action-bar.html' %}

    {# Project Header #}
    <header class="portfolio-single-header">
        {% if page.metadata.get('image') %}
        <div class="portfolio-hero-image">
            <img src="{{ page.metadata.get('image') }}" alt="{{ page.title }}">
        </div>
        {% endif %}

        <div class="portfolio-hero-content">
            <h1>{{ page.title }}</h1>

            {% if page.description %}
            <p class="portfolio-lead">{{ page.description }}</p>
            {% endif %}

            {# Project Meta #}
            <div class="portfolio-meta">
                {% if page.metadata.get('client') %}
                <div class="portfolio-meta-item">
                    <span class="portfolio-meta-label">Client</span>
                    <span class="portfolio-meta-value">{{ page.metadata.get('client') }}</span>
                </div>
                {% endif %}
                {% if page.metadata.get('role') %}
                <div class="portfolio-meta-item">
                    <span class="portfolio-meta-label">Role</span>
                    <span class="portfolio-meta-value">{{ page.metadata.get('role') }}</span>
                </div>
                {% endif %}
                {% if page.metadata.get('duration') %}
                <div class="portfolio-meta-item">
                    <span class="portfolio-meta-label">Duration</span>
                    <span class="portfolio-meta-value">{{ page.metadata.get('duration') }}</span>
                </div>
                {% endif %}
                {% if page.date %}
                <div class="portfolio-meta-item">
                    <span class="portfolio-meta-label">Completed</span>
                    <span class="portfolio-meta-value">{{ page.date | dateformat('%B %Y') }}</span>
                </div>
                {% endif %}
            </div>

            {# Technologies #}
            {% if page.metadata.get('technologies') %}
            <div class="portfolio-technologies">
                <span class="portfolio-meta-label">Technologies</span>
                <div class="portfolio-tech-list">
                    {% for tech in page.metadata.get('technologies') %}
                    <span class="tech-tag">{{ tech }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {# Action Buttons #}
            <div class="portfolio-actions">
                {% if page.metadata.get('demo_url') %}
                <a href="{{ page.metadata.get('demo_url') }}" class="btn btn-primary" target="_blank" rel="noopener">
                    {{ icon('external', size=16) }} View Live Demo
                </a>
                {% endif %}
                {% if page.metadata.get('github_url') %}
                <a href="{{ page.metadata.get('github_url') }}" class="btn btn-outline" target="_blank" rel="noopener">
                    {{ icon('github-logo', size=16) }} View Source
                </a>
                {% endif %}
            </div>
        </div>
    </header>

    {# Project Content #}
    <div class="portfolio-content prose">
        {{ content | safe }}
    </div>

    {# Image Gallery #}
    {% if page.metadata.get('gallery') %}
    <section class="portfolio-gallery">
        <h2>Gallery</h2>
        <div class="portfolio-gallery-grid">
            {% for image in page.metadata.get('gallery') %}
            <figure class="portfolio-gallery-item">
                <img src="{{ image.src }}" alt="{{ image.alt | default(page.title) }}" loading="lazy">
                {% if image.caption %}
                <figcaption>{{ image.caption }}</figcaption>
                {% endif %}
            </figure>
            {% endfor %}
        </div>
    </section>
    {% endif %}

    {# Project Navigation #}
    {{ page_navigation(page) }}
</article>

{# Related Projects #}
{% set related = page.related_posts[:3] %}
{% if related %}
<aside class="portfolio-related">
    <div class="container">
        <h2>Related Projects</h2>
        <div class="portfolio-grid">
            {% for project in related %}
            {% include 'partials/portfolio-card.html' %}
            {% endfor %}
        </div>
    </div>
</aside>
{% endif %}
{% endblock %}
```

---

### 2. Product/E-commerce Support

#### 2.1 ProductStrategy

```python
# bengal/content_types/strategies.py

class ProductStrategy(ContentTypeStrategy):
    """
    Strategy for product catalog/e-commerce content.

    Optimized for product listings with pricing, inventory status,
    and structured data for SEO. Suitable for static product catalogs,
    SaaS feature pages, or simple e-commerce sites.

    Auto-Detection:
        Detected when section name matches product patterns
        (``products``, ``shop``, ``store``, ``catalog``).

    Sorting:
        1. Featured products first
        2. In-stock before out-of-stock
        3. Then by weight (for manual ordering)
        4. Then by title alphabetically

    Templates:
        - List: ``product/list.html`` (grid with category filter)
        - Single: ``product/single.html`` (product detail with JSON-LD)

    Frontmatter Support:
        - ``price``: Product price (number)
        - ``sale_price``: Discounted price (optional)
        - ``currency``: Currency code (default: USD)
        - ``sku``: Stock keeping unit
        - ``in_stock``: Boolean availability
        - ``featured``: Show in featured section
        - ``images``: List of product images
        - ``features``: List of product features
        - ``category``: Product category
        - ``brand``: Brand name
        - ``structured_data``: Enable JSON-LD (default: true)

    Class Attributes:
        default_template: ``"product/list.html"``
        allows_pagination: ``True``
    """

    default_template = "product/list.html"
    allows_pagination = True

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort products: featured first, in-stock first, then weight, then title.
        """
        def sort_key(p: Page):
            is_featured = p.metadata.get("featured", False)
            is_in_stock = p.metadata.get("in_stock", True)
            weight = p.metadata.get("weight", 999999)
            title = p.title.lower()
            return (not is_featured, not is_in_stock, weight, title)

        return sorted(pages, key=sort_key)

    def detect_from_section(self, section: Section) -> bool:
        """Detect product sections by common naming patterns."""
        name = section.name.lower()
        return name in ("products", "shop", "store", "catalog", "pricing")

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Product-specific template selection."""
        if page is None:
            return self.default_template

        is_section_index = page.source_path.stem == "_index"

        if is_section_index:
            return "product/list.html"
        else:
            return "product/single.html"
```

#### 2.2 Product Templates

**`product/list.html`** - Product catalog grid:

```html
{% extends "base.html" %}

{% block content %}
<div class="product-container">
    {# Hero #}
    <header class="product-header hero--blob-background">
        <div class="hero__blobs" aria-hidden="true">
            <div class="hero__blob hero__blob--1"></div>
            <div class="hero__blob hero__blob--2"></div>
        </div>
        <div class="product-header-content">
            <h1>{{ section.title | default('Products') }}</h1>
            {% if section.description %}
            <p class="product-lead">{{ section.description }}</p>
            {% endif %}
        </div>
    </header>

    {# Category Filter #}
    {% set categories = posts | map(attribute='metadata.category') | unique | reject('none') | sort %}
    {% if categories | list %}
    <nav class="product-filters" aria-label="Filter products">
        <button class="product-filter-btn active" data-filter="all">All</button>
        {% for category in categories %}
        <button class="product-filter-btn" data-filter="{{ category | slugify }}">{{ category }}</button>
        {% endfor %}
    </nav>
    {% endif %}

    {# Featured Products #}
    {% set featured = posts | where('featured', true) %}
    {% if featured %}
    <section class="product-featured">
        <h2 class="product-section-title">Featured Products</h2>
        <div class="product-grid product-grid--featured">
            {% for product in featured %}
            {% include 'partials/product-card.html' with context %}
            {% endfor %}
        </div>
    </section>
    {% endif %}

    {# All Products #}
    {% set regular = posts | where_not('featured', true) %}
    <section class="product-all">
        {% if featured %}<h2 class="product-section-title">All Products</h2>{% endif %}
        <div class="product-grid">
            {% for product in regular %}
            {% include 'partials/product-card.html' with context %}
            {% endfor %}
        </div>
    </section>

    {# Pagination #}
    {% if total_pages and total_pages > 1 %}
    {{ pagination(current_page, total_pages, base_url) }}
    {% endif %}
</div>
{% endblock %}
```

**`partials/product-card.html`** - Product card component:

```html
<article class="product-card gradient-border fluid-combined"
         data-category="{{ product.metadata.get('category', '') | slugify }}">
    {# Product Image #}
    {% set images = product.metadata.get('images', []) %}
    {% set primary_image = images[0] if images else product.metadata.get('image') %}
    {% if primary_image %}
    <div class="product-card-image">
        <a href="{{ product.href }}">
            <img src="{{ primary_image }}" alt="{{ product.title }}" loading="lazy">
        </a>
        {# Badges #}
        <div class="product-badges">
            {% if product.metadata.get('featured') %}
            <span class="product-badge product-badge--featured">Featured</span>
            {% endif %}
            {% if product.metadata.get('sale_price') %}
            <span class="product-badge product-badge--sale">Sale</span>
            {% endif %}
            {% if not product.metadata.get('in_stock', true) %}
            <span class="product-badge product-badge--out">Out of Stock</span>
            {% endif %}
        </div>
    </div>
    {% endif %}

    {# Card Content #}
    <div class="product-card-content">
        {% if product.metadata.get('brand') %}
        <p class="product-card-brand">{{ product.metadata.get('brand') }}</p>
        {% endif %}

        <h3 class="product-card-title">
            <a href="{{ product.href }}">{{ product.title }}</a>
        </h3>

        {% if product.description or product.excerpt %}
        <p class="product-card-excerpt">
            {{ product.description | default(product.excerpt) | truncate(80) }}
        </p>
        {% endif %}

        {# Pricing #}
        <div class="product-card-pricing">
            {% set currency = product.metadata.get('currency', 'USD') %}
            {% set price = product.metadata.get('price') %}
            {% set sale_price = product.metadata.get('sale_price') %}

            {% if sale_price %}
            <span class="product-price product-price--sale">
                {{ format_price(sale_price, currency) }}
            </span>
            <span class="product-price product-price--original">
                {{ format_price(price, currency) }}
            </span>
            {% elif price %}
            <span class="product-price">{{ format_price(price, currency) }}</span>
            {% endif %}
        </div>

        {# CTA #}
        <a href="{{ product.href }}" class="product-card-cta">
            View Details {{ icon('arrow-right', size=14) }}
        </a>
    </div>
</article>
```

**`product/single.html`** - Product detail page:

```html
{% extends "base.html" %}
{% from 'partials/navigation-components.html' import breadcrumbs %}

{% block head_extra %}
{# JSON-LD Structured Data #}
{% include 'partials/product-jsonld.html' %}
{% endblock %}

{% block content %}
<article class="product-single">
    {{ breadcrumbs(page) }}

    <div class="product-single-layout">
        {# Product Gallery #}
        <div class="product-gallery">
            {% set images = page.metadata.get('images', []) %}
            {% set primary_image = images[0] if images else page.metadata.get('image') %}

            {% if primary_image %}
            <div class="product-gallery-main">
                <img src="{{ primary_image }}" alt="{{ page.title }}" id="product-main-image">
            </div>
            {% endif %}

            {% if images | length > 1 %}
            <div class="product-gallery-thumbs">
                {% for img in images %}
                <button class="product-thumb {% if loop.first %}active{% endif %}"
                        data-image="{{ img }}">
                    <img src="{{ img }}" alt="{{ page.title }} - Image {{ loop.index }}">
                </button>
                {% endfor %}
            </div>
            {% endif %}
        </div>

        {# Product Info #}
        <div class="product-info">
            {% if page.metadata.get('brand') %}
            <p class="product-brand">{{ page.metadata.get('brand') }}</p>
            {% endif %}

            <h1 class="product-title">{{ page.title }}</h1>

            {% if page.description %}
            <p class="product-description">{{ page.description }}</p>
            {% endif %}

            {# Pricing #}
            <div class="product-pricing">
                {% set currency = page.metadata.get('currency', 'USD') %}
                {% set price = page.metadata.get('price') %}
                {% set sale_price = page.metadata.get('sale_price') %}

                {% if sale_price %}
                <div class="product-price-group">
                    <span class="product-price product-price--current">
                        {{ format_price(sale_price, currency) }}
                    </span>
                    <span class="product-price product-price--was">
                        {{ format_price(price, currency) }}
                    </span>
                    {% set savings = ((price - sale_price) / price * 100) | round %}
                    <span class="product-savings">Save {{ savings }}%</span>
                </div>
                {% elif price %}
                <span class="product-price">{{ format_price(price, currency) }}</span>
                {% endif %}
            </div>

            {# Availability #}
            <div class="product-availability">
                {% if page.metadata.get('in_stock', true) %}
                <span class="availability availability--in-stock">
                    {{ icon('check-circle', size=16) }} In Stock
                </span>
                {% else %}
                <span class="availability availability--out">
                    {{ icon('x', size=16) }} Out of Stock
                </span>
                {% endif %}
                {% if page.metadata.get('sku') %}
                <span class="product-sku">SKU: {{ page.metadata.get('sku') }}</span>
                {% endif %}
            </div>

            {# Features List #}
            {% if page.metadata.get('features') %}
            <div class="product-features">
                <h3>Features</h3>
                <ul class="product-features-list">
                    {% for feature in page.metadata.get('features') %}
                    <li>{{ icon('check', size=14) }} {{ feature }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}

            {# CTA Buttons #}
            <div class="product-actions">
                {% if page.metadata.get('buy_url') %}
                <a href="{{ page.metadata.get('buy_url') }}" class="btn btn-primary btn-lg">
                    {{ icon('cart', size=18) }} Buy Now
                </a>
                {% endif %}
                {% if page.metadata.get('demo_url') %}
                <a href="{{ page.metadata.get('demo_url') }}" class="btn btn-outline btn-lg">
                    {{ icon('external', size=18) }} Try Demo
                </a>
                {% endif %}
            </div>
        </div>
    </div>

    {# Product Details/Content #}
    {% if content and content.strip() %}
    <div class="product-details prose">
        {{ content | safe }}
    </div>
    {% endif %}
</article>

{# Related Products #}
{% set related = page.related_posts[:4] %}
{% if related %}
<section class="product-related">
    <div class="container">
        <h2>Related Products</h2>
        <div class="product-grid">
            {% for product in related %}
            {% include 'partials/product-card.html' %}
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}
{% endblock %}
```

#### 2.3 Template Function: format_price

```python
# bengal/rendering/template_functions/pricing.py

def format_price(price: float | int, currency: str = "USD") -> str:
    """
    Format a price with currency symbol.

    Args:
        price: Numeric price value
        currency: ISO 4217 currency code

    Returns:
        Formatted price string

    Example:
        {{ format_price(99.99, 'USD') }}  → $99.99
        {{ format_price(79, 'EUR') }}     → €79.00
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CAD": "CA$",
        "AUD": "A$",
    }
    symbol = symbols.get(currency, currency + " ")

    # Format with 2 decimal places, no decimals for JPY
    if currency == "JPY":
        return f"{symbol}{int(price):,}"
    else:
        return f"{symbol}{price:,.2f}"
```

---

### 3. Resume Support

#### 3.1 ResumeStrategy

```python
# bengal/content_types/strategies.py

class ResumeStrategy(ContentTypeStrategy):
    """
    Strategy for resume/CV content.

    Optimized for professional profile pages with structured sections
    for experience, education, skills, and projects. Supports both
    data-driven (YAML) and markdown-based resumes.

    Auto-Detection:
        Detected when section name matches resume patterns
        (``resume``, ``cv``, ``about-me``) or when pages have
        resume-specific metadata (``experience``, ``education``).

    Data Sources:
        1. ``data/resume.yaml`` - Structured resume data
        2. Page frontmatter - Individual section overrides
        3. Page content - Additional narrative content

    Templates:
        - List: ``resume/list.html`` (for multiple team members)
        - Single: ``resume/single.html`` (individual resume)

    Frontmatter Support:
        - ``name``: Full name
        - ``headline``: Professional title/tagline
        - ``contact``: Email, phone, location, website, social links
        - ``summary``: Professional summary
        - ``experience``: List of work experiences
        - ``education``: List of education entries
        - ``skills``: Categorized skills
        - ``projects``: Notable projects
        - ``certifications``: Professional certifications
        - ``awards``: Awards and recognition
        - ``languages``: Language proficiencies
        - ``volunteer``: Volunteer experience

    Class Attributes:
        default_template: ``"resume/single.html"``
        allows_pagination: ``False``
    """

    default_template = "resume/single.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Sort resume pages by weight, then name."""
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def detect_from_section(self, section: Section) -> bool:
        """Detect resume sections by name or page metadata."""
        name = section.name.lower()
        if name in ("resume", "cv", "about-me", "team"):
            return True

        # Check page metadata for resume-specific fields
        if section.pages:
            for page in section.pages[:3]:
                if page.metadata.get("experience") or page.metadata.get("education"):
                    return True

        return False

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Resume-specific template selection."""
        if page is None:
            return self.default_template

        is_section_index = page.source_path.stem == "_index"

        if is_section_index:
            return "resume/list.html"
        else:
            return "resume/single.html"
```

#### 3.2 Resume Template Enhancements

The existing `resume/single.html` is comprehensive. Key improvements:

1. **Add print styles** (CSS media query)
2. **Add JSON-LD Person schema**
3. **Add variant support** (`variant: timeline` vs `variant: classic`)
4. **Add download PDF button** (via browser print)

**`partials/resume-jsonld.html`**:

```html
{%- set resume = site.data.get('resume') if site.data is defined and site.data else page.metadata %}
{%- if resume %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": {{ resume.get('name', page.title) | tojson }},
  {%- if resume.get('headline') %}
  "jobTitle": {{ resume.get('headline') | tojson }},
  {%- endif %}
  {%- if resume.get('contact', {}).get('email') %}
  "email": {{ resume.get('contact', {}).get('email') | tojson }},
  {%- endif %}
  {%- if resume.get('contact', {}).get('website') %}
  "url": {{ resume.get('contact', {}).get('website') | tojson }},
  {%- endif %}
  {%- if resume.get('contact', {}).get('location') %}
  "address": {
    "@type": "PostalAddress",
    "addressLocality": {{ resume.get('contact', {}).get('location') | tojson }}
  },
  {%- endif %}
  "sameAs": [
    {%- set social_links = [] %}
    {%- if resume.get('contact', {}).get('linkedin') %}{% set _ = social_links.append(resume.get('contact', {}).get('linkedin')) %}{% endif %}
    {%- if resume.get('contact', {}).get('github') %}{% set _ = social_links.append(resume.get('contact', {}).get('github')) %}{% endif %}
    {{ social_links | tojson }}
  ]
}
</script>
{%- endif %}
```

---

### 4. Landing Page Support

#### 4.1 LandingStrategy

```python
# bengal/content_types/strategies.py

class LandingStrategy(ContentTypeStrategy):
    """
    Strategy for marketing/landing page content.

    Optimized for single-page marketing sites with hero sections,
    feature grids, testimonials, and CTAs. Uses section-based
    content organization within a single page.

    Auto-Detection:
        Detected when page has ``type: landing`` or section name
        is ``landing`` or when pages have landing-specific metadata
        (``hero``, ``sections``, ``cta``).

    Templates:
        - Single: ``landing/single.html``

    Frontmatter Support:
        - ``hero``: Hero section config (title, subtitle, cta, image)
        - ``sections``: List of content sections
        - ``features``: Feature grid items
        - ``testimonials``: Customer testimonials
        - ``pricing``: Pricing tiers
        - ``cta``: Call-to-action config
        - ``stats``: Key statistics to highlight

    Section Types:
        - ``features``: Icon + title + description grid
        - ``testimonials``: Quote carousel/grid
        - ``pricing``: Pricing table
        - ``stats``: Big numbers with labels
        - ``content``: Prose content block
        - ``cta``: Full-width call to action

    Class Attributes:
        default_template: ``"landing/single.html"``
        allows_pagination: ``False``
    """

    default_template = "landing/single.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Landing pages sort by weight."""
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def detect_from_section(self, section: Section) -> bool:
        """Detect landing pages by metadata."""
        name = section.name.lower()
        if name == "landing":
            return True

        # Check for landing-specific frontmatter
        if section.pages:
            for page in section.pages[:3]:
                if page.metadata.get("hero") or page.metadata.get("sections"):
                    return True

        return False

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Landing page uses single template only."""
        return "landing/single.html"
```

#### 4.2 Landing Page Template

**`landing/single.html`**:

```html
{% extends "base.html" %}

{% block content %}
{# Hero Section #}
{% set hero = page.metadata.get('hero', {}) %}
<header class="landing-hero hero--blob-background">
    <div class="hero__blobs" aria-hidden="true">
        <div class="hero__blob hero__blob--1"></div>
        <div class="hero__blob hero__blob--2"></div>
        <div class="hero__blob hero__blob--3"></div>
        <div class="hero__blob hero__blob--4"></div>
    </div>
    <div class="landing-hero-content">
        <h1 class="landing-hero-title">
            <span class="fluid-text">{{ hero.get('title', page.title) }}</span>
        </h1>
        {% if hero.get('subtitle') or page.description %}
        <p class="landing-hero-subtitle">{{ hero.get('subtitle', page.description) }}</p>
        {% endif %}

        {% if hero.get('cta') %}
        <div class="landing-hero-cta">
            {% for button in hero.get('cta') %}
            <a href="{{ button.get('url') }}"
               class="hero__button hero__button--{{ button.get('style', 'primary') }}">
                {{ button.get('text') }}
            </a>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    {% if hero.get('image') %}
    <div class="landing-hero-image">
        <img src="{{ hero.get('image') }}" alt="">
    </div>
    {% endif %}
</header>

{# Stats Section #}
{% if page.metadata.get('stats') %}
<section class="landing-stats">
    <div class="landing-stats-grid">
        {% for stat in page.metadata.get('stats') %}
        <div class="landing-stat">
            <span class="landing-stat-value">{{ stat.get('value') }}</span>
            <span class="landing-stat-label">{{ stat.get('label') }}</span>
        </div>
        {% endfor %}
    </div>
</section>
{% endif %}

{# Features Section #}
{% if page.metadata.get('features') %}
<section class="landing-features">
    <div class="container">
        <h2 class="landing-section-title">{{ page.metadata.get('features_title', 'Features') }}</h2>
        <div class="landing-features-grid">
            {% for feature in page.metadata.get('features') %}
            <div class="landing-feature gradient-border fluid-combined">
                {% if feature.get('icon') %}
                <div class="landing-feature-icon">{{ icon(feature.get('icon'), size=32) }}</div>
                {% endif %}
                <h3 class="landing-feature-title">{{ feature.get('title') }}</h3>
                <p class="landing-feature-desc">{{ feature.get('description') }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}

{# Main Content #}
{% if content and content.strip() %}
<section class="landing-content prose">
    <div class="container">
        {{ content | safe }}
    </div>
</section>
{% endif %}

{# Testimonials Section #}
{% if page.metadata.get('testimonials') %}
<section class="landing-testimonials">
    <div class="container">
        <h2 class="landing-section-title">What People Say</h2>
        <div class="landing-testimonials-grid">
            {% for testimonial in page.metadata.get('testimonials') %}
            <blockquote class="landing-testimonial gradient-border">
                <p class="landing-testimonial-quote">"{{ testimonial.get('quote') }}"</p>
                <footer class="landing-testimonial-author">
                    {% if testimonial.get('avatar') %}
                    <img src="{{ testimonial.get('avatar') }}" alt="{{ testimonial.get('name') }}" class="landing-testimonial-avatar">
                    {% endif %}
                    <div>
                        <cite class="landing-testimonial-name">{{ testimonial.get('name') }}</cite>
                        {% if testimonial.get('title') %}
                        <span class="landing-testimonial-title">{{ testimonial.get('title') }}</span>
                        {% endif %}
                    </div>
                </footer>
            </blockquote>
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}

{# Pricing Section #}
{% if page.metadata.get('pricing') %}
<section class="landing-pricing">
    <div class="container">
        <h2 class="landing-section-title">{{ page.metadata.get('pricing_title', 'Pricing') }}</h2>
        <div class="landing-pricing-grid">
            {% for tier in page.metadata.get('pricing') %}
            <div class="landing-pricing-card {% if tier.get('featured') %}landing-pricing-card--featured{% endif %} gradient-border">
                <h3 class="landing-pricing-name">{{ tier.get('name') }}</h3>
                <div class="landing-pricing-price">
                    <span class="landing-pricing-amount">{{ format_price(tier.get('price', 0), tier.get('currency', 'USD')) }}</span>
                    <span class="landing-pricing-period">{{ tier.get('period', '/month') }}</span>
                </div>
                {% if tier.get('description') %}
                <p class="landing-pricing-desc">{{ tier.get('description') }}</p>
                {% endif %}
                <ul class="landing-pricing-features">
                    {% for feature in tier.get('features', []) %}
                    <li>{{ icon('check', size=14) }} {{ feature }}</li>
                    {% endfor %}
                </ul>
                <a href="{{ tier.get('url', '#') }}" class="landing-pricing-cta">
                    {{ tier.get('cta', 'Get Started') }}
                </a>
            </div>
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}

{# Final CTA Section #}
{% set cta = page.metadata.get('cta') %}
{% if cta %}
<section class="landing-cta">
    <div class="container">
        <h2 class="landing-cta-title">{{ cta.get('title', 'Ready to get started?') }}</h2>
        {% if cta.get('subtitle') %}
        <p class="landing-cta-subtitle">{{ cta.get('subtitle') }}</p>
        {% endif %}
        <div class="landing-cta-buttons">
            {% for button in cta.get('buttons', []) %}
            <a href="{{ button.get('url') }}"
               class="landing-cta-button landing-cta-button--{{ button.get('style', 'primary') }}">
                {{ button.get('text') }}
            </a>
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}
{% endblock %}
```

---

### 5. Wiki Support

#### 5.1 WikiStrategy

```python
# bengal/content_types/strategies.py

class WikiStrategy(ContentTypeStrategy):
    """
    Strategy for wiki/knowledge base content.

    Optimized for interconnected content with bidirectional links,
    categories, and easy cross-referencing. Emphasizes discoverability
    and content relationships over chronological ordering.

    Auto-Detection:
        Detected when section name matches wiki patterns
        (``wiki``, ``knowledge-base``, ``kb``, ``notes``).

    Sorting:
        Pages sorted alphabetically by title for easy scanning.
        Featured/pinned pages can be sorted first via ``pinned: true``.

    Features:
        - Backlinks (pages that link to this page)
        - Categories with index pages
        - Last modified dates prominently displayed
        - Full-text search emphasis
        - Graph visualization of connections

    Templates:
        - List: ``wiki/list.html`` (alphabetical index with categories)
        - Single: ``wiki/single.html`` (article with backlinks sidebar)

    Frontmatter Support:
        - ``aliases``: Alternative titles for linking (e.g., ``["JS", "JavaScript"]``)
        - ``pinned``: Show at top of lists
        - ``category``: Wiki category
        - ``related``: Manually specified related pages
        - ``stub``: Mark as incomplete article

    Class Attributes:
        default_template: ``"wiki/list.html"``
        allows_pagination: ``False`` (wikis show all pages)
    """

    default_template = "wiki/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort wiki pages: pinned first, then alphabetically by title.
        """
        def sort_key(p: Page):
            is_pinned = p.metadata.get("pinned", False)
            title = p.title.lower()
            return (not is_pinned, title)

        return sorted(pages, key=sort_key)

    def detect_from_section(self, section: Section) -> bool:
        """Detect wiki sections by common naming patterns."""
        name = section.name.lower()
        return name in ("wiki", "knowledge-base", "kb", "notes", "brain", "garden")

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Wiki-specific template selection."""
        if page is None:
            return self.default_template

        is_section_index = page.source_path.stem == "_index"

        if is_section_index:
            return "wiki/list.html"
        else:
            return "wiki/single.html"
```

#### 5.2 Wiki Templates

**`wiki/list.html`** - Alphabetical index with categories:

```html
{% extends "base.html" %}

{% block content %}
<div class="wiki-container">
    {# Hero #}
    <header class="wiki-header">
        <h1>{{ section.title | default('Knowledge Base') }}</h1>
        {% if section.description %}
        <p class="wiki-lead">{{ section.description }}</p>
        {% endif %}

        {# Quick search #}
        <div class="wiki-search">
            <input type="search" placeholder="Search wiki..."
                   class="wiki-search-input"
                   data-search-target="wiki">
            {{ icon('search', size=18) }}
        </div>
    </header>

    {# Categories #}
    {% set categories = posts | map(attribute='metadata.category') | unique | reject('none') | sort %}
    {% if categories | list %}
    <nav class="wiki-categories" aria-label="Categories">
        <h2 class="wiki-section-title">Categories</h2>
        <div class="wiki-category-grid">
            {% for category in categories %}
            {% set cat_pages = posts | where('metadata.category', category) %}
            <a href="#category-{{ category | slugify }}" class="wiki-category-card gradient-border">
                <span class="wiki-category-name">{{ category }}</span>
                <span class="wiki-category-count">{{ cat_pages | length }} articles</span>
            </a>
            {% endfor %}
        </div>
    </nav>
    {% endif %}

    {# Pinned Articles #}
    {% set pinned = posts | where('pinned', true) %}
    {% if pinned %}
    <section class="wiki-pinned">
        <h2 class="wiki-section-title">{{ icon('pin', size=18) }} Pinned</h2>
        <ul class="wiki-article-list">
            {% for article in pinned %}
            <li class="wiki-article-item">
                <a href="{{ article.href }}">{{ article.title }}</a>
                {% if article.description %}
                <span class="wiki-article-desc">{{ article.description | truncate(80) }}</span>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
    </section>
    {% endif %}

    {# Alphabetical Index #}
    {% set regular = posts | where_not('pinned', true) %}
    {% set grouped = regular | group_by_first_letter('title') %}

    <section class="wiki-index">
        <h2 class="wiki-section-title">All Articles ({{ regular | length }})</h2>

        {# Letter navigation #}
        <nav class="wiki-alphabet" aria-label="Jump to letter">
            {% for letter in grouped.keys() | sort %}
            <a href="#letter-{{ letter }}">{{ letter }}</a>
            {% endfor %}
        </nav>

        {# Articles by letter #}
        {% for letter, articles in grouped | dictsort %}
        <div class="wiki-letter-section" id="letter-{{ letter }}">
            <h3 class="wiki-letter">{{ letter }}</h3>
            <ul class="wiki-article-list">
                {% for article in articles | sort(attribute='title') %}
                <li class="wiki-article-item">
                    <a href="{{ article.href }}">{{ article.title }}</a>
                    {% if article.metadata.get('stub') %}
                    <span class="wiki-stub-badge">stub</span>
                    {% endif %}
                    {% if article.metadata.get('category') %}
                    <span class="wiki-article-category">{{ article.metadata.get('category') }}</span>
                    {% endif %}
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endfor %}
    </section>

    {# Recently Updated #}
    {% set recent = posts | sort(attribute='date', reverse=true) | limit(10) %}
    {% if recent %}
    <aside class="wiki-recent">
        <h2 class="wiki-section-title">{{ icon('clock', size=18) }} Recently Updated</h2>
        <ul class="wiki-article-list wiki-article-list--compact">
            {% for article in recent %}
            <li>
                <a href="{{ article.href }}">{{ article.title }}</a>
                <time>{{ article.date | time_ago }}</time>
            </li>
            {% endfor %}
        </ul>
    </aside>
    {% endif %}
</div>
{% endblock %}
```

**`wiki/single.html`** - Article with backlinks:

```html
{% extends "base.html" %}
{% from 'partials/navigation-components.html' import breadcrumbs %}

{% block content %}
<div class="wiki-article-layout">
    {# Main Article #}
    <article class="wiki-article">
        {{ breadcrumbs(page) }}

        <header class="wiki-article-header">
            <h1>{{ page.title }}</h1>

            {% if page.metadata.get('aliases') %}
            <p class="wiki-aliases">
                Also known as: {{ page.metadata.get('aliases') | join(', ') }}
            </p>
            {% endif %}

            <div class="wiki-article-meta">
                {% if page.metadata.get('category') %}
                <span class="wiki-meta-item">
                    {{ icon('folder', size=14) }}
                    <a href="#category-{{ page.metadata.get('category') | slugify }}">
                        {{ page.metadata.get('category') }}
                    </a>
                </span>
                {% endif %}
                {% if page.date %}
                <span class="wiki-meta-item">
                    {{ icon('clock', size=14) }}
                    Updated {{ page.date | time_ago }}
                </span>
                {% endif %}
                {% if page.metadata.get('stub') %}
                <span class="wiki-stub-warning">
                    {{ icon('warning', size=14) }}
                    This article is a stub and needs expansion
                </span>
                {% endif %}
            </div>
        </header>

        {# Article Content #}
        <div class="wiki-content prose">
            {{ content | safe }}
        </div>

        {# Related Articles (Manual) #}
        {% if page.metadata.get('related') %}
        <section class="wiki-related">
            <h2>Related Articles</h2>
            <ul>
                {% for related_slug in page.metadata.get('related') %}
                {% set related_page = get_page(related_slug) %}
                {% if related_page %}
                <li><a href="{{ related_page.href }}">{{ related_page.title }}</a></li>
                {% endif %}
                {% endfor %}
            </ul>
        </section>
        {% endif %}

        {# Page Navigation #}
        <nav class="wiki-nav-footer">
            {% if page.prev_in_section %}
            <a href="{{ page.prev_in_section.href }}" class="wiki-nav-prev">
                {{ icon('arrow-left', size=16) }} {{ page.prev_in_section.title }}
            </a>
            {% endif %}
            {% if page.next_in_section %}
            <a href="{{ page.next_in_section.href }}" class="wiki-nav-next">
                {{ page.next_in_section.title }} {{ icon('arrow-right', size=16) }}
            </a>
            {% endif %}
        </nav>
    </article>

    {# Sidebar: Backlinks & TOC #}
    <aside class="wiki-sidebar">
        {# Table of Contents #}
        {% if toc %}
        <nav class="wiki-toc">
            <h2>Contents</h2>
            {{ toc | safe }}
        </nav>
        {% endif %}

        {# Backlinks (pages that link to this one) #}
        {% set backlinks = get_backlinks(page) %}
        {% if backlinks %}
        <section class="wiki-backlinks">
            <h2>{{ icon('link', size=16) }} Linked From</h2>
            <ul class="wiki-backlinks-list">
                {% for backlink in backlinks %}
                <li><a href="{{ backlink.href }}">{{ backlink.title }}</a></li>
                {% endfor %}
            </ul>
        </section>
        {% endif %}

        {# Graph Visualization (if enabled) #}
        {% if site.features.graph %}
        <section class="wiki-graph">
            <h2>{{ icon('share', size=16) }} Connections</h2>
            <div class="graph-contextual" data-page-url="{{ page.href }}">
                <div class="graph-contextual-container"></div>
            </div>
        </section>
        {% endif %}
    </aside>
</div>
{% endblock %}
```

#### 5.3 Wiki Template Function

```python
# bengal/rendering/template_functions/wiki.py

def get_backlinks(page: Page, site: Site) -> list[Page]:
    """
    Get all pages that link to this page.

    Uses the crossref index to find incoming links.

    Args:
        page: Target page to find backlinks for
        site: Site instance

    Returns:
        List of pages that contain links to this page
    """
    backlinks = []
    page_url = page.href

    for other_page in site.pages:
        if other_page == page:
            continue

        # Check if other_page links to this page
        # This requires link extraction during parsing
        links = getattr(other_page, '_outgoing_links', [])
        if page_url in links or page.source_path.stem in links:
            backlinks.append(other_page)

    return sorted(backlinks, key=lambda p: p.title.lower())


def group_by_first_letter(pages: list[Page], attr: str = 'title') -> dict[str, list[Page]]:
    """
    Group pages by the first letter of an attribute.

    Args:
        pages: List of pages to group
        attr: Attribute to group by (default: 'title')

    Returns:
        Dict mapping first letter to list of pages
    """
    from collections import defaultdict

    grouped = defaultdict(list)
    for page in pages:
        value = getattr(page, attr, '') or ''
        first_letter = value[0].upper() if value else '#'
        if not first_letter.isalpha():
            first_letter = '#'
        grouped[first_letter].append(page)

    return dict(grouped)
```

---

### 6. Recipe/Cookbook Support

#### 6.1 RecipeStrategy

```python
# bengal/content_types/strategies.py

class RecipeStrategy(ContentTypeStrategy):
    """
    Strategy for recipe/cookbook content.

    Optimized for cooking recipes with structured data for ingredients,
    cook times, and step-by-step instructions. Generates JSON-LD Recipe
    schema for rich search results.

    Auto-Detection:
        Detected when section name matches recipe patterns
        (``recipes``, ``cookbook``, ``food``, ``meals``).

    Sorting:
        1. Featured recipes first
        2. Then by rating (if available)
        3. Then by date (newest first)

    Features:
        - JSON-LD Recipe structured data for Google
        - Cook time, prep time, total time display
        - Servings/yield with scaling
        - Ingredient lists with quantities
        - Step-by-step instructions
        - Nutritional info (optional)
        - Print-friendly layout

    Templates:
        - List: ``recipe/list.html`` (grid with filters)
        - Single: ``recipe/single.html`` (recipe card with JSON-LD)

    Frontmatter Support:
        - ``prep_time``: Preparation time (e.g., "15 minutes")
        - ``cook_time``: Cooking time (e.g., "30 minutes")
        - ``total_time``: Total time (auto-calculated if not set)
        - ``servings``: Number of servings/yield
        - ``difficulty``: easy, medium, hard
        - ``cuisine``: Cuisine type (e.g., "Italian", "Mexican")
        - ``course``: meal course (e.g., "dinner", "dessert")
        - ``diet``: Dietary info (e.g., "vegetarian", "gluten-free")
        - ``ingredients``: List of ingredients with quantities
        - ``instructions``: List of step-by-step instructions
        - ``nutrition``: Nutritional information dict
        - ``rating``: Recipe rating (1-5)
        - ``image``: Recipe photo

    Class Attributes:
        default_template: ``"recipe/list.html"``
        allows_pagination: ``True``
    """

    default_template = "recipe/list.html"
    allows_pagination = True

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort recipes: featured first, then by rating, then by date.
        """
        from datetime import datetime

        def sort_key(p: Page):
            is_featured = p.metadata.get("featured", False)
            rating = p.metadata.get("rating", 0)
            date = p.date if p.date else datetime.min
            return (not is_featured, -rating, date)

        return sorted(pages, key=sort_key, reverse=True)

    def detect_from_section(self, section: Section) -> bool:
        """Detect recipe sections by common naming patterns."""
        name = section.name.lower()
        if name in ("recipes", "cookbook", "food", "meals", "cooking"):
            return True

        # Check for recipe-specific metadata
        if section.pages:
            for page in section.pages[:3]:
                if page.metadata.get("ingredients") or page.metadata.get("cook_time"):
                    return True

        return False

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Recipe-specific template selection."""
        if page is None:
            return self.default_template

        is_section_index = page.source_path.stem == "_index"

        if is_section_index:
            return "recipe/list.html"
        else:
            return "recipe/single.html"
```

#### 6.2 Recipe Templates

**`recipe/list.html`** - Recipe grid with filters:

```html
{% extends "base.html" %}

{% block content %}
<div class="recipe-container">
    {# Hero #}
    <header class="recipe-header hero--blob-background">
        <div class="hero__blobs" aria-hidden="true">
            <div class="hero__blob hero__blob--1"></div>
            <div class="hero__blob hero__blob--2"></div>
        </div>
        <div class="recipe-header-content">
            <h1>{{ section.title | default('Recipes') }}</h1>
            {% if section.description %}
            <p class="recipe-lead">{{ section.description }}</p>
            {% endif %}
        </div>
    </header>

    {# Filters #}
    <nav class="recipe-filters">
        {# Course filter #}
        {% set courses = posts | map(attribute='metadata.course') | unique | reject('none') | sort %}
        {% if courses | list %}
        <div class="recipe-filter-group">
            <label>Course</label>
            <select class="recipe-filter-select" data-filter="course">
                <option value="all">All</option>
                {% for course in courses %}
                <option value="{{ course | slugify }}">{{ course | capitalize }}</option>
                {% endfor %}
            </select>
        </div>
        {% endif %}

        {# Difficulty filter #}
        <div class="recipe-filter-group">
            <label>Difficulty</label>
            <select class="recipe-filter-select" data-filter="difficulty">
                <option value="all">All</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
            </select>
        </div>

        {# Diet filter #}
        {% set diets = posts | map(attribute='metadata.diet') | flatten | unique | reject('none') | sort %}
        {% if diets | list %}
        <div class="recipe-filter-group">
            <label>Diet</label>
            <select class="recipe-filter-select" data-filter="diet">
                <option value="all">All</option>
                {% for diet in diets %}
                <option value="{{ diet | slugify }}">{{ diet }}</option>
                {% endfor %}
            </select>
        </div>
        {% endif %}
    </nav>

    {# Featured Recipes #}
    {% set featured = posts | where('featured', true) %}
    {% if featured %}
    <section class="recipe-featured">
        <h2 class="recipe-section-title">⭐ Featured Recipes</h2>
        <div class="recipe-grid recipe-grid--featured">
            {% for recipe in featured %}
            {% include 'partials/recipe-card.html' with context %}
            {% endfor %}
        </div>
    </section>
    {% endif %}

    {# All Recipes #}
    {% set regular = posts | where_not('featured', true) %}
    <section class="recipe-all">
        {% if featured %}<h2 class="recipe-section-title">All Recipes</h2>{% endif %}
        <div class="recipe-grid">
            {% for recipe in regular %}
            {% include 'partials/recipe-card.html' with context %}
            {% endfor %}
        </div>
    </section>

    {# Pagination #}
    {% if total_pages and total_pages > 1 %}
    {{ pagination(current_page, total_pages, base_url) }}
    {% endif %}
</div>
{% endblock %}
```

**`partials/recipe-card.html`** - Recipe card component:

```html
<article class="recipe-card gradient-border fluid-combined"
         data-course="{{ recipe.metadata.get('course', '') | slugify }}"
         data-difficulty="{{ recipe.metadata.get('difficulty', '') | slugify }}"
         data-diet="{{ (recipe.metadata.get('diet', []) | join(' ') | slugify) if recipe.metadata.get('diet') else '' }}">
    {# Recipe Image #}
    {% if recipe.metadata.get('image') %}
    <div class="recipe-card-image">
        <a href="{{ recipe.href }}">
            <img src="{{ recipe.metadata.get('image') }}" alt="{{ recipe.title }}" loading="lazy">
        </a>
        {# Time badge #}
        {% if recipe.metadata.get('total_time') or recipe.metadata.get('cook_time') %}
        <span class="recipe-time-badge">
            {{ icon('clock', size=12) }}
            {{ recipe.metadata.get('total_time') or recipe.metadata.get('cook_time') }}
        </span>
        {% endif %}
    </div>
    {% endif %}

    {# Card Content #}
    <div class="recipe-card-content">
        <h3 class="recipe-card-title">
            <a href="{{ recipe.href }}">{{ recipe.title }}</a>
        </h3>

        {% if recipe.description or recipe.excerpt %}
        <p class="recipe-card-excerpt">
            {{ recipe.description | default(recipe.excerpt) | truncate(100) }}
        </p>
        {% endif %}

        {# Recipe Meta #}
        <div class="recipe-card-meta">
            {% if recipe.metadata.get('difficulty') %}
            <span class="recipe-difficulty recipe-difficulty--{{ recipe.metadata.get('difficulty') }}">
                {{ recipe.metadata.get('difficulty') | capitalize }}
            </span>
            {% endif %}
            {% if recipe.metadata.get('servings') %}
            <span class="recipe-servings">
                {{ icon('users', size=12) }} {{ recipe.metadata.get('servings') }} servings
            </span>
            {% endif %}
            {% if recipe.metadata.get('rating') %}
            <span class="recipe-rating">
                {% for i in range(recipe.metadata.get('rating') | int) %}★{% endfor %}
            </span>
            {% endif %}
        </div>

        {# Diet badges #}
        {% if recipe.metadata.get('diet') %}
        <div class="recipe-diet-badges">
            {% for diet in recipe.metadata.get('diet') %}
            <span class="recipe-diet-badge">{{ diet }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</article>
```

**`recipe/single.html`** - Full recipe page:

```html
{% extends "base.html" %}
{% from 'partials/navigation-components.html' import breadcrumbs %}

{% block head_extra %}
{# JSON-LD Recipe Structured Data #}
{% include 'partials/recipe-jsonld.html' %}
{% endblock %}

{% block content %}
<article class="recipe-single">
    {{ breadcrumbs(page) }}

    {# Recipe Header #}
    <header class="recipe-header">
        {% if page.metadata.get('image') %}
        <div class="recipe-hero-image">
            <img src="{{ page.metadata.get('image') }}" alt="{{ page.title }}">
        </div>
        {% endif %}

        <div class="recipe-hero-content">
            <h1>{{ page.title }}</h1>

            {% if page.description %}
            <p class="recipe-lead">{{ page.description }}</p>
            {% endif %}

            {# Recipe Stats #}
            <div class="recipe-stats">
                {% if page.metadata.get('prep_time') %}
                <div class="recipe-stat">
                    <span class="recipe-stat-label">Prep Time</span>
                    <span class="recipe-stat-value">{{ page.metadata.get('prep_time') }}</span>
                </div>
                {% endif %}
                {% if page.metadata.get('cook_time') %}
                <div class="recipe-stat">
                    <span class="recipe-stat-label">Cook Time</span>
                    <span class="recipe-stat-value">{{ page.metadata.get('cook_time') }}</span>
                </div>
                {% endif %}
                {% if page.metadata.get('total_time') %}
                <div class="recipe-stat">
                    <span class="recipe-stat-label">Total Time</span>
                    <span class="recipe-stat-value">{{ page.metadata.get('total_time') }}</span>
                </div>
                {% endif %}
                {% if page.metadata.get('servings') %}
                <div class="recipe-stat">
                    <span class="recipe-stat-label">Servings</span>
                    <span class="recipe-stat-value">{{ page.metadata.get('servings') }}</span>
                </div>
                {% endif %}
            </div>

            {# Meta badges #}
            <div class="recipe-badges">
                {% if page.metadata.get('difficulty') %}
                <span class="recipe-badge recipe-badge--{{ page.metadata.get('difficulty') }}">
                    {{ page.metadata.get('difficulty') | capitalize }}
                </span>
                {% endif %}
                {% if page.metadata.get('cuisine') %}
                <span class="recipe-badge">{{ page.metadata.get('cuisine') }}</span>
                {% endif %}
                {% if page.metadata.get('course') %}
                <span class="recipe-badge">{{ page.metadata.get('course') | capitalize }}</span>
                {% endif %}
                {% for diet in page.metadata.get('diet', []) %}
                <span class="recipe-badge recipe-badge--diet">{{ diet }}</span>
                {% endfor %}
            </div>

            {# Print button #}
            <button class="recipe-print-btn" onclick="window.print()">
                {{ icon('download', size=16) }} Print Recipe
            </button>
        </div>
    </header>

    <div class="recipe-body">
        {# Ingredients #}
        {% if page.metadata.get('ingredients') %}
        <section class="recipe-ingredients">
            <h2>{{ icon('list', size=20) }} Ingredients</h2>
            <ul class="recipe-ingredient-list">
                {% for ingredient in page.metadata.get('ingredients') %}
                <li class="recipe-ingredient">
                    <input type="checkbox" id="ing-{{ loop.index }}" class="recipe-checkbox">
                    <label for="ing-{{ loop.index }}">{{ ingredient }}</label>
                </li>
                {% endfor %}
            </ul>
        </section>
        {% endif %}

        {# Instructions #}
        {% if page.metadata.get('instructions') %}
        <section class="recipe-instructions">
            <h2>{{ icon('list', size=20) }} Instructions</h2>
            <ol class="recipe-step-list">
                {% for step in page.metadata.get('instructions') %}
                <li class="recipe-step">
                    <div class="recipe-step-number">{{ loop.index }}</div>
                    <div class="recipe-step-content">{{ step }}</div>
                </li>
                {% endfor %}
            </ol>
        </section>
        {% endif %}

        {# Additional Content (notes, tips, etc.) #}
        {% if content and content.strip() %}
        <section class="recipe-notes prose">
            <h2>{{ icon('note', size=20) }} Notes</h2>
            {{ content | safe }}
        </section>
        {% endif %}

        {# Nutrition Info #}
        {% if page.metadata.get('nutrition') %}
        <section class="recipe-nutrition">
            <h2>{{ icon('info', size=20) }} Nutrition Facts</h2>
            <p class="recipe-nutrition-serving">Per serving</p>
            <dl class="recipe-nutrition-list">
                {% set nutrition = page.metadata.get('nutrition') %}
                {% if nutrition.get('calories') %}
                <div class="recipe-nutrition-item">
                    <dt>Calories</dt>
                    <dd>{{ nutrition.get('calories') }}</dd>
                </div>
                {% endif %}
                {% if nutrition.get('protein') %}
                <div class="recipe-nutrition-item">
                    <dt>Protein</dt>
                    <dd>{{ nutrition.get('protein') }}g</dd>
                </div>
                {% endif %}
                {% if nutrition.get('carbs') %}
                <div class="recipe-nutrition-item">
                    <dt>Carbs</dt>
                    <dd>{{ nutrition.get('carbs') }}g</dd>
                </div>
                {% endif %}
                {% if nutrition.get('fat') %}
                <div class="recipe-nutrition-item">
                    <dt>Fat</dt>
                    <dd>{{ nutrition.get('fat') }}g</dd>
                </div>
                {% endif %}
            </dl>
        </section>
        {% endif %}
    </div>
</article>

{# Related Recipes #}
{% set related = page.related_posts[:4] %}
{% if related %}
<section class="recipe-related">
    <div class="container">
        <h2>You Might Also Like</h2>
        <div class="recipe-grid">
            {% for recipe in related %}
            {% include 'partials/recipe-card.html' %}
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}
{% endblock %}
```

#### 6.3 Recipe JSON-LD

**`partials/recipe-jsonld.html`**:

```html
{%- if page.metadata.get('ingredients') %}
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Recipe",
  "name": {{ page.title | tojson }},
  "description": {{ (page.description | default(page.excerpt | default(''))) | tojson }},
  {%- if page.metadata.get('image') %}
  "image": ["{{ page.metadata.get('image') | absolute_url }}"],
  {%- endif %}
  {%- if page.author %}
  "author": {
    "@type": "Person",
    "name": {{ page.author.name | tojson }}
  },
  {%- endif %}
  "datePublished": "{{ page.date | date_iso }}",
  {%- if page.metadata.get('prep_time') %}
  "prepTime": "{{ page.metadata.get('prep_time') | iso_duration }}",
  {%- endif %}
  {%- if page.metadata.get('cook_time') %}
  "cookTime": "{{ page.metadata.get('cook_time') | iso_duration }}",
  {%- endif %}
  {%- if page.metadata.get('total_time') %}
  "totalTime": "{{ page.metadata.get('total_time') | iso_duration }}",
  {%- endif %}
  {%- if page.metadata.get('servings') %}
  "recipeYield": {{ page.metadata.get('servings') | string | tojson }},
  {%- endif %}
  {%- if page.metadata.get('cuisine') %}
  "recipeCuisine": {{ page.metadata.get('cuisine') | tojson }},
  {%- endif %}
  {%- if page.metadata.get('course') %}
  "recipeCategory": {{ page.metadata.get('course') | tojson }},
  {%- endif %}
  "recipeIngredient": {{ page.metadata.get('ingredients') | tojson }},
  "recipeInstructions": [
    {%- for step in page.metadata.get('instructions', []) %}
    {
      "@type": "HowToStep",
      "text": {{ step | tojson }}
    }{% if not loop.last %},{% endif %}
    {%- endfor %}
  ]
  {%- if page.metadata.get('nutrition') %},
  "nutrition": {
    "@type": "NutritionInformation"
    {%- if page.metadata.get('nutrition', {}).get('calories') %},
    "calories": "{{ page.metadata.get('nutrition').get('calories') }} calories"
    {%- endif %}
    {%- if page.metadata.get('nutrition', {}).get('protein') %},
    "proteinContent": "{{ page.metadata.get('nutrition').get('protein') }} g"
    {%- endif %}
  }
  {%- endif %}
  {%- if page.metadata.get('rating') %},
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": {{ page.metadata.get('rating') }},
    "ratingCount": 1
  }
  {%- endif %}
}
</script>
{%- endif %}
```

#### 6.4 Recipe Template Function

```python
# bengal/rendering/template_functions/time.py

def iso_duration(time_string: str) -> str:
    """
    Convert human-readable time to ISO 8601 duration.

    Args:
        time_string: Human time like "30 minutes", "1 hour 15 minutes"

    Returns:
        ISO 8601 duration like "PT30M", "PT1H15M"

    Example:
        {{ "30 minutes" | iso_duration }}  → PT30M
        {{ "1 hour" | iso_duration }}      → PT1H
        {{ "2 hours 30 minutes" | iso_duration }} → PT2H30M
    """
    import re

    total_minutes = 0

    # Match hours
    hour_match = re.search(r'(\d+)\s*h(?:our)?s?', time_string, re.I)
    if hour_match:
        total_minutes += int(hour_match.group(1)) * 60

    # Match minutes
    min_match = re.search(r'(\d+)\s*m(?:in(?:ute)?)?s?', time_string, re.I)
    if min_match:
        total_minutes += int(min_match.group(1))

    # Build ISO duration
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours and minutes:
        return f"PT{hours}H{minutes}M"
    elif hours:
        return f"PT{hours}H"
    elif minutes:
        return f"PT{minutes}M"
    else:
        return "PT0M"
```

---

## Registry Updates

```python
# bengal/content_types/registry.py

CONTENT_TYPE_REGISTRY: dict[str, ContentTypeStrategy] = {
    # Existing (10 types)
    "blog": BlogStrategy(),
    "archive": ArchiveStrategy(),
    "changelog": ChangelogStrategy(),
    "doc": DocsStrategy(),
    "autodoc-python": ApiReferenceStrategy(),
    "autodoc-cli": CliReferenceStrategy(),
    "tutorial": TutorialStrategy(),
    "track": TrackStrategy(),
    "page": PageStrategy(),
    "list": PageStrategy(),

    # NEW: Specialized site types (6 types)
    "portfolio": PortfolioStrategy(),
    "product": ProductStrategy(),
    "landing": LandingStrategy(),
    "wiki": WikiStrategy(),
    "recipe": RecipeStrategy(),
    "resume": ResumeStrategy(),  # Already has templates, adding strategy
}
```

---

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| **Portfolio** | |
| `templates/portfolio/list.html` | Portfolio grid with filtering |
| `templates/portfolio/single.html` | Project detail page |
| `templates/partials/portfolio-card.html` | Reusable project card |
| `css/components/portfolio.css` | Portfolio styles |
| **Product** | |
| `templates/product/list.html` | Product catalog grid |
| `templates/product/single.html` | Product detail page |
| `templates/partials/product-card.html` | Reusable product card |
| `css/components/product.css` | Product styles |
| `rendering/template_functions/pricing.py` | format_price() function |
| **Landing** | |
| `templates/landing/single.html` | Marketing landing page |
| `css/components/landing.css` | Landing page styles |
| **Wiki** | |
| `templates/wiki/list.html` | Alphabetical index with categories |
| `templates/wiki/single.html` | Article with backlinks sidebar |
| `css/components/wiki.css` | Wiki styles |
| `rendering/template_functions/wiki.py` | get_backlinks(), group_by_first_letter() |
| **Recipe** | |
| `templates/recipe/list.html` | Recipe grid with filters |
| `templates/recipe/single.html` | Full recipe page with JSON-LD |
| `templates/partials/recipe-card.html` | Reusable recipe card |
| `templates/partials/recipe-jsonld.html` | Recipe structured data |
| `css/components/recipe.css` | Recipe styles + print styles |
| `rendering/template_functions/time.py` | iso_duration() filter |
| **Resume** | |
| `templates/partials/resume-jsonld.html` | Person structured data |

### Modified Files

| File | Changes |
|------|---------|
| `content_types/strategies.py` | Add Portfolio, Product, Landing, Wiki, Recipe, Resume strategies |
| `content_types/registry.py` | Register 6 new strategies |
| `templates/resume/single.html` | Add JSON-LD, print styles, variants |
| `css/components/resume.css` | Add print styles |
| `themes/default/theme.yaml` | Add `content_types.supported` declaration |

---

## Template Conveniences Summary

### Portfolio

| Function/Property | Purpose |
|-------------------|---------|
| `page.metadata.technologies` | List of tech tags for filtering |
| `posts \| where('featured', true)` | Featured projects |
| Filter UI with JS | Category/tech filtering |

### Product

| Function/Property | Purpose |
|-------------------|---------|
| `format_price(price, currency)` | Currency-aware price formatting |
| `page.metadata.in_stock` | Availability status |
| `page.metadata.sale_price` | Discounted pricing |
| JSON-LD structured data | SEO product schema |

### Resume

| Function/Property | Purpose |
|-------------------|---------|
| `site.data.resume` | Structured resume data |
| JSON-LD Person schema | SEO structured data |
| Print styles | PDF-ready output |

### Landing

| Function/Property | Purpose |
|-------------------|---------|
| `page.metadata.hero` | Hero section config |
| `page.metadata.features` | Feature grid items |
| `page.metadata.testimonials` | Customer quotes |
| `page.metadata.pricing` | Pricing tiers |

### Wiki

| Function/Property | Purpose |
|-------------------|---------|
| `get_backlinks(page)` | Pages that link to this page |
| `posts \| group_by_first_letter('title')` | Alphabetical grouping |
| `page.metadata.aliases` | Alternative titles for linking |
| `page.metadata.pinned` | Featured at top of lists |
| `page.metadata.stub` | Mark incomplete articles |
| Graph visualization | Visual connections between pages |

### Recipe

| Function/Property | Purpose |
|-------------------|---------|
| `time_string \| iso_duration` | Convert "30 minutes" → "PT30M" |
| `page.metadata.prep_time` | Prep time display |
| `page.metadata.cook_time` | Cook time display |
| `page.metadata.ingredients` | Ingredient list |
| `page.metadata.instructions` | Step-by-step instructions |
| `page.metadata.nutrition` | Nutritional info |
| `page.metadata.servings` | Yield/servings |
| `page.metadata.difficulty` | easy/medium/hard badge |
| JSON-LD Recipe schema | Rich search results |
| Print styles | Print-friendly recipe cards |

---

## Testing Strategy

### Visual Testing
- [ ] Portfolio grid with 0, 1, 5, 20 projects
- [ ] Portfolio with/without featured projects
- [ ] Portfolio filtering by technology
- [ ] Product catalog in light/dark modes
- [ ] Product with/without sale price
- [ ] Product out of stock state
- [ ] Resume print preview
- [ ] Landing page with all sections
- [ ] Landing page minimal (hero only)
- [ ] Mobile responsive (320px, 768px, 1024px)

### Functional Testing
- [ ] Auto-detection from section names
- [ ] Sorting: featured first, then by date/weight
- [ ] JSON-LD output validation
- [ ] format_price() with various currencies
- [ ] Filter UI JavaScript

---

## Migration Path

**For existing sites**: All changes are additive. Users can opt-in by:
1. Setting `type: portfolio`, `type: product`, `type: resume`, or `type: landing` in frontmatter
2. Or naming sections with auto-detected names

**No breaking changes**.

---

## Estimated Effort

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 0: Theme Contract | Add `content_types` to theme.yaml + fallback | 2-3 hours |
| Phase 1: Strategies | Add 6 content strategies | 3-4 hours |
| Phase 2: Portfolio | Templates + CSS | 4-5 hours |
| Phase 3: Product | Templates + CSS + pricing func | 4-5 hours |
| Phase 4: Wiki | Templates + CSS + backlinks | 5-6 hours |
| Phase 5: Recipe | Templates + CSS + JSON-LD + print | 5-6 hours |
| Phase 6: Resume | Enhance templates + print + JSON-LD | 2-3 hours |
| Phase 7: Landing | Templates + CSS | 3-4 hours |
| Phase 8: Polish | Testing, docs, examples | 3-4 hours |
| **Total** | | **32-40 hours** |

### Suggested Phasing

**MVP (High Value, Low Effort)**:
1. Portfolio (universal appeal, reuses existing patterns)
2. Wiki (differentiator, backlinks are unique)
3. Recipe (strong SEO story with JSON-LD)

**Follow-up**:
4. Landing (marketing sites)
5. Product (catalog sites)
6. Resume (niche but has templates)

---

## Open Questions

1. **Should we add a `gallery` type for image-heavy portfolios?** (Lightbox grid, masonry layout)

2. **Should product support variants (size/color)?** (Static site limitation, but could show options)

3. **Should landing page support dynamic sections via markdown?** (Sections embedded in content vs frontmatter)

4. **Should resume support multiple output formats?** (HTML, PDF via puppeteer, JSON Resume spec)

5. **How should backlinks be indexed?** (Build-time scan, or leverage existing graph feature?)

6. **Should wiki support wikilinks syntax?** (`[[Page Name]]` linking, like Obsidian)

7. **Should recipe support scaling ingredients?** (JS-based serving size adjustment)

---

## Success Criteria

- [ ] Theme contract documented: themes can declare supported types
- [ ] Graceful fallback with warnings when theme doesn't support a type
- [ ] Custom strategy guide documented for themers
- [ ] `bengal new site --template portfolio` produces polished portfolio
- [ ] `bengal new site --template product` produces catalog with JSON-LD
- [ ] `bengal new site --template wiki` produces interconnected knowledge base
- [ ] `bengal new site --template recipe` produces cookbook with rich search results
- [ ] Resume pages print cleanly to PDF
- [ ] Recipe pages print cleanly
- [ ] Landing pages feel marketing-quality
- [ ] All templates use design system (blob backgrounds, gradient borders)
- [ ] Mobile experience excellent for all types

---

## Related RFCs

- **`rfc-css-tree-shaking.md`** - Content-aware CSS optimization (prevents CSS bundle bloat from new types)
- **`rfc-template-conveniences.md`** - Template helper functions (Author dataclass, reading_time, etc.)
- **`rfc-blog-layout-parity.md`** - Blog-specific template improvements
- **`rfc-theme-developer-ergonomics.md`** - Theme development improvements

---

## Appendix: Design Inspiration

**Portfolio**:
- Dribbble profiles
- Behance portfolios
- Linear.app team pages

**Product/E-commerce**:
- Stripe product pages
- Gumroad product listings
- Simple Commerce themes

**Resume**:
- JSON Resume rendered themes
- LinkedIn profiles
- Standard Resume

**Landing Pages**:
- Linear.app
- Vercel homepage
- Tailwind UI marketing templates
