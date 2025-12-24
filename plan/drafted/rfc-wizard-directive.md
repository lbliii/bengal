# RFC: Wizard Directive

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-21  
**Subsystems**: `bengal/directives/`, `bengal/themes/default/assets/`

---

## Executive Summary

Introduce a `{wizard}` directive that provides a carousel-style step-by-step progression experience. Unlike the existing `{steps}` directive which displays all steps as a vertical list, `{wizard}` shows one step at a time with Previous/Next navigation—a classic wizard UI pattern for tutorials, onboarding flows, and multi-stage workflows.

---

## Problem Statement

The current `{steps}` directive is excellent for displaying all steps at once in a visual list. However, some content benefits from **focused, sequential navigation**:

- **Onboarding flows**: Guide users through setup one step at a time
- **Multi-stage tutorials**: Prevent cognitive overload by revealing content progressively
- **Decision trees**: Show different steps based on progress
- **Form-like workflows**: Collect information or choices across multiple screens

There is no directive currently that provides this carousel/wizard UX pattern.

---

## Proposed Solution

Create `{wizard}` and `{wizard-step}` directives following the same closure pattern as `{steps}`/`{step}`:

### Syntax

```markdown
:::{wizard}
:title: Getting Started with Bengal
:show-progress: true

:::{wizard-step} Installation
:description: Install Bengal and set up your environment
:icon: 📦

Install Bengal using pip:

```bash
pip install bengal
```

:::{/wizard-step}

:::{wizard-step} Configuration
:description: Configure your first site
:icon: ⚙️

Create a configuration file...

:::{/wizard-step}

:::{wizard-step} Build & Deploy
:description: Build your site and deploy it
:icon: 🚀

Run the build command...

:::{/wizard-step}

:::{/wizard}
```

### Rendered Output

```
┌────────────────────────────────────────────────────────────────┐
│                   Getting Started with Bengal                   │
│                                                                │
│         ● ─────────── ○ ─────────── ○                          │
│    Installation    Configuration   Build & Deploy              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  📦 Installation                                               │
│  Install Bengal and set up your environment                   │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ pip install bengal                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                       [ Previous ] [ Next → ] │
└────────────────────────────────────────────────────────────────┘
```

---

## Design Details

### Container Options (`{wizard}`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:title:` | string | (none) | Wizard title displayed at top |
| `:class:` | string | (none) | Custom CSS class |
| `:show-progress:` | bool | `true` | Show step progress indicator |
| `:progress-style:` | enum | `dots` | Progress style: `dots`, `bar`, `numbered`, `none` |
| `:allow-skip:` | bool | `false` | Allow skipping to any step via progress indicator |
| `:restart-button:` | bool | `false` | Show "Start Over" button on final step |
| `:start:` | int | `1` | Start at specific step (1-indexed) |

### Step Options (`{wizard-step}`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:description:` | string | (none) | Subtitle/lead-in text below title |
| `:icon:` | string | (none) | Icon/emoji shown with title |
| `:class:` | string | (none) | Custom CSS class |
| `:next-label:` | string | `"Next"` | Custom label for Next button |
| `:prev-label:` | string | `"Previous"` | Custom label for Previous button |
| `:final:` | bool | (auto) | Mark as final step (auto-detected if last) |
| `:final-label:` | string | `"Finish"` | Label for final step's action button |

---

## Architecture

### Directive Structure

```
bengal/directives/wizard.py
├── WizardOptions(DirectiveOptions)     # Container options dataclass
├── WizardStepOptions(DirectiveOptions) # Step options dataclass
├── WizardStepDirective(BengalDirective)
│   ├── NAMES = ["wizard-step"]
│   ├── TOKEN_TYPE = "wizard_step"
│   ├── CONTRACT = WIZARD_STEP_CONTRACT  # requires_parent=("wizard",)
│   ├── parse_directive()
│   └── render()
└── WizardDirective(BengalDirective)
    ├── NAMES = ["wizard"]
    ├── TOKEN_TYPE = "wizard"
    ├── CONTRACT = WIZARD_CONTRACT        # requires_children=("wizard_step",)
    ├── parse_directive()
    └── render()
```

### Contracts (in `bengal/directives/contracts.py`)

```python
# Wizard directives
WIZARD_CONTRACT = DirectiveContract(
    requires_children=("wizard_step",),
    min_children=2,  # Wizard needs at least 2 steps
    allowed_children=("wizard_step", "blank_line"),
)

WIZARD_STEP_CONTRACT = DirectiveContract(
    requires_parent=("wizard",),
)
```

### HTML Output Structure

```html
<div class="wizard" data-wizard-id="wizard-abc123">
  <!-- Optional header -->
  <div class="wizard-header">
    <h3 class="wizard-title">Getting Started with Bengal</h3>
  </div>

  <!-- Progress indicator -->
  <nav class="wizard-progress" aria-label="Wizard progress">
    <ol class="wizard-progress-dots">
      <li class="active" aria-current="step">
        <button data-wizard-step="0">
          <span class="wizard-progress-dot"></span>
          <span class="wizard-progress-label">Installation</span>
        </button>
      </li>
      <li>
        <button data-wizard-step="1">
          <span class="wizard-progress-dot"></span>
          <span class="wizard-progress-label">Configuration</span>
        </button>
      </li>
      <li>
        <button data-wizard-step="2">
          <span class="wizard-progress-dot"></span>
          <span class="wizard-progress-label">Build & Deploy</span>
        </button>
      </li>
    </ol>
  </nav>

  <!-- Step panels -->
  <div class="wizard-steps">
    <article class="wizard-step active" data-step="0" role="tabpanel">
      <header class="wizard-step-header">
        <span class="wizard-step-icon">📦</span>
        <h4 class="wizard-step-title">Installation</h4>
      </header>
      <p class="wizard-step-description">Install Bengal and set up your environment</p>
      <div class="wizard-step-content">
        <!-- Rendered markdown content -->
      </div>
    </article>

    <article class="wizard-step" data-step="1" role="tabpanel" hidden>
      <!-- Step 2 content -->
    </article>

    <article class="wizard-step" data-step="2" role="tabpanel" hidden>
      <!-- Step 3 content -->
    </article>
  </div>

  <!-- Navigation -->
  <footer class="wizard-nav">
    <button class="wizard-nav-prev" disabled>Previous</button>
    <span class="wizard-nav-counter">Step 1 of 3</span>
    <button class="wizard-nav-next">Next →</button>
  </footer>
</div>
```

### JavaScript Enhancement

Create `bengal/themes/default/assets/js/enhancements/wizard.js`:

```javascript
/**
 * Bengal Enhancement: Wizard Component
 *
 * Provides carousel-style step navigation:
 * - Previous/Next button navigation
 * - Progress indicator interaction
 * - Keyboard navigation (arrow keys)
 * - Step state management
 * - Accessibility (ARIA, focus management)
 */

(function() {
  'use strict';

  const CLASS_ACTIVE = 'active';
  const SELECTOR_WIZARD = '.wizard';
  const SELECTOR_STEP = '.wizard-step';
  const SELECTOR_NAV_PREV = '.wizard-nav-prev';
  const SELECTOR_NAV_NEXT = '.wizard-nav-next';
  const SELECTOR_PROGRESS_BTN = '.wizard-progress button';

  class Wizard {
    constructor(element) {
      this.element = element;
      this.steps = Array.from(element.querySelectorAll(SELECTOR_STEP));
      this.currentIndex = 0;

      this.prevBtn = element.querySelector(SELECTOR_NAV_PREV);
      this.nextBtn = element.querySelector(SELECTOR_NAV_NEXT);
      this.progressBtns = Array.from(element.querySelectorAll(SELECTOR_PROGRESS_BTN));

      this.allowSkip = element.dataset.allowSkip === 'true';

      this.bindEvents();
      this.updateState();
    }

    bindEvents() {
      this.prevBtn?.addEventListener('click', () => this.prev());
      this.nextBtn?.addEventListener('click', () => this.next());

      this.progressBtns.forEach((btn, index) => {
        btn.addEventListener('click', () => {
          if (this.allowSkip || index <= this.currentIndex) {
            this.goTo(index);
          }
        });
      });

      // Keyboard navigation
      this.element.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') this.prev();
        if (e.key === 'ArrowRight') this.next();
      });
    }

    prev() {
      if (this.currentIndex > 0) {
        this.goTo(this.currentIndex - 1);
      }
    }

    next() {
      if (this.currentIndex < this.steps.length - 1) {
        this.goTo(this.currentIndex + 1);
      }
    }

    goTo(index) {
      if (index < 0 || index >= this.steps.length) return;

      this.currentIndex = index;
      this.updateState();

      // Dispatch event for external listeners
      this.element.dispatchEvent(new CustomEvent('wizard:change', {
        detail: { step: index, total: this.steps.length }
      }));
    }

    updateState() {
      // Update step visibility
      this.steps.forEach((step, i) => {
        step.classList.toggle(CLASS_ACTIVE, i === this.currentIndex);
        step.hidden = i !== this.currentIndex;
      });

      // Update progress indicator
      this.progressBtns.forEach((btn, i) => {
        const li = btn.closest('li');
        li?.classList.toggle(CLASS_ACTIVE, i === this.currentIndex);
        li?.classList.toggle('completed', i < this.currentIndex);

        if (i === this.currentIndex) {
          li?.setAttribute('aria-current', 'step');
        } else {
          li?.removeAttribute('aria-current');
        }
      });

      // Update navigation buttons
      if (this.prevBtn) {
        this.prevBtn.disabled = this.currentIndex === 0;
      }

      if (this.nextBtn) {
        const isLast = this.currentIndex === this.steps.length - 1;
        this.nextBtn.disabled = isLast;

        // Update label for final step
        const step = this.steps[this.currentIndex];
        const finalLabel = step?.dataset.finalLabel;
        if (isLast && finalLabel) {
          this.nextBtn.textContent = finalLabel;
          this.nextBtn.disabled = false;
        }
      }

      // Update counter
      const counter = this.element.querySelector('.wizard-nav-counter');
      if (counter) {
        counter.textContent = `Step ${this.currentIndex + 1} of ${this.steps.length}`;
      }
    }
  }

  // Initialize all wizards
  document.querySelectorAll(SELECTOR_WIZARD).forEach(el => new Wizard(el));

  // Support dynamic content
  const observer = new MutationObserver((mutations) => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.nodeType === 1) {
          node.querySelectorAll?.(SELECTOR_WIZARD).forEach(el => {
            if (!el._wizard) {
              el._wizard = new Wizard(el);
            }
          });
        }
      });
    });
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
```

### CSS Styling

Create `bengal/themes/default/assets/css/components/wizard.css`:

```css
/**
 * Wizard Component Styles
 *
 * Carousel-style step-by-step wizard with progress indicator.
 */

.wizard {
  --wizard-accent: var(--color-primary);
  --wizard-step-size: 1.5rem;
  --wizard-connector-height: 2px;

  margin-block: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  overflow: hidden;
}

/* Header */
.wizard-header {
  padding: var(--space-4) var(--space-6);
  background: var(--color-surface-alt);
  border-bottom: 1px solid var(--color-border);
}

.wizard-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}

/* Progress Indicator */
.wizard-progress {
  padding: var(--space-6);
  background: var(--color-surface-alt);
  border-bottom: 1px solid var(--color-border);
}

.wizard-progress-dots {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}

.wizard-progress-dots li {
  display: flex;
  align-items: center;
  position: relative;
}

/* Connector line between dots */
.wizard-progress-dots li:not(:last-child)::after {
  content: "";
  width: 4rem;
  height: var(--wizard-connector-height);
  background: var(--color-border);
  margin-inline: var(--space-2);
  transition: background var(--transition-normal);
}

.wizard-progress-dots li.completed::after {
  background: var(--wizard-accent);
}

.wizard-progress-dots button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-2);
}

.wizard-progress-dot {
  width: var(--wizard-step-size);
  height: var(--wizard-step-size);
  border-radius: 50%;
  border: 2px solid var(--color-border);
  background: var(--color-surface);
  transition: all var(--transition-normal);
  position: relative;
}

/* Active dot */
.wizard-progress-dots li.active .wizard-progress-dot {
  border-color: var(--wizard-accent);
  background: var(--wizard-accent);
  box-shadow: 0 0 0 4px var(--color-primary-muted);
}

/* Completed dot */
.wizard-progress-dots li.completed .wizard-progress-dot {
  border-color: var(--wizard-accent);
  background: var(--wizard-accent);
}

.wizard-progress-dots li.completed .wizard-progress-dot::after {
  content: "✓";
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.75rem;
  font-weight: bold;
}

.wizard-progress-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
  transition: color var(--transition-normal);
}

.wizard-progress-dots li.active .wizard-progress-label {
  color: var(--color-text-primary);
  font-weight: var(--weight-medium);
}

/* Step Panels */
.wizard-steps {
  position: relative;
  min-height: 200px;
}

.wizard-step {
  padding: var(--space-6);
}

.wizard-step[hidden] {
  display: none;
}

.wizard-step-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.wizard-step-icon {
  font-size: var(--text-2xl);
}

.wizard-step-title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}

.wizard-step-description {
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  margin-bottom: var(--space-4);
  line-height: var(--leading-relaxed);
}

.wizard-step-content > :last-child {
  margin-bottom: 0;
}

/* Navigation Footer */
.wizard-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  background: var(--color-surface-alt);
  border-top: 1px solid var(--color-border);
}

.wizard-nav-prev,
.wizard-nav-next {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.wizard-nav-prev {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.wizard-nav-prev:hover:not(:disabled) {
  background: var(--color-surface-hover);
  color: var(--color-text-primary);
}

.wizard-nav-next {
  background: var(--wizard-accent);
  border: 1px solid var(--wizard-accent);
  color: var(--color-text-inverse);
}

.wizard-nav-next:hover:not(:disabled) {
  filter: brightness(1.1);
}

.wizard-nav-prev:disabled,
.wizard-nav-next:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.wizard-nav-counter {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Progress Bar Style (alternative) */
.wizard[data-progress-style="bar"] .wizard-progress-bar {
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.wizard[data-progress-style="bar"] .wizard-progress-bar-fill {
  height: 100%;
  background: var(--wizard-accent);
  transition: width var(--transition-normal);
}

/* Compact mode */
.wizard-compact .wizard-header {
  padding: var(--space-3) var(--space-4);
}

.wizard-compact .wizard-step {
  padding: var(--space-4);
}

.wizard-compact .wizard-nav {
  padding: var(--space-3) var(--space-4);
}

/* Focus states for accessibility */
.wizard-progress-dots button:focus-visible,
.wizard-nav-prev:focus-visible,
.wizard-nav-next:focus-visible {
  outline: 2px solid var(--wizard-accent);
  outline-offset: 2px;
}
```

---

## Implementation Plan

### Phase 1: Core Directive (2-3 hours)

1. **Add contracts** to `bengal/directives/contracts.py`:
   - `WIZARD_CONTRACT`
   - `WIZARD_STEP_CONTRACT`

2. **Create directive** at `bengal/directives/wizard.py`:
   - `WizardOptions` dataclass
   - `WizardStepOptions` dataclass
   - `WizardStepDirective` class
   - `WizardDirective` class

3. **Register directive** in `bengal/directives/__init__.py`

### Phase 2: Theme Assets (1-2 hours)

4. **Create CSS** at `bengal/themes/default/assets/css/components/wizard.css`

5. **Create JavaScript** at `bengal/themes/default/assets/js/enhancements/wizard.js`

6. **Import in theme** - add to `components.css` and register in JS entry

### Phase 3: Documentation & Tests (1-2 hours)

7. **Add documentation** to `site/content/docs/reference/directives/interactive.md`

8. **Unit tests** at `tests/unit/rendering/test_wizard_directive.py`

9. **Integration tests** with example content

---

## Alternatives Considered

### Alternative A: Extend Tabs Directive

Use existing tabs infrastructure with wizard-specific styling.

**Pros**: Less code, reuses existing JS  
**Cons**: Semantically different (tabs are parallel, wizard is sequential); prev/next nav doesn't fit tabs model

### Alternative B: JavaScript-Only Enhancement

Keep steps directive, add CSS class for JS-enhanced wizard behavior.

```markdown
:::{steps}
:class: wizard
...
```

**Pros**: No new directive  
**Cons**: Steps semantic doesn't match wizard UX; requires awkward option overloading; harder to customize per-step nav labels

### Recommended: New Directive (Proposed Solution)

Cleaner separation of concerns, explicit semantics, full control over options.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| JavaScript required | Render all steps visible as fallback for no-JS; add CSS `@media (scripting: none)` support |
| Accessibility | ARIA roles, keyboard nav, focus management built-in |
| Deep nesting conflicts | Contract validation ensures proper structure |
| Print styles | Show all steps expanded when printing |

---

## Testing Strategy

### Unit Tests

```python
class TestWizardOptions:
    def test_default_values(self):
        options = WizardOptions.from_raw({})
        assert options.show_progress is True
        assert options.progress_style == "dots"
        assert options.allow_skip is False

class TestWizardDirective:
    def test_renders_container_with_steps(self):
        # Test HTML output structure

    def test_step_metadata_injection(self):
        # Test step numbering and total injected

    def test_progress_indicator_rendering(self):
        # Test progress dots/bar

class TestWizardStepDirective:
    def test_requires_wizard_parent(self):
        # Test contract validation

    def test_renders_hidden_non_first_steps(self):
        # First step active, others hidden
```

### Browser Tests

- Prev/Next navigation
- Progress indicator clicks (with/without allow-skip)
- Keyboard navigation (arrows)
- Focus management
- Screen reader compatibility

---

## Success Criteria

- [ ] Wizard renders with proper HTML structure
- [ ] JavaScript navigation works (prev/next/progress)
- [ ] Contract validation enforces parent-child relationship
- [ ] Keyboard accessible (arrow keys, focus)
- [ ] Graceful degradation without JavaScript
- [ ] All progress styles work (dots, bar, numbered, none)
- [ ] Step-specific labels work (next-label, prev-label, final-label)
- [ ] Documentation complete with examples
- [ ] Unit tests pass

---

## Related Work

- **Steps directive**: `bengal/directives/steps.py` - vertical list pattern
- **Tabs directive**: `bengal/directives/tabs.py` - tabbed content
- **Tabs JS**: `bengal/themes/default/assets/js/enhancements/tabs.js`

---

## References

- Steps directive implementation: `bengal/directives/steps.py:1-453`
- Contract system: `bengal/directives/contracts.py:37-79`
- Base directive: `bengal/directives/base.py:58-437`
- Tabs JS: `bengal/themes/default/assets/js/enhancements/tabs.js:1-94`


