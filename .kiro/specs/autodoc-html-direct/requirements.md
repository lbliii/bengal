# Requirements: Direct HTML Autodoc Generation

## Introduction

Replace Bengal's current Markdown+Jinja2 autodoc templates with direct HTML generation while maintaining full integration with Bengal's page system, navigation, search indexing, and output formats.

## Glossary

- **Autodoc System**: Bengal's AST-based documentation generation system
- **DocElement**: Parsed documentation element (module, class, function, etc.)
- **Page Integration**: Full participation in Bengal's page lifecycle (navigation, search, health checks, output formats)
- **Direct HTML Generation**: Generating final HTML without intermediate Markdown+Jinja2 step
- **Virtual Page**: Page object that represents generated content without source file

## Requirements

### Requirement 1: Eliminate Template Complexity

**User Story:** As a Bengal maintainer, I want to generate autodoc HTML directly so that I don't have to maintain complex 300+ line Jinja2+Markdown templates.

#### Acceptance Criteria

1. WHEN generating autodoc pages, THE Autodoc System SHALL generate HTML directly without Markdown intermediate step
2. WHEN rendering documentation elements, THE Autodoc System SHALL use simple HTML templates or programmatic generation
3. THE Autodoc System SHALL eliminate all `.md.jinja2` templates from the autodoc workflow
4. THE Autodoc System SHALL reduce template complexity by at least 80% compared to current approach

### Requirement 2: Maintain Page Integration

**User Story:** As a Bengal user, I want autodoc pages to appear in navigation, search, and all output formats so that they are fully discoverable.

#### Acceptance Criteria

1. WHEN autodoc generates pages, THE Bengal System SHALL include them in site navigation
2. WHEN building search index, THE Bengal System SHALL index autodoc page content
3. WHEN generating output formats, THE Bengal System SHALL include autodoc pages in JSON and LLM text outputs
4. WHEN running health checks, THE Bengal System SHALL validate autodoc pages like any other page
5. THE Bengal System SHALL support incremental builds for autodoc pages

### Requirement 3: Preserve Output Quality

**User Story:** As a documentation reader, I want autodoc pages to have the same visual quality and functionality as current pages so that the user experience is consistent.

#### Acceptance Criteria

1. THE Autodoc System SHALL generate HTML with equivalent visual quality to current Markdown output
2. THE Autodoc System SHALL support all current features (parameters tables, inheritance, examples, etc.)
3. THE Autodoc System SHALL maintain responsive design and accessibility standards
4. THE Autodoc System SHALL preserve all metadata and cross-references

### Requirement 4: Reliable HTML Delivery

**User Story:** As a Bengal user, I want autodoc builds to consistently produce valid HTML output so that documentation generation is reliable.

#### Acceptance Criteria

1. THE Autodoc System SHALL generate valid HTML5 markup
2. WHEN autodoc encounters errors, THE Bengal System SHALL provide clear error messages with context
3. THE Autodoc System SHALL handle edge cases without breaking the build process
4. THE Autodoc System SHALL validate generated HTML before writing to disk

### Requirement 5: Correct Output Path Handling

**User Story:** As a Bengal user, I want autodoc pages to be generated in the correct output directory so that they appear in the final built site without overwriting existing site content.

#### Acceptance Criteria

1. WHEN generating autodoc pages, THE Autodoc System SHALL output HTML files to the site's public directory
2. THE Autodoc System SHALL NOT output files to the site's source directory or other incorrect locations
3. THE Autodoc System SHALL NOT overwrite existing site directories like config/, content/, or other source directories
4. WHEN building the site, THE Bengal System SHALL include autodoc pages in the final public output
5. THE Autodoc System SHALL respect the configured output directory structure
6. THE Autodoc System SHALL generate URLs that match the actual file locations in the public directory
7. THE Autodoc System SHALL preserve all existing site configuration and content directories

### Requirement 6: Performance Maintenance

**User Story:** As a Bengal user, I want autodoc generation to remain fast so that build times don't increase significantly.

#### Acceptance Criteria

1. THE Autodoc System SHALL maintain current build performance characteristics
2. THE Autodoc System SHALL support parallel generation of documentation pages
3. THE Autodoc System SHALL cache generated HTML when source hasn't changed
4. THE Autodoc System SHALL integrate with Bengal's incremental build system
