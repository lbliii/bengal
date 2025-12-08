# RFC-004: Component System & Macros

**Status**: ⏸️ Deferred  
**Created**: 2024-12-08  
**Archived**: 2024-12-08  
**Part of**: [Theme Architecture Series](../active/rfc-theme-architecture-series.md)  

---

> **Why Deferred**: Current `partials/*.html` system works well. Formal macro library is nice-to-have but not urgent. Can be done incrementally without a full RFC when there's demand.  

---

## Summary

Introduce a formal component system with documented, reusable Jinja2 macros and optional component registry for discoverability and documentation.

---

## Problem Statement

### Current State

Reusable UI patterns are implemented inconsistently:

```jinja2
{# Some patterns are inline #}
<span class="badge badge--{{ type }}">{{ text }}</span>

{# Some are partials (context-dependent) #}
{% include 'partials/tag-list.html' %}

{# Some are semi-reusable but not parametric #}
{% include 'partials/page-hero.html' %}
```

### Problems

1. **Duplication** - Same patterns repeated across templates
2. **Inconsistent APIs** - No standard way to pass options
3. **Undocumented** - Have to read template to understand usage
4. **Not discoverable** - No component catalog
5. **Hard to test** - Components mixed with page logic

---

## Proposal

### Component Macro Library

Create `templates/macros/` with domain-grouped macro files:

```jinja2
{# templates/macros/components.html #}

{#-----------------------------------------------------------------------
  Badge Component

  Renders an inline badge/label.

  Args:
    text: Badge text content
    variant: Visual variant (default, primary, success, warning, error, info)
    size: Size variant (sm, md, lg)
    icon: Optional icon name to prepend

  Example:
    {{ badge('New', variant='success') }}
    {{ badge('Deprecated', variant='warning', icon='alert') }}
-----------------------------------------------------------------------#}
{% macro badge(text, variant='default', size='md', icon=none) %}
<span class="badge badge--{{ variant }} badge--{{ size }}">
  {%- if icon %}{{ icon_svg(icon, size=12) }} {% endif -%}
  {{ text }}
</span>
{% endmacro %}


{#-----------------------------------------------------------------------
  Card Component

  Renders a card with optional header, body, and footer.
  Uses Jinja2 caller() for body content.

  Args:
    title: Card title (optional)
    subtitle: Card subtitle (optional)
    variant: Visual variant (default, elevated, bordered, ghost)
    href: If provided, card becomes a link

  Example:
    {% call card('My Card', variant='elevated') %}
      <p>Card content here.</p>
    {% endcall %}
-----------------------------------------------------------------------#}
{% macro card(title=none, subtitle=none, variant='default', href=none) %}
{% set tag = 'a' if href else 'div' %}
<{{ tag }}{% if href %} href="{{ href }}"{% endif %} class="card card--{{ variant }}">
  {% if title or subtitle %}
  <div class="card__header">
    {% if title %}<h3 class="card__title">{{ title }}</h3>{% endif %}
    {% if subtitle %}<p class="card__subtitle">{{ subtitle }}</p>{% endif %}
  </div>
  {% endif %}
  <div class="card__body">
    {{ caller() }}
  </div>
</{{ tag }}>
{% endmacro %}


{#-----------------------------------------------------------------------
  Button Component

  Renders a button or link styled as button.

  Args:
    text: Button text
    href: If provided, renders as <a>
    variant: Visual variant (primary, secondary, ghost, danger)
    size: Size (sm, md, lg)
    icon: Optional icon name
    icon_position: 'start' or 'end'
    disabled: Disable button

  Example:
    {{ button('Submit', variant='primary') }}
    {{ button('Learn More', href='/docs', icon='arrow-right', icon_position='end') }}
-----------------------------------------------------------------------#}
{% macro button(text, href=none, variant='primary', size='md', icon=none, icon_position='start', disabled=false) %}
{% set tag = 'a' if href and not disabled else 'button' %}
<{{ tag }}
  {% if href and not disabled %}href="{{ href }}"{% endif %}
  {% if disabled %}disabled aria-disabled="true"{% endif %}
  class="btn btn--{{ variant }} btn--{{ size }}"
>
  {%- if icon and icon_position == 'start' %}{{ icon_svg(icon, size=16) }} {% endif -%}
  {{ text }}
  {%- if icon and icon_position == 'end' %} {{ icon_svg(icon, size=16) }}{% endif -%}
</{{ tag }}>
{% endmacro %}


{#-----------------------------------------------------------------------
  Alert/Callout Component

  Renders a callout box for important information.

  Args:
    type: Alert type (info, tip, warning, danger, note)
    title: Optional title override
    collapsible: Make content collapsible

  Example:
    {% call alert('warning', title='Deprecation Notice') %}
      This feature will be removed in v3.0.
    {% endcall %}
-----------------------------------------------------------------------#}
{% macro alert(type='info', title=none, collapsible=false) %}
{% set default_titles = {'info': 'Info', 'tip': 'Tip', 'warning': 'Warning', 'danger': 'Danger', 'note': 'Note'} %}
{% set resolved_title = title or default_titles.get(type, type | title) %}
{% if collapsible %}
<details class="alert alert--{{ type }}">
  <summary class="alert__header">
    {{ icon_svg(type, size=20) }}
    <span class="alert__title">{{ resolved_title }}</span>
  </summary>
  <div class="alert__body">{{ caller() }}</div>
</details>
{% else %}
<div class="alert alert--{{ type }}" role="alert">
  <div class="alert__header">
    {{ icon_svg(type, size=20) }}
    <span class="alert__title">{{ resolved_title }}</span>
  </div>
  <div class="alert__body">{{ caller() }}</div>
</div>
{% endif %}
{% endmacro %}
```

### Navigation Macros

```jinja2
{# templates/macros/navigation.html #}

{#-----------------------------------------------------------------------
  Breadcrumbs Component

  Renders breadcrumb navigation.

  Args:
    items: List of {title, url} dicts, or use page.breadcrumbs
    separator: Separator character/icon

  Example:
    {{ breadcrumbs(page.breadcrumbs) }}
    {{ breadcrumbs([{'title': 'Home', 'url': '/'}, {'title': 'Docs', 'url': '/docs/'}]) }}
-----------------------------------------------------------------------#}
{% macro breadcrumbs(items, separator='/') %}
<nav class="breadcrumbs" aria-label="Breadcrumb">
  <ol class="breadcrumbs__list">
    {% for item in items %}
    <li class="breadcrumbs__item">
      {% if loop.last %}
        <span class="breadcrumbs__current" aria-current="page">{{ item.title }}</span>
      {% else %}
        <a href="{{ item.url }}" class="breadcrumbs__link">{{ item.title }}</a>
        <span class="breadcrumbs__separator" aria-hidden="true">{{ separator }}</span>
      {% endif %}
    </li>
    {% endfor %}
  </ol>
</nav>
{% endmacro %}


{#-----------------------------------------------------------------------
  Pagination Component

  Renders previous/next navigation.

  Args:
    prev: Previous page object or {title, url}
    next: Next page object or {title, url}

  Example:
    {{ pagination(page.prev, page.next) }}
-----------------------------------------------------------------------#}
{% macro pagination(prev=none, next=none) %}
{% if prev or next %}
<nav class="pagination" aria-label="Page navigation">
  {% if prev %}
  <a href="{{ prev.url or prev.relative_url }}" class="pagination__link pagination__link--prev">
    {{ icon_svg('chevron-left', size=16) }}
    <span class="pagination__label">Previous</span>
    <span class="pagination__title">{{ prev.title }}</span>
  </a>
  {% else %}
  <div class="pagination__spacer"></div>
  {% endif %}

  {% if next %}
  <a href="{{ next.url or next.relative_url }}" class="pagination__link pagination__link--next">
    <span class="pagination__label">Next</span>
    <span class="pagination__title">{{ next.title }}</span>
    {{ icon_svg('chevron-right', size=16) }}
  </a>
  {% endif %}
</nav>
{% endif %}
{% endmacro %}


{#-----------------------------------------------------------------------
  Table of Contents

  Renders a table of contents from heading data.

  Args:
    headings: List of {id, text, level} dicts
    max_depth: Maximum heading depth to show
    title: Optional title for the TOC

  Example:
    {{ toc(page.toc, max_depth=3) }}
-----------------------------------------------------------------------#}
{% macro toc(headings, max_depth=3, title='On this page') %}
{% if headings %}
<nav class="toc" aria-label="Table of contents">
  {% if title %}<h2 class="toc__title">{{ title }}</h2>{% endif %}
  <ul class="toc__list">
    {% for heading in headings if heading.level <= max_depth %}
    <li class="toc__item toc__item--level-{{ heading.level }}">
      <a href="#{{ heading.id }}" class="toc__link">{{ heading.text }}</a>
    </li>
    {% endfor %}
  </ul>
</nav>
{% endif %}
{% endmacro %}
```

### API Documentation Macros

```jinja2
{# templates/macros/api.html #}

{#-----------------------------------------------------------------------
  API Parameter Table

  Renders a table of function/method parameters.

  Args:
    parameters: List of parameter dicts
    compact: Use compact styling
    show_default: Show default values column
-----------------------------------------------------------------------#}
{% macro param_table(parameters, compact=false, show_default=true) %}
{% if parameters %}
<div class="api-params">
  <table class="api-table{% if compact %} api-table--compact{% endif %}">
    <thead>
      <tr>
        <th>Parameter</th>
        <th>Type</th>
        {% if show_default %}<th>Default</th>{% endif %}
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      {% for param in parameters %}
      <tr>
        <td><code>{{ param.name }}</code></td>
        <td>{% if param.type %}<code>{{ param.type }}</code>{% else %}—{% endif %}</td>
        {% if show_default %}
        <td>{% if param.default %}<code>{{ param.default }}</code>{% else %}—{% endif %}</td>
        {% endif %}
        <td>{{ param.description | default('—') }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}
{% endmacro %}


{#-----------------------------------------------------------------------
  API Class Card

  Renders a class as an expandable card with methods and attributes.
-----------------------------------------------------------------------#}
{% macro class_card(cls, open=false) %}
<details class="api-card api-card--class"{% if open %} open{% endif %}>
  <summary class="api-card__header">
    <span class="api-card__icon">◆</span>
    <code class="api-card__name">{{ cls.name }}</code>
    {{ element_badges(cls, compact=true) }}
    <span class="api-card__toggle">▸</span>
  </summary>
  <div class="api-card__body">
    {% if cls.description %}
    <p class="api-card__description">{{ cls.description }}</p>
    {% endif %}

    {# Attributes #}
    {% set attributes = cls.children | selectattr('element_type', 'eq', 'attribute') | list %}
    {% if attributes %}
    {{ attr_table(attributes) }}
    {% endif %}

    {# Methods #}
    {% set methods = cls.children | selectattr('element_type', 'eq', 'method') | list %}
    {% if methods %}
    <div class="api-methods">
      <h4 class="api-subsection-title">Methods</h4>
      {% for method in methods %}
      {{ method_item(method) }}
      {% endfor %}
    </div>
    {% endif %}
  </div>
</details>
{% endmacro %}
```

### Component Registry (Optional)

For discoverability and documentation:

```yaml
# themes/default/components/buttons.yaml
name: Button
category: Interactive
description: Clickable button or link styled as button.

macro: components.button
file: macros/components.html

props:
  text:
    type: string
    required: true
    description: Button text content
  href:
    type: string
    required: false
    description: If provided, renders as anchor tag
  variant:
    type: enum
    values: [primary, secondary, ghost, danger]
    default: primary
    description: Visual style variant
  size:
    type: enum
    values: [sm, md, lg]
    default: md
  icon:
    type: string
    required: false
    description: Icon name to display
  icon_position:
    type: enum
    values: [start, end]
    default: start
  disabled:
    type: boolean
    default: false

examples:
  - title: Primary Button
    code: |
      {{ button('Submit', variant='primary') }}

  - title: Link Button with Icon
    code: |
      {{ button('Learn More', href='/docs', icon='arrow-right', icon_position='end') }}

  - title: Disabled State
    code: |
      {{ button('Unavailable', disabled=true) }}
```

Generated component gallery at `/dev/components/`:

```jinja2
{# Auto-generated component documentation page #}
{% for component in theme.components %}
<section class="component-doc" id="{{ component.name | slugify }}">
  <h2>{{ component.name }}</h2>
  <p>{{ component.description }}</p>

  <h3>Props</h3>
  <table>
    {% for prop_name, prop in component.props.items() %}
    <tr>
      <td><code>{{ prop_name }}</code></td>
      <td>{{ prop.type }}</td>
      <td>{{ prop.default | default('required') }}</td>
      <td>{{ prop.description }}</td>
    </tr>
    {% endfor %}
  </table>

  <h3>Examples</h3>
  {% for example in component.examples %}
  <div class="example">
    <h4>{{ example.title }}</h4>
    <div class="example__preview">
      {{ example.code | safe }}
    </div>
    <pre class="example__code">{{ example.code }}</pre>
  </div>
  {% endfor %}
</section>
{% endfor %}
```

### Usage in Templates

```jinja2
{# Import macros at top of template #}
{% from 'macros/components.html' import badge, card, button, alert %}
{% from 'macros/navigation.html' import breadcrumbs, pagination, toc %}
{% from 'macros/api.html' import param_table, class_card %}

{# Use throughout template #}
{{ breadcrumbs(page.breadcrumbs) }}

{% call card('Getting Started', variant='elevated') %}
  <p>Welcome to the documentation!</p>
  {{ button('Read the Docs', href='/docs/', variant='primary') }}
{% endcall %}

{% call alert('tip') %}
  Use {{ badge('Ctrl+K', size='sm') }} to open search.
{% endcall %}
```

---

## Benefits

1. **Reusability** - Define once, use everywhere
2. **Consistency** - Same component looks same everywhere
3. **Discoverable** - Component registry documents options
4. **Testable** - Macros can be unit tested
5. **Typed** - Registry provides prop documentation
6. **Maintainable** - Change in one place updates all uses

---

## Implementation

### Phase 1: Create Macro Libraries
- [ ] Create `macros/components.html` with core components
- [ ] Create `macros/navigation.html` with nav macros
- [ ] Create `macros/content.html` with content macros
- [ ] Create `macros/api.html` with API doc macros

### Phase 2: Migrate Templates
- [ ] Replace inline patterns with macro calls
- [ ] Replace context-dependent partials with macros where appropriate
- [ ] Update all theme templates to use macros

### Phase 3: Component Registry (Optional)
- [ ] Define YAML schema for component documentation
- [ ] Create component loader
- [ ] Generate component gallery page

### Phase 4: Documentation
- [ ] Document macro library
- [ ] Add component development guide
- [ ] Create visual component gallery

---

## Open Questions

1. **Should macros auto-import?**  
   Proposal: No, explicit imports keep dependencies clear

2. **How to handle macro versioning?**  
   Proposal: Macros follow theme version, document breaking changes

3. **Should components support slots beyond caller()?**  
   Proposal: Future enhancement, use named blocks in caller for now
