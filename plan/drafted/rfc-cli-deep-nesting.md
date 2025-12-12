## RFC: Support Deeply Nested CLI Navigation

**Priority**: P3 (Low)  

### Problem
- CLI autodoc currently flattens command-group sections: every group is added directly under the root `cli` section even if its qualified name implies deeper nesting. Evidence: `_create_cli_sections` always calls `cli_section.add_subsection(group_section)` regardless of depth. `group_parts` are used only to build the URL/title, not the hierarchy. (`bengal/autodoc/virtual_orchestrator.py:528-584`)
- Users with multi-level CLI hierarchies (e.g., `bengal.utils.graph.analyze`) cannot browse nested structure; sidebar renders a long flat list, hurting discoverability and making keyboard navigation noisy.

### Goals
- Preserve true CLI command-group hierarchy in autodoc navigation.
- Keep URLs stable (`/cli/<qualified>/`) and avoid breaking existing links.
- Avoid duplicate pages or alias bloat (alias dedupe already handled in CLI extractor).

### Non-Goals
- Changing CLI command definitions or runtime behavior.
- Altering API/OpenAPI navigation (already hierarchical).
- Redesigning docs-nav template.

### Option A — Build real section tree (recommended)
- Create missing parent sections recursively for each command-group from its qualified name parts.
- Attach group sections to their actual parent section instead of always to `cli_section`.
- Keep existing relative URLs (`cli/<qualified>/`) and titles.
- Ensure commands resolve their parent section via `_find_parent_section` (already uses qualified path, will work once sections exist).

Pros:
- Accurate hierarchy, better UX for large CLIs.
- Minimal surface area; contained to `_create_cli_sections`.
- No URL changes; low migration risk.

Cons:
- Slightly more section objects; negligible overhead.

Implementation sketch
1) When iterating command_groups, walk `group_parts` and create/find each ancestor section under the correct parent (starting from `cli_section`).
2) Reuse `join_url_paths` to build each ancestor’s relative_url; store in `sections` dict keyed by `cli/<path>`.
3) Add the final group_section as a child of its immediate parent (not always `cli_section`).
4) Keep metadata/type the same (`cli-reference`).
5) Add tests to validate nested groups render hierarchical sections and nav.

### Option B — Render flat but with grouped headings
- Keep flat sections but add display-only grouping markers in templates.
- Pros: minimal code change.
- Cons: still flat nav; poor keyboard navigation; doesn’t scale.

### Recommendation
- Adopt Option A (real section tree). It matches qualified names, improves nav for deep CLIs, and preserves URLs.

### Rollout & Testing
- Unit: add a synthetic CLI with nested groups (`alpha.beta.gamma`) and assert `_create_cli_sections` builds parent sections with correct relative_url and parent/child links.
- Integration: run autodoc to generate pages and assert nav tree includes nested sections.
- Manual: build docs for current CLI to confirm no regressions.

### Risks & Mitigations
- Risk: Missing parent sections could cause `_find_parent_section` fallback; mitigate by creating all ancestors.
- Risk: Performance on very large CLIs; mitigated by O(n) section creation with caching in `sections` dict.
