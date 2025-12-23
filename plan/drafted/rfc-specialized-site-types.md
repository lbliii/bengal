# RFC: Specialized Site Types - Portfolio, Product, Resume

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-23  
**Subsystems**: content_types, themes/default/templates, core

---

## Executive Summary

Add first-class content type strategies and template support for specialized site types beyond documentation and blogs. Bengal already has CLI scaffolding templates for portfolio, product, and resume sites, but lacks the content type strategies and theme templates needed for polished, production-ready sites.

**Key Additions**:
- `PortfolioStrategy` - Project showcase with featured projects, technology tags, live demos
- `ProductStrategy` - E-commerce/product catalog with pricing, inventory, JSON-LD
- `ResumeStrategy` - CV/professional site with structured data sections
- `LandingStrategy` - Marketing/landing pages with sections and CTAs

---

## Problem Statement

Bengal has a gap between **scaffolding** and **rendering** for specialized site types:

| Site Type | CLI Scaffold | Content Strategy | Theme Templates | Gap |
|-----------|--------------|------------------|-----------------|-----|
| Portfolio | ✅ `--template portfolio` | ❌ Missing | ❌ Missing | No sorting, no dedicated templates |
| Product | ✅ `--template product` | ❌ Missing | ⚠️ Partial (JSON-LD only) | No catalog features |
| Resume | ❌ No scaffold | ❌ Missing | ✅ `resume/list.html`, `resume/single.html` | Templates exist, no strategy |
| Landing | ❌ No scaffold | ❌ Missing | ❌ Missing | No support |

**Current Workarounds**:
- Portfolio: Use `type: page` with manual sorting/templates
- Product: Use `type: page` with JSON-LD partial, no catalog logic
- Resume: Use resume templates directly, but no type detection
- Landing: Build from scratch with `type: page`

**Result**: Users create these site types but get no platform assistance for common patterns.

---

## Goals

### Must Have
1. **Content strategies** for portfolio, product, resume, landing
2. **Theme templates** that work out of the box
3. **Auto-detection** from section names (like blog/docs)
4. **Design system parity** with existing docs/blog polish

### Should Have
5. **Data file support** (e.g., `data/resume.yaml`, `data/products.yaml`)
6. **Structured data** (JSON-LD) for SEO
7. **Template conveniences** specific to each type

### Nice to Have
8. **Variant support** (e.g., `variant: timeline` for resume)
9. **Category/filter UI** for portfolios and products
10. **Print styles** for resume

### Non-Goals
- Shopping cart or checkout (static site limitation)
- User accounts or authentication
- Dynamic pricing or inventory management
- Payment processing

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

## Registry Updates

```python
# bengal/content_types/registry.py

CONTENT_TYPE_REGISTRY: dict[str, ContentTypeStrategy] = {
    # Existing
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

    # NEW: Specialized site types
    "portfolio": PortfolioStrategy(),
    "product": ProductStrategy(),
    "resume": ResumeStrategy(),
    "landing": LandingStrategy(),
}
```

---

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `templates/portfolio/list.html` | Portfolio grid with filtering |
| `templates/portfolio/single.html` | Project detail page |
| `templates/partials/portfolio-card.html` | Reusable project card |
| `templates/product/list.html` | Product catalog grid |
| `templates/product/single.html` | Product detail page |
| `templates/partials/product-card.html` | Reusable product card |
| `templates/landing/single.html` | Marketing landing page |
| `templates/partials/resume-jsonld.html` | Person structured data |
| `css/components/portfolio.css` | Portfolio styles |
| `css/components/product.css` | Product styles |
| `css/components/landing.css` | Landing page styles |
| `rendering/template_functions/pricing.py` | format_price() function |

### Modified Files

| File | Changes |
|------|---------|
| `content_types/strategies.py` | Add Portfolio, Product, Resume, Landing strategies |
| `content_types/registry.py` | Register new strategies |
| `templates/resume/single.html` | Add JSON-LD, print styles, variants |
| `css/components/resume.css` | Add print styles |

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
| Phase 1: Strategies | Add 4 content strategies | 2-3 hours |
| Phase 2: Portfolio | Templates + CSS | 4-5 hours |
| Phase 3: Product | Templates + CSS + pricing func | 4-5 hours |
| Phase 4: Resume | Enhance templates + print + JSON-LD | 2-3 hours |
| Phase 5: Landing | Templates + CSS | 3-4 hours |
| Phase 6: Polish | Testing, docs, examples | 2-3 hours |
| **Total** | | **17-23 hours** |

---

## Open Questions

1. **Should we add a `gallery` type for image-heavy portfolios?** (Lightbox grid, masonry layout)

2. **Should product support variants (size/color)?** (Static site limitation, but could show options)

3. **Should landing page support dynamic sections via markdown?** (Sections embedded in content vs frontmatter)

4. **Should resume support multiple output formats?** (HTML, PDF via puppeteer, JSON Resume spec)

---

## Success Criteria

- [ ] `bengal new site --template portfolio` produces polished portfolio
- [ ] `bengal new site --template product` produces catalog with JSON-LD
- [ ] Resume pages print cleanly to PDF
- [ ] Landing pages feel marketing-quality
- [ ] All templates use design system (blob backgrounds, gradient borders)
- [ ] Mobile experience excellent for all types

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
