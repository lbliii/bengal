# Site Templates Implementation

**Date:** October 12, 2025  
**Status:** ✅ Complete

## Overview

Enhanced the `bengal new site` command to support multiple site templates, making it easier for users to get started with different types of websites.

## Implementation

### 1. Created Site Templates Module

**File:** `bengal/cli/site_templates.py`

Implemented a comprehensive template system with:
- `PageTemplate` dataclass for individual pages
- `SiteTemplate` dataclass for complete site configurations
- Template registry for easy access

### 2. Template Types

Created 6 different templates:

#### Default Template
- Basic site structure (original behavior)
- Single index page
- Minimal setup

#### Blog Template
- `content/posts/` directory with sample posts
- `content/drafts/` directory for work in progress
- About page
- Home page with blog introduction
- Sample posts with tags and categories

#### Docs Template
- Hierarchical documentation structure
- `content/getting-started/` - Installation, quickstart, configuration
- `content/guides/` - Step-by-step tutorials
- `content/api/` - API reference documentation
- `content/advanced/` - Advanced topics
- Navigation-friendly structure with sections and ordering

#### Portfolio Template
- Projects showcase structure
- `content/projects/` with sample projects
- About page with skills and experience
- Contact page
- Home page with introduction
- Sample project pages with featured images, demos, and GitHub links

#### Resume Template
- Professional resume/CV layout
- Single comprehensive page with:
  - Professional summary
  - Skills (technical and soft)
  - Work experience
  - Education
  - Certifications
  - Projects
  - Awards and recognition

#### Landing Template
- Marketing/product landing page
- Features section
- Pricing tiers
- Customer testimonials
- FAQ section
- Privacy policy and terms of service pages

### 3. Updated CLI Command

**File:** `bengal/cli/commands/new.py`

- Added `--template` option with choices: `default`, `blog`, `docs`, `portfolio`, `resume`, `landing`
- Updated help text with examples
- Enhanced output to show template description
- Maintains backward compatibility (defaults to "default" template)

## Usage Examples

```bash
# Create a blog
bengal new site myblog --template blog

# Create documentation site
bengal new site mydocs --template docs

# Create portfolio
bengal new site myportfolio --template portfolio

# Create resume site
bengal new site myresume --template resume

# Create landing page
bengal new site mylanding --template landing

# Default (backward compatible)
bengal new site mysite
# or explicitly:
bengal new site mysite --template default
```

## Testing

All templates were tested and verified:
- ✅ Default template creates 1 page
- ✅ Blog template creates 4 pages (index, about, 2 posts) + directories
- ✅ Docs template creates 6 pages across multiple sections
- ✅ Portfolio template creates 6 pages (home, about, contact, 2 projects)
- ✅ Resume template creates 1 comprehensive resume page
- ✅ Landing template creates 3 pages (landing, privacy, terms)

All templates successfully build and generate output.

## Benefits

1. **Better Onboarding** - Users get started faster with pre-configured structures
2. **Best Practices** - Each template demonstrates good content organization
3. **Learning Tool** - Sample content shows users what's possible
4. **Flexibility** - Users can choose the template that fits their needs
5. **Backward Compatible** - Default template maintains original behavior

## File Structure

```
bengal/cli/
  ├── commands/
  │   └── new.py           # Updated with --template option
  └── site_templates.py    # New: Template definitions
```

## Future Enhancements

Possible future improvements:
- Community-contributed templates
- Template inheritance/composition
- Template customization options
- Template preview/documentation site
- Custom template creation from existing sites
- Template variables for further customization

## Notes

- All templates use atomic writes for crash safety
- Templates include helpful placeholder text
- Sample content includes current dates
- Each template has appropriate directory structure
- Templates are designed to be immediately editable
