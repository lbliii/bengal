---
title: "Holographic Card Effects"
description: "Pokemon TCG-inspired holographic admonitions and card components"
date: 2024-12-03
layout: doc
tags: [experimental, css, components]
toc: true
---

# ✨ Holographic Card Effects

Pokemon TCG-inspired holographic effects for Bengal documentation components.

> **Inspiration**: Based on [simeydotme's Pokemon Cards CSS](https://github.com/simeydotme/pokemon-cards-css) and the [CSS-Tricks article](https://css-tricks.com/holographic-trading-card-effect/).

Move your cursor over the cards below to see the effects!

---

## Demo Cards

<div class="holo-demo-grid">
  <div class="holo-card holo-card--rainbow">
    <div class="holo-card__inner">
      <div class="holo-card__shine"></div>
      <div class="holo-card__glare"></div>
      <div class="holo-card__content">
        <div class="holo-card__header">
          <span class="energy-orb info">💧</span>
          <div>
            <strong>Rainbow Holo</strong>
            <small>Conic gradient</small>
          </div>
        </div>
        <p>Move your cursor around to see the rainbow foil shimmer effect!</p>
      </div>
    </div>
  </div>

  <div class="holo-card holo-card--cosmos">
    <div class="holo-card__inner">
      <div class="holo-card__shine"></div>
      <div class="holo-card__glare"></div>
      <div class="holo-card__content">
        <div class="holo-card__header">
          <span class="energy-orb psychic">🔮</span>
          <div>
            <strong>Cosmos</strong>
            <small>Ultra Rare</small>
          </div>
        </div>
        <p>Cosmic nebula effect with layered radial gradients.</p>
      </div>
    </div>
  </div>

  <div class="holo-card holo-card--sunburst holo-card--gold">
    <div class="holo-card__inner">
      <div class="holo-card__shine"></div>
      <div class="holo-card__glare"></div>
      <div class="holo-card__content">
        <div class="holo-card__header">
          <span class="energy-orb electric">⚡</span>
          <div>
            <strong>Sunburst Gold</strong>
            <small>Secret Rare</small>
          </div>
        </div>
        <p>Gold frame with radiating light rays. Maximum premium!</p>
      </div>
    </div>
  </div>
</div>

---

## Energy Orbs

<div class="orb-showcase">
  <div class="orb-item"><span class="energy-orb info">ℹ</span><small>Info</small></div>
  <div class="orb-item"><span class="energy-orb success">✓</span><small>Success</small></div>
  <div class="orb-item"><span class="energy-orb warning">!</span><small>Warning</small></div>
  <div class="orb-item"><span class="energy-orb error">✕</span><small>Error</small></div>
  <div class="orb-item"><span class="energy-orb fire">🔥</span><small>Fire</small></div>
  <div class="orb-item"><span class="energy-orb psychic">🔮</span><small>Psychic</small></div>
  <div class="orb-item"><span class="energy-orb electric">⚡</span><small>Electric</small></div>
</div>

---

## Holographic Admonitions

:::{note}
:class: holo

**Holographic Note** — Move your cursor around to see the rainbow foil shimmer!
:::

:::{tip}
:class: holo

**Pro Tip** — The effect uses CSS custom properties updated by JavaScript.
:::

:::{warning}
:class: holo

**Caution** — Warning gets an orange-shifted holo effect.
:::

:::{danger}
:class: holo

**Critical** — Danger shifts the holo effect red-ward.
:::

---

## Usage

```markdown
:::{note}
:class: holo

Your holographic content here...
:::
```

---

<!-- INLINE STYLES - All experimental CSS in one place -->
<style>
/* ============================================
   HOLOGRAPHIC CARD STYLES
   ============================================ */

:root {
  --holo-gradient: repeating-linear-gradient(
    0deg,
    rgb(255, 119, 115) calc(5% * 1),
    rgba(255, 237, 95, 1) calc(5% * 2),
    rgba(168, 255, 95, 1) calc(5% * 3),
    rgba(131, 255, 247, 1) calc(5% * 4),
    rgba(120, 148, 255, 1) calc(5% * 5),
    rgb(216, 117, 255) calc(5% * 6),
    rgb(255, 119, 115) calc(5% * 7)
  );
  --pointer-x: 50;
  --pointer-y: 50;
  --card-glow: rgba(59, 130, 246, 0.4);
}

/* Demo Grid */
.holo-demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
  perspective: 1000px;
}

/* Base Card */
.holo-card {
  --card-glow: rgba(59, 130, 246, 0.4);
  position: relative;
  min-height: 220px;
  border-radius: var(--radius-xl, 12px);
  transform-style: preserve-3d;
  transition: transform 0.4s cubic-bezier(0.23, 1, 0.32, 1);
}

.holo-card__inner {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: inherit;
  border-radius: inherit;
  overflow: hidden;
  background: var(--color-bg-primary, white);
  border: 2px solid var(--color-border, #e0e0e0);
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.1),
    0 0 30px var(--card-glow);
  transform-style: preserve-3d;
  transition:
    transform 0.4s cubic-bezier(0.23, 1, 0.32, 1),
    box-shadow 0.3s ease;
}

.holo-card:hover .holo-card__inner {
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.15),
    0 0 50px var(--card-glow);
}

/* Shine Layer (rainbow foil) */
.holo-card__shine {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--holo-gradient);
  background-size: 400% 400%;
  background-position:
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%);
  mix-blend-mode: color-dodge;
  opacity: 0;
  pointer-events: none;
  z-index: 3;
  transition: opacity 0.3s ease;
  -webkit-mask-image: radial-gradient(
    farthest-corner circle at
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%),
    rgba(0, 0, 0, 0.8) 10%,
    rgba(0, 0, 0, 0.5) 40%,
    transparent 80%
  );
  mask-image: radial-gradient(
    farthest-corner circle at
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%),
    rgba(0, 0, 0, 0.8) 10%,
    rgba(0, 0, 0, 0.5) 40%,
    transparent 80%
  );
}

.holo-card:hover .holo-card__shine {
  opacity: 0.7;
}

/* Glare Layer */
.holo-card__glare {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(
    farthest-corner circle at
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%),
    rgba(255, 255, 255, 0.8) 0%,
    rgba(255, 255, 255, 0.3) 25%,
    transparent 60%
  );
  mix-blend-mode: overlay;
  opacity: 0;
  pointer-events: none;
  z-index: 4;
  transition: opacity 0.3s ease;
}

.holo-card:hover .holo-card__glare {
  opacity: 0.4;
}

/* Content */
.holo-card__content {
  position: relative;
  z-index: 1;
  padding: 1.25rem;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.holo-card__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.holo-card__header strong {
  display: block;
  font-size: 1.125rem;
}

.holo-card__header small {
  color: var(--color-text-secondary, #666);
  font-size: 0.8125rem;
}

.holo-card__content p {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--color-text-secondary, #555);
}

/* Card Variants */
.holo-card--rainbow .holo-card__shine {
  background: conic-gradient(
    from calc(var(--pointer-x) * 3.6deg) at 50% 50%,
    hsl(0, 100%, 70%),
    hsl(60, 100%, 70%),
    hsl(120, 100%, 70%),
    hsl(180, 100%, 70%),
    hsl(240, 100%, 70%),
    hsl(300, 100%, 70%),
    hsl(360, 100%, 70%)
  );
  filter: saturate(1.2) brightness(1.1);
}

.holo-card--cosmos {
  --card-glow: rgba(168, 85, 247, 0.5);
}

.holo-card--cosmos .holo-card__shine {
  background:
    radial-gradient(circle at 20% 80%, rgba(255, 0, 128, 0.4) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(0, 200, 255, 0.4) 0%, transparent 50%),
    var(--holo-gradient);
  background-size: 200% 200%, 200% 200%, 400% 400%;
}

.holo-card--sunburst .holo-card__shine {
  background: repeating-conic-gradient(
    from calc(var(--pointer-x) * 1deg) at
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%),
    transparent 0deg,
    rgba(255, 255, 255, 0.3) 2deg,
    transparent 4deg
  ),
  var(--holo-gradient);
}

.holo-card--gold {
  --card-glow: rgba(251, 191, 36, 0.6);
}

.holo-card--gold .holo-card__inner {
  border: 3px solid;
  border-image: linear-gradient(135deg, #ffd700, #b8860b, #ffd700) 1;
}

/* ============================================
   ENERGY ORBS
   ============================================ */

.energy-orb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-size: 1rem;
  color: white;
  flex-shrink: 0;
  box-shadow:
    0 2px 8px var(--orb-glow, rgba(0,0,0,0.2)),
    inset 0 2px 4px rgba(255,255,255,0.4),
    inset 0 -2px 4px rgba(0,0,0,0.2);
  background: var(--orb-gradient);
}

.energy-orb.info {
  --orb-gradient: linear-gradient(135deg, #60a5fa, #2563eb);
  --orb-glow: rgba(59, 130, 246, 0.5);
}

.energy-orb.success {
  --orb-gradient: linear-gradient(135deg, #4ade80, #16a34a);
  --orb-glow: rgba(34, 197, 94, 0.5);
}

.energy-orb.warning {
  --orb-gradient: linear-gradient(135deg, #fbbf24, #d97706);
  --orb-glow: rgba(245, 158, 11, 0.5);
}

.energy-orb.error {
  --orb-gradient: linear-gradient(135deg, #f87171, #dc2626);
  --orb-glow: rgba(239, 68, 68, 0.5);
}

.energy-orb.fire {
  --orb-gradient: linear-gradient(135deg, #fb923c, #ea580c);
  --orb-glow: rgba(249, 115, 22, 0.5);
}

.energy-orb.psychic {
  --orb-gradient: linear-gradient(135deg, #c084fc, #9333ea);
  --orb-glow: rgba(168, 85, 247, 0.5);
}

.energy-orb.electric {
  --orb-gradient: linear-gradient(135deg, #fde047, #ca8a04);
  --orb-glow: rgba(234, 179, 8, 0.5);
}

/* Orb Showcase */
.orb-showcase {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  justify-content: center;
  padding: 2rem;
  background: var(--color-bg-secondary, #f5f5f5);
  border-radius: var(--radius-xl, 12px);
  margin: 1.5rem 0;
}

.orb-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.orb-item small {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ============================================
   HOLOGRAPHIC ADMONITIONS
   ============================================ */

.admonition.holo {
  position: relative;
  overflow: visible;
  isolation: isolate;
}

.admonition.holo::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--holo-gradient);
  background-size: 400% 400%;
  background-position:
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%);
  mix-blend-mode: color-dodge;
  opacity: 0;
  pointer-events: none;
  z-index: 10;
  transition: opacity 0.3s ease;
  -webkit-mask-image: radial-gradient(
    farthest-corner circle at
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%),
    rgba(0, 0, 0, 0.8) 10%,
    rgba(0, 0, 0, 0.5) 40%,
    transparent 80%
  );
  mask-image: radial-gradient(
    farthest-corner circle at
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%),
    rgba(0, 0, 0, 0.8) 10%,
    rgba(0, 0, 0, 0.5) 40%,
    transparent 80%
  );
}

.admonition.holo::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(
    farthest-corner circle at
    calc(var(--pointer-x) * 1%)
    calc(var(--pointer-y) * 1%),
    rgba(255, 255, 255, 0.7) 0%,
    rgba(255, 255, 255, 0.2) 30%,
    transparent 60%
  );
  mix-blend-mode: overlay;
  opacity: 0;
  pointer-events: none;
  z-index: 11;
  transition: opacity 0.3s ease;
}

.admonition.holo:hover::before {
  opacity: 0.5;
}

.admonition.holo:hover::after {
  opacity: 0.3;
}

/* Type-specific hue shifts */
.admonition.holo.note::before { filter: hue-rotate(180deg) saturate(0.8); }
.admonition.holo.tip::before { filter: hue-rotate(100deg) saturate(0.9); }
.admonition.holo.warning::before { filter: hue-rotate(30deg) saturate(1.2); }
.admonition.holo.danger::before { filter: hue-rotate(-30deg) saturate(1.3); }

/* ============================================
   DARK MODE
   ============================================ */

[data-theme="dark"] .holo-card__inner {
  background: var(--color-bg-primary, #1a1a1a);
  border-color: #333;
}

[data-theme="dark"] .holo-card:hover .holo-card__shine {
  opacity: 0.5;
}

[data-theme="dark"] .orb-showcase {
  background: #1a1a1a;
}

[data-theme="dark"] .admonition.holo:hover::before {
  opacity: 0.4;
}

/* ============================================
   REDUCED MOTION
   ============================================ */

@media (prefers-reduced-motion: reduce) {
  .holo-card,
  .holo-card__inner,
  .holo-card__shine,
  .holo-card__glare,
  .admonition.holo::before,
  .admonition.holo::after {
    transition: none !important;
  }
}
</style>

<!-- INLINE JAVASCRIPT - Mouse tracking for holographic effect -->
<script>
(function() {
  'use strict';

  const MAX_ROTATION = 12;

  function getPointerPosition(e, el) {
    const rect = el.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    return { x: Math.max(0, Math.min(100, x)), y: Math.max(0, Math.min(100, y)) };
  }

  function updateStyles(el, x, y) {
    const rotateY = ((x / 50) - 1) * MAX_ROTATION;
    const rotateX = ((y / 50) - 1) * -MAX_ROTATION;

    el.style.setProperty('--pointer-x', x.toFixed(1));
    el.style.setProperty('--pointer-y', y.toFixed(1));

    const inner = el.querySelector('.holo-card__inner');
    if (inner) {
      inner.style.transform = `rotateY(${rotateY.toFixed(1)}deg) rotateX(${rotateX.toFixed(1)}deg)`;
    }
  }

  function resetStyles(el) {
    el.style.setProperty('--pointer-x', '50');
    el.style.setProperty('--pointer-y', '50');

    const inner = el.querySelector('.holo-card__inner');
    if (inner) {
      inner.style.transform = '';
    }
  }

  // Initialize cards
  document.querySelectorAll('.holo-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const pos = getPointerPosition(e, card);
      updateStyles(card, pos.x, pos.y);
    });
    card.addEventListener('mouseleave', () => resetStyles(card));
  });

  // Initialize admonitions
  document.querySelectorAll('.admonition.holo').forEach(admon => {
    admon.addEventListener('mousemove', e => {
      const rect = admon.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      admon.style.setProperty('--pointer-x', Math.max(0, Math.min(100, x)).toFixed(1));
      admon.style.setProperty('--pointer-y', Math.max(0, Math.min(100, y)).toFixed(1));
    });
    admon.addEventListener('mouseleave', () => {
      admon.style.setProperty('--pointer-x', '50');
      admon.style.setProperty('--pointer-y', '50');
    });
  });
})();
</script>
