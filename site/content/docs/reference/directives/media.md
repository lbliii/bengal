---
title: Media Directives
description: Reference for media embed directives (YouTube, Vimeo, video, audio, figure, code playgrounds, terminal recordings)
weight: 15
tags:
- reference
- directives
- media
- video
- audio
- embed
- youtube
- vimeo
- figure
keywords:
- youtube
- vimeo
- video
- audio
- figure
- embed
- codepen
- codesandbox
- stackblitz
- gist
- asciinema
---

# Media Directives

Media directives embed external content like videos, code playgrounds, and terminal recordings into your documentation. All embeds are **privacy-respecting by default** and meet **WCAG 2.1 AA** accessibility requirements.

## Quick Reference

| Directive | Purpose | Required Options |
|-----------|---------|------------------|
| `{youtube}` | YouTube video | `:title:` |
| `{vimeo}` | Vimeo video | `:title:` |
| `{video}` | Self-hosted video | `:title:` |
| `{figure}` | Image with caption | `:alt:` |
| `{audio}` | Self-hosted audio | `:title:` |
| `{gist}` | GitHub Gist | — |
| `{codepen}` | CodePen embed | `:title:` |
| `{codesandbox}` | CodeSandbox embed | `:title:` |
| `{stackblitz}` | StackBlitz embed | `:title:` |
| `{asciinema}` | Terminal recording | `:title:` |

## Video Embeds

### YouTube

Embed YouTube videos with privacy-enhanced mode enabled by default (`youtube-nocookie.com`).

**Syntax**:

```markdown
:::{youtube} VIDEO_ID
:title: Video title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title for the iframe |
| `:privacy:` | `true` | Use `youtube-nocookie.com` |
| `:start:` | — | Start time in seconds |
| `:end:` | — | End time in seconds |
| `:autoplay:` | `false` | Auto-start video |
| `:muted:` | `false` | Start muted (required with autoplay) |
| `:loop:` | `false` | Loop video |
| `:controls:` | `true` | Show player controls |
| `:aspect:` | `16/9` | Aspect ratio (`16/9`, `4/3`, `21/9`) |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{youtube} dQw4w9WgXcQ
:title: Rick Astley - Never Gonna Give You Up
:::
```

With start time and custom aspect ratio:

```markdown
:::{youtube} dQw4w9WgXcQ
:title: Rick Astley - Never Gonna Give You Up
:start: 30
:aspect: 4/3
:::
```

Background video (autoplay, muted, looped, no controls):

```markdown
:::{youtube} dQw4w9WgXcQ
:title: Background video
:autoplay: true
:muted: true
:loop: true
:controls: false
:::
```

### Vimeo

Embed Vimeo videos with Do Not Track enabled by default.

**Syntax**:

```markdown
:::{vimeo} VIDEO_ID
:title: Video title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title for the iframe |
| `:dnt:` | `true` | Enable Do Not Track mode |
| `:color:` | — | Player accent color (hex without `#`) |
| `:background:` | `false` | Background mode (no controls) |
| `:autoplay:` | `false` | Auto-start video |
| `:muted:` | `false` | Start muted |
| `:loop:` | `false` | Loop video |
| `:aspect:` | `16/9` | Aspect ratio |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{vimeo} 123456789
:title: My Vimeo Video
:::
```

With custom color:

```markdown
:::{vimeo} 123456789
:title: My Vimeo Video
:color: ff0000
:::
```

### Self-Hosted Video

Embed videos from your own server using HTML5 `<video>`.

**Syntax**:

```markdown
:::{video} /path/to/video.mp4
:title: Video title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title |
| `:poster:` | — | Poster image path |
| `:autoplay:` | `false` | Auto-start video |
| `:muted:` | `false` | Start muted |
| `:loop:` | `false` | Loop video |
| `:controls:` | `true` | Show player controls |
| `:preload:` | `metadata` | Preload strategy (`none`, `metadata`, `auto`) |
| `:aspect:` | `16/9` | Aspect ratio |
| `:class:` | — | Additional CSS classes |

**Supported formats**: `.mp4`, `.webm`, `.ogg`, `.mov`

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{video} /assets/demo.mp4
:title: Product Demo
:::
```

With poster and options:

```markdown
:::{video} /assets/demo.mp4
:title: Product Demo
:poster: /assets/demo-poster.jpg
:preload: auto
:::
```

## Figure (Images with Captions)

Create semantic `<figure>` elements with optional captions, links, and alignment.

**Syntax**:

```markdown
:::{figure} /path/to/image.png
:alt: Descriptive alt text
:caption: Optional caption text
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:alt:` | (required) | Alt text (empty for decorative images) |
| `:caption:` | — | Caption text below image |
| `:width:` | — | Image width (`80%`, `500px`) |
| `:height:` | — | Image height |
| `:align:` | — | Alignment (`left`, `center`, `right`) |
| `:link:` | — | URL to link image to |
| `:target:` | — | Link target (`_blank` for new tab) |
| `:loading:` | `lazy` | Loading strategy (`lazy`, `eager`) |
| `:class:` | — | Additional CSS classes |

**Supported formats**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.avif`

:::{example-label} Examples
:::

Basic figure with alt text:

```markdown
:::{figure} /images/architecture.png
:alt: System architecture diagram showing component relationships
:::
```

With caption and alignment:

```markdown
:::{figure} /images/screenshot.png
:alt: Application dashboard
:caption: The main dashboard showing key metrics
:align: center
:width: 80%
:::
```

Linked image opening in new tab:

```markdown
:::{figure} /images/diagram.png
:alt: Workflow diagram
:link: https://example.com/full-diagram
:target: _blank
:::
```

Decorative image (empty alt):

```markdown
:::{figure} /images/decorative-border.png
:alt:
:::
```

## Audio

Embed self-hosted audio files using HTML5 `<audio>`.

**Syntax**:

```markdown
:::{audio} /path/to/audio.mp3
:title: Audio title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title |
| `:autoplay:` | `false` | Auto-start audio |
| `:loop:` | `false` | Loop audio |
| `:controls:` | `true` | Show player controls |
| `:preload:` | `metadata` | Preload strategy |
| `:class:` | — | Additional CSS classes |

**Supported formats**: `.mp3`, `.ogg`, `.wav`, `.m4a`

:::{example-label} Examples
:::

Basic audio:

```markdown
:::{audio} /assets/podcast-episode-1.mp3
:title: Episode 1 - Getting Started
:::
```

Background audio:

```markdown
:::{audio} /assets/ambience.mp3
:title: Ambient sound
:autoplay: true
:loop: true
:controls: false
:::
```

## Code Playground Embeds

### GitHub Gist

Embed GitHub Gists with optional file selection.

**Syntax**:

```markdown
:::{gist} USERNAME/GIST_ID
:file: optional-filename.py
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:file:` | — | Specific file from multi-file gist |

:::{example-label} Examples
:::

Basic gist:

```markdown
:::{gist} octocat/12345678901234567890123456789012
:::
```

Specific file:

```markdown
:::{gist} octocat/12345678901234567890123456789012
:file: example.py
:::
```

### CodePen

Embed CodePen pens.

**Syntax**:

```markdown
:::{codepen} USERNAME/PEN_ID
:title: Pen title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title |
| `:default-tab:` | `result` | Default tab (`html`, `css`, `js`, `result`) |
| `:theme:` | `dark` | Theme (`dark`, `light`) |
| `:height:` | `400` | Embed height in pixels |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{codepen} chriscoyier/KBQqza
:title: CSS Grid Layout Example
:::
```

With HTML tab visible:

```markdown
:::{codepen} chriscoyier/KBQqza
:title: CSS Grid Layout Example
:default-tab: html
:height: 500
:::
```

### CodeSandbox

Embed CodeSandbox projects.

**Syntax**:

```markdown
:::{codesandbox} SANDBOX_ID
:title: Sandbox title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title |
| `:module:` | — | Initial file to open (`/src/App.js`) |
| `:view:` | `split` | View mode (`editor`, `preview`, `split`) |
| `:height:` | `500` | Embed height in pixels |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{codesandbox} new-react-app
:title: React Starter
:::
```

With specific file:

```markdown
:::{codesandbox} new-react-app
:title: React Starter
:module: /src/App.js
:view: editor
:::
```

### StackBlitz

Embed StackBlitz projects.

**Syntax**:

```markdown
:::{stackblitz} PROJECT_ID
:title: Project title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title |
| `:file:` | — | Initial file to open |
| `:view:` | `both` | View mode (`editor`, `preview`, `both`) |
| `:height:` | `500` | Embed height in pixels |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{stackblitz} angular-quickstart
:title: Angular Quickstart
:::
```

With specific file:

```markdown
:::{stackblitz} angular-quickstart
:title: Angular Quickstart
:file: src/app.component.ts
:view: editor
:::
```

## Terminal Recordings

### Asciinema

Embed terminal recordings from asciinema.org.

**Syntax**:

```markdown
:::{asciinema} RECORDING_ID
:title: Recording title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible ARIA label |
| `:cols:` | — | Terminal width in columns |
| `:rows:` | — | Terminal height in rows |
| `:speed:` | `1.0` | Playback speed multiplier |
| `:autoplay:` | `false` | Auto-start playback |
| `:loop:` | `false` | Loop recording |
| `:preload:` | `false` | Preload recording data |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{asciinema} 590029
:title: Installing Bengal with pip
:::
```

With custom size and speed:

```markdown
:::{asciinema} 590029
:title: Installing Bengal with pip
:cols: 120
:rows: 30
:speed: 2.0
:autoplay: true
:::
```

## Accessibility Requirements

All media embeds follow **WCAG 2.1 AA** guidelines:

1. **Required titles**: All iframes require a `:title:` option for screen readers
2. **Alt text**: Figures require `:alt:` text (use empty string for decorative images)
3. **Fallback content**: All embeds include `<noscript>` fallbacks with direct links
4. **Keyboard navigation**: Video/audio players support keyboard controls
5. **ARIA labels**: Terminal recordings use `role="img"` and `aria-label`

## Privacy Features

Media embeds are **privacy-respecting by default**:

- **YouTube**: Uses `youtube-nocookie.com` (disable with `:privacy: false`)
- **Vimeo**: Enables Do Not Track (disable with `:dnt: false`)
- **No third-party tracking**: Self-hosted options available for video, audio, figures

## Security

All media directives validate inputs to prevent:

- **XSS attacks**: ID/URL validation rejects malicious input
- **Path traversal**: Local paths cannot escape content directory
- **Iframe sandboxing**: External embeds use restricted sandbox attributes

## Responsive Design

All embeds use CSS `aspect-ratio` for fluid responsive layouts:

```css
.video-embed iframe,
.video-embed video {
  aspect-ratio: var(--video-aspect, 16/9);
}
```

Override the aspect ratio with the `:aspect:` option or custom CSS classes.

## Related

- [Layout Directives](/docs/reference/directives/layout/) - Cards, tabs, grids
- [Interactive Directives](/docs/reference/directives/interactive/) - Code tabs, data tables
- [Hugo Migration](/docs/tutorials/onboarding/from-hugo/) - Migrating from Hugo shortcodes

