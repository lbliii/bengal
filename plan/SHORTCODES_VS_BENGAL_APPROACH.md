# Shortcodes vs Bengal's Approach

## The Question

Does Bengal need Hugo-style shortcodes or directive systems for embedding rich content in markdown?

## What Are Shortcodes?

**Hugo Shortcodes** are reusable snippets you can call from markdown:

```markdown
{{< youtube w7Ft2ymGmfc >}}
{{< figure src="/images/sunset.jpg" title="A sunset" caption="Beautiful sunset" >}}
{{< tweet 1234567890 >}}
{{< gist username abc123 >}}
```

**Sphinx/MyST Directives** (similar concept):

```markdown
```{youtube} w7Ft2ymGmfc
```

```{figure} /images/sunset.jpg
:alt: Sunset
Beautiful sunset
```
```

## Bengal's Current Approach

### 1. Direct HTML Embedding ✅

Bengal allows HTML directly in markdown (no special syntax needed):

```markdown
# My Article

Regular markdown content here.

<div class="video-container">
  <iframe width="560" height="315" 
          src="https://www.youtube.com/embed/w7Ft2ymGmfc" 
          frameborder="0" allowfullscreen>
  </iframe>
</div>

More markdown content continues...
```

**Pros:**
- ✅ No new syntax to learn
- ✅ Full HTML flexibility
- ✅ Works immediately, no configuration
- ✅ Standard across all SSGs

**Cons:**
- ❌ More verbose than shortcodes
- ❌ Harder for non-technical writers
- ❌ No built-in responsive wrapper
- ❌ Repetitive for common patterns

### 2. Markdown Extensions (Admonitions) ✅

Bengal has Python-Markdown admonitions enabled by default:

```markdown
!!! note "Pro Tip"
    This is a highlighted note box with a title.
    You can use markdown inside!

!!! warning
    Be careful with this configuration.

!!! tip "Performance Tip"
    Use incremental builds for faster iteration:
    
    ```bash
    bengal build --incremental
    ```
```

**Renders as:**
```html
<div class="admonition note">
  <p class="admonition-title">Pro Tip</p>
  <p>This is a highlighted note box...</p>
</div>
```

**Pros:**
- ✅ Directive-like syntax for callouts
- ✅ Semantic HTML output
- ✅ Standard Python-Markdown extension
- ✅ Great for docs/tutorials

**Types available:** note, warning, tip, danger, success, info

### 3. Cascading Frontmatter + Templates ✅ (NEW!)

For repeated content with variations, Bengal's approach is more ergonomic:

**Instead of Hugo shortcodes in every file:**
```markdown
<!-- Hugo approach - repetitive -->
{{< api-endpoint method="GET" path="/users" version="2.0" >}}
{{< api-endpoint method="POST" path="/users" version="2.0" >}}
{{< api-endpoint method="DELETE" path="/users/{id}" version="2.0" >}}
```

**Bengal approach - cascade + template:**

```markdown
# content/api/v2/_index.md
---
cascade:
  api_base_url: "https://api.example.com/v2"
  api_version: "2.0"
---

# content/api/v2/users.md
---
title: "Users API"
---

# Users API

**Base URL:** {{ page.metadata.api_base_url }}
**Version:** {{ page.metadata.api_version }}
```

Your template automatically wraps this with consistent headers, version badges, etc.

## Comparison: Real-World Use Cases

### Use Case 1: YouTube Video

**Hugo Shortcode:**
```markdown
{{< youtube w7Ft2ymGmfc >}}
```

**Bengal (HTML):**
```markdown
<iframe width="560" height="315" 
        src="https://www.youtube.com/embed/w7Ft2ymGmfc" 
        allowfullscreen>
</iframe>
```

**Bengal (with helper partial in template):**
```markdown
<div data-video-id="w7Ft2ymGmfc"></div>
<script>loadVideo();</script>
```

**Winner:** Hugo for simplicity, but Bengal's HTML approach is more flexible

### Use Case 2: Callout Boxes

**Hugo Shortcode:**
```markdown
{{< notice warning >}}
Be careful with this setting!
{{< /notice >}}
```

**Bengal (Admonition):**
```markdown
!!! warning
    Be careful with this setting!
```

**Winner:** Tie - Both are simple, Bengal's is standard Python-Markdown

### Use Case 3: Product Documentation

**Hugo Shortcode Approach:**
```markdown
{{< product-header name="DataFlow" version="2.0" >}}
{{< api-endpoint path="/users" method="GET" >}}
```

**Bengal Cascade Approach:**
```markdown
# _index.md
---
cascade:
  product_name: "DataFlow"
  product_version: "2.0"
---

# users.md (just writes content, metadata inherited)
# Template automatically displays product name, version, etc.
```

**Winner:** Bengal - Less repetitive, change once to update all pages

### Use Case 4: GitHub Gist Embed

**Hugo Shortcode:**
```markdown
{{< gist username abc123 >}}
```

**Bengal (HTML):**
```markdown
<script src="https://gist.github.com/username/abc123.js"></script>
```

**Winner:** Hugo for brevity

## Bengal's Philosophy: Simpler is Better

### What Bengal Does Well

1. **Standard Markdown** - No proprietary syntax
2. **HTML When Needed** - Full flexibility for complex cases
3. **Admonitions** - Directive-like syntax for common docs needs
4. **Cascade + Templates** - DRY approach for repeated metadata
5. **Template Functions** - 75+ filters for data transformation

### What Bengal Doesn't Need (Yet)

**Shortcodes are NOT needed if:**
- You're okay with HTML for one-off embeds
- You use admonitions for callouts
- You use cascade + templates for repeated patterns
- Your audience is technical enough for HTML

**Shortcodes MIGHT be useful for:**
- Non-technical content writers
- Very common patterns (YouTube, Gist, Tweet embeds)
- Marketing sites with lots of custom components
- Teams that want "no code" content editing

## Recommendation

### Phase 1 (Current): Simple & Powerful ✅

**Keep Bengal's current approach:**
1. ✅ HTML in Markdown (works now)
2. ✅ Admonitions enabled (works now)
3. ✅ Cascading frontmatter (just implemented!)
4. ✅ Template partials (works now)

**This covers 90% of use cases without adding complexity.**

### Phase 2 (Future): Optional Shortcodes

If demand emerges, add shortcodes as an **optional feature:**

```python
# bengal/rendering/shortcodes.py
def youtube(video_id: str, **kwargs) -> str:
    """Render YouTube embed."""
    return f'<iframe src="https://youtube.com/embed/{video_id}"...></iframe>'

def gist(username: str, gist_id: str) -> str:
    """Embed GitHub gist."""
    return f'<script src="https://gist.github.com/{username}/{gist_id}.js"></script>'
```

**Syntax options:**
```markdown
<!-- Option 1: Hugo-style -->
{{< youtube w7Ft2ymGmfc >}}

<!-- Option 2: MyST-style -->
```{youtube} w7Ft2ymGmfc
```

<!-- Option 3: HTML-style (custom elements) -->
<youtube video-id="w7Ft2ymGmfc"></youtube>
```

**Implementation:**
- Process shortcodes during markdown parsing
- Register shortcodes like template functions
- Allow users to create custom shortcodes
- Keep it optional (default: off)

## Comparison with Other SSGs

| SSG | Approach | Complexity | Flexibility |
|-----|----------|------------|-------------|
| **Hugo** | Shortcodes + Go templates | Medium | High |
| **Jekyll** | Liquid tags | Medium | Medium |
| **Eleventy** | Shortcodes (multiple syntaxes) | High | Very High |
| **Gatsby** | React components | High | Very High |
| **Pelican** | reStructuredText directives | Medium | Medium |
| **MkDocs** | Markdown + limited extensions | Low | Low |
| **Bengal** | HTML + Admonitions + Cascade | Low | High |

## Real Example: Technical Documentation

### Hugo Way (Shortcodes Everywhere)

```markdown
{{< api-version version="2.0" status="stable" >}}

# Authentication

{{< endpoint method="POST" path="/auth" >}}

{{< code-example language="python" >}}
import requests
{{< /code-example >}}

{{< note type="warning" >}}
Always use HTTPS
{{< /note >}}
```

**18 lines of shortcode syntax to learn**

### Bengal Way (Cascade + HTML + Admonitions)

```markdown
# content/api/v2/_index.md
---
cascade:
  version: "2.0"
  status: "stable"
  base_url: "https://api.example.com/v2"
---

# content/api/v2/auth.md
---
title: "Authentication"
---

# Authentication

**POST** `/auth`

```python
import requests
```

!!! warning
    Always use HTTPS
```

**Template automatically displays:** version badge, status, base URL

**Writer just writes content** - No shortcode syntax needed!

## Conclusion

### Bengal's Approach is More Ergonomic Because:

1. **Less syntax to learn** - Just markdown, HTML, and frontmatter
2. **Cascade handles repetition** - Define once, inherit everywhere
3. **Standard markdown** - No vendor lock-in
4. **Template flexibility** - Full Jinja2 power where needed
5. **Admonitions for callouts** - Standard, no custom syntax

### When You Might Want Shortcodes:

1. Non-technical content team
2. Lots of third-party embeds (YouTube, Twitter, etc.)
3. Complex interactive components
4. Marketing pages with custom widgets

### Decision

**✅ Keep Bengal simple for now**
- Current approach handles 90%+ of use cases
- Lower learning curve than Hugo
- More maintainable (less custom syntax)

**⏳ Add shortcodes later if needed**
- Monitor user feedback
- See if real demand emerges
- Implement as optional feature
- Keep default behavior simple

---

**TL;DR:** Bengal's combination of cascading frontmatter + templates + admonitions + HTML is simpler and more ergonomic than shortcodes for most use cases. Shortcodes can be added later if demand emerges, but they're not essential.

