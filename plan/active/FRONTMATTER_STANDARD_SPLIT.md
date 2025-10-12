# Split Frontmatter Standard into a modular docs section

- Source: `examples/showcase/content/docs/frontmatter-standard.md`
- Goal: Improve readability and navigation by splitting into a directory with child pages

## New Structure
- `examples/showcase/content/docs/frontmatter-standard/_index.md` (overview, list template)
- `examples/showcase/content/docs/frontmatter-standard/core-fields.md` (Core + Authorship)
- `examples/showcase/content/docs/frontmatter-standard/layout-structure.md` (Layout & Taxonomy)
- `examples/showcase/content/docs/frontmatter-standard/discoverability.md` (Search + Visibility)
- `examples/showcase/content/docs/frontmatter-standard/content-context.md` (Tutorial/Guide, API/CLI, Relationships)
- `examples/showcase/content/docs/frontmatter-standard/examples-reference.md` (Complete examples, optional fields, reference, validation, resources)

## Links to Update
- `examples/showcase/content/docs/_index.md` → link to `frontmatter-standard/`
- `examples/showcase/content/docs/kitchen-sink.md` → link to `frontmatter-standard/`
- `examples/showcase/content/docs/writing/frontmatter-guide.md` → link to `../frontmatter-standard/`
- Already correct: `examples/showcase/content/docs/output-formats.md` uses `/docs/frontmatter-standard/`

## Notes
- Keep original metadata (title, description, weight, tags) in `_index.md`
- Enable child listing with `template: doc/list.html` and `show_children: true`
- After migration, delete the legacy file
