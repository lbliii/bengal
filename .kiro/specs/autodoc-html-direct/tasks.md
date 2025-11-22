# Implementation Plan: Direct HTML Autodoc Generation

**STATUS: ABANDONED** - This feature was abandoned due to fundamental implementation issues with synthetic page generation and URL path handling. The existing Markdown + Jinja2 system works correctly and will be maintained.

Convert the feature design into a series of prompts for implementing direct HTML generation for autodoc while maintaining full Bengal integration.

## Task List

- [x] 1. Create SyntheticPage foundation
  - Create `bengal/core/synthetic_page.py` with SyntheticPage class extending Page
  - Implement virtual source path handling and content hashing for caching
  - Add proper integration with Page lifecycle methods (needs_rebuild, get_cache_key)
  - Ensure SyntheticPage objects work with existing navigation and search systems
  - _Requirements: 1.1, 2.1, 2.4_

- [x] 2. Implement HTML component rendering system
  - Create `bengal/autodoc/html_components.py` with reusable HTML component generators
  - Implement `render_parameters_table()` for function/method parameters
  - Implement `render_inheritance_chain()` for class inheritance display
  - Implement `render_examples_section()` for code examples with syntax highlighting
  - Add `render_attributes_table()` for class attributes
  - _Requirements: 1.2, 3.2_

- [x] 3. Build core HTMLRenderer system
  - Create `bengal/autodoc/html_renderer.py` with HTMLRenderer class
  - Implement `render_module()`, `render_class()`, `render_function()` methods
  - Add error handling with graceful degradation to error pages
  - Integrate HTML validation to ensure valid HTML5 output
  - Add theme class integration for consistent styling
  - _Requirements: 1.1, 1.2, 3.1, 4.1, 4.2_

- [x] 4. Modify AutodocGenerator for HTML generation
  - Update `bengal/autodoc/generator.py` to use HTMLRenderer instead of Jinja2 templates
  - Implement `generate_pages()` method returning list of SyntheticPage objects
  - Add metadata building for synthetic pages with proper frontmatter equivalent
  - Ensure URL path generation matches current autodoc URL structure
  - _Requirements: 1.1, 1.3, 2.3_

- [x] 5. Integrate synthetic pages into content discovery
  - Modify `bengal/discovery/content_discovery.py` to include autodoc synthetic pages
  - Add `_discover_autodoc_content()` method that generates SyntheticPage objects
  - Ensure synthetic pages are added to main page list for full pipeline integration
  - Add feature flag `autodoc.use_html_renderer` for gradual rollout
  - _Requirements: 2.1, 2.2, 2.5_

- [x] 6. Implement caching and incremental build support
  - Add cache key generation for synthetic pages based on source file timestamps and config
  - Implement `needs_rebuild()` logic for SyntheticPage objects
  - Ensure synthetic pages participate in incremental build system
  - Add cache invalidation when autodoc configuration changes
  - _Requirements: 2.5, 6.3, 6.4_

- [x] 13. Fix output path handling to prevent directory overwriting
  - Investigate and fix the issue where autodoc pages are being generated in wrong locations
  - Ensure synthetic pages only generate HTML files in the `site/public/` directory
  - Prevent overwriting of existing site directories like `config/`, `content/`, etc.
  - Fix URL generation to use proper web paths instead of absolute file system paths
  - Verify that all generated pages appear in the correct `/api/` URL structure
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 7. Create simple HTML templates for customization
  - Create `bengal/autodoc/html_templates/` directory with simple HTML templates
  - Add `module.html`, `class.html`, `function.html` templates under 50 lines each
  - Implement template loading and rendering in HTMLRenderer
  - Add template override capability for theme customization
  - _Requirements: 1.2, 3.1, 3.3_

- [x] 8. Add HTML validation and error handling
  - Implement HTML validation in HTMLRenderer to catch malformed output
  - Add comprehensive error handling with context information
  - Create error page generation for failed documentation elements
  - Add logging and debugging information for troubleshooting
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 9. Ensure output format integration
  - Verify synthetic pages appear in JSON output format generation
  - Verify synthetic pages appear in LLM text output format generation
  - Test search index generation includes synthetic page content
  - Confirm health checks validate synthetic pages like regular pages
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 10. Performance optimization and parallel generation
  - Add parallel processing support for generating multiple autodoc pages
  - Implement HTML-level caching to avoid regeneration when source unchanged
  - Profile performance compared to current Markdown+Jinja2 approach
  - Optimize memory usage for large documentation sets
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 11. Migration and backward compatibility
  - Add feature flag to switch between old and new systems
  - Create migration guide for users with custom autodoc templates
  - Ensure generated HTML maintains visual parity with current output
  - Add configuration options for HTML generation behavior
  - _Requirements: 1.4, 3.1, 3.2_

- [x] 12. Testing and validation
  - Create comprehensive tests for SyntheticPage class functionality
  - Add tests for HTMLRenderer with various DocElement types
  - Test integration with Bengal's page pipeline (navigation, search, health)
  - Add regression tests comparing HTML output quality to current system
  - Test error handling and graceful degradation scenarios
  - _Requirements: 1.4, 2.4, 3.1, 4.1, 4.3_

- [ ] 14. Fix CLI HTML rendering
  - Investigate why CLI synthetic pages generate JSON/TXT but not HTML files
  - Ensure CLI DocElements have proper content and metadata for HTML rendering
  - Fix any template or rendering issues specific to CLI command documentation
  - Verify CLI pages render with same quality as API pages (parameters, examples, etc.)
  - Test that all CLI commands, options, and arguments get proper HTML output
  - _Requirements: 1.1, 1.2, 3.1, 4.1_
