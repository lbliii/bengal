OpenAPI autodoc now generates an individual three-column explorer page for
every endpoint by default (the `consolidate` option defaults to `false`), so
endpoint cards link to real pages instead of dead `#anchors` and schema pages
render their properties, enums, and examples. Untagged endpoints nest under a
synthetic `default` tag section so their page URL agrees with their section
placement. Set `consolidate: true` to keep the previous consolidated
reference-view behavior.
