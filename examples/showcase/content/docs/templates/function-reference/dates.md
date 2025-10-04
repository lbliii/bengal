---
title: "Date Functions"
description: "3 date and time functions for formatting and displaying dates"
date: 2025-10-04
weight: 4
tags: ["templates", "functions", "dates", "time", "formatting"]
toc: true
---

# Date Functions

Bengal provides **3 date and time functions** for formatting dates in human-readable and machine-readable formats. Essential for blog posts, timestamps, and RSS feeds.

---

## 📚 Function Overview

| Function | Purpose | Example |
|----------|---------|---------|
| `time_ago` | Human-readable relative time | `{{/* date | time_ago */}}` → "2 days ago" |
| `date_iso` | ISO 8601 format | `{{ date | date_iso }}` → "2025-10-04T14:30:00" |
| `date_rfc822` | RFC 822 format (RSS) | `{{ date | date_rfc822 }}` → "Fri, 04 Oct 2025..." |

---

## ⏰ time_ago

Convert date to human-readable relative time format.

### Signature

```jinja2
{{/* date | time_ago */}}
```

### Parameters

- **date** (datetime|str): Date to convert (datetime object or ISO string)

### Returns

Human-readable relative time string (e.g., "2 days ago", "5 hours ago").

### Examples

#### Basic Usage

```jinja2
{# Show when post was published #}
<time>Published {{/* post.date | time_ago */}}</time>
```

**Outputs:**
- "just now" (< 1 minute)
- "5 minutes ago"
- "3 hours ago"
- "2 days ago"
- "3 months ago"
- "1 year ago"

#### Blog Post Meta

```jinja2
<article>
  <h2>{{ post.title }}</h2>
  <div class="meta">
    <span class="author">By {{ post.author }}</span>
    <span class="date">{{/* post.date | time_ago */}}</span>
    <span class="reading-time">{{ post.content | reading_time }} min read</span>
  </div>
</article>
```

#### Comment Timestamps

```jinja2
{% for comment in comments %}
  <div class="comment">
    <div class="comment-meta">
      <strong>{{ comment.author }}</strong>
      <time>{{/* comment.created_at | time_ago */}}</time>
    </div>
    <div class="comment-body">{{ comment.text }}</div>
  </div>
{% endfor %}
```

#### Activity Feed

```jinja2
<ul class="activity-feed">
  {% for activity in recent_activity %}
    <li>
      <strong>{{ activity.user }}</strong> {{ activity.action }}
      <time>{{/* activity.timestamp | time_ago */}}</time>
    </li>
  {% endfor %}
</ul>
```

**Example output:**
- "John Smith commented just now"
- "Jane Doe posted 15 minutes ago"
- "Admin updated 3 hours ago"

### Time Ranges

```{example} Time Ago Ranges

**< 1 minute:**
```jinja2
{{/* date | time_ago */}}  {# "just now" #}
```

**1-59 minutes:**
```jinja2
{{/* date | time_ago */}}  {# "15 minutes ago" #}
```

**1-23 hours:**
```jinja2
{{/* date | time_ago */}}  {# "5 hours ago" #}
```

**1-29 days:**
```jinja2
{{/* date | time_ago */}}  {# "12 days ago" #}
```

**1-11 months:**
```jinja2
{{/* date | time_ago */}}  {# "3 months ago" #}
```

**12+ months:**
```jinja2
{{/* date | time_ago */}}  {# "2 years ago" #}
```
```

### Accessibility with Actual Date

```{tip} Include Machine-Readable Date
For accessibility and SEO, include the actual date in `datetime` attribute:

```jinja2
<time datetime="{{ post.date | date_iso }}">
  {{/* post.date | time_ago */}}
</time>
```

**Result:**
```html
<time datetime="2025-10-02T14:30:00">
  2 days ago
</time>
```

Benefits:
- Screen readers can announce the actual date
- Browsers can format based on user locale
- Search engines know the exact date
```

### Combine with Fallback

```{example} Smart Date Display

```jinja2
{# Show relative time for recent posts, exact date for old posts #}
{% if (now - post.date).days < 7 %}
  <time datetime="{{ post.date | date_iso }}">
    {{/* post.date | time_ago */}}
  </time>
{% else %}
  <time datetime="{{ post.date | date_iso }}">
    {{ post.date.strftime('%B %d, %Y') }}
  </time>
{% endif %}
```

**Output:**
- Recent: "2 days ago"
- Old: "January 15, 2024"
```

---

## 📅 date_iso

Format date as ISO 8601 string.

### Signature

```jinja2
{{ date | date_iso }}
```

### Parameters

- **date** (datetime|str): Date to format

### Returns

ISO 8601 formatted date string (e.g., `"2025-10-04T14:30:00"`).

### Examples

#### Semantic HTML Time Tag

```jinja2
{# Machine-readable date for HTML5 #}
<time datetime="{{ post.date | date_iso }}">
  {{ post.date.strftime('%B %d, %Y') }}
</time>
```

**Output:**
```html
<time datetime="2025-10-04T14:30:00">
  October 4, 2025
</time>
```

#### JSON API Output

```jinja2
{# Export data as JSON #}
{
  "title": "{{ post.title }}",
  "date": "{{ post.date | date_iso }}",
  "author": "{{ post.author }}"
}
```

**Output:**
```json
{
  "title": "My Post",
  "date": "2025-10-04T14:30:00",
  "author": "John Doe"
}
```

#### Schema.org Structured Data

```jinja2
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "{{ post.title }}",
  "datePublished": "{{ post.date | date_iso }}",
  "dateModified": "{{ post.modified | date_iso }}",
  "author": {
    "@type": "Person",
    "name": "{{ post.author }}"
  }
}
</script>
```

#### Sitemap Generation

```jinja2
{# sitemap.xml #}
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  {% for page in pages %}
    <url>
      <loc>{{ page.url | absolute_url }}</loc>
      <lastmod>{{ page.date | date_iso }}</lastmod>
    </url>
  {% endfor %}
</urlset>
```

### ISO 8601 Format

```{note} Standard Format
ISO 8601 is the international standard for date/time:

**Format:** `YYYY-MM-DDTHH:MM:SS`

**Examples:**
- `2025-10-04T14:30:00` (no timezone)
- `2025-10-04T14:30:00+00:00` (UTC)
- `2025-10-04T14:30:00-05:00` (EST)

**Why use it?**
- ✅ Unambiguous (no MM/DD vs DD/MM confusion)
- ✅ Sortable (string sort = chronological sort)
- ✅ Parseable by all languages
- ✅ Required for HTML5 `<time>` tags
```

---

## 📡 date_rfc822

Format date as RFC 822 string for RSS feeds.

### Signature

```jinja2
{{ date | date_rfc822 }}
```

### Parameters

- **date** (datetime|str): Date to format

### Returns

RFC 822 formatted date string (e.g., `"Fri, 04 Oct 2025 14:30:00 +0000"`).

### Examples

#### RSS Feed

```jinja2
{# rss.xml template #}
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{{ site.title }}</title>
    <link>{{ site.baseurl }}</link>
    <description>{{ site.description }}</description>
    <lastBuildDate>{{ now | date_rfc822 }}</lastBuildDate>
    
    {% for post in recent_posts %}
      <item>
        <title>{{ post.title }}</title>
        <link>{{ post.url | absolute_url }}</link>
        <description>{{ post.content | strip_html | truncatewords(50) }}</description>
        <pubDate>{{ post.date | date_rfc822 }}</pubDate>
        <guid>{{ post.url | absolute_url }}</guid>
      </item>
    {% endfor %}
  </channel>
</rss>
```

#### Atom Feed

```jinja2
{# atom.xml template #}
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{{ site.title }}</title>
  <link href="{{ site.baseurl }}"/>
  <updated>{{ now | date_iso }}</updated>
  
  {% for post in recent_posts %}
    <entry>
      <title>{{ post.title }}</title>
      <link href="{{ post.url | absolute_url }}"/>
      <updated>{{ post.date | date_iso }}</updated>
      <published>{{ post.date | date_iso }}</published>
      <content type="html">{{ post.content }}</content>
    </entry>
  {% endfor %}
</feed>
```

### RFC 822 Format

```{note} Email-Style Date Format
RFC 822 is used in:
- RSS feeds (`<pubDate>`)
- Email headers
- HTTP headers
- Some APIs

**Format:** `Ddd, DD Mon YYYY HH:MM:SS ±HHMM`

**Example:** `"Fri, 04 Oct 2025 14:30:00 +0000"`

**Parts:**
- `Fri` - Day of week (3 letters)
- `04` - Day of month (2 digits)
- `Oct` - Month (3 letters)
- `2025` - Year (4 digits)
- `14:30:00` - Time (HH:MM:SS)
- `+0000` - Timezone offset
```

---

## 🎯 Common Patterns

### Complete Blog Post Metadata

```jinja2
<article class="blog-post">
  <header>
    <h1>{{ post.title }}</h1>
    
    <div class="post-meta">
      {# Author #}
      <span class="author">
        By {{ post.author }}
      </span>
      
      {# Published date (human-readable) #}
      <time datetime="{{ post.date | date_iso }}">
        {{/* post.date | time_ago */}}
      </time>
      
      {# Reading time #}
      <span class="reading-time">
        {{ post.content | reading_time }} min read
      </span>
    </div>
  </header>
  
  <div class="post-content">
    {{ post.content | safe }}
  </div>
  
  <footer class="post-footer">
    {% if post.modified and post.modified != post.date %}
      <p class="updated">
        Last updated
        <time datetime="{{ post.modified | date_iso }}">
          {{/* post.modified | time_ago */}}
        </time>
      </p>
    {% endif %}
  </footer>
</article>
```

### Archive Page by Date

```jinja2
{# Group posts by year and month #}
{% set by_year = posts | group_by('year') %}

<div class="archive">
  {% for year in by_year.keys() | sort(reverse=true) %}
    <section class="year-section">
      <h2>{{ year }}</h2>
      
      {% set year_posts = by_year[year] | sort_by('date', reverse=true) %}
      {% for post in year_posts %}
        <article class="archive-item">
          <time datetime="{{ post.date | date_iso }}">
            {{ post.date.strftime('%b %d') }}
          </time>
          <a href="{{ post.url }}">{{ post.title }}</a>
        </article>
      {% endfor %}
    </section>
  {% endfor %}
</div>
```

### Timestamps Everywhere

```jinja2
{# Recent activity with consistent formatting #}
<ul class="timeline">
  {% for item in activity %}
    <li class="timeline-item">
      <div class="timeline-marker"></div>
      <div class="timeline-content">
        <h3>{{ item.title }}</h3>
        <p>{{ item.description }}</p>
        <time datetime="{{ item.timestamp | date_iso }}" 
              title="{{ item.timestamp.strftime('%B %d, %Y at %I:%M %p') }}">
          {{/* item.timestamp | time_ago */}}
        </time>
      </div>
    </li>
  {% endfor %}
</ul>
```

---

## 📊 Date Display Strategies

Different use cases call for different date formats:

```{tabs}
:id: date-strategies

### Tab: Relative (Recent)

**For recent content:**
```jinja2
<time>{{/* post.date | time_ago */}}</time>
```

**Best for:**
- Recent posts (< 1 week)
- Comments
- Activity feeds
- Social media style

**Output:** "2 hours ago", "yesterday"

### Tab: Absolute (Archive)

**For older content:**
```jinja2
<time>{{ post.date.strftime('%B %d, %Y') }}</time>
```

**Best for:**
- Archive pages
- Old posts
- Historical content
- Legal documents

**Output:** "January 15, 2024"

### Tab: Hybrid

**Best of both:**
```jinja2
{% if (now - post.date).days < 7 %}
  {{/* post.date | time_ago */}}
{% else %}
  {{ post.date.strftime('%b %d, %Y') }}
{% endif %}
```

**Best for:**
- Blog feeds
- Mixed content ages
- User-friendly display

**Output:**
- Recent: "3 days ago"
- Old: "Jan 15, 2024"

### Tab: Machine-Readable

**For data/SEO:**
```jinja2
<time datetime="{{ post.date | date_iso }}">
  {{/* post.date | time_ago */}}
</time>
```

**Best for:**
- All cases (most flexible)
- SEO requirements
- Accessibility
- API output

**HTML:**
```html
<time datetime="2025-10-04T14:30:00">
  2 days ago
</time>
```
```

---

## 🌍 Internationalization Note

```{warning} Current Limitation
The date functions currently output in English only:

- "2 days ago" (not "il y a 2 jours")
- "Friday" (not "Vendredi")

**Workaround for i18n:**
Use Python's strftime with locale:

```jinja2
{% set formatted = post.date.strftime('%B %d, %Y') %}
```

Or wait for Bengal v2.0 which will include full i18n support!
```

---

## 📚 Related Functions

- **[String Functions](strings.md)** - truncatewords, excerpt
- **[SEO Functions](seo.md)** - canonical_url, meta_description
- **[Math Functions](math.md)** - Calculations with timestamps

---

## 💡 Best Practices

```{success} Always Include datetime Attribute

**Good:**
```jinja2
<time datetime="{{ post.date | date_iso }}">
  {{/* post.date | time_ago */}}
</time>
```

**Why:**
- Accessibility (screen readers)
- SEO (search engines understand exact date)
- Browser features (date formatting)
- Future-proof
```

```{tip} Pick the Right Format

**time_ago:** Casual, recent content
```jinja2
"Posted {{/* post.date | time_ago */}}"  {# "Posted 2 hours ago" #}
```

**date_iso:** Machine-readable, APIs, JSON
```jinja2
"published": "{{ post.date | date_iso }}"  {# ISO format #}
```

**date_rfc822:** RSS feeds only
```jinja2
<pubDate>{{ post.date | date_rfc822 }}</pubDate>
```
```

```{note} Timezone Handling
Bengal handles timezones automatically:

- UTC dates: Preserves timezone
- Naive dates: Treats as local time
- Comparison: Uses consistent timezone

For best results, store dates in UTC!
```

```{warning} Don't Hardcode Date Strings
**Bad:**
```jinja2
Published on 10/04/2025  {# Ambiguous! MM/DD or DD/MM? #}
```

**Good:**
```jinja2
<time datetime="{{ post.date | date_iso }}">
  {{ post.date.strftime('%B %d, %Y') }}
</time>
```

Let the date functions handle formatting!
```

---

## 🎓 Advanced Example

Complete date handling for a blog:

```jinja2
{# _post_meta.html partial #}
<div class="post-metadata">
  {# Primary date display #}
  <div class="date-primary">
    {% if (now - post.date).days < 30 %}
      {# Recent: Show relative time #}
      <time datetime="{{ post.date | date_iso }}" 
            title="{{ post.date.strftime('%B %d, %Y at %I:%M %p') }}">
        {{/* post.date | time_ago */}}
      </time>
    {% else %}
      {# Older: Show formatted date #}
      <time datetime="{{ post.date | date_iso }}">
        {{ post.date.strftime('%B %d, %Y') }}
      </time>
    {% endif %}
  </div>
  
  {# Updated indicator #}
  {% if post.modified and (post.modified - post.date).days > 0 %}
    <div class="date-updated">
      <span class="label">Updated:</span>
      <time datetime="{{ post.modified | date_iso }}" 
            title="{{ post.modified.strftime('%B %d, %Y at %I:%M %p') }}">
        {{/* post.modified | time_ago */}}
      </time>
    </div>
  {% endif %}
  
  {# Structured data for SEO #}
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "datePublished": "{{ post.date | date_iso }}",
    "dateModified": "{{ post.modified | date_iso }}"
  }
  </script>
</div>
```

---

**Module:** `bengal.rendering.template_functions.dates`  
**Functions:** 3  
**Last Updated:** October 4, 2025

