---
title: Images & Media
nav_title: Media
description: Add images, figures, videos, and embeds to your content
weight: 40
category: how-to
icon: image
---
# Images & Media

How to add visual content to your documentation.

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
| `:alt:` | Alt text for accessibility (required) | `:alt: Diagram showing data flow` |
| `:caption:` | Caption displayed below image | `:caption: Figure 1: Architecture` |
| `:align:` | Alignment: `left`, `center`, `right` | `:align: center` |
| `:width:` | Image width | `:width: 80%` or `:width: 400px` |
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

Options:
- `:title:` - Video title (required)
- `:width:` - Player width
- `:autoplay:` - Auto-play on load
- `:mute:` - Start muted

:::{note}
Bengal uses privacy-enhanced mode (`youtube-nocookie.com`) by default for GDPR compliance.
:::

### Vimeo

```markdown
:::{vimeo} 123456789
:title: Video Title
:::
```

### Self-Hosted Video

```markdown
:::{video} /videos/demo.mp4
:title: Product Demo
:poster: /images/demo-poster.jpg
:controls:
:::
```

Options:
- `:title:` - Video title
- `:poster:` - Preview image
- `:controls:` - Show player controls
- `:autoplay:` - Auto-play
- `:loop:` - Loop playback
- `:muted:` - Start muted

## Audio

```markdown
:::{audio} /audio/podcast-episode.mp3
:title: Episode 1: Getting Started
:controls:
:::
```

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

### CodeSandbox

```markdown
:::{codesandbox} sandbox_id
:title: React Example
:view: preview
:::
```

### StackBlitz

```markdown
:::{stackblitz} project_id
:title: Node.js Demo
:file: index.js
:::
```

## Terminal Recordings

Embed terminal recordings with Asciinema:

```markdown
:::{asciinema} 123456
:title: Installation walkthrough
:speed: 1.5
:rows: 24
:::
```

## Icons

Inline icons using the icon library:

```markdown
Check {icon}`check:24:icon-success` indicates success.

Click {icon}`settings` to open settings.
```

See [[docs/reference/icons|Icon Reference]] for the complete icon gallery.

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
