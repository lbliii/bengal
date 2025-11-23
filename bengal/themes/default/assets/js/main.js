/**
 * Bengal SSG Default Theme
 * Main JavaScript
 */

(function () {
  'use strict';

  // Ensure utils are available
  if (!window.BengalUtils) {
    console.error('BengalUtils not loaded - main.js requires utils.js');
    return;
  }

  const { log, copyToClipboard, isExternalUrl, ready } = window.BengalUtils;

  /**
   * Smooth scroll for anchor links
   */
  function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
      anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');

        // Skip empty anchors
        if (href === '#') {
          return;
        }

        // Extract ID from href (remove the '#')
        const id = href.substring(1);
        const target = document.getElementById(id);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });

          // Update URL without jumping
          history.pushState(null, null, href);

          // Focus target for accessibility
          target.focus({ preventScroll: true });
        }
      });
    });
  }

  /**
   * Add external link indicators
   */
  function setupExternalLinks() {
    const links = document.querySelectorAll('a[href]');
    links.forEach(function (link) {
      const href = link.getAttribute('href');
      
      // Skip anchor links and empty hrefs
      if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) {
        return;
      }

      // Check if external using URL parsing
      if (isExternalUrl(href)) {
        // Add external data attribute for CSS targeting
        link.setAttribute('data-external', 'true');
        link.setAttribute('rel', 'noopener noreferrer');
        link.setAttribute('target', '_blank');

        // Add visual indicator (optional)
        link.setAttribute('aria-label', link.textContent + ' (opens in new tab)');
      }
    });
  }

  /**
   * Copy code button for code blocks with language labels
   */
  function setupCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('pre code');

    codeBlocks.forEach(function (codeBlock) {
      const pre = codeBlock.parentElement;

      // Skip if already processed
      if (pre.querySelector('.code-copy-button')) {
        return;
      }

      // Detect language from class (e.g., language-python, hljs-python)
      let language = '';
      const classList = codeBlock.className;
      const matches = classList.match(/language-(\w+)|hljs-(\w+)/);
      if (matches) {
        language = (matches[1] || matches[2]).toUpperCase();
      }

      // Create header container
      const header = document.createElement('div');
      header.className = 'code-header-inline';

      // Create language label if detected
      if (language) {
        const langLabel = document.createElement('span');
        langLabel.className = 'code-language';
        langLabel.textContent = language;
        // Use CSS custom properties via getComputedStyle
        const root = getComputedStyle(document.documentElement);
        langLabel.style.fontSize = root.getPropertyValue('--text-caption').trim() || '0.75rem';
        langLabel.style.fontWeight = root.getPropertyValue('--weight-semibold').trim() || '600';
        langLabel.style.color = 'var(--color-text-muted)';
        langLabel.style.textTransform = 'uppercase';
        langLabel.style.letterSpacing = '0.05em';
        langLabel.style.opacity = '0.7';
        header.appendChild(langLabel);
      } else {
        // Empty span to maintain layout
        header.appendChild(document.createElement('span'));
      }

      // Create copy button
      const button = document.createElement('button');
      button.className = 'code-copy-button';
      button.setAttribute('aria-label', 'Copy code to clipboard');
      button.style.pointerEvents = 'auto';

      // Add copy icon (SVG) - icon only, no text
      button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span>Copy</span>
      `;

      header.appendChild(button);

      // Wrap pre in a container and place button outside the scrolling area
      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';
      wrapper.style.position = 'relative';

      // Move decorative border classes to wrapper so pseudo-borders stay fixed while <pre> scrolls
      const borderClasses = [
        'gradient-border',
        'gradient-border-subtle',
        'gradient-border-strong',
        'fluid-border',
        'fluid-combined'
      ];
      borderClasses.forEach(function (cls) {
        if (pre.classList.contains(cls)) {
          pre.classList.remove(cls);
          wrapper.classList.add(cls);
        }
      });

      // Insert wrapper before pre, then move pre into wrapper
      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(pre);

      // Add header to wrapper (not inside pre)
      wrapper.appendChild(header);

      // Adjust pre padding
      pre.style.paddingTop = '2.5rem'; // Make room for header

      // Copy functionality
      button.addEventListener('click', function (e) {
        e.preventDefault();
        const code = codeBlock.textContent;

        copyToClipboard(code).then(function () {
          // Show success
          button.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>Copied!</span>
          `;
          button.classList.add('copied');
          button.setAttribute('aria-label', 'Code copied!');

          // Reset after 2 seconds
          setTimeout(function () {
            button.innerHTML = `
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>Copy</span>
            `;
            button.classList.remove('copied');
            button.setAttribute('aria-label', 'Copy code to clipboard');
          }, 2000);
        }).catch(function (err) {
          log('Failed to copy code:', err);
          button.setAttribute('aria-label', 'Failed to copy');
          
          // Show error state briefly
          setTimeout(function () {
            button.innerHTML = `
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>Copy</span>
            `;
            button.setAttribute('aria-label', 'Copy code to clipboard');
          }, 2000);
        });
      });
    });
  }

  /**
   * Lazy load images
   */
  function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
            }
            imageObserver.unobserve(img);
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(function (img) {
        imageObserver.observe(img);
      });
    } else {
      // Fallback for older browsers
      document.querySelectorAll('img[data-src]').forEach(function (img) {
        img.src = img.dataset.src;
      });
    }
  }

  /**
   * Table of contents highlighting
   */
  function setupTOCHighlight() {
    const toc = document.querySelector('.toc');
    if (!toc) return;

    const headings = document.querySelectorAll('h2[id], h3[id], h4[id]');
    const tocLinks = toc.querySelectorAll('a');

    if (headings.length === 0 || tocLinks.length === 0) return;

    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');

          // Remove active class from all links
          tocLinks.forEach(function (link) {
            link.classList.remove('active');
          });

          // Add active class to current link
          // Use find() to match href ending with the ID (handles IDs starting with numbers)
          const activeLink = Array.from(tocLinks).find(function (link) {
            return link.getAttribute('href') === '#' + id;
          });
          if (activeLink) {
            activeLink.classList.add('active');
          }
        }
      });
    }, {
      rootMargin: '-80px 0px -80% 0px'
    });

    headings.forEach(function (heading) {
      observer.observe(heading);
    });
  }

  /**
   * Detect keyboard navigation for better focus indicators
   */
  function setupKeyboardDetection() {
    // Add class to body when user tabs (keyboard navigation)
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Tab') {
        document.body.classList.add('user-is-tabbing');
      }
    });

    // Remove class when user clicks (mouse navigation)
    document.addEventListener('mousedown', function () {
      document.body.classList.remove('user-is-tabbing');
    });
  }

  /**
   * Initialize all features
   */
  function init() {
    setupSmoothScroll();
    setupExternalLinks();
    setupCodeCopyButtons();
    setupLazyLoading();
    setupTOCHighlight();
    setupKeyboardDetection();

    log('Bengal theme initialized');
  }

  // Initialize after DOM is ready
  ready(init);
})();
