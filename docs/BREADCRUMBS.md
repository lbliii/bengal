# Breadcrumbs Guide

Bengal provides a powerful `get_breadcrumbs()` function that handles all breadcrumb logic while giving you complete control over styling and HTML structure.

## Why Use `get_breadcrumbs()`?

The function handles complex logic that's error-prone in templates:
- Building the ancestor chain
- Detecting section index pages (prevents duplication like "Docs / Markdown / Markdown")
- Determining which item is the current page
- Providing clean, testable data

**You maintain full control over:**
- HTML structure
- CSS styling
- Accessibility attributes
- Additional markup (icons, separators, etc.)

## Basic Usage

```jinja2
{% set breadcrumb_items = get_breadcrumbs(page) %}
{% if breadcrumb_items %}
<nav aria-label="Breadcrumb">
  <ol>
    {% for item in breadcrumb_items %}
      <li>
        {% if item.is_current %}
          {{ item.title }}
        {% else %}
          <a href="{{ item.url }}">{{ item.title }}</a>
        {% endif %}
      </li>
    {% endfor %}
  </ol>
</nav>
{% endif %}
```

## Data Structure

Each breadcrumb item is a dictionary with:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Display text for the breadcrumb |
| `url` | string | URL to link to |
| `is_current` | boolean | `true` if this is the current page (shouldn't be a link) |

## Styling Examples

### With Separators

```jinja2
{% set items = get_breadcrumbs(page) %}
<nav class="breadcrumbs">
  {% for item in items %}
    {% if not loop.first %}
      <span class="separator">›</span>
    {% endif %}
    
    {% if item.is_current %}
      <span class="current">{{ item.title }}</span>
    {% else %}
      <a href="{{ item.url }}">{{ item.title }}</a>
    {% endif %}
  {% endfor %}
</nav>
```

### Bootstrap Style

```jinja2
{% set items = get_breadcrumbs(page) %}
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    {% for item in items %}
      <li class="breadcrumb-item {{ 'active' if item.is_current else '' }}"
          {% if item.is_current %}aria-current="page"{% endif %}>
        {% if item.is_current %}
          {{ item.title }}
        {% else %}
          <a href="{{ item.url }}">{{ item.title }}</a>
        {% endif %}
      </li>
    {% endfor %}
  </ol>
</nav>
```

### With Icons

```jinja2
{% set items = get_breadcrumbs(page) %}
<nav class="breadcrumbs">
  {% for item in items %}
    {% if not loop.first %}
      <svg class="separator" viewBox="0 0 20 20">
        <path d="M7 10l5 5 5-5z"/>
      </svg>
    {% endif %}
    
    {% if item.is_current %}
      <strong>{{ item.title }}</strong>
    {% else %}
      <a href="{{ item.url }}">{{ item.title }}</a>
    {% endif %}
  {% endfor %}
</nav>
```

### Tailwind CSS Style

```jinja2
{% set items = get_breadcrumbs(page) %}
<nav class="flex" aria-label="Breadcrumb">
  <ol class="inline-flex items-center space-x-1 md:space-x-3">
    {% for item in items %}
      <li class="inline-flex items-center">
        {% if not loop.first %}
          <svg class="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"></path>
          </svg>
        {% endif %}
        
        {% if item.is_current %}
          <span class="ml-1 text-sm font-medium text-gray-500 md:ml-2">
            {{ item.title }}
          </span>
        {% else %}
          <a href="{{ item.url }}" 
             class="ml-1 text-sm font-medium text-gray-700 hover:text-blue-600 md:ml-2">
            {{ item.title }}
          </a>
        {% endif %}
      </li>
    {% endfor %}
  </ol>
</nav>
```

## SEO: JSON-LD Structured Data

Use the same function to generate schema.org breadcrumb structured data:

```jinja2
{% set items = get_breadcrumbs(page) %}
{% if items %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {% for item in items %}
    {
      "@type": "ListItem",
      "position": {{ loop.index }},
      "name": "{{ item.title | escape }}",
      "item": "{{ item.url | absolute_url }}"
    }{{ "," if not loop.last else "" }}
    {% endfor %}
  ]
}
</script>
{% endif %}
```

## Custom Breadcrumb Rendering

You can create your own breadcrumb partial with custom logic:

```jinja2
{# templates/partials/my-breadcrumbs.html #}
{% set items = get_breadcrumbs(page) %}
<nav class="custom-breadcrumbs">
  {% for item in items %}
    {# Add custom logic based on item properties #}
    {% if loop.first %}
      {# Special rendering for home #}
      <a href="{{ item.url }}" class="home-icon">🏠</a>
    {% elif item.is_current %}
      {# Current page styling #}
      <span class="current-page">{{ item.title }}</span>
    {% else %}
      {# Regular breadcrumb #}
      <a href="{{ item.url }}">{{ item.title }}</a>
    {% endif %}
    
    {# Add separator except after last item #}
    {% if not loop.last %}
      <span class="sep">/</span>
    {% endif %}
  {% endfor %}
</nav>
```

## Accessibility Best Practices

1. **Always use `<nav>` with `aria-label="Breadcrumb"`**
   ```jinja2
   <nav class="breadcrumbs" aria-label="Breadcrumb">
   ```

2. **Mark the current page with `aria-current="page"`**
   ```jinja2
   {% if item.is_current %}
     <li aria-current="page">{{ item.title }}</li>
   {% endif %}
   ```

3. **Use semantic HTML with `<ol>` and `<li>`**
   ```jinja2
   <ol>
     {% for item in breadcrumb_items %}
       <li>...</li>
     {% endfor %}
   </ol>
   ```

4. **Don't make the current page a link** (handled automatically if you check `item.is_current`)

## How It Works

The `get_breadcrumbs()` function:

1. Returns an empty list if the page has no ancestors
2. Always starts with "Home" (/)
3. Adds all ancestor sections in order (root → current)
4. Detects if you're viewing a section's index page (like `/docs/markdown/_index.md`)
5. Prevents duplication by not adding the page title separately if it's already the last ancestor
6. Marks the appropriate item as `is_current`

### Section Index Detection Example

When viewing `/docs/markdown/_index.md`:
- **Without detection:** Home → Docs → Markdown → Markdown ❌
- **With detection:** Home → Docs → Markdown ✓

## Integration with Templates

The default Bengal templates already use `get_breadcrumbs()` in `partials/breadcrumbs.html`. You can:

1. **Use the default** - Include it in your templates:
   ```jinja2
   {% include 'partials/breadcrumbs.html' %}
   ```

2. **Customize the partial** - Create your own version in your project:
   ```
   your-project/
     templates/
       partials/
         breadcrumbs.html  ← Your custom version
   ```

3. **Inline in your template** - Use `get_breadcrumbs()` directly:
   ```jinja2
   {% set items = get_breadcrumbs(page) %}
   {# Your custom rendering #}
   ```

## Testing Breadcrumbs

You can test breadcrumb generation by checking the structure:

```python
# In your tests
breadcrumbs = get_breadcrumbs(page)
assert len(breadcrumbs) > 0
assert breadcrumbs[0]['title'] == 'Home'
assert breadcrumbs[-1]['is_current'] == True
```

## Migration from Template Logic

If you were using template logic before:

**Before (template logic):**
```jinja2
{% if page.ancestors %}
  {% for ancestor in page.ancestors | reverse %}
    {# Complex logic to detect section index, handle current page, etc. #}
  {% endfor %}
{% endif %}
```

**After (clean and simple):**
```jinja2
{% for item in get_breadcrumbs(page) %}
  {% if item.is_current %}
    {{ item.title }}
  {% else %}
    <a href="{{ item.url }}">{{ item.title }}</a>
  {% endif %}
{% endfor %}
```

## Related Functions

- `url_for(page)` - Generate URL for a page
- `absolute_url(url)` - Convert relative URL to absolute
- `page.ancestors` - Raw ancestor list (if you need custom logic)
- `page.parent` - Direct parent section

## Next Steps

- Check out other [template functions](../TEMPLATES.md)
- Learn about [navigation and sections](../ARCHITECTURE.md)
- Explore [SEO optimization](./SEO.md)

