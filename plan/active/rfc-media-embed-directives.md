# RFC: Media Embed Directives

**Status**: Draft  
**Created**: 2025-12-09  
**Author**: AI Assistant  
**Related**: `plan/implemented/rfc-directive-system-v2.md`, Hugo migration guide

---

## Executive Summary

Bengal's directive system has a significant gap: **no built-in directives for embedding media content** (videos, code playgrounds, terminal recordings, etc.). Users migrating from Hugo lose access to `{{< youtube >}}`, `{{< vimeo >}}`, `{{< gist >}}` and must fall back to raw HTML iframes.

**Recommendation**: Add a prioritized set of media embed directives that cover 90% of use cases while maintaining security and accessibility best practices.

---

## Problem Statement

### Current State

From `site/content/docs/tutorials/onboarding/from-hugo.md`:

```markdown
:::{note}
Bengal doesn't have a built-in YouTube shortcode. Use standard HTML embeds or create a custom template partial.
:::
```

Users are forced to write raw HTML:

```markdown
<!-- Current workaround - verbose, error-prone, no privacy controls -->
<iframe
  width="560"
  height="315"
  src="https://www.youtube.com/embed/dQw4w9WgXcQ"
  frameborder="0"
  allowfullscreen>
</iframe>
```

### Impact

1. **Migration friction** - Hugo users lose convenient shortcodes
2. **Inconsistent markup** - No standard pattern for embeds
3. **No privacy controls** - YouTube tracking enabled by default
4. **No accessibility** - Missing titles, fallback text
5. **Security risks** - Users may use unsafe iframe patterns

---

## Current Directive Inventory

### What Bengal Has (37 directive names)

| Category | Directives |
|----------|------------|
| **Admonitions** | note, tip, warning, danger, error, info, example, success, seealso, important, hint, attention, caution |
| **Layout** | cards, card, child-cards, grid, grid-item-card, tabs, tab-set, tab-item, dropdown, details, container, div |
| **Code** | code-tabs, literalinclude |
| **Tables** | list-table, data-table |
| **Navigation** | breadcrumbs, siblings, prev-next, related |
| **UI Elements** | button, badge, icon, svg-icon, checklist, rubric |
| **Content Reuse** | include, literalinclude |
| **Data** | glossary |
| **Steps** | steps, step |
| **Interactive** | marimo (optional) |

### What's Missing (Media/Embed Gap)

| Category | Missing Directives | Priority |
|----------|--------------------|----------|
| **Video** | youtube, vimeo, video (self-hosted) | P0 - Critical |
| **Developer Tools** | gist, codepen, codesandbox, stackblitz | P1 - High |
| **Terminal** | asciinema, terminalizer | P1 - High |
| **Images** | figure (semantic image+caption) | P2 - Medium |
| **Audio** | audio (self-hosted) | P2 - Medium |
| **Social** | tweet/twitter (deprecated platform APIs) | P3 - Low |
| **Presentations** | slideshare, speakerdeck | P3 - Low |

---

## Proposed Solution

### Design Principles

1. **Privacy-first** - Use privacy-enhanced embeds by default (e.g., `youtube-nocookie.com`)
2. **Accessible** - Require/generate titles, provide fallback text
3. **Secure** - Use sandbox attributes, validate URLs
4. **Responsive** - All embeds scale to container width
5. **Lazy-loading** - Use native lazy loading for performance
6. **Consistent API** - Similar option patterns across all embed directives

### P0: Video Directives (Critical)

#### `{youtube}` - YouTube Video Embed

**Syntax**:

```markdown
:::{youtube} dQw4w9WgXcQ
:title: Never Gonna Give You Up
:start: 30
:privacy: true
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | (required) | Accessible title for iframe |
| `start` | int | 0 | Start time in seconds |
| `privacy` | bool | true | Use youtube-nocookie.com |
| `autoplay` | bool | false | Auto-start video |
| `controls` | bool | true | Show player controls |
| `loop` | bool | false | Loop video |
| `class` | string | "" | Custom CSS class |
| `aspect` | string | "16/9" | Aspect ratio (16/9, 4/3, 1/1) |

**Output**:

```html
<div class="video-embed youtube" style="aspect-ratio: 16/9">
  <iframe
    src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?start=30"
    title="Never Gonna Give You Up"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen
    loading="lazy"
  ></iframe>
</div>
```

#### `{vimeo}` - Vimeo Video Embed

**Syntax**:

```markdown
:::{vimeo} 123456789
:title: My Vimeo Video
:color: ff0000
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | (required) | Accessible title |
| `color` | string | "" | Player accent color (hex) |
| `autopause` | bool | true | Pause when another video starts |
| `dnt` | bool | true | Do Not Track mode |
| `class` | string | "" | Custom CSS class |
| `aspect` | string | "16/9" | Aspect ratio |

#### `{video}` - Self-Hosted Video

**Syntax**:

```markdown
:::{video} /assets/demo.mp4
:title: Product Demo
:poster: /assets/demo-poster.jpg
:controls: true
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | (required) | Accessible title |
| `poster` | string | "" | Poster image URL |
| `controls` | bool | true | Show controls |
| `autoplay` | bool | false | Auto-start (muted required) |
| `muted` | bool | false | Start muted |
| `loop` | bool | false | Loop video |
| `preload` | string | "metadata" | none, metadata, auto |
| `width` | string | "100%" | Width |
| `class` | string | "" | Custom CSS class |

**Output**:

```html
<video
  class="video-embed self-hosted"
  title="Product Demo"
  poster="/assets/demo-poster.jpg"
  controls
  preload="metadata"
  width="100%"
>
  <source src="/assets/demo.mp4" type="video/mp4">
  <p>Your browser doesn't support HTML5 video. <a href="/assets/demo.mp4">Download the video</a>.</p>
</video>
```

### P1: Developer Tool Embeds (High)

#### `{gist}` - GitHub Gist Embed

**Syntax**:

```markdown
:::{gist} username/gist_id
:file: example.py
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `file` | string | "" | Specific file from gist |
| `class` | string | "" | Custom CSS class |

**Output**:

```html
<div class="gist-embed">
  <script src="https://gist.github.com/username/gist_id.js?file=example.py"></script>
  <noscript>
    <p>View gist: <a href="https://gist.github.com/username/gist_id">username/gist_id</a></p>
  </noscript>
</div>
```

#### `{codepen}` - CodePen Embed

**Syntax**:

```markdown
:::{codepen} username/pen_id
:title: Interactive Example
:default-tab: result
:height: 400
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | (required) | Accessible title |
| `default-tab` | string | "result" | html, css, js, result |
| `height` | int | 300 | Height in pixels |
| `theme` | string | "" | light, dark, or theme ID |
| `editable` | bool | false | Allow editing |
| `class` | string | "" | Custom CSS class |

#### `{codesandbox}` - CodeSandbox Embed

**Syntax**:

```markdown
:::{codesandbox} sandbox_id
:title: React Example
:module: /src/App.js
:view: preview
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | (required) | Accessible title |
| `module` | string | "" | File to show initially |
| `view` | string | "split" | editor, preview, split |
| `height` | int | 500 | Height in pixels |
| `fontsize` | int | 14 | Editor font size |
| `hidenavigation` | bool | false | Hide file navigation |
| `class` | string | "" | Custom CSS class |

#### `{stackblitz}` - StackBlitz Embed

**Syntax**:

```markdown
:::{stackblitz} project_id
:title: Angular Demo
:file: src/app.component.ts
:embed: 1
:::
```

#### `{asciinema}` - Terminal Recording Embed

**Syntax**:

```markdown
:::{asciinema} recording_id
:title: Installation Demo
:cols: 80
:rows: 24
:speed: 1.5
:autoplay: true
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | (required) | Accessible title |
| `cols` | int | 80 | Terminal columns |
| `rows` | int | 24 | Terminal rows |
| `speed` | float | 1.0 | Playback speed |
| `autoplay` | bool | false | Auto-start |
| `loop` | bool | false | Loop playback |
| `theme` | string | "" | Color theme |
| `poster` | string | "" | Preview frame (npt:MM:SS) |
| `class` | string | "" | Custom CSS class |

**Output**:

```html
<div class="asciinema-embed">
  <script
    id="asciicast-recording_id"
    src="https://asciinema.org/a/recording_id.js"
    async
    data-cols="80"
    data-rows="24"
    data-speed="1.5"
    data-autoplay="true"
  ></script>
  <noscript>
    <a href="https://asciinema.org/a/recording_id">View recording on asciinema.org</a>
  </noscript>
</div>
```

### P2: Image & Audio (Medium)

#### `{figure}` - Semantic Image with Caption

**Syntax**:

```markdown
:::{figure} /images/architecture.png
:alt: System Architecture Diagram
:caption: High-level system architecture showing data flow
:width: 80%
:align: center
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `alt` | string | (required) | Alt text for accessibility |
| `caption` | string | "" | Caption text (markdown supported) |
| `width` | string | "" | Width (px or %) |
| `height` | string | "" | Height (px or %) |
| `align` | string | "" | left, center, right |
| `link` | string | "" | Link URL when clicked |
| `class` | string | "" | Custom CSS class |

**Output**:

```html
<figure class="figure align-center" style="width: 80%">
  <img
    src="/images/architecture.png"
    alt="System Architecture Diagram"
    loading="lazy"
  >
  <figcaption>High-level system architecture showing data flow</figcaption>
</figure>
```

**Why not just use cards?** The card workaround documented in Hugo migration lacks:
- Semantic HTML (`<figure>` + `<figcaption>`)
- Proper accessibility patterns
- Caption styling separate from body text
- Standard width/align controls

#### `{audio}` - Self-Hosted Audio

**Syntax**:

```markdown
:::{audio} /assets/podcast-ep1.mp3
:title: Episode 1: Getting Started
:controls: true
:::
```

---

## Implementation Plan

### Phase 1: P0 Video Directives (Week 1-2)

| Task | File | Effort |
|------|------|--------|
| Create `video.py` with VideoDirective base class | `directives/video.py` | 2h |
| Implement YouTubeDirective | `directives/video.py` | 3h |
| Implement VimeoDirective | `directives/video.py` | 2h |
| Implement VideoDirective (self-hosted) | `directives/video.py` | 2h |
| Add CSS for responsive video containers | `themes/default/assets/css/` | 1h |
| Add tests | `tests/unit/test_video_directives.py` | 3h |
| Update documentation | `site/content/docs/reference/directives/` | 2h |

### Phase 2: P1 Developer Tools (Week 3-4)

| Task | File | Effort |
|------|------|--------|
| Create `embed.py` with EmbedDirective base class | `directives/embed.py` | 2h |
| Implement GistDirective | `directives/embed.py` | 2h |
| Implement CodePenDirective | `directives/embed.py` | 2h |
| Implement CodeSandboxDirective | `directives/embed.py` | 2h |
| Implement StackBlitzDirective | `directives/embed.py` | 2h |
| Create `terminal.py` for AsciinemaDirective | `directives/terminal.py` | 3h |
| Add CSS for embed containers | `themes/default/assets/css/` | 1h |
| Add tests | `tests/unit/test_embed_directives.py` | 4h |
| Update documentation | `site/content/docs/reference/directives/` | 3h |

### Phase 3: P2 Figure & Audio (Week 5)

| Task | File | Effort |
|------|------|--------|
| Create `figure.py` for FigureDirective | `directives/figure.py` | 3h |
| Create `audio.py` for AudioDirective | `directives/audio.py` | 2h |
| Add CSS for figure styling | `themes/default/assets/css/` | 1h |
| Add tests | `tests/unit/test_figure_directives.py` | 2h |
| Update documentation | `site/content/docs/reference/directives/` | 2h |

---

## Security Considerations

### URL Validation

All embed directives must validate URLs to prevent:
- XSS via malicious URLs
- Open redirects
- Content injection

```python
ALLOWED_YOUTUBE_DOMAINS = ["youtube.com", "youtu.be", "youtube-nocookie.com"]
ALLOWED_VIMEO_DOMAINS = ["vimeo.com", "player.vimeo.com"]

def validate_youtube_id(video_id: str) -> bool:
    """Validate YouTube video ID format (11 alphanumeric chars)."""
    return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))
```

### Iframe Sandboxing

Third-party embeds should use appropriate sandbox attributes:

```html
<iframe
  sandbox="allow-scripts allow-same-origin allow-popups"
  ...
>
```

### CSP Headers

Document required Content Security Policy headers for embeds:

```
Content-Security-Policy:
  frame-src 'self'
    https://www.youtube-nocookie.com
    https://player.vimeo.com
    https://gist.github.com
    https://codepen.io
    https://codesandbox.io
    https://stackblitz.com
    https://asciinema.org;
```

---

## Accessibility Requirements

### All Video Embeds

1. **Title attribute** - Required, descriptive title
2. **Fallback content** - Link to video for users without JavaScript
3. **Keyboard navigation** - Native player controls
4. **Captions** - Document how to enable captions (YouTube auto-captions)

### Figure Directive

1. **Alt text** - Required for all images
2. **Caption** - Available for additional context
3. **Decorative images** - Support `alt=""` for decorative images

---

## CSS Requirements

### New CSS Files

```
themes/default/assets/css/components/
├── video-embed.css      # Video containers, aspect ratios
├── code-embed.css       # CodePen, CodeSandbox, StackBlitz
├── figure.css           # Figure + figcaption styling
└── asciinema.css        # Terminal recording styling
```

### Responsive Video Container

```css
.video-embed {
  position: relative;
  width: 100%;
  max-width: 100%;
}

.video-embed iframe,
.video-embed video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 0;
}

.video-embed.aspect-16-9 { aspect-ratio: 16 / 9; }
.video-embed.aspect-4-3 { aspect-ratio: 4 / 3; }
.video-embed.aspect-1-1 { aspect-ratio: 1 / 1; }
```

---

## Testing Strategy

### Unit Tests

```python
def test_youtube_directive_basic():
    """Test basic YouTube embed."""
    markdown = """
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:::
"""
    result = parse(markdown)
    assert "youtube-nocookie.com" in result  # Privacy default
    assert 'title="Test Video"' in result
    assert "loading=\"lazy\"" in result

def test_youtube_directive_validates_id():
    """Test YouTube ID validation."""
    markdown = """
:::{youtube} invalid<script>
:title: Test
:::
"""
    result = parse(markdown)
    assert "<script>" not in result  # XSS prevented
```

### Integration Tests

- Test all embed directives render in full build
- Test CSP headers don't break embeds
- Test responsive behavior at different viewports

---

## Migration Path

### Hugo Users

Update `from-hugo.md` with new equivalents:

```markdown
| Hugo | Bengal | Notes |
|------|--------|-------|
| `{{</* youtube id */>}}` | `:::{youtube} id` | Privacy-enhanced by default |
| `{{</* vimeo id */>}}` | `:::{vimeo} id` | DNT mode by default |
| `{{</* gist user/id */>}}` | `:::{gist} user/id` | Same functionality |
| `{{</* figure src="..." */>}}` | `:::{figure} ...` | Semantic HTML output |
```

---

## Alternatives Considered

### 1. Generic `{embed}` Directive

**Rejected**: Too permissive, security risks, no type-specific options

```markdown
<!-- Rejected approach -->
:::{embed} https://any-url.com
:type: iframe
:::
```

### 2. Raw HTML Only (Current State)

**Rejected**: Poor DX, no consistency, no privacy defaults, accessibility gaps

### 3. Template Partials Only

**Rejected**: Requires template knowledge, breaks content/template separation

---

## Success Criteria

1. ✅ All P0 video directives implemented with tests
2. ✅ Privacy-enhanced defaults (youtube-nocookie, Vimeo DNT)
3. ✅ Accessibility requirements met (titles, fallbacks)
4. ✅ Security validation for all URL inputs
5. ✅ Responsive CSS for all embed types
6. ✅ Documentation updated for Hugo migration
7. ✅ At least 90% test coverage for new directives

---

## Open Questions

1. **Should we support Twitter/X embeds?** Platform APIs are unstable, embeds break frequently
2. **Should `{figure}` support multiple images?** (gallery mode)
3. **Should we add `{loom}` for screen recording embeds?** (common in docs)
4. **Should we support `{pdf}` for embedded PDFs?**

---

## Appendix: Hugo Built-in Shortcodes Reference

| Hugo Shortcode | Bengal Equivalent | Status |
|----------------|-------------------|--------|
| `figure` | `{figure}` | **Proposed** |
| `gist` | `{gist}` | **Proposed** |
| `highlight` | Native fenced code blocks | ✅ Exists |
| `instagram` | N/A (API deprecated) | Not planned |
| `param` | `{{ page.metadata.x }}` | ✅ Exists |
| `ref` / `relref` | Cross-reference plugin | ✅ Exists |
| `tweet` | N/A (API unstable) | Not planned |
| `vimeo` | `{vimeo}` | **Proposed** |
| `youtube` | `{youtube}` | **Proposed** |

---

## References

- [Hugo Built-in Shortcodes](https://gohugo.io/content-management/shortcodes/)
- [Docusaurus MDX Components](https://docusaurus.io/docs/markdown-features)
- [MyST Directives Specification](https://myst-parser.readthedocs.io/en/latest/syntax/directives.html)
- [YouTube IFrame Player API](https://developers.google.com/youtube/iframe_api_reference)
- [Vimeo oEmbed](https://developer.vimeo.com/api/oembed)
- [Asciinema Embedding](https://asciinema.org/docs/embedding)

