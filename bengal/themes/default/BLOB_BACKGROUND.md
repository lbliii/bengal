# Organic Blob Background Animation

Peaceful, organic blob animations for hero sections that adapt to light and dark themes.

## Features

- ✨ Peaceful floating blob animations
- 🌓 Automatic light/dark mode support
- 🎨 Uses semantic design tokens
- ♿ Respects `prefers-reduced-motion`
- 🎯 Subtle, non-distracting background effect

## Usage

Enable blob background on any hero section by adding `blob_background: true` to your page metadata:

```yaml
---
title: Welcome to Bengal
blob_background: true
description: A modern static site generator
---
```

Or add the modifier class directly in templates:

```html
<header class="hero hero--large hero--blob-background">
  <!-- Hero content -->
</header>
```

## Customization

Blob colors are controlled via semantic tokens in `tokens/semantic.css`:

```css
/* Light mode */
--color-blob-1: var(--blue-400);
--color-blob-2: var(--purple-400);
--color-blob-3: var(--orange-400);
--color-blob-4: var(--green-400);
--color-blob-opacity: 0.15;
--color-blob-blur: 60px;

/* Dark mode */
--color-blob-1: var(--blue-500);
--color-blob-2: var(--purple-500);
--color-blob-3: var(--orange-500);
--color-blob-4: var(--green-500);
--color-blob-opacity: 0.12;
--color-blob-blur: 80px;
```

Override in your site's CSS:

```css
:root {
  --color-blob-1: #your-color;
  --color-blob-opacity: 0.2; /* More visible */
}
```

## Technical Details

- Uses CSS `filter: blur()` for organic shapes
- `mix-blend-mode: screen` for color blending
- GPU-accelerated transforms for smooth animation
- Four blobs with independent animation timings (8s, 10s, 12s, 9s)
- Animations disabled when `prefers-reduced-motion: reduce`

## Browser Support

Works in all modern browsers that support:
- CSS `filter` property
- CSS `mix-blend-mode`
- CSS `@keyframes`

Fallback: Blobs gracefully degrade to static shapes in older browsers.
