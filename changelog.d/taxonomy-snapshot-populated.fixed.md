Fixed a latent bug where the internal taxonomy snapshot (`SiteSnapshot.taxonomy`)
was always empty because `_snapshot_taxonomies` mis-iterated the `{name, slug,
pages}` term dict, leaving the renderer's lock-free tag-page fast path dead. Tag
pages now resolve through the corrected snapshot with byte-identical output, and
per-language tag pages under i18n `share_taxonomies = false` correctly list only
their own language's posts.
