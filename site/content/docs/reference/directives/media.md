---
title: Media Directives
nav_title: Media
description: Reference for media embed directives (YouTube, Vimeo, TikTok, Spotify, SoundCloud, video, audio, figure, code playgrounds, terminal recordings)
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
- tiktok
- spotify
- soundcloud
- figure
keywords:
- youtube
- vimeo
- tiktok
- spotify
- soundcloud
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
| `{tiktok}` | TikTok video | `:title:` |
| `{video}` | Self-hosted video | `:title:` |
| `{spotify}` | Spotify track/album/playlist/podcast | `:title:` |
| `{soundcloud}` | SoundCloud track/playlist | `:title:` |
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
| `:width:` | `100%` | Container width (`100%`, `80%`, `800px`) |
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

**Live example**:

:::{youtube} dQw4w9WgXcQ
:title: Rick Astley - Never Gonna Give You Up
:::

With start time (starts at 43 seconds):

```markdown
:::{youtube} dQw4w9WgXcQ
:title: Rick Astley - Never Gonna Give You Up (Chorus)
:start: 43
:::
```

**Live example**:

:::{youtube} dQw4w9WgXcQ
:title: Rick Astley - Never Gonna Give You Up (Chorus)
:start: 43
:::

With custom width (50%):

```markdown
:::{youtube} dQw4w9WgXcQ
:title: Rick Astley - Never Gonna Give You Up
:width: 50%
:::
```

**Live example**:

:::{youtube} dQw4w9WgXcQ
:title: Rick Astley - Never Gonna Give You Up (50% width)
:width: 50%
:::

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
| `:width:` | `100%` | Container width (`100%`, `80%`, `800px`) |
| `:dnt:` | `true` | Enable Do Not Track mode |
| `:color:` | — | Player accent color (hex without `#`) |
| `:autopause:` | `true` | Pause when another video starts |
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
:::{vimeo} 203011020
:title: Beautiful Cinematic Video
:::
```

**Live example**:

:::{vimeo} 203011020
:title: Beautiful Cinematic Video
:::

With custom accent color:

```markdown
:::{vimeo} 203011020
:title: Beautiful Cinematic Video
:color: 00adef
:::
```

**Live example**:

:::{vimeo} 203011020
:title: Beautiful Cinematic Video
:color: 00adef
:::

### TikTok

Embed TikTok videos. Ideal for blogs and social content.

**Syntax**:

```markdown
:::{tiktok} VIDEO_ID
:title: Video title for accessibility
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title for the iframe |
| `:width:` | `100%` | Container width (`100%`, `80%`, `400px`) |
| `:autoplay:` | `false` | Auto-start video |
| `:muted:` | `false` | Start muted |
| `:loop:` | `false` | Loop video |
| `:aspect:` | `9/16` | Aspect ratio (vertical by default) |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{tiktok} 7251756576833309995
:title: Bengal Cat Video
:::
```

**Live example**:

:::{tiktok} 7251756576833309995
:title: Bengal Cat from @bengalsofbama
:::

:::{tip}
TikTok video IDs are 19 digits. Find them in the URL: `tiktok.com/@user/video/7251756576833309995`
:::

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
| `:width:` | `100%` | Video width (px or %) |
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
| `:muted:` | `false` | Start muted |
| `:loop:` | `false` | Loop audio |
| `:controls:` | `true` | Show player controls |
| `:preload:` | `metadata` | Preload strategy |
| `:class:` | — | Additional CSS classes |

**Supported formats**: `.mp3`, `.ogg`, `.wav`, `.flac`, `.m4a`, `.aac`

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

## Audio Streaming Embeds

### Spotify

Embed Spotify tracks, albums, playlists, and podcast episodes.

**Syntax**:

```markdown
:::{spotify} SPOTIFY_ID
:title: Track/Album/Playlist title
:type: track
:::
```

The `SPOTIFY_ID` is the 22-character alphanumeric ID from the Spotify URL. For example, in `https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh`, the ID is `4iV5W9uYEdYUVa79Axb7Rh`.

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title for iframe |
| `:type:` | `track` | Content type: `track`, `album`, `playlist`, `episode`, `show`, `artist` |
| `:height:` | (auto) | Embed height in pixels (auto-detected by type) |
| `:theme:` | `0` | Color theme: `0` for dark, `1` for light |
| `:class:` | — | Additional CSS classes |

**Default heights by type**:

| Type | Height |
|------|--------|
| `track` | 152px |
| `album`, `playlist`, `show`, `artist` | 352px |
| `episode` | 232px |

:::{example-label} Examples
:::

**Track embed**:

```markdown
:::{spotify} 13JAl3SvRcko5HgfwMU5q5
:title: CCTV by Phantoms & JEV
:type: track
:::
```

:::{spotify} 13JAl3SvRcko5HgfwMU5q5
:title: CCTV by Phantoms & JEV
:type: track
:::

**Album embed**:

```markdown
:::{spotify} 5xBJBxfQFowtJ5yq7MnXMG
:title: HEAT by Tove Lo
:type: album
:::
```

:::{spotify} 5xBJBxfQFowtJ5yq7MnXMG
:title: HEAT by Tove Lo
:type: album
:::

**Playlist embed**:

```markdown
:::{spotify} 37i9dQZF1DXcBWIGoYBM5M
:title: Today's Top Hits
:type: playlist
:::
```

:::{spotify} 37i9dQZF1DXcBWIGoYBM5M
:title: Today's Top Hits
:type: playlist
:::

**Podcast episode**:

```markdown
:::{spotify} 4rOoJ6Egrf8K2IrywzwOMk
:title: The Joe Rogan Experience Episode
:type: episode
:::
```

:::{spotify} 4rOoJ6Egrf8K2IrywzwOMk
:title: The Joe Rogan Experience Episode
:type: episode
:::

**Light theme**:

```markdown
:::{spotify} 13JAl3SvRcko5HgfwMU5q5
:title: CCTV by Phantoms & JEV
:type: track
:theme: 1
:::
```

:::{spotify} 13JAl3SvRcko5HgfwMU5q5
:title: CCTV by Phantoms & JEV
:type: track
:theme: 1
:::

### SoundCloud

Embed SoundCloud tracks and playlists.

**Syntax**:

```markdown
:::{soundcloud} username/track-name
:title: Track title
:::
```

Use the path from the SoundCloud URL (everything after `soundcloud.com/`). You can also paste the full URL — the directive will extract the path automatically.

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible title for iframe |
| `:type:` | `track` | Content type: `track` or `playlist` |
| `:height:` | (auto) | Embed height in pixels (auto-detected by type) |
| `:color:` | `ff5500` | Accent color hex without # |
| `:autoplay:` | `false` | Auto-start playback |
| `:hide_related:` | `false` | Hide related tracks |
| `:show_comments:` | `true` | Show comments |
| `:show_user:` | `true` | Show uploader info |
| `:show_reposts:` | `false` | Show reposts |
| `:visual:` | `false` | Use visual player (larger artwork) |
| `:class:` | — | Additional CSS classes |

**Default heights by type**:

| Type | Height |
|------|--------|
| `track` | 166px |
| `track` (visual) | 300px |
| `playlist` | 450px |

:::{example-label} Examples
:::

**Track embed** (from URL path):

```markdown
:::{soundcloud} user-604227447/celine-dion-the-whispers-im-alive-x-and-the-beat-goes-on-the-jammin-kid-mashup
:title: I'm Alive x And The Beat Goes On (Mashup)
:::
```

:::{soundcloud} user-604227447/celine-dion-the-whispers-im-alive-x-and-the-beat-goes-on-the-jammin-kid-mashup
:title: I'm Alive x And The Beat Goes On (Mashup)
:::

**Visual player**:

```markdown
:::{soundcloud} user-604227447/celine-dion-the-whispers-im-alive-x-and-the-beat-goes-on-the-jammin-kid-mashup
:title: I'm Alive x And The Beat Goes On (Mashup)
:visual: true
:::
```

:::{soundcloud} user-604227447/celine-dion-the-whispers-im-alive-x-and-the-beat-goes-on-the-jammin-kid-mashup
:title: I'm Alive x And The Beat Goes On (Mashup)
:visual: true
:::

**Custom accent color**:

```markdown
:::{soundcloud} user-604227447/celine-dion-the-whispers-im-alive-x-and-the-beat-goes-on-the-jammin-kid-mashup
:title: I'm Alive x And The Beat Goes On (Mashup)
:color: 8b5cf6
:::
```

:::{soundcloud} user-604227447/celine-dion-the-whispers-im-alive-x-and-the-beat-goes-on-the-jammin-kid-mashup
:title: I'm Alive x And The Beat Goes On (Mashup)
:color: 8b5cf6
:::

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
:::{gist} lbliii/21314a0babc8838bc2b5eecb53faec75
:::
```

**Live example**:

:::{gist} lbliii/21314a0babc8838bc2b5eecb53faec75
:::

Specific file from multi-file gist:

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
| `:height:` | `300` | Embed height in pixels |
| `:editable:` | `false` | Allow editing in embed |
| `:preview:` | `true` | Show preview on load |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{codepen} mrdanielschwarz/VYaPVgr
:title: CSS Animation Demo
:::
```

**Live example**:

:::{codepen} mrdanielschwarz/VYaPVgr
:title: CSS Animation Demo
:height: 400
:::

With CSS tab visible:

```markdown
:::{codepen} mrdanielschwarz/VYaPVgr
:title: CSS Animation Demo
:default-tab: css
:height: 400
:::
```

**Live example**:

:::{codepen} mrdanielschwarz/VYaPVgr
:title: CSS Animation Demo
:default-tab: css
:height: 400
:::

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
| `:fontsize:` | `14` | Editor font size in pixels |
| `:hidenavigation:` | `false` | Hide file navigation sidebar |
| `:theme:` | `dark` | Color theme (`dark`, `light`) |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{codesandbox} new
:title: New Sandbox
:::
```

**Live example**:

:::{codesandbox} new
:title: New Sandbox
:height: 400
:::

With preview only:

```markdown
:::{codesandbox} new
:title: New Sandbox Preview
:view: preview
:height: 400
:::
```

**Live example**:

:::{codesandbox} new
:title: New Sandbox Preview
:view: preview
:height: 400
:::

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
| `:hidenavigation:` | `false` | Hide file navigation sidebar |
| `:hidedevtools:` | `false` | Hide dev tools panel |
| `:class:` | — | Additional CSS classes |

:::{example-label} Examples
:::

Basic embed:

```markdown
:::{stackblitz} vitejs-vite
:title: Vite Starter Project
:::
```

**Live example**:

:::{stackblitz} vitejs-vite
:title: Vite Starter Project
:height: 450
:::

With preview only:

```markdown
:::{stackblitz} vitejs-vite
:title: Vite Starter Preview
:view: preview
:height: 400
:::
```

**Live example**:

:::{stackblitz} vitejs-vite
:title: Vite Starter Preview
:view: preview
:height: 400
:::

## Terminal Recordings

### Asciinema

Embed terminal recordings from asciinema.org or local `.cast` files.

**Syntax**:

Remote recording (asciinema.org):
```markdown
:::{asciinema} RECORDING_ID
:title: Recording title for accessibility
:::
```

Local recording file:
```markdown
:::{asciinema} recordings/demo.cast
:title: Recording title for accessibility
:::
```

**Input**:
- **Numeric ID** (e.g., `590029`) for asciinema.org recordings
- **File path** ending in `.cast` (e.g., `recordings/demo.cast`) for local files
  - Local files should be placed in your `static/` directory
  - Paths are resolved relative to site root (e.g., `static/recordings/demo.cast` → `/recordings/demo.cast`)

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | (required) | Accessible ARIA label |
| `:cols:` | `80` | Terminal width in columns |
| `:rows:` | `24` | Terminal height in rows |
| `:speed:` | `1.0` | Playback speed multiplier |
| `:autoplay:` | `false` | Auto-start playback |
| `:loop:` | `false` | Loop recording |
| `:theme:` | `asciinema` | Color theme name |
| `:poster:` | `npt:0:0` | Preview frame (`npt:MM:SS` format) |
| `:idle-time-limit:` | — | Max idle time between frames (seconds) |
| `:start-at:` | — | Start playback at specific time |
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

With custom theme and idle time limit:

```markdown
:::{asciinema} 590029
:title: Build process demo
:theme: monokai
:idle-time-limit: 2
:poster: npt:0:5
:::
```

Using a local recording file:

```markdown
:::{asciinema} recordings/install-demo.cast
:title: Installation walkthrough
:cols: 120
:speed: 1.5
:autoplay: true
:::
```

**Note**: For local files, place your `.cast` files in the `static/` directory (e.g., `static/recordings/demo.cast`). The directive will automatically load the asciinema player and initialize it with your local file.

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
- [Hugo Migration](/docs/tutorials/migration/from-hugo/) - Migrating from Hugo shortcodes
