---
title: Content Freshness
description: Show "new" badges and staleness warnings based on content age
weight: 100
draft: false
lang: en
tags:
- cookbook
- dates
- freshness
keywords:
- new badge
- stale content
- content age
- freshness indicator
category: cookbook
---

# Content Freshness

Display freshness indicators like "new" badges for recent content and staleness warnings for old content.

:::{note}
**Default Theme Approach**

Bengal's default theme uses **tags** for badges:
- Add `tags: [new]` for "✨ New" badge
- Add `tags: [featured]` for "⭐ Featured" badge

This recipe shows how to use `page.age_days` for **automatic** freshness detection based on publication date.
:::

## The Pattern

```jinja2
{% if page.age_days < 7 %}
<span class="badge badge-new">New</span>
{% elif page.age_months > 12 %}
<div class="notice notice-stale">
  This article is over a year old and may contain outdated information.
</div>
{% endif %}
```

## What's Happening

| Property/Filter | Purpose |
|-----------------|---------|
| `page.age_days` | Days since publication (computed, cached) |
| `page.age_months` | Calendar months since publication |
| `days_ago` filter | Calculate days from any date |
| `humanize_days` filter | "today", "yesterday", "3 days ago" |

## Variations

:::{tab-set}
:::{tab-item} Post List Badge

```jinja2
{% for post in posts %}
<article>
  <a href="{{ post.href }}">{{ post.title }}</a>

  {% if post.age_days < 7 %}
  <span class="badge-new">New</span>
  {% elif post.age_days < 30 %}
  <span class="badge-recent">Recent</span>
  {% endif %}
</article>
{% endfor %}
```

:::{/tab-item}
:::{tab-item} Humanized Date

```jinja2
<time datetime="{{ page.date | date_iso }}">
  {% if page.age_days == 0 %}
    Published today
  {% elif page.age_days == 1 %}
    Published yesterday
  {% elif page.age_days < 7 %}
    Published {{ page.age_days }} days ago
  {% elif page.age_days < 30 %}
    Published {{ (page.age_days / 7) | round | int }} weeks ago
  {% else %}
    Published {{ page.date | date('%B %d, %Y') }}
  {% endif %}
</time>
```

Or use the filter directly:

```jinja2
<time>Published {{ page.date | days_ago | humanize_days }}</time>
```

:::{/tab-item}
:::{tab-item} Staleness Warning

```jinja2
{% if page.age_months > 6 %}
<aside class="staleness-warning" role="alert">
  <strong>Heads up!</strong>
  This article was published {{ page.age_months }} months ago.
  {% if page.metadata.last_reviewed %}
    Last reviewed: {{ page.metadata.last_reviewed | date('%B %Y') }}
  {% else %}
    Some information may be outdated.
  {% endif %}
</aside>
{% endif %}
```

:::{/tab-item}
:::{tab-item} Tiered Styling

```jinja2
{% set freshness = 'fresh' if page.age_days < 30
                   else 'aging' if page.age_days < 180
                   else 'stale' %}

<article class="post freshness-{{ freshness }}">
  <h2>{{ page.title }}</h2>
  <time>{{ page.date | date('%B %d, %Y') }}</time>
</article>
```

:::{/tab-item}
:::{tab-item} Recently Updated

```jinja2
{# Show posts updated in the last 7 days #}
{% set recently_updated = site.pages
  | where('metadata.updated', none, 'ne')
  | sort_by('metadata.updated', reverse=true) %}

<section class="recently-updated">
  <h3>Recently Updated</h3>
  {% for post in recently_updated | limit(5) %}
    {% if post.metadata.updated | days_ago < 7 %}
    <a href="{{ post.href }}">
      {{ post.title }}
      <span class="updated-badge">Updated</span>
    </a>
    {% endif %}
  {% endfor %}
</section>
```

:::{/tab-item}
:::{tab-item} Review Reminder

For documentation sites that need regular review:

```jinja2
{% set needs_review = page.age_months > 6 and not page.metadata.reviewed_date %}

{% if needs_review %}
<div class="review-needed">
  <strong>Review needed:</strong>
  This page hasn't been reviewed in {{ page.age_months }} months.
</div>
{% endif %}
```

:::{/tab-item}
:::{/tab-set}

## Example CSS

```css
.badge-new {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  background: var(--color-success);
  color: white;
  border-radius: 4px;
}

.badge-recent {
  background: var(--color-info);
  color: white;
}

.staleness-warning {
  padding: 1rem;
  margin: 1rem 0;
  background: var(--color-warning-bg);
  border-left: 4px solid var(--color-warning);
  border-radius: 4px;
}

.freshness-fresh { border-left-color: var(--color-success); }
.freshness-aging { border-left-color: var(--color-warning); }
.freshness-stale { border-left-color: var(--color-muted); }
```

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/#date-filters) — Date filters
- [Template Functions Reference](/docs/reference/template-functions/#age-properties) — Age properties
:::
