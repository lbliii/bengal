Docs "Edit this page" links now open the correct GitHub edit URL instead of a broken `/None` path.

The default theme builds edit links from `repo_url` and site path params via a new `page_github_edit_url()` helper, and hides the control when no URL can be resolved. Shard parse workers now reuse the site's discovered section tree so page-dependent directives like child-cards match in-process parses.
