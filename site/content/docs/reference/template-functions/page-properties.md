---
title: Page & Section Properties
description: Properties available on page and section objects
weight: 60
type: doc
tags:
- reference
- properties
- pages
- sections
category: reference
---

# Page Properties

These properties are available on all page objects.

## Author Properties

Access structured author information from frontmatter.

```kida
{# Single author #}
{% if page.author %}
<div class="author">
  {% if page.author.avatar %}
  <img src="{{ page.author.avatar }}" alt="{{ page.author.name }}">
  {% end %}
  <span>{{ page.author.name }}</span>
  {% if page.author.twitter %}
  <a href="https://twitter.com/{{ page.author.twitter }}">@{{ page.author.twitter }}</a>
  {% end %}
</div>
{% end %}

{# Multiple authors #}
{% for author in page.authors %}
<span class="author">{{ author.name }}</span>
{% end %}
```

**Author fields:** `name`, `email`, `bio`, `avatar`, `url`, `twitter`, `github`, `linkedin`, `mastodon`, `social` (dict)

## Series Properties

For multi-part content like tutorials.

```kida
{% if page.series %}
<nav class="series-nav">
  <h4>{{ page.series.name }}</h4>
  <p>Part {{ page.series.part }} of {{ page.series.total }}</p>

  {% if page.prev_in_series %}
  <a href="{{ page.prev_in_series.href }}">← {{ page.prev_in_series.title }}</a>
  {% end %}

  {% if page.next_in_series %}
  <a href="{{ page.next_in_series.href }}">{{ page.next_in_series.title }} →</a>
  {% end %}
</nav>
{% end %}
```

**Series frontmatter:**
```yaml
series:
  name: "Building a Blog with Bengal"
  part: 2
  total: 5
```

## Age Properties

Content age as computed properties.

```kida
{# Days since publication #}
{% if page.age_days < 7 %}
<span class="badge">New</span>
{% elif page.age_months > 6 %}
<div class="notice">This article is {{ page.age_months }} months old.</div>
{% end %}
```

---

# Section Properties

These properties are available on section objects.

## post_count

Count of pages in a section.

```kida
<span>{{ section.post_count }} articles</span>
<span>{{ section.post_count_recursive }} total in all subsections</span>
```

## featured_posts

Get featured pages from a section.

```kida
{% for post in section.featured_posts(3) %}
<article class="featured">
  <h2>{{ post.title }}</h2>
</article>
{% end %}
```

## Section Statistics

```kida
<div class="section-stats">
  <span>{{ section.word_count | intcomma }} words</span>
  <span>{{ section.total_reading_time }} min total reading time</span>
</div>
```

---

# Social Sharing

Generate share URLs for social platforms.

## share_url

Generate share URL for any supported platform.

```kida
<a href="{{ share_url('twitter', page) }}">Share on Twitter</a>
<a href="{{ share_url('linkedin', page) }}">Share on LinkedIn</a>
<a href="{{ share_url('facebook', page) }}">Share on Facebook</a>
<a href="{{ share_url('reddit', page) }}">Share on Reddit</a>
<a href="{{ share_url('hackernews', page) }}">Share on HN</a>
```

**Supported Platforms:** `twitter`, `linkedin`, `facebook`, `reddit`, `hackernews` (or `hn`), `email`, `mastodon`

## Individual Share Functions

For more control, use platform-specific functions:

```kida
{# Twitter with via attribution #}
<a href="{{ twitter_share_url(page.absolute_href, page.title, via='myblog') }}">
  Tweet this
</a>

{# Reddit #}
<a href="{{ reddit_share_url(page.absolute_href, page.title) }}">
  Submit to Reddit
</a>

{# Email #}
<a href="{{ email_share_url(page.absolute_href, page.title) }}">
  Share via Email
</a>
```
