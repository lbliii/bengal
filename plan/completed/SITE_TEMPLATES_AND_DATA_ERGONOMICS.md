# Site Templates & Data Ergonomics Implementation

**Date:** October 12, 2025  
**Status:** ✅ Templates Complete, 📋 Data Feature Planned

## Summary

Implemented comprehensive site templates for `bengal new site` command and identified data ergonomics improvements inspired by Hugo.

## What We Implemented

### 1. Site Templates (Complete ✅)

Created 6 site templates with sample content:

- **Blog** - Posts with tags/categories
- **Docs** - Hierarchical documentation
- **Portfolio** - Projects showcase
- **Resume** - Data-driven CV (YAML frontmatter)
- **Landing** - Marketing page
- **Default** - Basic structure

**Usage:**
```bash
bengal new site myblog --template blog
bengal new site mydocs --template docs
bengal new site myresume --template resume
```

**Files Created:**
- `bengal/cli/site_templates.py` - All template definitions
- `bengal/themes/default/templates/resume/single.html` - Resume template
- Updated: `bengal/cli/commands/new.py` - Added --template option

### 2. Resume Template - Data-Driven Approach

The resume template uses structured YAML data in frontmatter:

```yaml
---
title: Resume
section: resume
name: Your Full Name
contact:
  email: your@email.com
experience:
  - title: Senior Engineer
    company: Tech Co
    highlights: [...]
skills:
  - category: Programming
    items: [Python, JS]  # Note: Used bracket notation to avoid .items() collision
---
```

**Key Learning:** Jinja2's dot notation (`obj.items`) accesses dict methods, not fields named "items". Solution: Use bracket notation `obj['items']`.

## What We Discovered

### Ergonomic Issues Found

1. **Jinja2 Gotcha** - Field names like `items`, `keys`, `values` conflict with dict methods
2. **Error Visibility** - Need `--debug` flag to see template line numbers
3. **Data in Frontmatter** - Large datasets bloat frontmatter (200+ lines for resume)

### Lessons from Hugo

Researched [Hugo's `.Site.Data`](https://gohugo.io/methods/site/data/) and [`transform.Unmarshal`](https://gohugo.io/functions/transform/unmarshal/):

**Hugo's Approach:**
```go
// data/resume.yaml automatically loaded
{{ range .Site.Data.resume.experience }}
  {{ .title }}
{{ end }}
```

**Bengal's Current Approach:**
```jinja2
{% set resume = get_data('data/resume.yaml') %}
{% for job in resume.experience %}
  {{ job.title }}
{% endfor %}
```

## Recommendations

### High Priority 🔥

**1. Implement `site.data` Feature**
- Auto-load `data/` directory on site init
- Make accessible as `site.data.filename`
- Cache data (don't reload per page)
- ~4 hours implementation

**Benefits:**
- Cleaner templates: `site.data.resume` vs `get_data('data/resume.yaml')`
- Better performance (cached)
- Familiar pattern from Hugo
- Separates data from content

**2. Improve Error Visibility**
- Show template line numbers by default (not just with `--debug`)
- Make template errors more prominent in output
- ~1 hour implementation

### Medium Priority 💡

**3. Add `field()` Helper Function**
```jinja2
{# Avoid dict method collisions #}
{% for skill in skill_group | field('items') %}
```

**4. Better Documentation**
- Document Jinja2 gotchas prominently
- Add "Data-Driven Templates" guide
- Show resume template as example

### Long Term 📋

**5. Optional Schema Validation**
- Use JSON Schema or Pydantic
- Validate structured frontmatter
- Catch typos at build time

**6. Template Linting**
- `bengal lint` command
- Warn about common gotchas
- Static analysis of templates

## Files Created/Modified

### New Files
- `bengal/cli/site_templates.py` (830 lines)
- `bengal/themes/default/templates/resume/single.html` (758 lines)
- `plan/DATA_ERGONOMICS_ANALYSIS.md` (analysis document)
- `plan/SITE_DATA_FEATURE.md` (implementation plan)
- `plan/completed/SITE_TEMPLATES_IMPLEMENTATION.md` (original summary)

### Modified Files
- `bengal/cli/commands/new.py` (added --template option)
- `bengal/themes/default/templates/resume/single.html` (fixed .items gotcha)

## Testing

All templates verified:
- ✅ Blog template - 4 pages (index, about, 2 posts)
- ✅ Docs template - 6 pages (hierarchical structure)
- ✅ Portfolio template - 6 pages (projects showcase)
- ✅ Resume template - 1 page (data-driven)
- ✅ Landing template - 3 pages (marketing + legal)
- ✅ Default template - 1 page (basic)

All templates build successfully and generate valid output.

## User Experience

**Before:**
```bash
$ bengal new site mysite
# Gets basic site with single index.md
# User has to create structure from scratch
```

**After:**
```bash
$ bengal new site myblog --template blog
# Gets complete blog structure with:
# - content/posts/ directory
# - content/drafts/ directory
# - Sample posts with tags/categories
# - About page
# - Ready to customize and extend
```

**For Resume:**
```bash
$ bengal new site myresume --template resume
# Gets data-driven resume with:
# - Structured YAML for all sections
# - Professional template
# - Print-friendly CSS
# - Just edit the YAML data
```

## Next Steps

### Immediate
1. ✅ Merge site templates feature
2. Document templates in user guide
3. Add to CHANGELOG

### Short Term (Next Sprint)
1. Implement `site.data` feature
2. Add DotDict wrapper
3. Update resume template to use `data/resume.yaml`
4. Improve error visibility

### Medium Term
1. Add `field()` helper function
2. Create comprehensive data-driven templates guide
3. Add more example templates (team page, product catalog)

## Impact

**Onboarding Experience:** Significantly improved
- New users get working examples immediately
- Templates demonstrate best practices
- Reduces time to first working site

**Data-Driven Development:** Foundation laid
- Resume template shows the pattern
- Identified areas for improvement
- Clear path forward with `site.data`

**Community Growth:** Enables
- Template sharing
- Best practice examples
- Showcase sites

## Conclusion

The site templates feature is complete and ready to use. The resume template implementation revealed ergonomic opportunities (especially around data handling) that are documented and planned.

**Key Takeaways:**
1. Data-driven templates are powerful but need better ergonomics
2. Hugo's `.Site.Data` pattern is worth adopting
3. Jinja2 gotchas need clear documentation
4. Template error messages could be more visible

**Recommendation:** Proceed with `site.data` implementation as high-priority follow-up. The 4-hour investment will significantly improve the experience for data-driven templates like resumes, team pages, and product catalogs.
