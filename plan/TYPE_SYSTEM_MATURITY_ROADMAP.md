# Type System Maturity Roadmap

**Goal**: Bring Bengal's type-based template selection to production maturity  
**Status**: Phase 1 Complete (Core Implementation)  
**Target**: Phases 2-5 for v1.0 release

## Current State ✅

### Implemented (Phase 1)
- [x] Type-based template selection for single pages
- [x] Type-based template selection for index pages
- [x] Type → template mappings system
- [x] Cascade support for type inheritance
- [x] API reference templates with sidebar navigation
- [x] CLI reference templates with sidebar navigation
- [x] Basic type mappings (python-module, cli-command, doc, tutorial, blog)
- [x] Fallback chain (type → section → default)

### What's Missing

**Templates**: Only 2 of 5 types have full template families  
**Documentation**: Patterns documented but not in user-facing guides  
**Examples**: No showcase sites demonstrating the system  
**Tooling**: No CLI scaffolding for types/templates  
**Validation**: No helpful errors when things go wrong  
**Testing**: No comprehensive test coverage  

## Phase 2: Complete Template Families 🎨

**Goal**: Provide production-ready templates for all core types  
**Duration**: 3-5 days  
**Priority**: HIGH

### 2.1 Documentation Templates (doc/)

Create the full `doc/` template family:

**Files to Create:**
- ✅ `doc/single.html` - Already exists as `doc.html`, need to move
- ✅ `doc/list.html` - Already exists as `docs.html`, need to move
- [ ] Ensure both use 3-column layout with sidebar navigation

**Tasks:**
1. Refactor existing `doc.html` → `doc/single.html`
2. Refactor existing `docs.html` → `doc/list.html`  
3. Create aliases for backward compatibility
4. Test with showcase docs section

**Acceptance Criteria:**
- Setting `type: doc` uses doc templates
- Both index and pages have consistent styling
- Sidebar navigation works
- Backward compatible with existing `template: doc.html`

### 2.2 Tutorial Templates (tutorial/)

Create tutorial template family optimized for learning:

**Files to Create:**
- [ ] `tutorial/list.html` - Grid/card layout with difficulty, time, prerequisites
- [ ] `tutorial/single.html` - Linear step-by-step layout
- [ ] `partials/tutorial-card.html` - Reusable tutorial card
- [ ] `partials/tutorial-nav.html` - Prev/next with progress

**Features:**
- Difficulty badges (beginner, intermediate, advanced)
- Estimated time to complete
- Prerequisites list
- Progress indicator (Step 1 of 5)
- Large prev/next buttons
- Optional video embed support
- Code examples with copy button

**Design Direction:**
- Friendly, encouraging tone
- Prominent navigation (don't let users get stuck)
- Visual hierarchy emphasizing current step
- Mobile-first (tutorials on phones/tablets)

**Tasks:**
1. Design tutorial card component
2. Implement tutorial list as grid
3. Create step-based single page layout
4. Add progress tracking JavaScript
5. Style for mobile-first experience

### 2.3 Blog Templates (blog/)

Create blog template family for content marketing:

**Files to Create:**
- [ ] `blog/list.html` - Reverse-chrono with featured posts
- [ ] `blog/single.html` - Article layout with author, sharing
- [ ] `partials/blog-card.html` - Post card with image, excerpt
- [ ] `partials/author-bio.html` - Author information box
- [ ] `partials/social-share.html` - Share buttons

**Features:**
- Featured posts section (hero or top 3)
- Reverse chronological order
- Pagination (10-20 posts per page)
- Author info with avatar
- Reading time estimate
- Social sharing buttons
- Related posts
- Comment integration hooks (data-comments-target)
- Newsletter signup CTA

**Design Direction:**
- Magazine/blog aesthetic
- Large featured images
- Readable typography (serif for body?)
- Author attribution prominent
- Engagement-focused (CTAs, shares)

**Tasks:**
1. Implement featured posts logic
2. Create blog post card component
3. Design single post layout
4. Add author bio partial
5. Implement social share buttons
6. Add pagination to list view
7. Style for content-first reading experience

### 2.4 Landing Page Template (landing/)

Special template for marketing pages:

**Files to Create:**
- [ ] `landing/single.html` - Hero, features, CTA sections
- [ ] `partials/hero.html` - Reusable hero component
- [ ] `partials/feature-grid.html` - Feature showcase
- [ ] `partials/cta-section.html` - Call-to-action blocks

**Features:**
- Hero section with image/video
- Feature grid with icons
- Testimonials section
- Pricing table support
- Multi-CTA support
- Full-width sections
- No sidebar (content is king)

**Use Case:**
```yaml
---
title: Welcome to Our Product
type: landing
---
```

### 2.5 API Reference Enhancement

Enhance existing API templates:

**Tasks:**
- [ ] Add "Edit on GitHub" links
- [ ] Add copy import path button
- [ ] Add source code links
- [ ] Improve mobile navigation
- [ ] Add search integration hooks

## Phase 3: Documentation & Guides 📚

**Goal**: Comprehensive documentation for users and theme developers  
**Duration**: 4-6 days  
**Priority**: HIGH

### 3.1 User Guide

**File**: `docs/CONTENT_TYPES.md`

**Sections:**
1. Introduction to Content Types
   - What are content types?
   - Why use types vs templates?
   - When to use each approach

2. Available Content Types
   - `doc` - Reference documentation
   - `tutorial` - Step-by-step guides
   - `blog` - Blog posts and articles
   - `api-reference` - API documentation
   - `cli-reference` - CLI documentation
   - `landing` - Marketing pages

3. Using Content Types
   - Setting type in frontmatter
   - Cascading types to children
   - Overriding with template
   - Custom types

4. Common Patterns
   - Uniform section types
   - Custom index + standard pages
   - Mixed content types
   - Migration from templates

5. Troubleshooting
   - Type not working
   - Template not found
   - Cascade not applying

### 3.2 Theme Developer Guide

**File**: `docs/THEME_DEVELOPMENT.md` (new section)

**Sections:**
1. Template Families
   - Concept and structure
   - Naming conventions
   - Required files vs optional

2. Creating a Template Family
   - Directory structure
   - list.html vs single.html
   - Shared partials
   - CSS organization

3. Type Mappings
   - How mappings work
   - Adding custom types
   - Type inheritance

4. Template Context
   - Available variables
   - Accessing page metadata
   - Section relationships
   - Template functions

5. Best Practices
   - Semantic types
   - Graceful degradation
   - Mobile-first
   - Accessibility

6. Example: Complete Template Family
   - Step-by-step tutorial
   - Code samples
   - Common patterns

### 3.3 Migration Guide

**File**: `docs/MIGRATION_TYPE_SYSTEM.md`

**Sections:**
1. Overview of Changes
2. Backward Compatibility
3. Migration Steps
4. Common Scenarios
   - Section templates → Type families
   - Template frontmatter → Type cascade
   - Custom templates → Hybrid approach
5. Checklist

### 3.4 Inline Documentation

**Update existing docs:**
- [ ] `TEMPLATES.md` - Add type-based section
- [ ] `README.md` - Mention type system in features
- [ ] `GETTING_STARTED.md` - Add type examples
- [ ] `bengal.toml.example` - Add type examples in comments

### 3.5 API Documentation

Document the implementation:
- [ ] `bengal/rendering/renderer.py` - Expand docstrings
- [ ] Add code examples to docstrings
- [ ] Document type_mappings extension point

## Phase 4: Tooling & CLI Support 🛠️

**Goal**: Make it easy to scaffold and work with types  
**Duration**: 3-4 days  
**Priority**: MEDIUM

### 4.1 Content Scaffolding

Add CLI commands for creating typed content:

```bash
# Create new section with type
bengal new section docs --type doc

# Create new page with type
bengal new page tutorials/my-tutorial --type tutorial

# Create new blog post
bengal new post "My Blog Post" --type blog
```

**Implementation:**
```python
# bengal/cli.py

@cli.command()
@click.argument('section_name')
@click.option('--type', help='Content type for section')
def new_section(section_name, type):
    """Create a new section with _index.md"""
    # Create directory
    # Generate _index.md with type and cascade
    # Success message
```

**Files to Update:**
- `bengal/cli.py` - Add new commands
- `bengal/utils/scaffolding.py` - New module for templates

### 4.2 Template Scaffolding

Help theme developers create template families:

```bash
# Create new template family
bengal theme template tutorial

# Creates:
# themes/default/templates/tutorial/list.html
# themes/default/templates/tutorial/single.html
```

**Implementation:**
```python
@theme_cli.command()
@click.argument('type_name')
def template(type_name):
    """Create a new template family"""
    # Create directory
    # Generate list.html and single.html stubs
    # Add CSS file
```

### 4.3 Type Validation

Add validation during build:

```bash
bengal build --validate
```

**Checks:**
- Type has corresponding template family
- Cascaded types are valid
- Template files exist
- Type mappings are configured

**Output:**
```
⚠️  Warning: Page 'tutorials/intro.md' has type 'tutorial' 
             but no template 'tutorial/single.html' found.
             Falling back to section template.

💡 Create template: bengal theme template tutorial
```

### 4.4 Type Statistics

Show type usage in build output:

```bash
bengal build --stats

📊 Content Types:
   doc:           45 pages (using doc/single.html)
   tutorial:      12 pages (using tutorial/single.html)
   blog:          28 pages (using blog/single.html)
   api-reference: 156 pages (using api-reference/single.html)
   (default):     5 pages (using page.html)
```

### 4.5 Interactive Type Selector

When creating content interactively:

```bash
$ bengal new section tutorials

? What type of content? (Use arrow keys)
  ❯ doc - Reference documentation
    tutorial - Step-by-step guides
    blog - Blog posts
    api-reference - API documentation
    custom - Specify custom type
    (none) - No type, use defaults
```

## Phase 5: Testing & Validation ✅

**Goal**: Comprehensive test coverage for type system  
**Duration**: 2-3 days  
**Priority**: HIGH

### 5.1 Unit Tests

**File**: `tests/unit/rendering/test_template_selection.py`

**Test Cases:**
```python
class TestTypeBasedTemplateSelection:
    def test_type_maps_to_template_single()
    def test_type_maps_to_template_list()
    def test_type_cascade_from_parent()
    def test_template_override_beats_type()
    def test_type_fallback_to_section_name()
    def test_type_fallback_to_default()
    def test_unknown_type_fallback()
    def test_type_mappings_extensible()
    
class TestTypeMappings:
    def test_python_module_maps_to_api_reference()
    def test_cli_command_maps_to_cli_reference()
    def test_direct_type_names_work()
    def test_custom_type_passthrough()
    
class TestTypeCascade:
    def test_cascade_applies_to_children()
    def test_cascade_applies_to_grandchildren()
    def test_child_can_override_cascade()
    def test_multiple_cascade_levels()
```

### 5.2 Integration Tests

**File**: `tests/integration/test_type_system.py`

**Test Cases:**
```python
class TestTypeSystemIntegration:
    def test_doc_section_with_type()
    def test_tutorial_section_with_type()
    def test_blog_section_with_type()
    def test_mixed_types_in_site()
    def test_custom_index_standard_pages()
    def test_autodoc_types_work()
```

### 5.3 E2E Tests

**File**: `tests/e2e/test_type_scenarios.py`

Build complete sites and verify output:

```python
def test_documentation_site_with_types():
    """Build docs site using type: doc everywhere"""
    
def test_mixed_content_site():
    """Build site with docs, tutorials, blog, API"""
    
def test_type_cascade_site():
    """Build site using cascades, verify inheritance"""
```

### 5.4 Template Existence Tests

**File**: `tests/unit/themes/test_default_templates.py`

```python
def test_all_types_have_templates():
    """Verify all mapped types have template files"""
    types = ['doc', 'tutorial', 'blog', 'api-reference', 'cli-reference']
    for type_name in types:
        assert_template_exists(f"{type_name}/list.html")
        assert_template_exists(f"{type_name}/single.html")
```

### 5.5 Cascade Tests

**File**: `tests/unit/content/test_type_cascade.py`

```python
def test_cascade_inherits_type():
    """Child pages inherit parent's cascaded type"""
    
def test_cascade_does_not_affect_siblings():
    """Cascade only affects children, not siblings"""
    
def test_nested_cascade_override():
    """Deeper cascades can override parent cascades"""
```

## Phase 6: Examples & Showcase 🎪

**Goal**: Demonstrate the system with real examples  
**Duration**: 3-4 days  
**Priority**: MEDIUM

### 6.1 Enhanced Showcase Site

**Update**: `examples/showcase/`

**Add Sections:**
```
examples/showcase/content/
  docs/          (type: doc, cascade)
    _index.md    (custom template)
    guide-1.md   (inherits type)
    guide-2.md   (inherits type)
  
  tutorials/     (type: tutorial, cascade)
    _index.md
    beginner/
    advanced/
  
  blog/          (type: blog, cascade)
    _index.md
    2024/
      post-1.md
      post-2.md
  
  api/           (autodoc, type: python-module)
  
  home.md        (type: landing)
```

**Demonstrate:**
- All 5 content types
- Cascade patterns
- Custom index + standard pages
- Mixed types
- Template overrides

### 6.2 Starter Templates

Create starter projects:

**File**: `examples/starters/README.md`

**Starters to Create:**

1. **Documentation Site**
   ```
   starters/docs-site/
     content/docs/
     bengal.toml
     README.md
   ```
   - Pure documentation
   - Uses `type: doc` everywhere
   - Sidebar navigation

2. **Blog Site**
   ```
   starters/blog/
     content/blog/
     bengal.toml
   ```
   - Blog posts only
   - Author system
   - Tags and categories

3. **Product Site**
   ```
   starters/product-site/
     content/
       docs/
       tutorials/
       blog/
       api/
   ```
   - Marketing landing page
   - Documentation section
   - Tutorial section
   - Blog
   - API reference

4. **Personal Site**
   ```
   starters/personal/
     content/
       about.md
       blog/
       projects/
   ```
   - About page
   - Blog
   - Project showcase

### 6.3 Video Tutorial

Create screencast tutorial:

**Topics:**
1. Introduction to content types (5 min)
2. Creating a docs site with types (10 min)
3. Adding tutorials to your site (8 min)
4. Customizing templates (12 min)
5. Advanced: Creating template families (15 min)

**Total**: ~50 minutes, split into 5 videos

### 6.4 Interactive Tutorial

**File**: `examples/interactive-tutorial/`

Self-guided tutorial that teaches the type system:

```markdown
# Step 1: Your First Typed Content
Create a docs section...

# Step 2: Cascading Types
Learn how to apply types to multiple pages...

# Step 3: Custom Indexes
Create a custom landing page...

# Step 4: Mixed Types
Build a site with multiple content types...

# Step 5: Create Your Own Template Family
Advanced: Build a custom template...
```

## Phase 7: Polish & Release Prep 🚀

**Goal**: Production-ready release  
**Duration**: 2-3 days  
**Priority**: HIGH

### 7.1 Error Messages

Improve error messages for common issues:

**Current:**
```
Template not found: tutorial/single.html
```

**Improved:**
```
❌ Template Error

   Page: content/tutorials/intro.md
   Type: tutorial
   Looking for: tutorial/single.html
   
   The page has type 'tutorial' but the template 'tutorial/single.html' 
   doesn't exist in your theme.
   
   💡 Solutions:
   1. Create the template:
      bengal theme template tutorial
   
   2. Use a different type:
      Change 'type: tutorial' to 'type: doc'
   
   3. Remove the type to use defaults
   
   4. Set an explicit template:
      Add 'template: page.html' to frontmatter
```

### 7.2 Build Warnings

Add helpful warnings:

```
⚠️  10 pages have type 'tutorial' but you haven't created 
    'tutorial/single.html'. Using fallback template.
    
    💡 Create tutorial template: bengal theme template tutorial
```

### 7.3 Debug Mode

Add `--debug-templates` flag:

```bash
bengal build --debug-templates
```

**Output:**
```
📄 content/docs/intro.md
   ├─ type: doc
   ├─ template: (not set)
   ├─ section: docs
   ├─ Trying: doc/single.html ✓
   └─ Using: doc/single.html

📄 content/tutorials/getting-started.md
   ├─ type: tutorial
   ├─ template: (not set)
   ├─ section: tutorials
   ├─ Trying: tutorial/single.html ✗
   ├─ Trying: tutorial/page.html ✗
   ├─ Trying: tutorials/single.html ✓
   └─ Using: tutorials/single.html
```

### 7.4 Performance

Optimize template selection:

- [ ] Cache template existence checks
- [ ] Memoize type mappings
- [ ] Profile template lookup performance

### 7.5 Accessibility Audit

Review all template families:

- [ ] Semantic HTML
- [ ] ARIA labels
- [ ] Keyboard navigation
- [ ] Screen reader testing
- [ ] Color contrast

### 7.6 Mobile Optimization

Test all templates on mobile:

- [ ] Sidebar navigation works on mobile
- [ ] Touch targets are appropriate
- [ ] No horizontal scroll
- [ ] Fast loading
- [ ] Progressive enhancement

### 7.7 Release Checklist

Final checks before release:

- [ ] All template families complete
- [ ] Documentation complete
- [ ] Tests passing (>90% coverage)
- [ ] Examples showcase all features
- [ ] CLI commands work
- [ ] Error messages helpful
- [ ] Performance acceptable (<1s for 1000 pages)
- [ ] Changelog updated
- [ ] Migration guide ready
- [ ] Backward compatibility verified

## Implementation Timeline

### Sprint 1 (Week 1): Templates
- Days 1-2: Doc templates
- Days 3-4: Tutorial templates
- Day 5: Blog templates

### Sprint 2 (Week 2): Documentation & Tooling
- Days 1-3: User & developer docs
- Days 4-5: CLI scaffolding

### Sprint 3 (Week 3): Testing & Examples
- Days 1-2: Test suite
- Days 3-4: Showcase & starters
- Day 5: Polish & bug fixes

### Sprint 4 (Week 4): Release
- Days 1-2: Performance & accessibility
- Day 3: Final testing
- Days 4-5: Release prep & launch

## Success Criteria

### User Success
- [ ] New user can create typed content without reading docs (intuitive)
- [ ] Docs show clear examples of all patterns
- [ ] Common tasks have < 3 steps
- [ ] Error messages guide users to solution

### Developer Success
- [ ] Theme developer can create template family in < 30 min
- [ ] Template conventions are clear
- [ ] Extension points are documented
- [ ] Code is maintainable

### Technical Success
- [ ] Test coverage > 90%
- [ ] No performance regression
- [ ] Backward compatible
- [ ] Extensible for future types

### Adoption Success
- [ ] At least 3 types in default theme
- [ ] Showcase demonstrates all features
- [ ] Starter templates available
- [ ] Video tutorial available

## Future Enhancements (Post v1.0)

Ideas for future iterations:

1. **Dynamic Type Registration**
   ```python
   # bengal.toml
   [types.recipe]
   templates = ["recipe/list.html", "recipe/single.html"]
   icon = "🍳"
   ```

2. **Type-Specific Validation**
   ```python
   # Validate tutorial must have difficulty
   [types.tutorial]
   required_fields = ["difficulty", "time_estimate"]
   ```

3. **Type Inheritance**
   ```yaml
   type: advanced-tutorial
   extends: tutorial  # Inherits tutorial behavior
   ```

4. **Visual Type Editor**
   - GUI for managing types
   - Template preview
   - Metadata editor

5. **Type Analytics**
   - Track which types are used
   - Template rendering time by type
   - Popular type combinations

## Notes

- Maintain backward compatibility throughout
- Document every breaking change (none expected)
- Keep it simple - don't over-engineer
- User experience > technical purity
- Convention > configuration
- Semantic > implementation details

## Questions to Resolve

1. Should we support custom type mappings in config?
2. Should types be registered or just convention-based?
3. Do we need a type validation schema?
4. Should we have a type plugin system?
5. How do we handle type conflicts?

## Dependencies

- Phase 2 blocks Phase 6 (need templates for showcase)
- Phase 3 can happen in parallel with Phase 2
- Phase 4 can happen in parallel with Phase 2-3
- Phase 5 needs Phase 2 complete (test templates)
- Phase 7 needs everything complete

## Resources Needed

- Design review for templates (UX/UI)
- Accessibility audit
- Documentation review
- Beta testers for showcase sites

## Risk Assessment

**Low Risk:**
- Core implementation already done
- Backward compatible
- Incremental rollout

**Medium Risk:**
- Template design quality (need design review)
- Documentation completeness (need tech writer?)
- Learning curve for users (need good examples)

**Mitigation:**
- Get early feedback on templates
- Extensive examples and tutorials
- Beta release before v1.0
- Iterate based on user feedback

