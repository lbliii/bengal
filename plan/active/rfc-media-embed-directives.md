# RFC: Media Embed Directives

**Status**: Draft  
**Created**: 2025-12-09  
**Updated**: 2025-12-09  
**Author**: AI Assistant  
**Related**: `plan/implemented/rfc-directive-system-v2.md`, Hugo migration guide  
**Confidence**: 88% 🟢

---

## Executive Summary

Bengal's directive system has a significant gap: **no built-in directives for embedding media content** (videos, code playgrounds, terminal recordings, etc.). Users migrating from Hugo lose access to `{{< youtube >}}`, `{{< vimeo >}}`, `{{< gist >}}` and must fall back to raw HTML iframes.

**Recommendation**: Implement **Option A (Type-Specific Directives)** — add a prioritized set of media embed directives that cover 90% of use cases while maintaining security and accessibility best practices, leveraging the established `BengalDirective` base class pattern.

**Impact**: 12 new directive names across 4 new Python modules, ~50 hours implementation effort over 5 weeks.

---

## Problem Statement

### Current State

From `site/content/docs/tutorials/onboarding/from-hugo.md:210-212`:

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

**Evidence**: `site/content/docs/tutorials/onboarding/from-hugo.md:198-205`

### User Impact

1. **Migration friction** — Hugo users lose convenient shortcodes they rely on
2. **Inconsistent markup** — No standard pattern for embeds across documentation
3. **No privacy controls** — YouTube tracking enabled by default (GDPR concerns)
4. **No accessibility** — Missing titles, fallback text for screen readers
5. **Security risks** — Users may use unsafe iframe patterns without sandboxing

### Quantified Gap

Bengal currently has **44 registered directive names** (verified via `KNOWN_DIRECTIVE_NAMES`). None support:
- Video embedding (YouTube, Vimeo, self-hosted)
- Code playground embedding (CodePen, CodeSandbox, StackBlitz)
- Terminal recording playback (asciinema)
- Semantic image figures with captions

---

## Goals & Non-Goals

### Goals

1. **G1**: Provide drop-in replacements for Hugo's media shortcodes (`youtube`, `vimeo`, `gist`, `figure`)
2. **G2**: Enforce privacy-by-default for third-party embeds (youtube-nocookie.com, Vimeo DNT)
3. **G3**: Meet WCAG 2.1 AA accessibility requirements (titles, fallbacks, keyboard navigation)
4. **G4**: Prevent XSS and content injection via strict URL/ID validation
5. **G5**: Support responsive design with native CSS aspect-ratio
6. **G6**: Integrate with existing `BengalDirective` architecture for consistency

### Non-Goals

1. **NG1**: Social media embeds (Twitter/X, Instagram) — platform APIs unstable, embeds break frequently
2. **NG2**: Presentation embeds (SlideShare, SpeakerDeck) — low demand, niche use case
3. **NG3**: Generic iframe directive — too permissive, security risks
4. **NG4**: oEmbed auto-discovery — complexity not justified for initial release
5. **NG5**: Client-side JavaScript players — keep embeds server-rendered

---

## Architecture Impact

### Affected Subsystems

**Primary**: `bengal/rendering/plugins/directives/`
- 4 new modules: `video.py`, `embed.py`, `terminal.py`, `figure.py`
- Updates to `__init__.py` (registry additions)

**Secondary**: `bengal/themes/default/assets/css/`
- 4 new CSS files for embed styling

**No changes required**:
- `bengal/core/` — No data model changes
- `bengal/orchestration/` — No build pipeline changes
- `bengal/cache/` — Existing directive caching applies
- `bengal/health/` — Existing directive validator applies

### Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    Mistune Markdown Parser                       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              FencedDirective (patched for indentation)           │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────┐
│ BengalDirective │   │  DirectiveContract   │   │ DirectiveOptions │
│   (base class)  │   │  (nesting rules)     │   │  (typed options) │
└────────┬────────┘   └─────────────────────┘   └─────────────────┘
         │
         ├── VideoDirective (base)
         │   ├── YouTubeDirective
         │   ├── VimeoDirective
         │   └── SelfHostedVideoDirective
         │
         ├── EmbedDirective (base)
         │   ├── GistDirective
         │   ├── CodePenDirective
         │   ├── CodeSandboxDirective
         │   └── StackBlitzDirective
         │
         ├── TerminalDirective (base)
         │   └── AsciinemaDirective
         │
         └── FigureDirective
             └── AudioDirective
```

### Directive Registry Updates

```python
# bengal/rendering/plugins/directives/__init__.py

DIRECTIVE_CLASSES: list[type] = [
    # ... existing 44 directives ...
    
    # NEW: Video directives (P0)
    YouTubeDirective,      # youtube
    VimeoDirective,        # vimeo
    SelfHostedVideoDirective,  # video
    
    # NEW: Developer embeds (P1)
    GistDirective,         # gist
    CodePenDirective,      # codepen
    CodeSandboxDirective,  # codesandbox
    StackBlitzDirective,   # stackblitz
    AsciinemaDirective,    # asciinema
    
    # NEW: Figure & Audio (P2)
    FigureDirective,       # figure
    AudioDirective,        # audio
]

# Post-implementation: 54 directive names (44 existing + 10 new)
```

---

## Current Directive Inventory

### What Bengal Has (44 directive names)

**Verified**: `python -c "from bengal.rendering.plugins.directives import KNOWN_DIRECTIVE_NAMES; print(len(KNOWN_DIRECTIVE_NAMES))"`

| Category | Directives | Count |
|----------|------------|-------|
| **Admonitions** | `note`, `tip`, `warning`, `danger`, `error`, `info`, `example`, `success`, `seealso`, `caution` | 10 |
| **Layout** | `cards`, `card`, `child-cards`, `grid`, `grid-item-card`, `tabs`, `tab-set`, `tab-item`, `tab`, `dropdown`, `details`, `container`, `div` | 13 |
| **Code** | `code-tabs`, `code_tabs`, `literalinclude` | 3 |
| **Tables** | `list-table`, `data-table` | 2 |
| **Navigation** | `breadcrumbs`, `siblings`, `prev-next`, `related` | 4 |
| **UI Elements** | `button`, `badge`, `bdg`, `icon`, `svg-icon`, `checklist`, `rubric` | 7 |
| **Content Reuse** | `include` | 1 |
| **Data** | `glossary` | 1 |
| **Steps** | `steps`, `step` | 2 |
| **Interactive** | `marimo` | 1 |
| **Total** | | **44** |

### What's Missing (Media/Embed Gap)

| Category | Missing Directives | Priority | Hugo Equivalent |
|----------|--------------------|----------|-----------------|
| **Video** | `youtube`, `vimeo`, `video` | P0 - Critical | `{{< youtube >}}`, `{{< vimeo >}}` |
| **Developer Tools** | `gist`, `codepen`, `codesandbox`, `stackblitz` | P1 - High | `{{< gist >}}` |
| **Terminal** | `asciinema` | P1 - High | N/A |
| **Images** | `figure` | P2 - Medium | `{{< figure >}}` |
| **Audio** | `audio` | P2 - Medium | N/A |

---

## Design Options

### Option A: Type-Specific Directives (Recommended)

**Description**: Create dedicated directives for each embed type (`youtube`, `vimeo`, `gist`, etc.) with type-specific validation and options.

**Pros**:
- ✅ Strong security via per-type URL/ID validation
- ✅ Type-specific options (e.g., `start` for YouTube, `default-tab` for CodePen)
- ✅ Clear documentation per directive
- ✅ Follows existing Bengal pattern (e.g., `tabs` vs `dropdown`)
- ✅ Easy to add new embed types later

**Cons**:
- ❌ More files/classes to maintain (10 new directive classes)
- ❌ Slight API learning curve (different directive per service)

**Complexity**: Moderate  
**Evidence**: Matches Hugo's approach (separate shortcodes per service)

### Option B: Generic `{embed}` Directive with Type Parameter

**Description**: Single `{embed}` directive with `:type:` option to specify service.

```markdown
:::{embed} dQw4w9WgXcQ
:type: youtube
:title: My Video
:::
```

**Pros**:
- ✅ Single directive to learn
- ✅ Fewer files to maintain

**Cons**:
- ❌ Type parameter required on every use
- ❌ Complex validation logic in single class
- ❌ Options vary by type (confusing API)
- ❌ Security: harder to audit all code paths
- ❌ No IDE autocomplete for type-specific options

**Complexity**: Low initial, High maintenance  
**Evidence**: Docusaurus uses type-specific components, not generic embed

### Option C: Raw HTML with Validation Helper

**Description**: Keep raw HTML but provide a validation shortcode.

```markdown
:::{validate-embed}
<iframe src="https://youtube.com/embed/..."></iframe>
:::
```

**Pros**:
- ✅ Minimal implementation
- ✅ Full control for users

**Cons**:
- ❌ Doesn't solve DX problem
- ❌ Users still write verbose HTML
- ❌ No privacy defaults
- ❌ No accessibility enforcement

**Complexity**: Low  
**Evidence**: Poor DX, rejected by other SSGs

### Recommendation: Option A

**Reasoning**:
1. **Security**: Type-specific validation is easier to audit and more secure
2. **DX**: Matches user mental model (YouTube vs Vimeo vs Gist are different)
3. **Extensibility**: Adding `{loom}` later is trivial
4. **Consistency**: Follows Bengal's existing directive patterns
5. **Hugo Parity**: Direct mapping from Hugo shortcodes

---

## Detailed Design (Option A)

### Base Classes

```python
# bengal/rendering/plugins/directives/video.py

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.options import DirectiveOptions

@dataclass
class VideoOptions(DirectiveOptions):
    """Common options for all video directives."""
    title: str  # Required - accessibility
    aspect: str = "16/9"
    class_: str = ""
    autoplay: bool = False
    loop: bool = False
    
class VideoDirective(BengalDirective):
    """Base class for video embed directives."""
    
    OPTIONS_CLASS = VideoOptions
    
    def validate_source(self, source: str) -> str | None:
        """Validate and sanitize video source. Override in subclasses."""
        raise NotImplementedError
    
    def build_iframe_attrs(self, options: VideoOptions) -> dict[str, str]:
        """Build common iframe attributes."""
        return {
            "title": options.title,
            "loading": "lazy",
            "allowfullscreen": "",
            "style": f"aspect-ratio: {options.aspect}",
        }
```

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
| `end` | int | None | End time in seconds |
| `privacy` | bool | true | Use youtube-nocookie.com |
| `autoplay` | bool | false | Auto-start video |
| `controls` | bool | true | Show player controls |
| `loop` | bool | false | Loop video |
| `mute` | bool | false | Start muted |
| `class` | string | "" | Custom CSS class |
| `aspect` | string | "16/9" | Aspect ratio (16/9, 4/3, 1/1) |

**Implementation**:

```python
class YouTubeDirective(VideoDirective):
    DIRECTIVE_NAMES = ["youtube"]
    
    YOUTUBE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    
    def validate_source(self, video_id: str) -> str | None:
        """Validate YouTube video ID (11 alphanumeric chars)."""
        if not self.YOUTUBE_ID_PATTERN.match(video_id):
            return f"Invalid YouTube video ID: {video_id!r}"
        return None
    
    def build_embed_url(self, video_id: str, options: YouTubeOptions) -> str:
        domain = "youtube-nocookie.com" if options.privacy else "youtube.com"
        params = []
        if options.start:
            params.append(f"start={options.start}")
        if options.end:
            params.append(f"end={options.end}")
        if options.autoplay:
            params.append("autoplay=1")
        if options.mute:
            params.append("mute=1")
        if options.loop:
            params.append(f"loop=1&playlist={video_id}")
        if not options.controls:
            params.append("controls=0")
        
        query = "&".join(params)
        return f"https://www.{domain}/embed/{video_id}{'?' + query if query else ''}"
```

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
| `color` | string | "" | Player accent color (hex without #) |
| `autopause` | bool | true | Pause when another video starts |
| `dnt` | bool | true | Do Not Track mode |
| `background` | bool | false | Background mode (no controls) |
| `class` | string | "" | Custom CSS class |
| `aspect` | string | "16/9" | Aspect ratio |

**Implementation**:

```python
class VimeoDirective(VideoDirective):
    DIRECTIVE_NAMES = ["vimeo"]
    
    VIMEO_ID_PATTERN = re.compile(r'^\d{6,11}$')
    
    def validate_source(self, video_id: str) -> str | None:
        """Validate Vimeo video ID (6-11 digits)."""
        if not self.VIMEO_ID_PATTERN.match(video_id):
            return f"Invalid Vimeo video ID: {video_id!r}"
        return None
```

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
<figure class="video-embed self-hosted">
  <video
    title="Product Demo"
    poster="/assets/demo-poster.jpg"
    controls
    preload="metadata"
    width="100%"
  >
    <source src="/assets/demo.mp4" type="video/mp4">
    <p>Your browser doesn't support HTML5 video. <a href="/assets/demo.mp4">Download the video</a>.</p>
  </video>
</figure>
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

**Validation**:

```python
GIST_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+/[a-f0-9]{32}$')
```

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
| `theme` | string | "dark" | light, dark, or theme ID |
| `editable` | bool | false | Allow editing |
| `preview` | bool | true | Show preview on load |
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
| `theme` | string | "dark" | light, dark |
| `class` | string | "" | Custom CSS class |

#### `{stackblitz}` - StackBlitz Embed

**Syntax**:

```markdown
:::{stackblitz} project_id
:title: Angular Demo
:file: src/app.component.ts
:view: preview
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | (required) | Accessible title |
| `file` | string | "" | File to show initially |
| `view` | string | "both" | editor, preview, both |
| `height` | int | 500 | Height in pixels |
| `hidenavigation` | bool | false | Hide file navigation |
| `hidedevtools` | bool | false | Hide dev tools |
| `class` | string | "" | Custom CSS class |

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
| `theme` | string | "asciinema" | Color theme |
| `poster` | string | "npt:0:0" | Preview frame (npt:MM:SS) |
| `idle-time-limit` | float | None | Max idle time between frames |
| `class` | string | "" | Custom CSS class |

**Output**:

```html
<figure class="asciinema-embed" role="img" aria-label="Installation Demo">
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
    <a href="https://asciinema.org/a/recording_id">View recording: Installation Demo</a>
  </noscript>
</figure>
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
| `target` | string | "_self" | Link target (_blank, _self) |
| `loading` | string | "lazy" | lazy, eager |
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
- Proper accessibility patterns (alt text handling)
- Caption styling separate from body text
- Standard width/align controls expected by content authors

#### `{audio}` - Self-Hosted Audio

**Syntax**:

```markdown
:::{audio} /assets/podcast-ep1.mp3
:title: Episode 1: Getting Started
:controls: true
:::
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | (required) | Accessible title |
| `controls` | bool | true | Show controls |
| `autoplay` | bool | false | Auto-start (not recommended) |
| `loop` | bool | false | Loop audio |
| `muted` | bool | false | Start muted |
| `preload` | string | "metadata" | none, metadata, auto |
| `class` | string | "" | Custom CSS class |

**Output**:

```html
<figure class="audio-embed">
  <audio
    title="Episode 1: Getting Started"
    controls
    preload="metadata"
  >
    <source src="/assets/podcast-ep1.mp3" type="audio/mpeg">
    <p>Your browser doesn't support HTML5 audio. <a href="/assets/podcast-ep1.mp3">Download the audio</a>.</p>
  </audio>
</figure>
```

---

## Tradeoffs & Risks

### Tradeoffs

| Tradeoff | What We Gain | What We Lose |
|----------|-------------|--------------|
| Type-specific directives | Strong security, clear API | More classes to maintain |
| Privacy-by-default | GDPR compliance, user trust | Slightly longer embed URLs |
| Required title option | Accessibility compliance | Extra typing for users |
| Lazy loading default | Better page performance | Initial empty space before load |
| Script-based embeds (Gist, asciinema) | Full functionality | Requires JS, harder to test |

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Third-party API changes** | Medium | Medium | Use stable embed APIs, not custom integrations. Document CSP requirements. |
| **YouTube/Vimeo break privacy mode** | Low | Medium | Privacy mode uses documented features. Monitor for deprecation. |
| **Asciinema.org downtime** | Low | Low | Provide noscript fallback with link. Consider self-hosted option later. |
| **ID validation too strict** | Medium | Low | Test against real-world IDs. Allow regex override in config. |
| **CSS conflicts with themes** | Medium | Low | Use BEM naming, provide CSS custom properties for theming. |
| **Security bypass via crafted input** | Low | High | Extensive unit tests for all validation. Security review before merge. |

---

## Performance & Compatibility

### Performance Impact

| Metric | Impact | Notes |
|--------|--------|-------|
| **Build time** | Negligible | Directives are simple string transformations |
| **Memory** | +~50KB | 10 new directive classes loaded |
| **Page weight** | +2-5KB CSS | One-time load, cacheable |
| **Runtime (LCP)** | Improved | `loading="lazy"` defers iframe loading |
| **Cache invalidation** | None | New directives don't affect existing cache |

### Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| `aspect-ratio` CSS | 88+ | 89+ | 15+ | 88+ |
| `loading="lazy"` | 77+ | 75+ | 15.4+ | 79+ |
| iframe sandbox | All | All | All | All |

**Fallback**: For older browsers, aspect-ratio falls back to padding-bottom trick via CSS feature query.

### Compatibility

- **Breaking changes**: None — additive only
- **Migration path**: N/A (new feature)
- **Deprecation timeline**: N/A

---

## Security Considerations

### URL/ID Validation

All embed directives validate inputs to prevent:
- XSS via malicious URLs
- Open redirects
- Content injection

```python
# Validation patterns per service
VALIDATORS = {
    "youtube": re.compile(r'^[a-zA-Z0-9_-]{11}$'),  # 11 alphanumeric
    "vimeo": re.compile(r'^\d{6,11}$'),  # 6-11 digits
    "gist": re.compile(r'^[a-zA-Z0-9_-]+/[a-f0-9]{32}$'),  # user/32-char hex
    "codepen": re.compile(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$'),  # user/slug
    "codesandbox": re.compile(r'^[a-z0-9]{5,}$'),  # 5+ alphanumeric
    "stackblitz": re.compile(r'^[a-zA-Z0-9_-]+$'),  # alphanumeric
    "asciinema": re.compile(r'^\d+$'),  # numeric only
}

def validate_embed_id(service: str, embed_id: str) -> str | None:
    """Validate embed ID for service. Returns error message or None if valid."""
    pattern = VALIDATORS.get(service)
    if not pattern:
        return f"Unknown service: {service}"
    if not pattern.match(embed_id):
        return f"Invalid {service} ID format: {embed_id!r}"
    return None
```

### Iframe Sandboxing

Third-party embeds use appropriate sandbox attributes:

```html
<!-- Video embeds need scripts and same-origin for player -->
<iframe
  sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
  ...
>

<!-- Code embeds need more permissions -->
<iframe
  sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
  ...
>
```

### CSP Headers

Document required Content Security Policy headers for embeds:

```
Content-Security-Policy:
  frame-src 'self'
    https://www.youtube-nocookie.com
    https://www.youtube.com
    https://player.vimeo.com
    https://gist.github.com
    https://codepen.io
    https://codesandbox.io
    https://stackblitz.com
    https://asciinema.org;
  script-src 'self'
    https://gist.github.com
    https://asciinema.org;
```

---

## Accessibility Requirements

### All Video Embeds

1. **Title attribute** — Required via `:title:` option, descriptive and unique
2. **Fallback content** — Link to video for users without JavaScript/iframe support
3. **Keyboard navigation** — Native player controls accessible via Tab
4. **Captions** — Document how to enable captions (YouTube: `cc_load_policy=1`)

### Figure Directive

1. **Alt text** — Required via `:alt:` option for all images
2. **Caption** — Optional via `:caption:` for additional context
3. **Decorative images** — Support `:alt: ""` (empty string) for decorative images
4. **Long descriptions** — Support `:longdesc:` option for complex images

### Terminal Recordings

1. **ARIA role** — Use `role="img"` with `aria-label` for recordings
2. **Transcript link** — Recommend providing text transcript for complex recordings

---

## CSS Requirements

### New CSS Files

```
bengal/themes/default/assets/css/components/
├── _video-embed.css      # Video containers, aspect ratios
├── _code-embed.css       # CodePen, CodeSandbox, StackBlitz
├── _figure.css           # Figure + figcaption styling
└── _terminal-embed.css   # Asciinema styling
```

### Responsive Video Container

```css
/* _video-embed.css */
.video-embed {
  position: relative;
  width: 100%;
  max-width: 100%;
  margin-block: var(--spacing-4);
}

.video-embed iframe,
.video-embed video {
  width: 100%;
  height: auto;
  aspect-ratio: var(--video-aspect, 16/9);
  border: 0;
  border-radius: var(--radius-md);
}

/* Aspect ratio variants */
.video-embed[data-aspect="16/9"] { --video-aspect: 16/9; }
.video-embed[data-aspect="4/3"] { --video-aspect: 4/3; }
.video-embed[data-aspect="1/1"] { --video-aspect: 1/1; }
.video-embed[data-aspect="9/16"] { --video-aspect: 9/16; }

/* Fallback for older browsers */
@supports not (aspect-ratio: 16/9) {
  .video-embed {
    padding-bottom: 56.25%; /* 16:9 */
    height: 0;
  }
  .video-embed iframe,
  .video-embed video {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }
}
```

### Figure Styling

```css
/* _figure.css */
.figure {
  margin-block: var(--spacing-4);
}

.figure img {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-md);
}

.figure figcaption {
  margin-top: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  text-align: center;
}

.figure.align-left { margin-right: auto; }
.figure.align-center { margin-inline: auto; }
.figure.align-right { margin-left: auto; }
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/directives/test_video_directives.py

class TestYouTubeDirective:
    """Test YouTube directive rendering and validation."""
    
    def test_basic_embed(self):
        """Test basic YouTube embed with required title."""
        markdown = """
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:::
"""
        result = parse(markdown)
        assert "youtube-nocookie.com" in result  # Privacy default
        assert 'title="Test Video"' in result
        assert 'loading="lazy"' in result
    
    def test_privacy_disabled(self):
        """Test YouTube embed with privacy mode disabled."""
        markdown = """
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:privacy: false
:::
"""
        result = parse(markdown)
        assert "youtube.com/embed" in result
        assert "youtube-nocookie.com" not in result
    
    def test_start_time(self):
        """Test YouTube embed with start time."""
        markdown = """
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:start: 30
:::
"""
        result = parse(markdown)
        assert "start=30" in result
    
    def test_invalid_id_sanitized(self):
        """Test that invalid YouTube IDs are rejected."""
        markdown = """
:::{youtube} invalid<script>alert(1)</script>
:title: Test
:::
"""
        result = parse(markdown)
        assert "<script>" not in result  # XSS prevented
        assert "error" in result.lower() or "invalid" in result.lower()
    
    def test_missing_title_error(self):
        """Test that missing title produces helpful error."""
        markdown = """
:::{youtube} dQw4w9WgXcQ
:::
"""
        result = parse(markdown)
        assert "title" in result.lower() and "required" in result.lower()


class TestFigureDirective:
    """Test figure directive rendering."""
    
    def test_basic_figure(self):
        """Test basic figure with alt text."""
        markdown = """
:::{figure} /images/test.png
:alt: Test image description
:::
"""
        result = parse(markdown)
        assert "<figure" in result
        assert 'alt="Test image description"' in result
        assert 'loading="lazy"' in result
    
    def test_figure_with_caption(self):
        """Test figure with caption renders figcaption."""
        markdown = """
:::{figure} /images/test.png
:alt: Test image
:caption: This is the caption text
:::
"""
        result = parse(markdown)
        assert "<figcaption>" in result
        assert "This is the caption text" in result
    
    def test_decorative_image(self):
        """Test decorative image with empty alt."""
        markdown = """
:::{figure} /images/decorative.png
:alt: ""
:::
"""
        result = parse(markdown)
        assert 'alt=""' in result
```

### Integration Tests

```python
# tests/integration/test_media_directives_build.py

def test_all_media_directives_render_in_build(test_site):
    """Test all embed directives render in full build."""
    # Create test page with all directives
    content = """
---
title: Media Test
---

:::{youtube} dQw4w9WgXcQ
:title: YouTube Test
:::

:::{vimeo} 123456789
:title: Vimeo Test
:::

:::{figure} /images/test.png
:alt: Figure Test
:caption: Test caption
:::
"""
    test_site.create_page("media-test.md", content)
    test_site.build()
    
    output = test_site.read_output("media-test/index.html")
    
    assert "youtube-nocookie.com" in output
    assert "player.vimeo.com" in output
    assert "<figure" in output
    assert "<figcaption>" in output
```

### Security Tests

```python
# tests/unit/directives/test_embed_security.py

@pytest.mark.parametrize("malicious_id", [
    "dQw4w9WgXcQ<script>",
    "dQw4w9WgXcQ\"><img onerror=alert(1)>",
    "../../../etc/passwd",
    "javascript:alert(1)",
    "dQw4w9WgXcQ&autoplay=1&mute=1",  # URL injection
])
def test_youtube_id_sanitization(malicious_id):
    """Test that malicious YouTube IDs are sanitized."""
    result = validate_youtube_id(malicious_id)
    assert result is not None  # Should return error
```

---

## Implementation Plan

### Phase 1: P0 Video Directives (Week 1-2)

| Task | File | Effort | Dependencies |
|------|------|--------|--------------|
| Create `video.py` with VideoDirective base class | `directives/video.py` | 2h | None |
| Implement YouTubeDirective | `directives/video.py` | 3h | base class |
| Implement VimeoDirective | `directives/video.py` | 2h | base class |
| Implement SelfHostedVideoDirective | `directives/video.py` | 2h | base class |
| Add CSS for responsive video containers | `themes/default/assets/css/` | 1h | None |
| Add unit tests | `tests/unit/directives/test_video_directives.py` | 3h | implementations |
| Add integration tests | `tests/integration/test_media_directives_build.py` | 2h | implementations |
| Update documentation | `site/content/docs/reference/directives/` | 2h | implementations |
| Update `__init__.py` registry | `directives/__init__.py` | 0.5h | implementations |

**Subtotal**: 17.5h

### Phase 2: P1 Developer Tools (Week 3-4)

| Task | File | Effort | Dependencies |
|------|------|--------|--------------|
| Create `embed.py` with EmbedDirective base class | `directives/embed.py` | 2h | None |
| Implement GistDirective | `directives/embed.py` | 2h | base class |
| Implement CodePenDirective | `directives/embed.py` | 2h | base class |
| Implement CodeSandboxDirective | `directives/embed.py` | 2h | base class |
| Implement StackBlitzDirective | `directives/embed.py` | 2h | base class |
| Create `terminal.py` for AsciinemaDirective | `directives/terminal.py` | 3h | None |
| Add CSS for embed containers | `themes/default/assets/css/` | 1h | None |
| Add unit tests | `tests/unit/directives/test_embed_directives.py` | 4h | implementations |
| Update documentation | `site/content/docs/reference/directives/` | 3h | implementations |

**Subtotal**: 21h

### Phase 3: P2 Figure & Audio (Week 5)

| Task | File | Effort | Dependencies |
|------|------|--------|--------------|
| Create `figure.py` for FigureDirective | `directives/figure.py` | 3h | None |
| Create AudioDirective in `figure.py` | `directives/figure.py` | 2h | FigureDirective |
| Add CSS for figure styling | `themes/default/assets/css/` | 1h | None |
| Add unit tests | `tests/unit/directives/test_figure_directives.py` | 2h | implementations |
| Update documentation | `site/content/docs/reference/directives/` | 2h | implementations |
| Update Hugo migration guide | `from-hugo.md` | 1h | all phases |

**Subtotal**: 11h

**Total Effort**: ~50h (5 weeks at ~10h/week)

---

## Migration Path

### Hugo Users

Update `site/content/docs/tutorials/onboarding/from-hugo.md` with new equivalents:

| Hugo | Bengal | Notes |
|------|--------|-------|
| `{{</* youtube id */>}}` | `:::{youtube} id` | Privacy-enhanced by default |
| `{{</* youtube id="..." autoplay="true" */>}}` | `:::{youtube} id`<br>`:autoplay: true` | Options as directive options |
| `{{</* vimeo id */>}}` | `:::{vimeo} id` | DNT mode by default |
| `{{</* gist user id */>}}` | `:::{gist} user/id` | Combined user/id format |
| `{{</* gist user id "file.py" */>}}` | `:::{gist} user/id`<br>`:file: file.py` | File as option |
| `{{</* figure src="..." */>}}` | `:::{figure} ...` | Semantic HTML output |
| `{{</* figure src="..." caption="..." */>}}` | `:::{figure} ...`<br>`:caption: ...` | Caption as option |

### Migration Script (Optional)

```python
# scripts/migrate_hugo_shortcodes.py
import re

MIGRATIONS = [
    (r'\{\{<\s*youtube\s+(\S+)\s*>\}\}', r':::{youtube} \1\n:title: TODO - add title\n:::'),
    (r'\{\{<\s*vimeo\s+(\S+)\s*>\}\}', r':::{vimeo} \1\n:title: TODO - add title\n:::'),
    (r'\{\{<\s*gist\s+(\S+)\s+(\S+)\s*>\}\}', r':::{gist} \1/\2\n:::'),
]
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

**Why rejected**: 
- Impossible to validate arbitrary URLs securely
- No type-specific options (start time, theme, etc.)
- CSP would need to allow all frame sources

### 2. Raw HTML Only (Current State)

**Rejected**: Poor DX, no consistency, no privacy defaults, accessibility gaps

**Why rejected**:
- Users write same boilerplate repeatedly
- No enforcement of accessibility requirements
- No privacy-by-default possible

### 3. Template Partials Only

**Rejected**: Requires template knowledge, breaks content/template separation

```jinja2
{% include "partials/youtube.html" with id="..." %}
```

**Why rejected**:
- Content authors shouldn't need to know Jinja
- Partials can't validate inputs at parse time
- Poor DX compared to directives

### 4. oEmbed Auto-Discovery

**Rejected for v1**: Complexity not justified for initial release

```markdown
:::{oembed} https://youtube.com/watch?v=dQw4w9WgXcQ
:::
```

**Why deferred**:
- Requires HTTP requests during build (performance)
- oEmbed responses vary widely in quality
- Security concerns with arbitrary endpoint discovery
- **Future consideration**: Could add as P3 feature

---

## Success Criteria

1. ✅ All P0 video directives implemented with tests
2. ✅ Privacy-enhanced defaults (youtube-nocookie, Vimeo DNT)
3. ✅ Accessibility requirements met (titles required, fallbacks present)
4. ✅ Security validation for all URL/ID inputs (no XSS possible)
5. ✅ Responsive CSS for all embed types
6. ✅ Documentation updated for Hugo migration
7. ✅ At least 90% test coverage for new directives
8. ✅ Health check validates new directive names
9. ✅ CSP requirements documented

---

## Open Questions

1. **Should we support Twitter/X embeds?** 
   - Platform APIs are unstable, embeds break frequently
   - **Recommendation**: No, mark as NG1 (non-goal)

2. **Should `{figure}` support multiple images?** (gallery mode)
   - **Recommendation**: Defer to v2, use `{cards}` with images for now

3. **Should we add `{loom}` for screen recording embeds?** (common in docs)
   - **Recommendation**: Add to P3 backlog, assess demand after v1

4. **Should we support `{pdf}` for embedded PDFs?**
   - **Recommendation**: Add to P2, PDF.js integration useful for docs

5. **Should we support local asciinema recordings (`.cast` files)?**
   - **Recommendation**: Yes, add `:src:` option for local files in v1

---

## Confidence Scoring

### Formula

```
Confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15)
```

### Breakdown

| Component | Score | Reasoning |
|-----------|-------|-----------|
| **Evidence** | 36/40 | Problem verified via `from-hugo.md`. Directive system well-documented. API designs based on established patterns (Hugo, MyST). |
| **Consistency** | 28/30 | Design aligns with existing `BengalDirective` pattern. Follows `rfc-directive-system-v2.md` architecture. Minor gap: no prototype implementation yet. |
| **Recency** | 14/15 | RFC created 2025-12-09. Directive system actively maintained. Hugo migration guide current. |
| **Tests** | 10/15 | Test strategy defined. No implementation yet to test. Patterns follow existing directive tests. |

**Total**: **88/100** 🟢 (High Confidence)

**Gate Status**: ✅ Meets 85% threshold for planning phase.

---

## Appendix: Hugo Built-in Shortcodes Reference

| Hugo Shortcode | Bengal Equivalent | Status |
|----------------|-------------------|--------|
| `figure` | `{figure}` | **Proposed P2** |
| `gist` | `{gist}` | **Proposed P1** |
| `highlight` | Native fenced code blocks | ✅ Exists |
| `instagram` | N/A (API deprecated) | Not planned |
| `param` | `{{ page.metadata.x }}` | ✅ Exists |
| `ref` / `relref` | Cross-reference plugin | ✅ Exists |
| `tweet` | N/A (API unstable) | Not planned |
| `vimeo` | `{vimeo}` | **Proposed P0** |
| `youtube` | `{youtube}` | **Proposed P0** |

---

## References

- [Hugo Built-in Shortcodes](https://gohugo.io/content-management/shortcodes/)
- [Docusaurus MDX Components](https://docusaurus.io/docs/markdown-features)
- [MyST Directives Specification](https://myst-parser.readthedocs.io/en/latest/syntax/directives.html)
- [YouTube IFrame Player API](https://developers.google.com/youtube/iframe_api_reference)
- [Vimeo oEmbed](https://developer.vimeo.com/api/oembed)
- [Asciinema Embedding](https://asciinema.org/docs/embedding)
- [WCAG 2.1 Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- Bengal: `plan/implemented/rfc-directive-system-v2.md` (BengalDirective architecture)
- Bengal: `bengal/rendering/plugins/directives/__init__.py` (directive registry)
