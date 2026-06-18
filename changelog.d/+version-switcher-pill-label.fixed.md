The sidebar version switcher pill now shows the correct version label on section landing pages (`_index.md`). It previously read the lazy `current_version` context and fell back to "Latest" even when viewing an older docs version; it now resolves the label from `page.version` and the versions list, matching the dropdown selection.

Section snapshots now compute nav root the same way live sections do (`nav_root` boundaries and the `_versions/` folder stop), so parallel shard renders scope the docs sidebar to the correct parent header instead of the site-wide root.
