# BaseURL: Template Context Wrapper (Implemented)

**Status**: Implemented  
**Completed**: 2025-11-26  
**Release**: 0.1.4

---

## Summary

Implemented `TemplatePageWrapper` to auto-apply baseurl in templates, making `page.url` always include baseurl.

## What Was Implemented

### TemplatePageWrapper

`bengal/rendering/template_context.py`:
- Wraps Page objects in template context
- `page.url` automatically includes baseurl
- `page.relative_url` available for comparisons
- Works with all baseurl formats (path, absolute, file://, s3://)

### TemplateSectionWrapper

- Same pattern for Section objects
- Wrapped pages/subsections automatically

### TemplateSiteWrapper

- Wraps site.pages and site.regular_pages

### Template Changes

- All templates now use `page.url` consistently
- No more confusion between `url` vs `permalink`
- Graph scripts, navigation, links all use correct URLs

## Related Commits

- `6afaccf` - themes: use page.url instead of page.relative_url for graph-contextual
- `eb65fae` - analysis: fix doubled baseurl in graph_visualizer
- `1068fff` - orchestration: use relative_url for menu items to avoid double baseurl
- `9121e5d` - tests: add regression tests for baseurl handling

## Files Changed

- `bengal/rendering/template_context.py` (new)
- `bengal/core/page/metadata.py` (updated - permalink delegates to url)
- Various templates updated to use `page.url`

## Related Plans

- Original: `plan/active/rfc-baseurl-pattern-improvement.md` (deleted)

