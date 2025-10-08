# Default Theme: Next Implementation Priorities

**Date**: October 8, 2025  
**Current State**: Feature-rich documentation/blog theme  
**Purpose**: Identify highest-impact improvements

---

## Executive Summary

The Bengal default theme is **already quite comprehensive** with:
- ✅ Dark mode toggle with persistence
- ✅ Mobile-first responsive design
- ✅ Full-text search (Lunr.js) with smart preloading
- ✅ Advanced interactions (back-to-top, reading progress, scroll spy)
- ✅ Accessibility features (ARIA, skip links, keyboard nav)
- ✅ SEO optimization (Open Graph, Twitter Cards, structured data)
- ✅ Modern CSS architecture (semantic design tokens)
- ✅ Rich documentation features (TOC, breadcrumbs, navigation)

**What's Missing**: PWA features, social sharing implementation, keyboard shortcuts, version switching, and some polish.

**Top Priority**: **Progressive Web App (PWA) support** - Make documentation available offline

---

## Current Feature Inventory

### ✅ Already Implemented (Excellent)

| Feature | Status | Quality |
|---------|--------|---------|
| **Core UX** | | |
| Dark/Light mode toggle | ✅ Complete | Excellent - localStorage + system preference |
| Mobile navigation | ✅ Complete | Excellent - slide-out menu with animation |
| Responsive design | ✅ Complete | Excellent - mobile-first approach |
| Smooth scrolling | ✅ Complete | Good - respects prefers-reduced-motion |
| Back-to-top button | ✅ Complete | Good - appears after 300px scroll |
| Reading progress bar | ✅ Complete | Good - top bar indicator |
| **Navigation** | | |
| Hierarchical menus | ✅ Complete | Excellent - nested dropdowns |
| Breadcrumbs | ✅ Complete | Good - uses ancestors system |
| Table of contents | ✅ Complete | Excellent - scroll spy, sidebar |
| Prev/Next navigation | ✅ Complete | Good - section-aware |
| Scroll spy (active TOC) | ✅ Complete | Good - highlights current heading |
| **Search** | | |
| Full-text search | ✅ Complete | Excellent - Lunr.js based |
| Smart preloading | ✅ Complete | Excellent - 3 modes (immediate/smart/lazy) |
| Search shortcut (⌘K) | ✅ Complete | Good - keyboard accessible |
| **Content Features** | | |
| Code copy buttons | ✅ Complete | Good - with visual feedback |
| Image lightbox | ✅ Complete | Good - click to enlarge |
| Lazy loading images | ✅ Complete | Good - IntersectionObserver |
| External link handling | ✅ Complete | Good - auto rel/target |
| Tabs/Dropdowns | ✅ Complete | Good - for code examples |
| Admonitions | ✅ Complete | Excellent - 7+ types |
| **Accessibility** | | |
| Skip to content link | ✅ Complete | Good - hidden until focused |
| ARIA labels | ✅ Complete | Good - navigation, landmarks |
| Keyboard navigation | ✅ Complete | Good - detects tab key |
| Focus indicators | ✅ Complete | Good - visible for keyboard users |
| Reduced motion support | ✅ Complete | Good - respects preference |
| **SEO & Sharing** | | |
| Open Graph tags | ✅ Complete | Excellent - title, desc, image |
| Twitter Cards | ✅ Complete | Good - summary_large_image |
| Canonical URLs | ✅ Complete | Good - prevents duplicates |
| RSS feed link | ✅ Complete | Good - auto-discovery |
| Structured meta | ✅ Complete | Good - keywords, description |
| **Design System** | | |
| Semantic design tokens | ✅ Complete | Excellent - 200+ tokens |
| Dark mode support | ✅ Complete | Excellent - all components |
| CSS architecture | ✅ Complete | Excellent - scoped, modular |
| Print stylesheet | ✅ Complete | Good - basic print styles |

### ⚠️ Partially Implemented (Needs Completion)

| Feature | Status | What's Missing |
|---------|--------|----------------|
| Social sharing buttons | ⚠️ Partial | CSS exists, no HTML implementation |
| Share to clipboard | ⚠️ Partial | Copy link exists, need share API |
| Version/language switcher | ⚠️ Partial | No UI for multi-version docs |
| Keyboard shortcuts | ⚠️ Partial | Only ⌘K for search |
| Print optimization | ⚠️ Partial | Basic styles, could be better |

### ❌ Not Implemented (Missing)

| Feature | Priority | Impact |
|---------|----------|--------|
| **PWA Support** | 🔥 High | Offline docs, app-like feel |
| Service worker | ❌ None | Caching, offline access |
| Web app manifest | ❌ None | Install to home screen |
| Offline page | ❌ None | Graceful offline experience |
| **Advanced Features** | | |
| Keyboard shortcuts panel | 🔥 High | Power user productivity |
| Command palette (⌘K) | 🔥 High | Quick navigation |
| Social share integration | 🔴 Medium | Increase content reach |
| Comments system | 🔴 Medium | Community engagement |
| Version switcher | 🔴 Medium | Multi-version docs sites |
| Language switcher | 🔴 Medium | i18n support |
| **Analytics & Monitoring** | | |
| Privacy-friendly analytics | 🟡 Low | Usage insights |
| Performance monitoring | 🟡 Low | Real user monitoring |
| **Customization** | | |
| Theme customizer UI | 🟡 Low | Live style editing |
| Font size controls | 🟡 Low | Accessibility |
| **Other** | | |
| Newsletter signup | 🟡 Low | Email list building |
| Cookie consent banner | 🟡 Low | GDPR compliance |
| Table sorting | 🟡 Low | Interactive tables |

---

## Top 5 Priorities (Ranked by Impact)

### 1. 🔥 Progressive Web App (PWA) Support
**Why**: Make documentation sites work offline, feel native, installable

**What to Build**:
```javascript
// 1. Service Worker (sw.js)
- Cache static assets (CSS, JS, fonts)
- Cache pages (with freshness strategy)
- Offline fallback page
- Update notification

// 2. Web App Manifest (manifest.json)
{
  "name": "Bengal Documentation",
  "short_name": "Bengal Docs",
  "icons": [...],
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#2563eb"
}

// 3. Registration in base.html
<link rel="manifest" href="/manifest.json">
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
  }
</script>
```

**Impact**:
- ✅ Documentation available offline (flights, trains, poor wifi)
- ✅ Faster subsequent loads (cached assets)
- ✅ Install to home screen/dock (app-like experience)
- ✅ Push notifications (future: update alerts)
- ✅ Modern, professional feel

**Effort**: Medium (2-3 days)
- Service worker: 1 day
- Manifest + icons: 0.5 day
- Testing (offline, install, updates): 0.5 day
- Documentation: 0.5 day

**Example Use Cases**:
- Developer reading API docs on plane ✈️
- Workshop attendee with flaky conference wifi 📶
- Quick reference without opening browser 🚀

---

### 2. 🔥 Advanced Keyboard Shortcuts & Command Palette
**Why**: Power users love keyboard navigation, increases productivity

**What to Build**:
```javascript
// Keyboard shortcuts:
⌘K / Ctrl+K  → Open command palette
⌘/            → Show shortcuts help
Esc           → Close modals/overlays
G then H      → Go to Home
G then D      → Go to Docs
[ / ]         → Prev/Next page
T             → Toggle theme
/             → Focus search

// Command Palette (⌘K enhancement)
- Quick navigation (fuzzy search all pages)
- Quick actions (toggle theme, copy URL, etc.)
- Recent pages history
- Keyboard-driven (arrow keys, enter)
```

**Impact**:
- ✅ Power users stay in keyboard flow
- ✅ Faster navigation than mouse
- ✅ Professional developer tool feel
- ✅ Discoverability (shortcuts panel)
- ✅ Accessibility improvement

**Effort**: Medium (2-3 days)
- Keyboard shortcut manager: 1 day
- Command palette UI: 1 day
- Shortcuts help modal: 0.5 day
- Testing + docs: 0.5 day

**Reference**: Like GitHub's ⌘K, VS Code's ⌘P, Linear's ⌘K

---

### 3. 🔴 Social Sharing Implementation
**Why**: CSS exists, just need HTML/JS. Increases content reach.

**What to Build**:
```html
<!-- Add to post.html and page.html -->
<div class="share-buttons" aria-label="Share this page">
  <button class="share-button twitter" data-share="twitter">
    <svg>...</svg>
    <span class="sr-only">Share on Twitter</span>
  </button>
  <button class="share-button linkedin" data-share="linkedin">...</button>
  <button class="share-button facebook" data-share="facebook">...</button>
  <button class="share-button copy" data-share="copy">
    <svg>...</svg>
    <span class="sr-only">Copy link</span>
  </button>
</div>

<script>
// Use native Web Share API (mobile) or fallback to custom URLs
if (navigator.share) {
  // Native share
} else {
  // Open share URLs
}
</script>
```

**Impact**:
- ✅ Easy content sharing (1-click)
- ✅ Increased traffic from social media
- ✅ Better engagement
- ✅ Professional polish

**Effort**: Low (0.5 day)
- HTML partial: 1 hour
- JavaScript share logic: 2 hours
- Testing (mobile/desktop): 1 hour

---

### 4. 🔴 Version Switcher UI
**Why**: Essential for documentation sites with multiple versions

**What to Build**:
```html
<!-- Version switcher dropdown in header -->
<div class="version-switcher">
  <button aria-label="Select version" aria-expanded="false">
    <span>v1.0.0</span>
    <svg class="icon-chevron">...</svg>
  </button>
  <ul class="version-menu" role="menu">
    <li><a href="/v1.0/">v1.0.0 (stable)</a></li>
    <li><a href="/v0.9/">v0.9.0</a></li>
    <li><a href="/latest/">latest (dev)</a></li>
  </ul>
</div>
```

**Config**:
```toml
[site]
versions = [
  { name = "v1.0.0", url = "/v1.0/", label = "stable" },
  { name = "v0.9.0", url = "/v0.9/" },
  { name = "latest", url = "/latest/", label = "dev" }
]
current_version = "v1.0.0"
```

**Impact**:
- ✅ Support multi-version docs
- ✅ Users can access older versions
- ✅ Important for libraries/frameworks
- ✅ Standard documentation feature

**Effort**: Medium (1-2 days)
- Config parsing: 0.5 day
- UI component: 0.5 day
- Template integration: 0.5 day
- Testing: 0.5 day

**Note**: Requires build system support for multi-version output

---

### 5. 🔴 Enhanced Print Optimization
**Why**: Documentation should print beautifully (PDFs, hard copies)

**What to Improve**:
```css
/* print.css enhancements */
@media print {
  /* Better page breaks */
  h1, h2, h3 { page-break-after: avoid; }
  pre, table { page-break-inside: avoid; }
  
  /* Hide non-essential elements */
  nav, .toc-sidebar, .back-to-top, .share-buttons { display: none; }
  
  /* Expand all code blocks */
  pre { max-height: none; }
  
  /* Show link URLs */
  a[href^="http"]:after {
    content: " (" attr(href) ")";
    font-size: 0.8em;
    color: #666;
  }
  
  /* Print-friendly footer on every page */
  @page { margin: 2cm; }
  footer { position: fixed; bottom: 0; }
}
```

**Add**:
- Print button with nice icon
- "Print-friendly version" page variant
- PDF export button (use browser's print-to-PDF)
- Table of contents on first page for multi-page prints

**Impact**:
- ✅ Professional PDF generation
- ✅ Easy offline reading (printed docs)
- ✅ Enterprise customers often print docs
- ✅ Better accessibility (low vision users may prefer paper)

**Effort**: Low (1 day)
- Enhanced print.css: 0.5 day
- Print button: 0.25 day
- Testing across browsers: 0.25 day

---

## Medium Priority Features

### 6. Comments System Integration (Optional)
**Options**:
- Giscus (GitHub Discussions) - Free, privacy-friendly
- Utterances (GitHub Issues) - Simple, clean
- Disqus - Popular but privacy concerns
- Self-hosted Isso - Full control

**Why Not Higher Priority**: Not essential for docs, more for blogs

---

### 7. Analytics Integration (Privacy-First)
**Options**:
- Plausible (paid, privacy-friendly)
- Umami (self-hosted, open source)
- Simple Analytics (paid, simple)
- Fathom (paid, privacy-first)

**Config**:
```toml
[analytics]
provider = "plausible"
domain = "docs.bengal-ssg.com"
```

**Why Not Higher Priority**: Not essential for launch, can add later

---

### 8. Font Size Controls (A11y)
```html
<div class="font-size-controls">
  <button aria-label="Decrease font size">A-</button>
  <button aria-label="Reset font size">A</button>
  <button aria-label="Increase font size">A+</button>
</div>
```

**Why Not Higher Priority**: Users can use browser zoom

---

## Low Priority (Nice to Have)

- Newsletter signup integration (Mailchimp, ConvertKit)
- Cookie consent banner (GDPR)
- Table sorting (interactive data tables)
- Theme customizer UI (live color picker)
- Auto-scroll to TOC active item
- Sticky table headers
- Floating action button (FAB) menu
- Easter eggs / fun interactions

---

## Implementation Roadmap

### Phase 1: Foundation (v0.3.0) - 1 week
**Goal**: Add PWA support and keyboard shortcuts

1. **PWA Implementation** (3 days)
   - Service worker with caching strategy
   - Web app manifest
   - Offline page
   - Install prompt
   - Update notification
   - Icons (192x192, 512x512, maskable)

2. **Keyboard Shortcuts** (2 days)
   - Shortcut manager (keypress detection)
   - Command palette UI (⌘K enhancement)
   - Shortcuts help modal (? key)
   - Documentation

3. **Social Sharing** (0.5 day)
   - Share buttons HTML partial
   - Web Share API + fallback
   - Add to templates

4. **Polish** (0.5 day)
   - Testing
   - Documentation
   - Screenshots

**Deliverables**:
- Offline-capable documentation site
- Power user keyboard navigation
- Easy social sharing

---

### Phase 2: Polish (v0.4.0) - 1 week
**Goal**: Version switching and print optimization

1. **Version Switcher** (2 days)
   - Config schema for versions
   - UI component
   - Template integration
   - Build system updates

2. **Enhanced Print** (1 day)
   - Improved print.css
   - Print button
   - PDF optimization

3. **Minor Enhancements** (2 days)
   - Font size controls
   - Better breadcrumbs visibility
   - Improved search filters
   - Small UX improvements

**Deliverables**:
- Multi-version documentation support
- Professional print output
- Refined user experience

---

### Phase 3: Optional (v0.5.0+) - As needed
**Goal**: Community and customization features

- Comments integration (config-based)
- Analytics integration (config-based)
- Newsletter signup (config-based)
- Cookie consent (if needed)
- Theme customizer (power users)

**Approach**: Make these **opt-in** via config, not enabled by default

---

## Success Metrics

### PWA (Phase 1)
- [ ] Service worker installs successfully
- [ ] Offline page loads when no connection
- [ ] Assets cache on first visit
- [ ] Update notification appears on new version
- [ ] Install prompt shows on supported browsers
- [ ] Lighthouse PWA score: 90+

### Keyboard Shortcuts (Phase 1)
- [ ] All shortcuts work as documented
- [ ] Command palette filters pages correctly
- [ ] Help modal shows all shortcuts
- [ ] No conflicts with browser shortcuts
- [ ] Shortcuts work in all browsers

### Social Sharing (Phase 1)
- [ ] Share buttons appear on posts/pages
- [ ] Web Share API works on mobile
- [ ] Fallback URLs work on desktop
- [ ] Copy link provides feedback
- [ ] Accessible (keyboard, screen reader)

### Print (Phase 2)
- [ ] Clean print layout (no clutter)
- [ ] Code blocks don't break across pages
- [ ] Links show URLs in print
- [ ] Table of contents on first page
- [ ] Professional appearance

---

## Design Considerations

### PWA Icons Needed
- `icon-192.png` (192x192) - Standard
- `icon-512.png` (512x512) - High-res
- `icon-maskable-512.png` - Maskable icon (safe area)
- `favicon.ico` - Browser tab
- `apple-touch-icon.png` - iOS home screen

### Color Scheme for PWA
```json
{
  "theme_color": "#2563eb",     // Primary blue
  "background_color": "#ffffff"  // White background
}
```

### Command Palette Design
- Modal overlay (dim background)
- Search input at top
- Results list (keyboard navigable)
- Grouped by type (pages, actions, shortcuts)
- Recent items at top
- Fuzzy search (flexible matching)

---

## Dependencies & Considerations

### PWA Requirements
- HTTPS required (service workers only work on HTTPS)
- Service worker must be in root (or use `Service-Worker-Allowed` header)
- Manifest must be served with `application/manifest+json`
- Icons must meet size requirements

### Keyboard Shortcuts Considerations
- Don't conflict with browser shortcuts
- Respect user's keyboard layout
- Provide way to disable (accessibility)
- Document all shortcuts clearly
- Consider international keyboards

### Browser Support
- Service workers: Chrome 40+, Firefox 44+, Safari 11.1+, Edge 17+
- Web Share API: Chrome 61+ (Android), Safari 12+ (iOS)
- Command palette: All modern browsers (just JS/CSS)

---

## Conclusion

**Recommended Implementation Order**:

1. **PWA Support** (highest impact) - 3 days
2. **Keyboard Shortcuts** (power users) - 2 days  
3. **Social Sharing** (quick win) - 0.5 day
4. **Version Switcher** (docs sites) - 2 days
5. **Enhanced Print** (polish) - 1 day

**Total Effort**: ~8-9 days (1-2 weeks)

**Result**: World-class documentation theme that rivals Docusaurus, VitePress, and MkDocs Material

---

## Questions for Discussion

1. Should PWA be opt-in or enabled by default?
   - **Recommendation**: Enabled by default, configurable
   
2. What keyboard shortcuts are most important?
   - **Recommendation**: Start with ⌘K (command palette), /, T (theme), [ ] (nav)
   
3. Which social networks to support?
   - **Recommendation**: Twitter, LinkedIn, Facebook, Copy Link (cover 95%)
   
4. Should version switcher require manual config or auto-detect?
   - **Recommendation**: Manual config (more explicit, predictable)

5. Add analytics by default or make it opt-in?
   - **Recommendation**: Opt-in only (privacy-first approach)

---

**Next Steps**: Approve priorities and start Phase 1 implementation

