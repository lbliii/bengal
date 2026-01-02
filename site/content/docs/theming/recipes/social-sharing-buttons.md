---
title: Social Sharing Buttons
description: Add share buttons for Twitter, LinkedIn, Facebook, and more
weight: 80
draft: false
lang: en
tags:
- cookbook
- social
- sharing
keywords:
- share buttons
- twitter share
- linkedin share
- social media
category: cookbook
---

# Social Sharing Buttons

Add share buttons to let readers share your content on social platforms.

:::{note}
**Built into Default Theme**

Bengal's default theme includes social sharing in blog posts:
- **Social share buttons** in blog post footers
- Uses `share_url()` template functions
- Includes Twitter, LinkedIn, Facebook, Reddit, Email, and copy-link

This recipe shows how to customize placement or add additional platforms.
:::

## The Pattern

```kida
<div class="share-buttons">
  <span>Share:</span>

  <a href="{{ share_url('twitter', page) }}" target="_blank" rel="noopener">
    Twitter
  </a>

  <a href="{{ share_url('linkedin', page) }}" target="_blank" rel="noopener">
    LinkedIn
  </a>

  <a href="{{ share_url('facebook', page) }}" target="_blank" rel="noopener">
    Facebook
  </a>
</div>
```

## What's Happening

| Function | Purpose |
|----------|---------|
| `share_url(platform, page)` | Generates share URL for any platform |
| `twitter_share_url(url, text, via)` | Twitter with optional via attribution |
| `linkedin_share_url(url, title)` | LinkedIn share |
| `email_share_url(url, subject, body)` | Email with pre-filled subject and body |
| `reddit_share_url(url, title)` | Reddit submit URL |
| `hackernews_share_url(url, title)` | Hacker News submit URL |
| `mastodon_share_text(url, text)` | Returns share text (not URL) for Mastodon |

**Supported Platforms:** `twitter`, `linkedin`, `facebook`, `reddit`, `hackernews`, `email`, `mastodon`

## Variations

:::{tab-set}
:::{tab-item} With Icons

```kida
<div class="share-buttons">
  <a href="{{ share_url('twitter', page) }}" aria-label="Share on Twitter">
    <svg><!-- Twitter icon --></svg>
  </a>
  <a href="{{ share_url('linkedin', page) }}" aria-label="Share on LinkedIn">
    <svg><!-- LinkedIn icon --></svg>
  </a>
  <a href="{{ share_url('reddit', page) }}" aria-label="Share on Reddit">
    <svg><!-- Reddit icon --></svg>
  </a>
  <a href="{{ share_url('hackernews', page) }}" aria-label="Share on Hacker News">
    <svg><!-- HN icon --></svg>
  </a>
</div>
```

:::{/tab-item}
:::{tab-item} Twitter via Attribution

```kida
<a href="{{ twitter_share_url(page.absolute_href, page.title, via='yourblog') }}">
  Tweet this
</a>
```

This adds `via @yourblog` to the tweet.

:::{/tab-item}
:::{tab-item} Full Share Bar

```kida
<aside class="share-bar">
  <span class="share-label">Share this article</span>

  <div class="share-links">
    <a href="{{ twitter_share_url(page.absolute_href, page.title) }}"
       class="share-twitter" target="_blank" rel="noopener">
      <i class="icon-twitter"></i>
      <span>Twitter</span>
    </a>

    <a href="{{ linkedin_share_url(page.absolute_href, page.title) }}"
       class="share-linkedin" target="_blank" rel="noopener">
      <i class="icon-linkedin"></i>
      <span>LinkedIn</span>
    </a>

    <a href="{{ reddit_share_url(page.absolute_href, page.title) }}"
       class="share-reddit" target="_blank" rel="noopener">
      <i class="icon-reddit"></i>
      <span>Reddit</span>
    </a>

    <a href="{{ hackernews_share_url(page.absolute_href, page.title) }}"
       class="share-hn" target="_blank" rel="noopener">
      <i class="icon-hackernews"></i>
      <span>HN</span>
    </a>

    <a href="{{ email_share_url(page.absolute_href, page.title) }}"
       class="share-email">
      <i class="icon-email"></i>
      <span>Email</span>
    </a>
  </div>
</aside>
```

:::{/tab-item}
:::{tab-item} Copy Link Button

Add a "copy link" button alongside social shares:

```kida
<div class="share-buttons">
  <a href="{{ share_url('twitter', page) }}">Twitter</a>
  <a href="{{ share_url('linkedin', page) }}">LinkedIn</a>

  <button class="copy-link" data-url="{{ page.absolute_href }}">
    Copy Link
  </button>
</div>

<script>
document.querySelector('.copy-link').addEventListener('click', function() {
  navigator.clipboard.writeText(this.dataset.url);
  this.textContent = 'Copied!';
  setTimeout(() => this.textContent = 'Copy Link', 2000);
});
</script>
```

:::{/tab-item}
:::{tab-item} Mastodon

Mastodon requires users to paste into their instance, so we generate share text:

```kida
<button class="share-mastodon"
        data-text="{{ mastodon_share_text(page.title, page.absolute_href) }}">
  Share on Mastodon
</button>

<script>
document.querySelector('.share-mastodon').addEventListener('click', function() {
  navigator.clipboard.writeText(this.dataset.text);
  alert('Copied! Paste this into your Mastodon instance.');
});
</script>
```

:::{/tab-item}
:::{tab-item} Floating Bar

```kida
<aside class="share-floating">
  <a href="{{ share_url('twitter', page) }}"><i class="icon-twitter"></i></a>
  <a href="{{ share_url('linkedin', page) }}"><i class="icon-linkedin"></i></a>
  <a href="{{ share_url('facebook', page) }}"><i class="icon-facebook"></i></a>
</aside>
```

:::{/tab-item}
:::{/tab-set}

## Example CSS

```css
.share-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin: 2rem 0;
}

.share-buttons a {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.share-twitter { background: #1da1f2; color: white; }
.share-linkedin { background: #0077b5; color: white; }
.share-reddit { background: #ff4500; color: white; }
.share-facebook { background: #1877f2; color: white; }

.share-buttons a:hover {
  filter: brightness(1.1);
}

/* Floating variant */
.share-floating {
  position: fixed;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.share-floating a {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--bg-secondary);
  color: var(--text);
}
```

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/#social-sharing) — All share functions with parameters
- [URL Functions](/docs/reference/template-functions/#url-functions) — `absolute_href` and other URL helpers
:::
