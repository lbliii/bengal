---
title: Template Functions Reference (Generated)
nav_title: Functions Index
description: Auto-generated index of all template filters and functions
weight: 45
---

# Template Functions Reference

This page is **auto-generated** from `register_all()`.
Do not edit manually. Run `poe gen-docs` or `poe build` to regenerate.

## Filters

Use with the pipe operator: `{{ value | filter_name }}` or `{{ value |> filter_name }}`

| Filter | Implementation |
|--------|----------------|
| `absolute_url` | `absolute_url_with_site` |
| `archive_years` | `archive_years` |
| `author_view` | `author_view_filter` |
| `authors` | `authors_filter` |
| `avatar_url` | `avatar_url_filter` |
| `base64_decode` | `base64_decode` |
| `base64_encode` | `base64_encode` |
| `camelize` | `camelize` |
| `card_excerpt` | `card_excerpt` |
| `card_excerpt_html` | `card_excerpt_html` |
| `ceil` | `ceil_filter` |
| `children_by_type` | `children_by_type` |
| `chunk` | `chunk` |
| `coerce_int` | `coerce_int_filter` |
| `command_view` | `command_view_filter` |
| `commands` | `commands_filter` |
| `complement` | `complement` |
| `contains` | `contains` |
| `date_add` | `date_add` |
| `date_diff` | `date_diff` |
| `date_iso` | `date_iso` |
| `date_rfc822` | `date_rfc822` |
| `days_ago` | `days_ago` |
| `debug` | `debug` |
| `demote_headings` | `demote_headings` |
| `divided_by` | `divided_by` |
| `emojify` | `emojify` |
| `endpoints` | `endpoints_filter` |
| `excerpt` | `excerpt` |
| `excerpt_for_card` | `excerpt_for_card` |
| `extract_content` | `extract_content` |
| `feature_enabled` | `feature_enabled_filter` |
| `featured_posts` | `featured_posts_filter` |
| `filesize` | `filesize` |
| `first` | `first` |
| `first_sentence` | `first_sentence` |
| `flatten` | `flatten` |
| `floor` | `floor_filter` |
| `get` | `dict_get` |
| `get_element_stats` | `get_element_stats` |
| `get_nested` | `get_nested` |
| `get_params` | `get_params` |
| `get_return_info` | `get_return_info` |
| `group_by` | `group_by` |
| `group_by_month` | `group_by_month` |
| `group_by_year` | `group_by_year` |
| `has_key` | `has_key` |
| `has_prefix` | `has_prefix` |
| `has_suffix` | `has_suffix` |
| `has_tag` | `has_tag` |
| `highlight` | `filter_highlight` |
| `highlight_path_params` | `highlight_path_params` |
| `href` | `href_filter` |
| `html_escape` | `html_escape` |
| `html_unescape` | `html_unescape` |
| `humanize_days` | `humanize_days` |
| `image_alt` | `image_alt` |
| `image_srcset` | `image_srcset` |
| `indent` | `indent_text` |
| `inspect` | `inspect` |
| `intersect` | `intersect` |
| `is_autodoc_page` | `is_autodoc_page` |
| `items` | `items_filter` |
| `jsonify` | `jsonify` |
| `keys` | `keys_filter` |
| `last` | `last` |
| `last_segment` | `last_segment` |
| `limit` | `limit` |
| `markdownify` | `markdownify` |
| `member_view` | `member_view_filter` |
| `members` | `members_filter` |
| `merge` | `merge` |
| `meta_description` | `meta_description` |
| `meta_keywords` | `meta_keywords` |
| `method_color_class` | `method_color_class` |
| `month_name` | `month_name` |
| `months_ago` | `months_ago` |
| `nl2br` | `nl2br` |
| `offset` | `offset` |
| `option_view` | `option_view_filter` |
| `options` | `options_filter` |
| `paginate` | `paginate_items` |
| `param_count` | `param_count` |
| `percentage` | `percentage` |
| `plainify` | `strip_html` |
| `pluralize` | `pluralize` |
| `post_view` | `post_view_filter` |
| `posts` | `posts_filter` |
| `prefix_heading_ids` | `prefix_heading_ids` |
| `private_only` | `private_only` |
| `public_only` | `public_only` |
| `reading_time` | `reading_time` |
| `regex_findall` | `regex_findall` |
| `regex_search` | `regex_search` |
| `release_view` | `release_view_filter` |
| `releases` | `releases_filter` |
| `replace_regex` | `replace_regex` |
| `resolve_links_for_embedding` | `resolve_links_for_embedding` |
| `resolve_pages` | `resolve_pages_with_site` |
| `return_type` | `return_type` |
| `reverse` | `reverse` |
| `round` | `round_filter` |
| `safe_html` | `safe_html` |
| `sample` | `sample` |
| `schemas` | `schemas_filter` |
| `shuffle` | `shuffle` |
| `slugify` | `slugify` |
| `smartquotes` | `smartquotes` |
| `softwrap_ident` | `softwrap_identifier` |
| `sort_by` | `sort_by` |
| `split` | `split_string` |
| `status_code_class` | `status_code_class` |
| `strip_html` | `strip_html` |
| `strip_whitespace` | `strip_whitespace` |
| `tag_accent_index` | `tag_accent_index_filter` |
| `tag_view` | `tag_view_filter` |
| `tag_views` | `tag_views_filter` |
| `time_ago` | `time_ago` |
| `times` | `times` |
| `titleize` | `titleize` |
| `to_sentence` | `to_sentence` |
| `trim_prefix` | `trim_prefix` |
| `trim_suffix` | `trim_suffix` |
| `truncate_chars` | `truncate_chars` |
| `truncatewords` | `truncatewords` |
| `truncatewords_html` | `truncatewords_html` |
| `typeof` | `typeof` |
| `underscore` | `underscore` |
| `union` | `union` |
| `uniq` | `uniq` |
| `url` | `absolute_url_with_site` |
| `url_decode` | `url_decode` |
| `url_encode` | `url_encode` |
| `url_param` | `url_param` |
| `url_parse` | `url_parse` |
| `url_query` | `url_query` |
| `urlize` | `urlize` |
| `values` | `values_filter` |
| `where` | `where` |
| `where_not` | `where_not` |
| `word_count` | `word_count` |
| `wordcount` | `word_count` |
| `wrap` | `wrap_text` |

## Functions

Call directly: `{{ function_name() }}` or `{{ function_name(arg) }}`

| Function | Implementation |
|----------|----------------|
| `alternate_links` | `alternate_links` |
| `anchor` | `anchor_with_site` |
| `asset_url` | `asset_url` |
| `build_artifact_url` | `build_artifact_url_with_site` |
| `build_toc_tree` | `build_toc_tree` |
| `canonical_url` | `canonical_url_with_site` |
| `children_by_type` | `children_by_type` |
| `combine_track_toc` | `combine_track_toc_with_get_page` |
| `command_view` | `command_view_filter` |
| `commands` | `commands_filter` |
| `current_lang` | `current_lang` |
| `cursor_mcp_install_url` | `cursor_mcp_install_url_with_site` |
| `doc` | `doc_with_site` |
| `email_share_url` | `email_share_url` |
| `ensure_trailing_slash` | `ensure_trailing_slash` |
| `ext` | `ext` |
| `ext_exists` | `ext_exists` |
| `facebook_share_url` | `facebook_share_url` |
| `feature_enabled` | `feature_enabled_filter` |
| `file_exists` | `file_exists_with_site` |
| `file_size` | `file_size_with_site` |
| `generate_code_sample` | `generate_code_sample` |
| `get_auto_nav` | `get_auto_nav` |
| `get_breadcrumbs` | `get_breadcrumbs` |
| `get_data` | `get_data_with_site` |
| `get_element_stats` | `get_element_stats` |
| `get_nav_context` | `get_nav_context` |
| `get_nav_tree` | `get_nav_tree` |
| `get_page` | `get_page` |
| `get_pagination_items` | `get_pagination_items` |
| `get_params` | `get_params` |
| `get_response_example` | `get_response_example` |
| `get_return_info` | `get_return_info` |
| `get_section` | `get_section_wrapper` |
| `get_social_card_url` | `get_social_card_url_with_site` |
| `get_toc_grouped` | `get_toc_grouped` |
| `get_version_target_url` | `get_version_target_url_wrapper` |
| `hackernews_share_url` | `hackernews_share_url` |
| `highlight_path_params` | `highlight_path_params` |
| `icon` | `icon` |
| `image_data_uri` | `image_data_uri_with_site` |
| `image_dimensions` | `image_dimensions_with_site` |
| `image_srcset_gen` | `image_srcset_gen` |
| `image_url` | `image_url_with_site` |
| `is_autodoc_page` | `is_autodoc_page` |
| `languages` | `languages` |
| `linkedin_share_url` | `linkedin_share_url` |
| `locale_date` | `locale_date` |
| `mastodon_share_text` | `mastodon_share_text` |
| `member_view` | `member_view_filter` |
| `members` | `members_filter` |
| `method_color_class` | `method_color_class` |
| `notebook_colab_url` | `notebook_colab_url_with_site` |
| `notebook_download_url` | `notebook_download_url_with_site` |
| `og_image` | `og_image_with_site` |
| `option_view` | `option_view_filter` |
| `options` | `options_filter` |
| `page_exists` | `page_exists_wrapper` |
| `page_exists_in_version` | `page_exists_in_version_wrapper` |
| `page_range` | `page_range` |
| `page_url` | `page_url` |
| `param_count` | `param_count` |
| `popular_tags` | `popular_tags_with_site` |
| `private_only` | `private_only` |
| `public_only` | `public_only` |
| `read_file` | `read_file_with_site` |
| `reddit_share_url` | `reddit_share_url` |
| `ref` | `ref_with_site` |
| `related_posts` | `related_posts_with_site` |
| `relref` | `relref_with_site` |
| `render_icon` | `icon` |
| `resources` | `resources` |
| `return_type` | `return_type` |
| `section_pages` | `section_pages_wrapper` |
| `share_url` | `share_url_with_site` |
| `status_code_class` | `status_code_class` |
| `t` | `t` |
| `tag_url` | `tag_url` |
| `twitter_share_url` | `twitter_share_url` |
| `xref` | `ref_with_site` |

## See Also

- [String & Date Filters](/docs/reference/template-functions/string-date-filters/)
- [Collection Filters](/docs/reference/template-functions/collection-filters/)
- [Content Filters](/docs/reference/template-functions/content-filters/)
- [Navigation Functions](/docs/reference/template-functions/navigation-functions/)
- [Linking Functions](/docs/reference/template-functions/linking-functions/)
