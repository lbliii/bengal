---
title: Directive Options (Registry)
nav_title: Registry Options
description: Auto-generated directive option tables from create_default_registry()
weight: 90
tags:
- reference
- directives
---

# Directive Options (Registry)

Auto-generated from `create_default_registry()`. Regenerate with:

```bash
python scripts/update_directive_options_snapshot.py
```

For usage examples, see the category pages under [[docs/reference/directives|Directives Reference]].

## `admonition` {#admonition}

**Directives:** `{caution}`, `{danger}`, `{error}`, `{example}`, `{important}`, `{info}`, `{note}`, `{seealso}`, `{success}`, `{tip}`, `{warning}`

**Options class:** `AdmonitionOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:collapsible:` | false | — |
| `:open:` | true | — |

## `asciinema_embed` {#asciinema_embed}

**Directives:** `{asciinema}`

**Options class:** `AsciinemaOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:cols:` | 80 | — |
| `:rows:` | 24 | — |
| `:speed:` | 1.0 | — |
| `:autoplay:` | false | — |
| `:loop:` | false | — |
| `:theme:` | asciinema | — |
| `:poster:` | npt:0:0 | — |
| `:idle_time_limit:` | none | — |
| `:start_at:` | "" | — |
| `:css_class:` | "" | — |
| `:recording_id:` | "" | — |
| `:is_local_file:` | false | — |
| `:error:` | "" | — |

## `audio_embed` {#audio_embed}

**Directives:** `{audio}`

**Options class:** `AudioOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:controls:` | true | — |
| `:autoplay:` | false | — |
| `:loop:` | false | — |
| `:muted:` | false | — |
| `:preload:` | metadata | — |
| `:css_class:` | "" | — |

## `badge` {#badge}

**Directives:** `{badge}`, `{bdg}`

**Options class:** `BadgeOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:css_class:` | badge badge-secondary | — |
| `:label:` | "" | — |

## `breadcrumbs` {#breadcrumbs}

**Directives:** `{breadcrumbs}`

**Options class:** `BreadcrumbsOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:separator:` | › | — |
| `:show_home:` | true | — |
| `:home_text:` | Home | — |
| `:home_url:` | / | — |

## `build` {#build}

**Directives:** `{build}`

**Options class:** `BuildOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:json:` | false | — |
| `:inline:` | false | — |
| `:align:` | "" | — |
| `:css_class:` | "" | — |
| `:alt:` | Built in badge | — |
| `:dir_name:` | bengal | — |

## `button` {#button}

**Directives:** `{button}`

**Options class:** `ButtonOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:color:` | primary | — |
| `:style:` | default | — |
| `:size:` | medium | — |
| `:icon:` | "" | — |
| `:target:` | "" | — |
| `:url:` | # | — |
| `:label:` | Button | — |

## `card` {#card}

**Directives:** `{card}`

**Options class:** `CardOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:icon:` | "" | — |
| `:link:` | "" | — |
| `:description:` | "" | — |
| `:badge:` | "" | — |
| `:color:` | "" | — |
| `:image:` | "" | — |
| `:footer:` | "" | — |
| `:pull:` | "" | — |
| `:layout:` | "" | — |

## `cards_grid` {#cards_grid}

**Directives:** `{cards}`

**Options class:** `CardsOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:columns:` | auto | — |
| `:gap:` | medium | — |
| `:style:` | default | — |
| `:variant:` | navigation | — |
| `:layout:` | default | — |

## `changed` {#changed}

**Directives:** `{changed}`, `{versionchanged}`

**Options class:** `ChangedOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:css_class:` | version-changed | — |
| `:version:` | "" | — |
| `:has_content:` | false | — |

## `checklist` {#checklist}

**Directives:** `{checklist}`

**Options class:** `ChecklistOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:style:` | default | — |
| `:show-progress:` | false | — |
| `:compact:` | false | — |
| `:class:` | "" | — |

## `child_cards` {#child_cards}

**Directives:** `{child-cards}`

**Options class:** `ChildCardsOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:columns:` | auto | — |
| `:gap:` | medium | — |
| `:include:` | all | — |
| `:fields:` | title, description | — |
| `:layout:` | default | — |
| `:style:` | default | — |

## `code_tabs` {#code_tabs}

**Directives:** `{code-tabs}`, `{code_tabs}`

**Options class:** `CodeTabsOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:sync:` | language | — |
| `:linenos:` | none | — |
| `:tabs:` | none | — |

## `codepen_embed` {#codepen_embed}

**Directives:** `{codepen}`

**Options class:** `CodePenOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:default-tab:` | result | — |
| `:height:` | 300 | — |
| `:theme:` | dark | — |
| `:editable:` | false | — |
| `:preview:` | true | — |
| `:class:` | "" | — |
| `:username:` | "" | — |
| `:pen_id:` | "" | — |
| `:error:` | "" | — |

## `codesandbox_embed` {#codesandbox_embed}

**Directives:** `{codesandbox}`

**Options class:** `CodeSandboxOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:module:` | "" | — |
| `:view:` | split | — |
| `:height:` | 500 | — |
| `:fontsize:` | 14 | — |
| `:hidenavigation:` | false | — |
| `:theme:` | dark | — |
| `:css_class:` | "" | — |
| `:sandbox_id:` | "" | — |
| `:error:` | "" | — |

## `container` {#container}

**Directives:** `{container}`, `{div}`

**Options class:** `ContainerOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |

## `data_table` {#data_table}

**Directives:** `{data-table}`

**Options class:** `DataTableOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:search:` | true | — |
| `:filter:` | true | — |
| `:sort:` | true | — |
| `:pagination:` | 50 | — |
| `:height:` | auto | — |
| `:columns:` | "" | — |
| `:file_path:` | "" | — |
| `:table_id:` | "" | — |
| `:visible_columns:` | none | — |
| `:error:` | "" | — |
| `:table_columns:` | — | — |
| `:table_data:` | — | — |

## `deprecated` {#deprecated}

**Directives:** `{deprecated}`, `{versionremoved}`

**Options class:** `DeprecatedOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:css_class:` | version-deprecated | — |
| `:version:` | "" | — |
| `:has_content:` | false | — |

## `dropdown` {#dropdown}

**Directives:** `{details}`, `{dropdown}`

**Options class:** `DropdownOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:open:` | false | — |
| `:icon:` | none | — |
| `:badge:` | none | — |
| `:color:` | none | — |
| `:description:` | none | — |

## `example_label` {#example_label}

**Directives:** `{example-label}`

**Options class:** `ExampleLabelOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:css_class:` | "" | — |
| `:prefix:` | Example | — |
| `:no_prefix:` | false | — |

## `excerpt_break` {#excerpt_break}

**Directives:** `{excerpt-break}`

**Options class:** `DirectiveOptions`

_No typed options._

## `figure` {#figure}

**Directives:** `{figure}`

**Options class:** `FigureOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:alt:` | "" | — |
| `:caption:` | "" | — |
| `:width:` | "" | — |
| `:height:` | "" | — |
| `:align:` | "" | — |
| `:link:` | "" | — |
| `:target:` | _self | — |
| `:loading:` | lazy | — |
| `:class:` | "" | — |

## `gallery` {#gallery}

**Directives:** `{gallery}`

**Options class:** `GalleryOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:columns:` | 3 | — |
| `:lightbox:` | true | — |
| `:gap:` | 1rem | — |
| `:aspect_ratio:` | 4/3 | — |
| `:css_class:` | "" | — |

## `gist_embed` {#gist_embed}

**Directives:** `{gist}`

**Options class:** `GistOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:file:` | "" | — |
| `:css_class:` | "" | — |
| `:gist_ref:` | "" | — |
| `:error:` | "" | — |

## `glossary` {#glossary}

**Directives:** `{glossary}`

**Options class:** `GlossaryOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:tags:` | "" | — |
| `:sorted:` | false | — |
| `:show_tags:` | false | — |
| `:collapsed:` | false | — |
| `:limit:` | 0 | — |
| `:source:` | data/glossary.yaml | — |

## `icon` {#icon}

**Directives:** `{icon}`, `{svg-icon}`

**Options class:** `IconOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:size:` | 24 | — |
| `:class:` | "" | — |
| `:aria-label:` | "" | — |
| `:icon_name:` | "" | — |
| `:error:` | "" | — |

## `include` {#include}

**Directives:** `{include}`

**Options class:** `IncludeOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:file:` | "" | — |
| `:start_line:` | none | — |
| `:end_line:` | none | — |
| `:file_path:` | "" | — |
| `:error:` | "" | — |

## `list_table` {#list_table}

**Directives:** `{list-table}`

**Options class:** `ListTableOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:header-rows:` | 0 | — |
| `:widths:` | "" | — |
| `:class:` | "" | — |

## `literalinclude` {#literalinclude}

**Directives:** `{literalinclude}`

**Options class:** `LiteralIncludeOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:file:` | "" | — |
| `:language:` | "" | — |
| `:start_line:` | none | — |
| `:end_line:` | none | — |
| `:emphasize_lines:` | "" | — |
| `:linenos:` | false | — |
| `:caption:` | "" | — |
| `:file_path:` | "" | — |
| `:code:` | "" | — |
| `:error:` | "" | — |

## `marimo_cell` {#marimo_cell}

**Directives:** `{marimo}`

**Options class:** `MarimoOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:show-code:` | true | — |
| `:cache:` | true | — |
| `:label:` | "" | — |
| `:code:` | "" | — |
| `:cell_id:` | 0 | — |
| `:error:` | "" | — |

## `prev_next` {#prev_next}

**Directives:** `{prev-next}`

**Options class:** `PrevNextOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:show_title:` | true | — |
| `:show_section:` | false | — |

## `related` {#related}

**Directives:** `{related}`

**Options class:** `RelatedOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:limit:` | 5 | — |
| `:section_title:` | Related Articles | — |
| `:show_tags:` | false | — |

## `rubric` {#rubric}

**Directives:** `{rubric}`

**Options class:** `RubricOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:css_class:` | "" | — |

## `self_hosted_video` {#self_hosted_video}

**Directives:** `{video}`

**Options class:** `SelfHostedVideoOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:poster:` | "" | — |
| `:controls:` | true | — |
| `:autoplay:` | false | — |
| `:muted:` | false | — |
| `:loop:` | false | — |
| `:preload:` | metadata | — |
| `:width:` | 100% | — |
| `:aspect:` | 16/9 | — |
| `:css_class:` | "" | — |
| `:video_path:` | "" | — |
| `:mime_type:` | "" | — |
| `:error:` | "" | — |

## `siblings` {#siblings}

**Directives:** `{siblings}`

**Options class:** `SiblingsOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:limit:` | 0 | — |
| `:exclude_current:` | true | — |
| `:show_description:` | false | — |

## `since` {#since}

**Directives:** `{since}`, `{versionadded}`

**Options class:** `SinceOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:css_class:` | version-since | — |
| `:version:` | "" | — |
| `:has_content:` | false | — |

## `soundcloud_embed` {#soundcloud_embed}

**Directives:** `{soundcloud}`

**Options class:** `SoundCloudOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:type:` | track | — |
| `:height:` | 0 | — |
| `:color:` | ff5500 | — |
| `:autoplay:` | false | — |
| `:hide_related:` | false | — |
| `:show_comments:` | true | — |
| `:show_user:` | true | — |
| `:show_reposts:` | false | — |
| `:visual:` | false | — |
| `:css_class:` | "" | — |
| `:url_path:` | "" | — |
| `:error:` | "" | — |

## `spotify_embed` {#spotify_embed}

**Directives:** `{spotify}`

**Options class:** `SpotifyOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:type:` | track | — |
| `:height:` | 0 | — |
| `:theme:` | 0 | — |
| `:css_class:` | "" | — |
| `:spotify_id:` | "" | — |
| `:error:` | "" | — |

## `stackblitz_embed` {#stackblitz_embed}

**Directives:** `{stackblitz}`

**Options class:** `StackBlitzOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:file:` | "" | — |
| `:view:` | both | — |
| `:height:` | 500 | — |
| `:hidenavigation:` | false | — |
| `:hidedevtools:` | false | — |
| `:css_class:` | "" | — |
| `:project_id:` | "" | — |
| `:error:` | "" | — |

## `step` {#step}

**Directives:** `{step}`

**Options class:** `StepOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:description:` | none | — |
| `:optional:` | false | — |
| `:duration:` | none | — |
| `:step_number:` | none | — |
| `:heading_level:` | none | — |

## `steps` {#steps}

**Directives:** `{steps}`

**Options class:** `StepsOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:style:` | none | — |
| `:start:` | 1 | — |

## `tab_item` {#tab_item}

**Directives:** `{tab}`, `{tab-item}`

**Options class:** `TabItemOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:selected:` | false | — |
| `:icon:` | none | — |
| `:badge:` | none | — |
| `:disabled:` | false | — |
| `:sync:` | none | — |

## `tab_set` {#tab_set}

**Directives:** `{tab-set}`, `{tabs}`

**Options class:** `TabSetOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | none | — |
| `:name:` | none | — |
| `:id:` | none | — |
| `:sync:` | none | — |
| `:mode:` | none | — |

## `target` {#target}

**Directives:** `{anchor}`, `{target}`

**Options class:** `TargetOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:id:` | none | — |
| `:error:` | none | — |

## `tiktok_video` {#tiktok_video}

**Directives:** `{tiktok}`

**Options class:** `TikTokOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:width:` | "" | — |
| `:aspect:` | 9/16 | — |
| `:css_class:` | "" | — |
| `:autoplay:` | false | — |
| `:loop:` | false | — |
| `:muted:` | false | — |
| `:video_id:` | "" | — |
| `:embed_url:` | "" | — |
| `:error:` | "" | — |

## `vimeo_video` {#vimeo_video}

**Directives:** `{vimeo}`

**Options class:** `VimeoOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:width:` | "" | — |
| `:aspect:` | 16/9 | — |
| `:css_class:` | "" | — |
| `:autoplay:` | false | — |
| `:loop:` | false | — |
| `:muted:` | false | — |
| `:color:` | "" | — |
| `:autopause:` | true | — |
| `:dnt:` | true | — |
| `:background:` | false | — |
| `:video_id:` | "" | — |
| `:embed_url:` | "" | — |
| `:error:` | "" | — |

## `youtube_video` {#youtube_video}

**Directives:** `{youtube}`

**Options class:** `YouTubeOptions`

| Option | Default | Description |
|--------|---------|-------------|
| `:title:` | "" | — |
| `:width:` | "" | — |
| `:aspect:` | 16/9 | — |
| `:class:` | "" | — |
| `:autoplay:` | false | — |
| `:loop:` | false | — |
| `:muted:` | false | — |
| `:start:` | 0 | — |
| `:end:` | none | — |
| `:privacy:` | true | — |
| `:controls:` | true | — |
| `:video_id:` | "" | — |
| `:embed_url:` | "" | — |
| `:error:` | "" | — |
