/**
 * Page feedback widget — dispatches CustomEvent, no default telemetry.
 */
(function () {
  'use strict';

  if (!window.Bengal?.define) return;

  window.Bengal.define('bengal-page-feedback', class extends window.Bengal.Base {
    connectedCallback() {
      if (this._wired) return;
      this._wired = true;

      const popover = this.querySelector('[popover]');
      const thanks = this.querySelector('.page-meta-feedback__thanks');
      const question = this.querySelector('.page-meta-feedback__question');
      const actions = this.querySelector('.page-meta-feedback__actions');

      this.querySelectorAll('[data-feedback]').forEach((button) => {
        button.addEventListener('click', () => {
          const helpful = button.dataset.feedback === 'yes';
          this.dispatchEvent(new CustomEvent('pagefeedback', {
            bubbles: true,
            detail: {
              helpful,
              pageTitle: this.dataset.pageTitle || document.title,
              path: window.location.pathname,
            },
          }));

          if (question) question.hidden = true;
          if (actions) actions.hidden = true;
          if (thanks) thanks.hidden = false;

          if (popover?.hidePopover) {
            setTimeout(() => popover.hidePopover(), 1200);
          }
        });
      });
    }
  });
})();
