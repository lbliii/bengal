---
title: Images & Media
nav_title: Media
description: Add images, figures, videos, and embeds to your content
weight: 40
category: how-to
icon: image
---
# Images & Media

Add visual content to your documentation with images, videos, and interactive embeds.

## Basic Images

Use standard Markdown syntax:

```markdown
![Alt text](/images/screenshot.png)
```

With a title (shows on hover):

```markdown
![Alt text](/images/screenshot.png "Image title")
```

## Figures with Captions

For images that need captions, use the `figure` directive:

```markdown
:::{figure} /images/architecture.png
:alt: System architecture diagram
:caption: Overview of the Bengal build pipeline
:align: center
:::
```

### Figure Options

| Option | Description | Example |
|--------|-------------|---------|
| `:alt:` | Alt text for accessibility | `:alt: Diagram showing data flow` |
| `:caption:` | Caption displayed below image | `:caption: Figure 1: Architecture` |
| `:align:` | Alignment: `left`, `center`, `right` | `:align: center` |
| `:width:` | Image width | `:width: 80%` or `:width: 400px` |
| `:height:` | Image height | `:height: 300px` |
| `:link:` | URL to link image to | `:link: /docs/architecture/` |
| `:target:` | Link target: `_self`, `_blank` | `:target: _blank` |
| `:loading:` | Loading strategy: `lazy` (default), `eager` | `:loading: lazy` |
| `:class:` | CSS class for styling | `:class: rounded shadow` |

### Example with All Options

```markdown
:::{figure} /images/workflow.png
:alt: Content workflow diagram
:caption: How content flows through Bengal
:align: center
:width: 80%
:class: rounded
:::
```

## Image Paths

| Path Type | Example | Use When |
|-----------|---------|----------|
| **Absolute** | `/images/logo.png` | Images in `assets/images/` |
| **Relative** | `./screenshot.png` | Co-located with content (page bundles) |
| **External** | `https://example.com/img.png` | External images |

:::{tip}
For page-specific images, use [page bundles](/docs/content/organization/) — put images next to your markdown file and reference them with `./image.png`.
:::

## Videos

### YouTube

```markdown
:::{youtube} dQw4w9WgXcQ
:title: Video Title (required for accessibility)
:::
```

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | — | Video title (required for accessibility) |
| `:width:` | `100%` | Player width |
| `:start:` | — | Start time in seconds |
| `:end:` | — | End time in seconds |
| `:privacy:` | `true` | Use `youtube-nocookie.com` |
| `:autoplay:` | `false` | Auto-play on load |
| `:muted:` | `false` | Start muted |
| `:loop:` | `false` | Loop playback |
| `:controls:` | `true` | Show player controls |

:::{note}
Bengal uses privacy-enhanced mode (`youtube-nocookie.com`) by default for GDPR compliance. Set `:privacy: false` to use standard YouTube.
:::

### Vimeo

```markdown
:::{vimeo} 123456789
:title: Video Title
:::
```

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | — | Video title (required) |
| `:dnt:` | `true` | Do Not Track mode for privacy |
| `:color:` | — | Player accent color (hex without `#`) |
| `:autoplay:` | `false` | Auto-play on load |
| `:muted:` | `false` | Start muted |
| `:loop:` | `false` | Loop playback |

### Self-Hosted Video

```markdown
:::{video} /videos/demo.mp4
:title: Product Demo
:poster: /images/demo-poster.jpg
:controls:
:::
```

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | — | Video title (required) |
| `:poster:` | — | Preview image before playback |
| `:controls:` | `true` | Show player controls |
| `:autoplay:` | `false` | Auto-play (requires `:muted:`) |
| `:muted:` | `false` | Start muted |
| `:loop:` | `false` | Loop playback |
| `:preload:` | `metadata` | Preload mode: `none`, `metadata`, `auto` |

## Audio

```markdown
:::{audio} /audio/podcast-episode.mp3
:title: Episode 1: Getting Started
:controls:
:::
```

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | — | Audio title (required) |
| `:controls:` | `true` | Show audio controls |
| `:autoplay:` | `false` | Auto-play |
| `:loop:` | `false` | Loop playback |
| `:muted:` | `false` | Start muted |
| `:preload:` | `metadata` | Preload mode: `none`, `metadata`, `auto` |

## Code Playgrounds

### GitHub Gist

```markdown
:::{gist} username/gist_id
:file: specific_file.py
:::
```

### CodePen

```markdown
:::{codepen} username/pen_id
:title: Interactive Demo
:height: 400
:default-tab: result
:::
```

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | — | Pen title (required) |
| `:height:` | `300` | Height in pixels |
| `:default-tab:` | `result` | Tab to show: `html`, `css`, `js`, `result` |
| `:theme:` | `dark` | Color theme: `light`, `dark` |
| `:editable:` | `false` | Allow editing |

### CodeSandbox

```markdown
:::{codesandbox} sandbox_id
:title: React Example
:view: preview
:::
```

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | — | Sandbox title (required) |
| `:view:` | `split` | Display mode: `editor`, `preview`, `split` |
| `:height:` | `500` | Height in pixels |
| `:module:` | — | File to show initially |
| `:theme:` | `dark` | Color theme: `light`, `dark` |

### StackBlitz

```markdown
:::{stackblitz} project_id
:title: Node.js Demo
:file: index.js
:::
```

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | — | Project title (required) |
| `:file:` | — | File to show initially |
| `:view:` | `both` | Display mode: `editor`, `preview`, `both` |
| `:height:` | `500` | Height in pixels |

## Terminal Recordings

Embed terminal recordings with Asciinema:

```markdown
:::{asciinema} 123456
:title: Installation walkthrough
:speed: 1.5
:rows: 24
:::
```

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | — | Recording title (required) |
| `:cols:` | `80` | Terminal columns |
| `:rows:` | `24` | Terminal rows |
| `:speed:` | `1.0` | Playback speed multiplier |
| `:autoplay:` | `false` | Auto-start playback |
| `:loop:` | `false` | Loop playback |
| `:theme:` | `asciinema` | Color theme name |

## Icons

Inline icons using the icon library:

```markdown
The {icon}`terminal` icon indicates CLI commands.

Click {icon}`bengal-rosette:32` for the Bengal logo.
```

Syntax: `{icon}\`name\`` or `{icon}\`name:size\`` or `{icon}\`name:size:class\``

See [[docs/reference/icons|Icon Reference]] for available icons.

## Accessibility Checklist

:::{checklist}

- Always provide meaningful `:alt:` text for images
- Always provide `:title:` for video/audio embeds
- Use empty `:alt:` for decorative images only
- Ensure sufficient color contrast in diagrams
- Provide text alternatives for complex visuals

:::

## Best Practices

:::{checklist}

- Use `figure` for images that need captions
- Optimize images before adding to your site
- Use relative paths for page-specific images
- Add descriptive alt text for accessibility
- Consider lazy loading for image-heavy pages

:::

::::{seealso}

- [[docs/reference/directives/media|Media Directives Reference]] — Complete options
- [[docs/reference/icons|Icon Reference]] — Available icons
- [[docs/theming/assets|Asset Pipeline]] — Image optimization

::::
