Editor code blocks now show IDE-style window chrome with traffic lights, an active file tab, and toolbar actions.

Titled fences and `frame=editor` blocks fold the filename into the tab bar via `data-title`, dedupe the legacy title strip, and fall back to the language name when no title is set.
