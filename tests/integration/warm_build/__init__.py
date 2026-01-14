"""
Warm build (incremental) integration tests.

This test suite ensures Bengal's incremental build system correctly
detects and handles changes to:
- Navigation/menu configuration
- Taxonomy (tags/categories) membership
- Data files (data/*.yaml)
- Template inheritance chains
- Output formats (RSS, sitemap, llm-full.txt)
- Edge cases and cross-feature interactions

See: plan/rfc-warm-build-test-expansion.md for rationale and design.
"""
