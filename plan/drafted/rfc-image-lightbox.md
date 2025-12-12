# RFC: Image Lightbox Enhancements

| Field | Value |
|-------|-------|
| **Title** | Image Lightbox Enhancements |
| **Author** | AI + Human reviewer |
| **Date** | 2025-12-10 |
| **Status** | Draft |
| **Confidence** | 92% 🟢 |

---

## Executive Summary

Enhance Bengal's existing lightbox with zoom controls, touch gestures, and gallery indicators. The core lightbox is already implemented and working — this RFC proposes incremental improvements to match or exceed `mkdocs-glightbox` functionality.

**Strategic Context**: Bengal already has a lightbox (unlike MkDocs which requires a plugin). These enhancements make it a compelling reason to migrate.

---

## Current State ✅

Bengal already has a fully functional lightbox in `bengal/themes/default/assets/js/enhancements/lightbox.js`:

### What's Already Done

| Feature | Status | Implementation |
|---------|--------|----------------|
| Click-to-open overlay | ✅ Done | `openLightbox()` |
| Keyboard nav (Esc, ← →) | ✅ Done | `handleKeyboard()` |
| Gallery navigation | ✅ Done | `navigateImages()` |
| Captions from alt text | ✅ Done | `.lightbox__caption` |
| Auto-skip small images | ✅ Done | `< 400px` filter |
| Skip images in links | ✅ Done | `.closest('a')` check |
| ARIA accessibility | ✅ Done | `role`, `aria-label`, `aria-hidden` |
| Focus management | ✅ Done | Returns focus on close |
| Dark theme support | ✅ Done | CSS variables |
| Reduced motion | ✅ Done | `prefers-reduced-motion` |
| MutationObserver | ✅ Done | Dynamic content support |
| View Transitions API | ✅ Done | Smooth open/close |

**Evidence**:
- JS: `bengal/themes/default/assets/js/enhancements/lightbox.js`
- CSS: `bengal/themes/default/assets/css/components/interactive.css:327-500`

---

## Proposed Enhancements

### Enhancement 1: Zoom Controls

**Current**: No zoom capability  
**Proposed**: Add zoom in/out with controls and gestures

**Features**:
- `+` / `-` buttons in overlay
- Mouse wheel zoom
- Keyboard: `+`/`-` or `=`/`-` keys
- Double-click to toggle zoom
- Pan when zoomed (drag to move)

**Implementation**:
```javascript
// Add to lightbox.js

let zoomLevel = 1;
const ZOOM_STEP = 0.25;
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 3;

function zoomIn() {
  zoomLevel = Math.min(zoomLevel + ZOOM_STEP, ZOOM_MAX);
  applyZoom();
}

function zoomOut() {
  zoomLevel = Math.max(zoomLevel - ZOOM_STEP, ZOOM_MIN);
  applyZoom();
}

function resetZoom() {
  zoomLevel = 1;
  applyZoom();
}

function applyZoom() {
  const img = lightbox.querySelector('.lightbox__image');
  img.style.transform = `scale(${zoomLevel})`;

  // Enable/disable pan when zoomed
  img.style.cursor = zoomLevel > 1 ? 'grab' : 'default';

  // Update zoom indicator
  updateZoomIndicator();
}

// Mouse wheel zoom
lightbox.addEventListener('wheel', (e) => {
  if (!lightbox.classList.contains('active')) return;
  e.preventDefault();

  if (e.deltaY < 0) zoomIn();
  else zoomOut();
}, { passive: false });

// Double-click to toggle zoom
img.addEventListener('dblclick', () => {
  if (zoomLevel === 1) {
    zoomLevel = 2;
  } else {
    zoomLevel = 1;
  }
  applyZoom();
});
```

**UI**:
```
┌─────────────────────────────────────────────────────┐
│                                          [×]        │
│                                                     │
│                     IMAGE                           │
│                                                     │
│                                                     │
│         [-]  100%  [+]                              │
│                                                     │
│                   Caption                           │
└─────────────────────────────────────────────────────┘
```

---

### Enhancement 2: Gallery Counter

**Current**: No indication of position in gallery  
**Proposed**: Show "3 / 10" counter for multi-image pages

**Implementation**:
```javascript
function updateGalleryCounter() {
  const images = document.querySelectorAll('[data-lightbox]');
  const counter = lightbox.querySelector('.lightbox__counter');

  if (images.length <= 1) {
    counter.style.display = 'none';
    return;
  }

  const currentIndex = Array.from(images).indexOf(currentImage);
  counter.textContent = `${currentIndex + 1} / ${images.length}`;
  counter.style.display = 'block';
}
```

**CSS**:
```css
.lightbox__counter {
  position: absolute;
  top: 1rem;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.875rem;
  font-variant-numeric: tabular-nums;
  background: rgba(0, 0, 0, 0.4);
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
}
```

---

### Enhancement 3: Touch Gestures (Mobile)

**Current**: Basic click support only  
**Proposed**: Native-feeling touch interactions

| Gesture | Action |
|---------|--------|
| Swipe left/right | Navigate gallery |
| Pinch | Zoom in/out |
| Double-tap | Toggle zoom |
| Swipe down | Close lightbox |

**Implementation**:
```javascript
// Touch gesture handling
let touchStartX = 0;
let touchStartY = 0;
let touchStartDistance = 0;

lightbox.addEventListener('touchstart', (e) => {
  if (e.touches.length === 1) {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  } else if (e.touches.length === 2) {
    // Pinch start
    touchStartDistance = getTouchDistance(e.touches);
  }
}, { passive: true });

lightbox.addEventListener('touchend', (e) => {
  const touchEndX = e.changedTouches[0].clientX;
  const touchEndY = e.changedTouches[0].clientY;

  const deltaX = touchEndX - touchStartX;
  const deltaY = touchEndY - touchStartY;

  const SWIPE_THRESHOLD = 50;

  // Horizontal swipe - navigate
  if (Math.abs(deltaX) > SWIPE_THRESHOLD && Math.abs(deltaX) > Math.abs(deltaY)) {
    if (deltaX > 0) navigateImages(-1); // Swipe right = prev
    else navigateImages(1); // Swipe left = next
  }

  // Vertical swipe down - close
  if (deltaY > SWIPE_THRESHOLD * 2 && Math.abs(deltaY) > Math.abs(deltaX)) {
    closeLightbox();
  }
}, { passive: true });

lightbox.addEventListener('touchmove', (e) => {
  if (e.touches.length === 2) {
    // Pinch zoom
    const currentDistance = getTouchDistance(e.touches);
    const scale = currentDistance / touchStartDistance;

    if (scale > 1.1) zoomIn();
    else if (scale < 0.9) zoomOut();

    touchStartDistance = currentDistance;
  }
}, { passive: true });

function getTouchDistance(touches) {
  const dx = touches[0].clientX - touches[1].clientX;
  const dy = touches[0].clientY - touches[1].clientY;
  return Math.sqrt(dx * dx + dy * dy);
}
```

---

### Enhancement 4: Loading Indicator

**Current**: No feedback while large images load  
**Proposed**: Show spinner for images > 100KB or slow connections

**Implementation**:
```javascript
function showLoadingIndicator() {
  const loader = lightbox.querySelector('.lightbox__loader');
  loader.style.display = 'flex';
}

function hideLoadingIndicator() {
  const loader = lightbox.querySelector('.lightbox__loader');
  loader.style.display = 'none';
}

function openLightbox(imgElement) {
  // ... existing code ...

  const img = lightbox.querySelector('.lightbox__image');

  // Show loader while high-res loads
  showLoadingIndicator();
  img.style.opacity = '0';

  img.onload = () => {
    hideLoadingIndicator();
    img.style.opacity = '1';
  };

  img.src = highResSrc;
}
```

**CSS**:
```css
.lightbox__loader {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: none;
}

.lightbox__loader::after {
  content: '';
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

### Enhancement 5: Navigation Arrows (Optional)

**Current**: Keyboard-only navigation  
**Proposed**: Visual prev/next arrows for discoverability

```css
.lightbox__nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(0, 0, 0, 0.3);
  border: none;
  color: white;
  padding: 1rem 0.75rem;
  cursor: pointer;
  opacity: 0;
  transition: opacity 200ms;
}

.lightbox:hover .lightbox__nav {
  opacity: 1;
}

.lightbox__nav--prev { left: 1rem; }
.lightbox__nav--next { right: 1rem; }

/* Hide on single-image pages */
.lightbox[data-single="true"] .lightbox__nav {
  display: none;
}
```

---

## Implementation Plan

### Phase 1: Zoom Controls (1 day)

1. Add zoom state management to `lightbox.js`
2. Implement keyboard shortcuts (`+`, `-`, `0`)
3. Add mouse wheel zoom
4. Add zoom indicator UI
5. Update CSS for zoom controls

### Phase 2: Gallery Enhancements (0.5 day)

1. Add counter element to lightbox HTML
2. Implement `updateGalleryCounter()`
3. Add navigation arrows (optional, CSS-hidden by default)

### Phase 3: Touch Gestures (1 day)

1. Add touch event listeners
2. Implement swipe detection
3. Implement pinch-to-zoom
4. Test on iOS Safari, Chrome Android

### Phase 4: Polish (0.5 day)

1. Add loading indicator
2. Update keyboard shortcut documentation
3. Test accessibility with screen readers
4. Performance optimization

**Total**: ~3 days

---

## Backward Compatibility

**No breaking changes**. All enhancements are additive:

- Existing lightbox behavior preserved
- New features enhance, don't replace
- Config options for new features default to enabled
- Can disable individual features via config

---

## Configuration

```toml
# bengal.toml (optional - defaults are sensible)

[lightbox]
enabled = true  # Default: true (already exists)

# New options
zoom_enabled = true
zoom_step = 0.25
zoom_max = 3

touch_gestures = true
swipe_threshold = 50

show_counter = true
show_nav_arrows = true  # Visual prev/next buttons
loading_indicator = true
```

---

## Testing Strategy

### Unit Tests

```python
def test_zoom_keyboard_shortcuts():
    """+ and - keys adjust zoom."""
    # Simulate keypress
    # Assert zoom level changed

def test_touch_swipe_navigation():
    """Swipe gestures navigate gallery."""
    # Simulate touch events
    # Assert image changed

def test_counter_display():
    """Counter shows correct position."""
    # Open lightbox on 3rd of 5 images
    # Assert counter shows "3 / 5"
```

### E2E Tests (Playwright)

```python
def test_zoom_interaction(page):
    """Mouse wheel zooms image."""
    page.goto("/docs/screenshots/")
    page.click("article img >> nth=0")

    # Scroll to zoom
    page.mouse.wheel(0, -100)

    # Assert transform scale changed
    img = page.locator(".lightbox__image")
    style = img.get_attribute("style")
    assert "scale" in style

def test_mobile_swipe(page):
    """Touch swipe navigates gallery."""
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto("/docs/screenshots/")
    page.click("article img >> nth=0")

    # Simulate swipe
    page.locator(".lightbox").swipe("left")

    # Assert new image loaded
```

---

## Comparison: Bengal vs mkdocs-glightbox

| Feature | Bengal (Current) | Bengal (Enhanced) | mkdocs-glightbox |
|---------|------------------|-------------------|------------------|
| Click to open | ✅ | ✅ | ✅ |
| Keyboard nav | ✅ | ✅ | ✅ |
| Gallery mode | ✅ | ✅ | ✅ |
| Captions | ✅ | ✅ | ✅ |
| ARIA support | ✅ | ✅ | Partial |
| Zoom controls | ❌ | ✅ | ✅ |
| Touch gestures | ❌ | ✅ | ✅ |
| Gallery counter | ❌ | ✅ | ✅ |
| Loading indicator | ❌ | ✅ | ❌ |
| Nav arrows | ❌ | ✅ | ✅ |
| Bundle size | ~3KB | ~5KB | ~15KB |
| External dep | ❌ | ❌ | ✅ (GLightbox) |
| Theme matching | ✅ | ✅ | Manual |
| View Transitions | ✅ | ✅ | ❌ |

**Bengal advantages**:
- Smaller bundle (5KB vs 15KB)
- No external dependencies
- Native theme integration
- View Transitions API support
- Built-in, not a plugin

---

## Success Metrics

1. **Feature parity**: Match or exceed mkdocs-glightbox functionality
2. **Bundle size**: Stay under 6KB gzipped
3. **Performance**: < 16ms frame time during animations
4. **Accessibility**: Pass WCAG 2.1 AA

---

## Open Questions

1. **Nav arrows default**: Show always, on hover, or never?
2. **Zoom persistence**: Reset zoom between images, or preserve?
3. **High-res loading**: Auto-detect `srcset` for high-res versions?

---

## References

- Current implementation: `bengal/themes/default/assets/js/enhancements/lightbox.js`
- CSS: `bengal/themes/default/assets/css/components/interactive.css`
- GLightbox (for reference): https://biati-digital.github.io/glightbox/
- Touch Events API: https://developer.mozilla.org/en-US/docs/Web/API/Touch_events
