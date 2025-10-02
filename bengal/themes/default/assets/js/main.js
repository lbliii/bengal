/**
 * Bengal SSG Default Theme
 * Main JavaScript
 */

(function() {
  'use strict';
  
  /**
   * Smooth scroll for anchor links
   */
  function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        
        // Skip empty anchors
        if (href === '#') {
          return;
        }
        
        const target = document.querySelector(href);
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
    const links = document.querySelectorAll('a[href^="http"]');
    links.forEach(function(link) {
      const href = link.getAttribute('href');
      
      // Check if external (not same domain)
      if (!href.includes(window.location.hostname)) {
        // Add external attribute
        link.setAttribute('rel', 'noopener noreferrer');
        link.setAttribute('target', '_blank');
        
        // Add visual indicator (optional)
        link.setAttribute('aria-label', link.textContent + ' (opens in new tab)');
      }
    });
  }
  
  /**
   * Copy code button for code blocks
   */
  function setupCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('pre code');
    
    codeBlocks.forEach(function(codeBlock) {
      const pre = codeBlock.parentElement;
      
      // Create copy button
      const button = document.createElement('button');
      button.className = 'code-copy-button';
      button.setAttribute('aria-label', 'Copy code');
      button.innerHTML = '<span>Copy</span>';
      
      // Insert button
      pre.style.position = 'relative';
      button.style.position = 'absolute';
      button.style.top = 'var(--space-2)';
      button.style.right = 'var(--space-2)';
      pre.appendChild(button);
      
      // Copy functionality
      button.addEventListener('click', function() {
        const code = codeBlock.textContent;
        
        navigator.clipboard.writeText(code).then(function() {
          // Show success
          button.innerHTML = '<span>Copied!</span>';
          button.classList.add('copied');
          
          // Reset after 2 seconds
          setTimeout(function() {
            button.innerHTML = '<span>Copy</span>';
            button.classList.remove('copied');
          }, 2000);
        }).catch(function(err) {
          console.error('Failed to copy code:', err);
          button.innerHTML = '<span>Failed</span>';
          
          setTimeout(function() {
            button.innerHTML = '<span>Copy</span>';
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
      const imageObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
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
      
      document.querySelectorAll('img[data-src]').forEach(function(img) {
        imageObserver.observe(img);
      });
    } else {
      // Fallback for older browsers
      document.querySelectorAll('img[data-src]').forEach(function(img) {
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
    
    const observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');
          
          // Remove active class from all links
          tocLinks.forEach(function(link) {
            link.classList.remove('active');
          });
          
          // Add active class to current link
          const activeLink = toc.querySelector('a[href="#' + id + '"]');
          if (activeLink) {
            activeLink.classList.add('active');
          }
        }
      });
    }, {
      rootMargin: '-80px 0px -80% 0px'
    });
    
    headings.forEach(function(heading) {
      observer.observe(heading);
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
    
    // Log initialization (optional, remove in production)
    console.log('Bengal theme initialized');
  }
  
  // Initialize after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

