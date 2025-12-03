---
title: Add RSS Feed
description: Generate an RSS feed for your Bengal site
weight: 20
draft: false
lang: en
tags: [recipe, rss, feed, syndication]
keywords: [rss, feed, atom, syndication, blog]
category: recipe
---

# Add RSS Feed

Generate an RSS feed for your blog or news section.

## Time Required

⏱️ 5 minutes

## What You'll Build

- RSS 2.0 feed at `/feed.xml`
- Auto-discovery link in HTML head
- Latest posts included automatically

## Step 1: Enable RSS in Config

Add to your `bengal.toml`:

```toml
[build.outputs]
rss = true

[rss]
title = "My Site RSS Feed"
description = "Latest posts from my site"
language = "en-us"
limit = 20  # Number of items in feed
sections = ["blog", "news"]  # Sections to include
```

## Step 2: Add Auto-Discovery Link

Add to your base template's `<head>`:

```html
<!-- templates/base.html -->
<head>
  <!-- ... other head content ... -->
  
  <link rel="alternate" type="application/rss+xml" 
        title="{{ site.title }} RSS Feed" 
        href="{{ site.baseurl }}/feed.xml">
</head>
```

## Step 3: Build and Verify

```bash
bengal build
```

Check `public/feed.xml` exists and contains your posts.

## Customizing the Feed

### Custom Feed Template

Override the default RSS template:

```xml
<!-- templates/rss.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{{ site.title }}</title>
    <link>{{ site.baseurl }}</link>
    <description>{{ site.description }}</description>
    <language>{{ site.language }}</language>
    <lastBuildDate>{{ now | date("%a, %d %b %Y %H:%M:%S %z") }}</lastBuildDate>
    <atom:link href="{{ site.baseurl }}/feed.xml" rel="self" type="application/rss+xml"/>
    
    {% for page in site.pages | where('section', 'blog') | sort_by('date', reverse=true) | limit(20) %}
    <item>
      <title>{{ page.title | escape }}</title>
      <link>{{ site.baseurl }}{{ page.url }}</link>
      <description>{{ page.description | escape }}</description>
      <pubDate>{{ page.date | date("%a, %d %b %Y %H:%M:%S %z") }}</pubDate>
      <guid isPermaLink="true">{{ site.baseurl }}{{ page.url }}</guid>
    </item>
    {% endfor %}
  </channel>
</rss>
```

### Multiple Feeds

Create section-specific feeds:

```toml
# bengal.toml
[rss.feeds.blog]
path = "/blog/feed.xml"
sections = ["blog"]

[rss.feeds.news]
path = "/news/feed.xml"
sections = ["news"]
```

## Result

Your site now has:
- ✅ RSS feed at `/feed.xml`
- ✅ Auto-discovery for RSS readers
- ✅ Latest posts automatically included

## See Also

- [Configuration](/docs/building/configuration/) — More output options
- [Deployment](/docs/building/deployment/) — Deploy your site

