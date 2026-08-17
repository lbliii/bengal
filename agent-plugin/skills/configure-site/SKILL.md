---
name: configure-site
description: Edit Bengal site configuration (bengal.toml or config/) using keys that exist in the schema and configuration docs. Use when changing title, baseurl, theme, build output, features, output formats, or Content Signals.
---

# Configure a Bengal Site

Change **existing** config keys only. Source of truth for authors:

- [/docs/ship/configuration/](https://lbliii.github.io/bengal/docs/ship/configuration/)
- [/docs/ship/configuration/reference/](https://lbliii.github.io/bengal/docs/ship/configuration/reference/)

If a key is not in those docs, write **TODO** — never invent a key. Confirm
with `bengal config show` after editing.

## Where config lives

Bengal loads **either** `config/` (preferred) **or** `bengal.toml`. If `config/`
exists, `bengal.toml` is ignored.

```toml
# bengal.toml — small sites
[site]
title = "My Site"
baseurl = "https://example.com"
description = "Site description"
author = "Author Name"
language = "en"

[build]
output_dir = "public"
content_dir = "content"

[theme]
name = "default"
```

Directory layout (from the configuration guide):

```text
config/
├── _default/
│   ├── site.yaml
│   ├── build.yaml
│   └── theme.yaml
└── environments/
    ├── local.yaml
    └── production.yaml
```

Create a directory or file config (from `bengal config init --help`):

```bash
bengal config init --help
bengal config init --init-type directory --template docs
```

`--init-type`: `directory` or `file`. `--template`: `docs`, `blog`, `minimal`.

## Inspect before editing

```bash
bengal config show
bengal config show --section site
bengal config show --environment production --origin
bengal config doctor
```

`--section` examples from help: `site`, `build`. `--environment` examples:
`local`, `preview`, `production`.

## Keys you may set (documented)

Claim these tables only as they appear in the configuration reference. Do not
copy stale defaults from memory — `bengal config show` prints the merged values.

**`[site]`:** `title`, `baseurl`, `description`, `author`, `language`

**`[build]`:** `output_dir`, `content_dir`, `assets_dir`, `templates_dir`,
`parallel`, `incremental`, `pretty_urls`, `minify_html`, `strict_mode`,
`validate_build`, `validate_templates`, `validate_links`

**`[theme]`:** `name`, `default_appearance` (`light`, `dark`, `system`)

**`[features]`:** `rss`, `sitemap`, `search`, `json`, `llm_txt`

**`[content]`:** `default_type`, `toc_depth`, `sort_pages_by`, `sort_order`

Environment override example (docs):

```bash
bengal build --environment production
```

```yaml
# config/environments/production.yaml
site:
  baseurl: "https://example.com"

build:
  minify_html: true
  strict_mode: true
```

CLI flags override file config. See `bengal build --help` and
`bengal serve --help` for flags (`--config`, `--environment`, `--profile`,
`--strict`, `--drafts`). `--profile` values on build help: `writer`,
`theme-dev`, `dev`.

## Output formats and Content Signals

Do not re-document every format here. Read:

- [/docs/ship/ai-native-output/](https://lbliii.github.io/bengal/docs/ship/ai-native-output/)
- [/docs/ship/output-formats/](https://lbliii.github.io/bengal/docs/ship/output-formats/)

Documented tables:

```toml
[output_formats]
enabled = true
per_page = ["json", "llm_txt", "markdown"]
site_wide = ["index_json"]

[content_signals]
search = true
ai_input = true
ai_train = false
```

Page/section overrides use frontmatter `visibility` (see the AI-native docs).
`bengal build` writes these artifacts when the formats are enabled.

**TODO:** Any output format name or signal not listed in those docs.

## Apply and verify

```bash
bengal config doctor
bengal build
bengal serve
```

## Checklist

- [ ] Edited `config/` **or** `bengal.toml`, not both as competing sources
- [ ] Every key appears in the configuration reference
- [ ] `bengal config show` reflects the change
- [ ] `bengal config doctor` and `bengal build` succeed
