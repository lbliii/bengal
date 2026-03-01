# RFC: Discourse Forum Integration

**Status**: Draft  
**Created**: 2026-01-17  
**Author**: AI Assistant  
**Related**: `rfc-docs-feedback-signals.md`

---

## Executive Summary

Add native Discourse forum integration to Bengal, enabling documentation sites to seamlessly connect with their community forums. This goes beyond a simple nav link—it provides embedded comments, topic linking, and "discuss this page" flows that turn static docs into community-driven resources.

### Why Discourse?

Discourse is the de facto standard for open-source project forums (Rust, Elixir, Hugo, Docker, etc.). Unlike Disqus:
- **Self-hosted or managed** - No third-party data harvesting
- **Full-featured** - Categories, tags, moderation, trust levels
- **API-first** - Rich JSON API for integration
- **Embed-native** - Built-in embedding system for static sites

### Proposed Features

| Feature | Complexity | Value |
|---------|------------|-------|
| Embedded comments | Low | High |
| "Discuss this page" links | Low | Medium |
| Topic preview directive | Medium | Medium |
| Latest topics widget | Medium | Low |

**Recommendation**: Start with **embedded comments** + **discuss links**. These cover 80% of use cases with minimal implementation effort.

---

## Feature 1: Embedded Comments (Primary)

### How Discourse Embedding Works

Discourse has a built-in embedding system. When enabled:

1. Site owner configures allowed embed hosts in Discourse admin
2. Static pages include a small JS snippet
3. When a user comments, Discourse creates a topic automatically
4. Comments appear inline on the static page

```html
<!-- Standard Discourse embed snippet -->
<div id="discourse-comments"></div>
<script type="text/javascript">
  DiscourseEmbed = {
    discourseUrl: 'https://forum.example.com/',
    discourseEmbedUrl: 'https://docs.example.com/guides/getting-started/'
  };
  (function() {
    var d = document.createElement('script');
    d.type = 'text/javascript';
    d.async = true;
    d.src = DiscourseEmbed.discourseUrl + 'javascripts/embed.js';
    document.getElementsByTagName('head')[0].appendChild(d);
  })();
</script>
```

### Proposed Bengal Integration

#### Site Configuration

```yaml
# bengal.yaml
discourse:
  enabled: true
  url: "https://forum.example.com"

  # Embedding settings
  embed:
    enabled: true
    # Which content types get comments (default: all)
    content_types: ["docs", "blog", "guides"]
    # Or use section paths
    sections:
      - docs/
      - blog/
    # Exclude specific paths
    exclude:
      - docs/api/  # API reference doesn't need comments
      - blog/archive/

  # Category mapping (optional - for "discuss this" links)
  categories:
    docs/: "documentation"
    blog/: "announcements"
    guides/: "tutorials"
```

#### Page Frontmatter

```yaml
---
title: Getting Started
discourse:
  embed: true          # Enable comments on this page
  # OR
  embed: false         # Disable comments on this page
  # OR
  topic_id: 1234       # Link to existing topic instead of auto-create
---
```

#### Template Integration

Create `partials/discourse-comments.html`:

```html
{% if discourse.embed_enabled and page.discourse_embed_enabled %}
<section class="discourse-comments" aria-label="Discussion">
  <h2 class="discourse-comments__heading">
    {{ discourse.heading | default("Join the Discussion") }}
  </h2>
  <div id="discourse-comments"></div>
  <noscript>
    <p>
      Comments powered by <a href="{{ discourse.url }}">our community forum</a>.
      <a href="{{ page.discourse_topic_url }}">View this discussion →</a>
    </p>
  </noscript>
</section>

<script type="text/javascript">
  DiscourseEmbed = {
    discourseUrl: '{{ discourse.url }}/',
    {% if page.discourse_topic_id %}
    topicId: {{ page.discourse_topic_id }},
    {% else %}
    discourseEmbedUrl: '{{ page.canonical_url }}'
    {% end %}
  };
  (function() {
    var d = document.createElement('script');
    d.type = 'text/javascript';
    d.async = true;
    d.src = DiscourseEmbed.discourseUrl + 'javascripts/embed.js';
    document.getElementsByTagName('head')[0].appendChild(d);
  })();
</script>
{% end %}
```

Include in `layouts/docs/single.html`:

```html
{% block content %}
<article>
  {{ page.content }}
</article>

{% include "partials/discourse-comments.html" %}
{% end %}
```

---

## Feature 2: "Discuss This Page" Links

For pages without embedded comments, provide a link to discuss on the forum.

### Automatic Topic URL Generation

```python
def get_discourse_topic_url(page: PageLike, config: DiscourseConfig) -> str:
    """Generate URL to discuss this page on Discourse.

    If topic_id is set in frontmatter, link directly.
    Otherwise, generate a new topic URL with pre-filled title.
    """
    if page.discourse_topic_id:
        return f"{config.url}/t/{page.discourse_topic_id}"

    # Pre-fill new topic
    category = config.get_category_for_path(page.path)
    title = f"Discussion: {page.title}"
    body = f"Discussing [{page.title}]({page.canonical_url})"

    return (
        f"{config.url}/new-topic?"
        f"category={category}&"
        f"title={quote(title)}&"
        f"body={quote(body)}"
    )
```

### Template Helper

```html
{# In page template #}
{% if discourse.enabled and not page.discourse_embed_enabled %}
<aside class="discuss-link">
  <a href="{{ page | discourse_topic_url }}"
     class="discuss-link__button"
     target="_blank"
     rel="noopener">
    {{ icon("message-circle") }}
    Discuss this page
  </a>
</aside>
{% end %}
```

---

## Feature 3: Topic Preview Directive (Optional)

Embed a preview card for a specific Discourse topic.

### Syntax

```markdown
:::{discourse-topic} 1234
:show-replies: 3
:::
```

### Output

```html
<aside class="discourse-topic-preview" data-topic-id="1234">
  <h3 class="discourse-topic-preview__title">
    <a href="https://forum.example.com/t/1234">How do I configure SSO?</a>
  </h3>
  <div class="discourse-topic-preview__meta">
    <span class="reply-count">24 replies</span>
    <span class="last-activity">Active 2h ago</span>
  </div>
  <div class="discourse-topic-preview__replies">
    <!-- First 3 replies rendered -->
  </div>
</aside>
```

### Implementation Notes

This requires either:
- **Build-time fetch**: Call Discourse API during build (adds build dependency)
- **Client-side fetch**: JS fetches topic data (no build dependency, but slower)

**Recommendation**: Client-side fetch with skeleton loading, similar to link previews.

---

## Feature 4: Latest Topics Widget (Optional)

Show recent forum activity on homepage or sidebar.

### Syntax

```markdown
:::{discourse-latest}
:category: documentation
:limit: 5
:style: compact
:::
```

### Implementation

Client-side fetch from `/latest.json` (Discourse's public API):

```javascript
// Fetch latest topics
const response = await fetch(`${discourseUrl}/c/${category}.json`);
const data = await response.json();
const topics = data.topic_list.topics.slice(0, limit);
```

**Recommendation**: Lower priority. Most sites just want comments.

---

## Implementation Plan

### Phase 1: Embedded Comments (1-2 hours)

1. **Add config type** (`bengal/config/types.py`)

```python
class DiscourseEmbedConfig(TypedDict, total=False):
    """Discourse embed settings."""
    enabled: bool
    content_types: list[str]
    sections: list[str]
    exclude: list[str]

class DiscourseConfig(TypedDict, total=False):
    """Discourse integration configuration."""
    enabled: bool
    url: str
    embed: DiscourseEmbedConfig
    categories: dict[str, str]
    heading: str
```

2. **Add defaults** (`bengal/config/defaults.py`)

```python
"discourse": {
    "enabled": False,
    "url": "",
    "embed": {
        "enabled": True,
        "content_types": [],
        "sections": [],
        "exclude": [],
    },
    "categories": {},
    "heading": "Join the Discussion",
},
```

3. **Add template context** (`bengal/rendering/template_context.py`)
   - Expose `discourse` config to templates
   - Add `page.discourse_embed_enabled` computed property

4. **Create template partial** (`themes/default/templates/partials/discourse-comments.html`)

5. **Include in doc layouts** (optional - users can add manually)

### Phase 2: Discuss Links (30 min)

1. **Add Jinja filter** `discourse_topic_url`
2. **Add CSS** for `.discuss-link` component

### Phase 3: Topic Directive (Optional - 2-3 hours)

1. **Create directive** (`bengal/directives/discourse.py`)
2. **Add client-side JS** for topic preview loading
3. **Add CSS** for `.discourse-topic-preview`

---

## Files to Change

| File | Change |
|------|--------|
| `bengal/config/types.py` | Add `DiscourseConfig`, `DiscourseEmbedConfig` |
| `bengal/config/defaults.py` | Add `discourse` defaults |
| `bengal/rendering/template_context.py` | Expose discourse config |
| `themes/default/templates/partials/discourse-comments.html` | **New file** |
| `themes/default/assets/css/components/discourse.css` | **New file** |
| `bengal/rendering/template_functions/filters.py` | Add `discourse_topic_url` filter |

### Optional (Phase 3)
| File | Change |
|------|--------|
| `bengal/directives/discourse.py` | **New file** - Topic directive |
| `themes/default/assets/js/enhancements/discourse.js` | **New file** - Client-side fetch |

---

## User Experience

### Minimal Setup (2 lines)

```yaml
# bengal.yaml
discourse:
  url: "https://forum.example.com"
```

Comments appear on all doc pages. That's it.

### Full Control

```yaml
discourse:
  url: "https://forum.example.com"
  embed:
    sections:
      - docs/guides/
      - blog/
    exclude:
      - docs/api/
  categories:
    docs/guides/: tutorials
    blog/: announcements
  heading: "Questions? Ask the community!"
```

### Per-Page Override

```yaml
---
title: Quick Reference
discourse:
  embed: false  # No comments on this cheatsheet
---
```

---

## Security Considerations

1. **XSS Prevention**: Discourse URL must be validated (HTTPS, no query params)
2. **CSP Headers**: May need to allow `frame-src` and `script-src` for Discourse domain
3. **No API Keys**: Embedding uses public Discourse features (no secrets in config)

---

## Accessibility

1. **Semantic heading**: Comments section has `<h2>` heading
2. **ARIA landmark**: `aria-label="Discussion"` on comments section
3. **Noscript fallback**: Link to forum for JS-disabled users
4. **Focus management**: Focus moves to comments when navigating to `#discourse-comments`

---

## Alternatives Considered

### 1. Disqus Integration
- ❌ Third-party data collection
- ❌ Ads on free tier
- ❌ Less control over moderation
- ✅ Easier setup (no self-hosting)

**Decision**: Discourse aligns better with open-source values and Bengal's target audience.

### 2. GitHub Discussions
- ❌ Requires GitHub account
- ❌ Less feature-rich than Discourse
- ✅ Zero hosting cost
- ✅ Familiar to developers

**Decision**: Could be a future addition. Discourse is more universal.

### 3. utterances (GitHub Issues)
- ❌ Limited features (no threading, no moderation)
- ✅ Free, lightweight
- ✅ Familiar GitHub auth

**Decision**: Too limited for documentation with active communities.

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Setup time | < 5 minutes with existing Discourse |
| Config lines | 2-10 lines typical |
| Page load impact | < 50ms (async script load) |
| Accessibility | WCAG 2.1 AA compliant |

---

## Open Questions

1. **Should comments be opt-in or opt-out by default?**
   - Current proposal: Opt-in via `discourse.embed.sections` or `discourse.embed.content_types`
   - Alternative: Enable everywhere, opt-out via `exclude`

2. **Build-time topic validation?**
   - Should we validate `topic_id` references exist during build?
   - Adds build-time dependency on Discourse API availability

3. **Theme support?**
   - Should comments inherit site theme colors?
   - Discourse embed has limited styling options

---

## References

- [Discourse Embedding Documentation](https://meta.discourse.org/t/embedding-discourse-comments-via-javascript/31963)
- [Discourse API Documentation](https://docs.discourse.org/)
- [Hugo Discourse Integration](https://gohugo.io/content-management/comments/#discourse) (reference implementation)
