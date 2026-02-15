# RFC: Documentation Feedback Signals

**Status**: Draft  
**Created**: 2026-01-12  
**Author**: Bengal Team  
**Target Version**: 0.2.x

---

## Executive Summary

Add a documentation feedback system that enables readers to:

1. **Report issues with code samples** via a code block toolbar button (like Mintlify/Fern)
2. **Provide page-level feedback** via action bar or footer widget
3. **Route feedback to configurable backends**: GitHub Issues/Discussions, Slack, or custom webhooks

The goal is to create a low-friction feedback loop between documentation readers and maintainers, improving docs quality through direct user signals.

---

## Motivation

### Problem

Documentation quality degrades silently. Code samples become outdated, API examples break after updates, and configuration defaults change—but maintainers often don't know until users complain in unrelated channels (Discord, support tickets, Twitter).

### Opportunity

Modern docs platforms (Mintlify, Fern, GitBook) provide inline feedback mechanisms that:
- Let readers flag incorrect code **at the point of frustration**
- Create structured feedback with page context auto-filled
- Route issues to the right place (GitHub, Slack) without requiring users to context-switch

### Why Bengal Should Have This

1. **Competitive parity**: Mintlify's "Report incorrect code" is a standout feature
2. **Open source friendly**: GitHub Issues/Discussions integration is natural for OSS docs
3. **Low implementation cost**: Builds on existing action bar and code block patterns
4. **High user value**: Direct signal on where docs are failing

---

## Design Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Bengal Theme                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────────────────────┐  │
│  │   Code Block     │    │         Action Bar               │  │
│  │  ┌────────────┐  │    │  ┌─────────────────────────────┐ │  │
│  │  │ Copy  │ ⚠️ │  │    │  │  Breadcrumbs  │  [Share] [?]│ │  │
│  │  └────────────┘  │    │  └─────────────────────────────┘ │  │
│  │  (flag issue)    │    │              (page feedback)     │  │
│  └──────────────────┘    └──────────────────────────────────┘  │
│           │                            │                        │
│           └──────────┬─────────────────┘                        │
│                      ▼                                          │
│           ┌──────────────────┐                                  │
│           │  Feedback Modal  │                                  │
│           │  ┌────────────┐  │                                  │
│           │  │ Issue Type │  │                                  │
│           │  │ [Optional] │  │                                  │
│           │  │  Message   │  │                                  │
│           │  │  [Submit]  │  │                                  │
│           │  └────────────┘  │                                  │
│           └────────┬─────────┘                                  │
│                    │                                            │
└────────────────────┼────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   Configured Backend   │
        ├────────────────────────┤
        │ • GitHub Issues        │
        │ • GitHub Discussions   │
        │ • Slack Webhook        │
        │ • Custom Endpoint      │
        └────────────────────────┘
```

### Component Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| Code block feedback button | `partials/code-block.html` | Flag incorrect code samples |
| Action bar feedback button | `partials/action-bar.html` | Page-level feedback |
| Footer feedback widget | `partials/feedback-footer.html` | "Was this helpful?" |
| Feedback modal | `partials/feedback-modal.html` | Unified feedback form |
| Feedback JS enhancement | `js/enhancements/feedback.js` | Form handling, API calls |
| Backend config | `theme.yaml` / `site.yaml` | Backend configuration |

---

## Detailed Design

### 1. Configuration Schema

#### Site-level Configuration (`site.yaml`)

```yaml
# Feedback configuration
feedback:
  enabled: true

  # Backend: where feedback goes
  backend:
    type: github  # github | slack | webhook

    # GitHub backend
    github:
      repo: "org/docs-repo"
      type: discussions  # issues | discussions
      category: "Feedback"  # For discussions: category name
      labels: ["docs-feedback", "triage"]  # For issues: auto-labels

    # Slack backend (alternative)
    slack:
      webhook_url: "${SLACK_WEBHOOK_URL}"  # From env var
      channel: "#docs-feedback"  # Optional override

    # Custom webhook (alternative)
    webhook:
      url: "https://api.example.com/docs-feedback"
      method: POST
      headers:
        Authorization: "Bearer ${FEEDBACK_API_KEY}"

  # UI Configuration
  ui:
    # Code block feedback
    code_blocks:
      enabled: true
      button_label: "Report issue"  # Tooltip text
      icon: "warning"  # Icon name from theme

    # Page-level feedback
    page:
      enabled: true
      position: action-bar  # action-bar | footer | floating

      # Quick feedback (thumbs up/down)
      quick_feedback: true

      # Detailed feedback form
      form:
        types:
          - id: incorrect
            label: "Incorrect information"
            icon: "x-circle"
          - id: outdated
            label: "Outdated content"
            icon: "clock"
          - id: unclear
            label: "Unclear explanation"
            icon: "question"
          - id: missing
            label: "Missing information"
            icon: "plus-circle"
          - id: other
            label: "Other feedback"
            icon: "message"

        # Optional message field
        message:
          enabled: true
          placeholder: "Tell us more (optional)..."
          max_length: 1000

        # Optional email field
        email:
          enabled: false
          placeholder: "your@email.com (optional)"

  # Privacy & spam protection
  privacy:
    # Collect page URL and timestamp (always on)
    collect_context: true
    # Collect user agent (for debugging rendering issues)
    collect_user_agent: false
    # Rate limiting
    rate_limit:
      max_per_minute: 5
      max_per_session: 20
```

#### Theme-level Feature Flag (`theme.yaml`)

```yaml
features:
  feedback:
    code_blocks: true    # Show on code blocks
    page: true           # Show page-level feedback
    quick_feedback: true # Show thumbs up/down
```

### 2. Code Block Feedback Button

**Visual Design** (matches Mintlify):

```
┌────────────────────────────────────────────────────┐
│ Example config.yaml                   [⚠️] [📋] [✨]│
├────────────────────────────────────────────────────┤
│ database:                                          │
│   host: localhost                                  │
│   port: 5432                                       │
└────────────────────────────────────────────────────┘
         │
         └─► [⚠️] Report issue  [📋] Copy  [✨] Ask AI
```

**Template Partial** (`partials/code-block-actions.html`):

```jinja2
{# Code block action buttons - injected by code block renderer #}
{% if 'feedback.code_blocks' in theme.features %}
<div class="code-block__actions">
  {% if config.feedback.ui.code_blocks.enabled %}
  <button
    type="button"
    class="code-block__action code-block__action--feedback"
    data-action="feedback-code"
    data-code-lang="{{ lang }}"
    data-code-hash="{{ code_hash }}"
    aria-label="{{ config.feedback.ui.code_blocks.button_label ?? 'Report incorrect code' }}"
    title="{{ config.feedback.ui.code_blocks.button_label ?? 'Report incorrect code' }}">
    {{ icon(config.feedback.ui.code_blocks.icon ?? 'warning', size=16) }}
  </button>
  {% end %}

  <button
    type="button"
    class="code-block__action code-block__action--copy"
    data-action="copy-code"
    aria-label="Copy code">
    {{ icon('copy', size=16) }}
  </button>
</div>
```

### 3. Page-Level Feedback (Action Bar)

**Option A: Action Bar Button**

Add next to the existing share button:

```jinja2
{# In partials/action-bar.html #}
<div class="action-bar-actions">
  {# Existing share button #}
  <div class="action-bar-share">...</div>

  {# New feedback button #}
  {% if 'feedback.page' in theme.features %}
  <button
    class="action-bar-feedback"
    popovertarget="feedback-popover"
    aria-label="{{ t('feedback.button_label', default='Give feedback') }}">
    {{ icon('message-circle', size=16) }}
  </button>
  {% end %}
</div>
```

**Option B: Footer Widget ("Was this helpful?")**

Common pattern from AWS, Azure, Stripe docs:

```jinja2
{# partials/feedback-footer.html #}
{% if 'feedback.page' in theme.features %}
<div class="feedback-footer" data-bengal="feedback-footer">
  <span class="feedback-footer__prompt">Was this page helpful?</span>
  <div class="feedback-footer__buttons">
    <button
      class="feedback-footer__btn feedback-footer__btn--positive"
      data-action="feedback-quick"
      data-feedback-type="helpful"
      aria-label="Yes, this page was helpful">
      {{ icon('thumbs-up', size=20) }}
      <span>Yes</span>
    </button>
    <button
      class="feedback-footer__btn feedback-footer__btn--negative"
      data-action="feedback-quick"
      data-feedback-type="not-helpful"
      aria-label="No, this page needs improvement">
      {{ icon('thumbs-down', size=20) }}
      <span>No</span>
    </button>
  </div>
  <a href="#" class="feedback-footer__detailed" data-action="feedback-detailed">
    More options...
  </a>
</div>
{% end %}
```

### 4. Feedback Modal

**Unified modal for detailed feedback:**

```jinja2
{# partials/feedback-modal.html #}
<dialog id="feedback-modal" class="feedback-modal">
  <form method="dialog" class="feedback-modal__form" data-bengal="feedback-form">
    <header class="feedback-modal__header">
      <h2>{{ t('feedback.modal_title', default='Send Feedback') }}</h2>
      <button type="submit" value="close" class="feedback-modal__close" aria-label="Close">
        {{ icon('x', size=20) }}
      </button>
    </header>

    <div class="feedback-modal__body">
      {# Context display #}
      <div class="feedback-modal__context">
        <span class="feedback-modal__context-label">About:</span>
        <span class="feedback-modal__context-value" data-feedback-context></span>
      </div>

      {# Issue type selection #}
      <fieldset class="feedback-modal__types">
        <legend>What kind of issue?</legend>
        {% for type in config.feedback.ui.form.types %}
        <label class="feedback-modal__type">
          <input type="radio" name="feedback-type" value="{{ type.id }}" required>
          {{ icon(type.icon, size=16) }}
          <span>{{ type.label }}</span>
        </label>
        {% end %}
      </fieldset>

      {# Message textarea #}
      {% if config.feedback.ui.form.message.enabled %}
      <label class="feedback-modal__message">
        <span class="sr-only">Additional details</span>
        <textarea
          name="feedback-message"
          placeholder="{{ config.feedback.ui.form.message.placeholder }}"
          maxlength="{{ config.feedback.ui.form.message.max_length }}"
          rows="4"></textarea>
      </label>
      {% end %}
    </div>

    <footer class="feedback-modal__footer">
      <button type="submit" value="close" class="feedback-modal__cancel">Cancel</button>
      <button type="submit" value="submit" class="feedback-modal__submit" data-action="feedback-submit">
        Send Feedback
      </button>
    </footer>
  </form>
</dialog>
```

### 5. JavaScript Enhancement (`feedback.js`)

```javascript
/**
 * Feedback Enhancement
 *
 * PATTERN: DIALOG (see COMPONENT-PATTERNS.md)
 * - Modal uses native <dialog> API
 * - Browser handles: focus trap, escape key, backdrop
 * - JS handles: Form submission, API calls, state
 */

(function() {
  'use strict';

  const { log, ready } = window.BengalUtils;

  // Configuration from inline script (set by template)
  const config = window.BENGAL_FEEDBACK_CONFIG || {};

  ready(init);

  function init() {
    initCodeBlockFeedback();
    initQuickFeedback();
    initDetailedFeedback();
  }

  /**
   * Code block "Report issue" buttons
   */
  function initCodeBlockFeedback() {
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="feedback-code"]');
      if (!btn) return;

      const codeBlock = btn.closest('.code-block, pre');
      const code = codeBlock?.querySelector('code')?.textContent || '';
      const lang = btn.dataset.codeLang || '';

      openFeedbackModal({
        type: 'code',
        context: `Code sample (${lang})`,
        metadata: {
          code_snippet: code.slice(0, 500), // First 500 chars
          language: lang,
          code_hash: btn.dataset.codeHash,
        }
      });
    });
  }

  /**
   * Quick thumbs up/down feedback
   */
  function initQuickFeedback() {
    document.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-action="feedback-quick"]');
      if (!btn) return;

      const feedbackType = btn.dataset.feedbackType;

      // Visual feedback immediately
      const container = btn.closest('.feedback-footer');
      if (container) {
        container.innerHTML = `
          <span class="feedback-footer__thanks">
            Thanks for your feedback! ${feedbackType === 'helpful' ? '🎉' : ''}
          </span>
        `;
      }

      // Submit in background
      await submitFeedback({
        type: feedbackType,
        page_url: window.location.href,
        page_title: document.title,
      });
    });
  }

  /**
   * Detailed feedback modal
   */
  function initDetailedFeedback() {
    const modal = document.getElementById('feedback-modal');
    if (!modal) return;

    // Handle "More options" link
    document.addEventListener('click', (e) => {
      const link = e.target.closest('[data-action="feedback-detailed"]');
      if (!link) return;
      e.preventDefault();

      openFeedbackModal({
        type: 'page',
        context: document.title,
      });
    });

    // Handle form submission
    const form = modal.querySelector('[data-bengal="feedback-form"]');
    form?.addEventListener('submit', async (e) => {
      if (e.submitter?.value !== 'submit') return;

      e.preventDefault();

      const formData = new FormData(form);
      await submitFeedback({
        type: formData.get('feedback-type'),
        message: formData.get('feedback-message'),
        page_url: window.location.href,
        page_title: document.title,
        ...modal.feedbackMetadata,
      });

      // Close modal and show confirmation
      modal.close();
      showConfirmation();
    });
  }

  /**
   * Open feedback modal with context
   */
  function openFeedbackModal({ type, context, metadata = {} }) {
    const modal = document.getElementById('feedback-modal');
    if (!modal) return;

    // Set context display
    const contextEl = modal.querySelector('[data-feedback-context]');
    if (contextEl) {
      contextEl.textContent = context;
    }

    // Store metadata for submission
    modal.feedbackMetadata = {
      feedback_source: type,
      ...metadata,
    };

    modal.showModal();
  }

  /**
   * Submit feedback to configured backend
   */
  async function submitFeedback(data) {
    const payload = {
      ...data,
      timestamp: new Date().toISOString(),
      user_agent: config.collectUserAgent ? navigator.userAgent : undefined,
    };

    try {
      switch (config.backend?.type) {
        case 'github':
          await submitToGitHub(payload);
          break;
        case 'slack':
          await submitToSlack(payload);
          break;
        case 'webhook':
          await submitToWebhook(payload);
          break;
        default:
          log('Feedback backend not configured');
      }
    } catch (error) {
      log('Feedback submission failed:', error);
      // Don't throw - fail silently to not disrupt user
    }
  }

  /**
   * GitHub Issues/Discussions backend
   */
  async function submitToGitHub(data) {
    const { repo, type } = config.backend.github;

    // Build issue/discussion URL with pre-filled content
    const title = encodeURIComponent(`[Docs Feedback] ${data.page_title}`);
    const body = encodeURIComponent(buildGitHubBody(data));

    if (type === 'issues') {
      const labels = config.backend.github.labels?.join(',') || '';
      window.open(
        `https://github.com/${repo}/issues/new?title=${title}&body=${body}&labels=${labels}`,
        '_blank',
        'noopener,noreferrer'
      );
    } else {
      // Discussions
      const category = encodeURIComponent(config.backend.github.category || 'Feedback');
      window.open(
        `https://github.com/${repo}/discussions/new?category=${category}&title=${title}&body=${body}`,
        '_blank',
        'noopener,noreferrer'
      );
    }
  }

  /**
   * Build GitHub issue/discussion body
   */
  function buildGitHubBody(data) {
    let body = `## Feedback\n\n`;
    body += `**Page**: [${data.page_title}](${data.page_url})\n`;
    body += `**Type**: ${data.type}\n`;

    if (data.message) {
      body += `\n### Details\n\n${data.message}\n`;
    }

    if (data.code_snippet) {
      body += `\n### Code Sample\n\n\`\`\`${data.language}\n${data.code_snippet}\n\`\`\`\n`;
    }

    body += `\n---\n*Submitted via docs feedback on ${data.timestamp}*`;

    return body;
  }

  /**
   * Slack webhook backend
   */
  async function submitToSlack(data) {
    // Note: Direct webhook calls expose URL. Use serverless proxy in production.
    await fetch(config.backend.slack.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: `📝 *Docs Feedback*`,
        blocks: [
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: `*Page*: <${data.page_url}|${data.page_title}>\n*Type*: ${data.type}${data.message ? `\n*Message*: ${data.message}` : ''}`
            }
          },
          ...(data.code_snippet ? [{
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: `*Code (${data.language})*:\n\`\`\`\n${data.code_snippet.slice(0, 200)}\n\`\`\``
            }
          }] : [])
        ]
      })
    });
  }

  /**
   * Custom webhook backend
   */
  async function submitToWebhook(data) {
    const { url, method, headers } = config.backend.webhook;

    await fetch(url, {
      method: method || 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
      body: JSON.stringify(data),
    });
  }

  /**
   * Show confirmation after submission
   */
  function showConfirmation() {
    // Could use toast notification or inline message
    log('Feedback submitted successfully');
  }

})();
```

### 6. Serverless Proxy Templates (For Slack)

Direct webhook URLs expose credentials. Provide example serverless functions:

**Cloudflare Worker** (`examples/feedback-worker.js`):

```javascript
/**
 * Cloudflare Worker: Docs Feedback → Slack
 *
 * Validates requests and forwards to Slack webhook.
 * Deploy: wrangler deploy
 *
 * Environment variables:
 *   SLACK_WEBHOOK_URL - Slack incoming webhook URL
 *   ALLOWED_ORIGINS - Comma-separated allowed origins
 */

export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: corsHeaders(env.ALLOWED_ORIGINS),
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    // Origin check
    const origin = request.headers.get('Origin');
    if (!isAllowedOrigin(origin, env.ALLOWED_ORIGINS)) {
      return new Response('Forbidden', { status: 403 });
    }

    try {
      const data = await request.json();

      // Rate limiting would go here (use KV or Durable Objects)

      // Forward to Slack
      const slackResponse = await fetch(env.SLACK_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildSlackPayload(data)),
      });

      if (!slackResponse.ok) {
        throw new Error(`Slack error: ${slackResponse.status}`);
      }

      return new Response(JSON.stringify({ success: true }), {
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders(env.ALLOWED_ORIGINS),
        },
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: 'Failed to process feedback' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};

function buildSlackPayload(data) {
  return {
    text: `📝 Docs Feedback`,
    blocks: [
      {
        type: 'section',
        fields: [
          { type: 'mrkdwn', text: `*Page:*\n<${data.page_url}|${data.page_title}>` },
          { type: 'mrkdwn', text: `*Type:*\n${data.type}` },
        ],
      },
      ...(data.message ? [{
        type: 'section',
        text: { type: 'mrkdwn', text: `*Details:*\n${data.message}` },
      }] : []),
    ],
  };
}

function corsHeaders(allowedOrigins) {
  return {
    'Access-Control-Allow-Origin': allowedOrigins?.split(',')[0] || '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function isAllowedOrigin(origin, allowedOrigins) {
  if (!allowedOrigins) return true;
  return allowedOrigins.split(',').includes(origin);
}
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (v0.2.0)

| Task | Files | Effort |
|------|-------|--------|
| Add feedback config schema | `bengal/config/schema.py` | 0.5d |
| Feedback modal template | `themes/default/templates/partials/feedback-modal.html` | 0.5d |
| Feedback JS enhancement | `themes/default/assets/js/enhancements/feedback.js` | 1d |
| Feedback CSS | `themes/default/assets/css/components/feedback.css` | 0.5d |
| Theme feature flags | `themes/default/theme.yaml`, `themes/config.py` | 0.25d |

**Total Phase 1**: ~3 days

### Phase 2: UI Integration (v0.2.0)

| Task | Files | Effort |
|------|-------|--------|
| Code block feedback button | `themes/default/templates/partials/code-block-actions.html` | 0.5d |
| Action bar feedback button | `themes/default/templates/partials/action-bar.html` | 0.25d |
| Footer feedback widget | `themes/default/templates/partials/feedback-footer.html` | 0.5d |
| Integration tests | `tests/integration/test_feedback.py` | 0.5d |

**Total Phase 2**: ~2 days

### Phase 3: Backend Integrations (v0.2.0)

| Task | Files | Effort |
|------|-------|--------|
| GitHub Issues/Discussions backend | `feedback.js` | 0.5d |
| Serverless proxy templates | `examples/feedback-*.js` | 0.5d |
| Documentation | `site/content/docs/features/feedback.md` | 0.5d |

**Total Phase 3**: ~1.5 days

**Grand Total**: ~6.5 days

---

## UX Considerations

### Visual Design

1. **Code block button**: Subtle, appears on hover (like existing copy button)
2. **Action bar button**: Small icon button, unobtrusive
3. **Footer widget**: Clear CTA, appears after content
4. **Modal**: Clean, minimal fields, fast to complete

### Accessibility

- All buttons have `aria-label`
- Modal uses native `<dialog>` for proper focus management
- Keyboard navigable (Tab, Escape)
- Screen reader announcements for success/error states

### Privacy

- No PII collected by default
- Optional email field (off by default)
- Page URL and title are auto-filled (users can see what's sent)
- Rate limiting prevents abuse

---

## Alternatives Considered

### 1. Third-Party Services (Canny, UserVoice)

**Pros**: Full-featured, analytics, voting  
**Cons**: External dependency, cost, overkill for most docs  
**Decision**: Offer as alternative in docs, not built-in

### 2. Client-Side Only (Direct Slack Webhook)

**Pros**: Simpler  
**Cons**: Exposes webhook URL  
**Decision**: Provide serverless templates for secure option

### 3. GitHub App Integration

**Pros**: Could create issues via API without user auth  
**Cons**: Requires app installation, token management  
**Decision**: Defer to future version; URL-based approach works for MVP

---

## Success Metrics

After 3 months of deployment:

- [ ] At least 3 Bengal-powered docs sites enable feedback
- [ ] Reduction in "outdated docs" complaints in community channels
- [ ] Feedback submission latency < 2 seconds
- [ ] No reported security issues with backends

---

## Open Questions

1. **Should feedback require a GitHub account for GitHub backend?**
   - Current: Yes (opens GitHub in new tab for issue/discussion creation)
   - Alternative: Anonymous via GitHub App API (adds complexity)

2. **Should we support email notifications directly?**
   - Current: No (use Slack or webhook → email integration)
   - Could add later via webhook/SMTP

3. **Should quick feedback (thumbs) be opt-in or opt-out?**
   - Current: Opt-in via feature flag
   - Could default to enabled if feedback feature is on

---

## References

- [Mintlify "Report incorrect code"](https://mintlify.com/docs) - Inspiration for code block feedback
- [Fern Docs Feedback](https://www.buildwithfern.com/) - Similar implementation
- [GitBook Ratings](https://docs.gitbook.com/) - Footer feedback widget pattern
- [Stripe Docs Feedback](https://stripe.com/docs) - "Was this page helpful?" pattern
- [bengal/themes/default/templates/partials/action-bar.html](../bengal/themes/default/templates/partials/action-bar.html) - Existing action bar
- [bengal/themes/default/assets/js/enhancements/action-bar.js](../bengal/themes/default/assets/js/enhancements/action-bar.js) - Existing enhancement pattern
