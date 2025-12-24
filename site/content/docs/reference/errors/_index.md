---
title: Error Code Reference
nav_title: Error Codes
description: Complete reference for all Bengal error codes
weight: 50
icon: alert-triangle
tags: [reference, errors, troubleshooting]
---

# Error Code Reference

Bengal uses prefixed error codes for quick identification and searchability.
Each error code links to documentation with explanations and solutions.

## Error Categories

| Prefix | Category | Description |
|--------|----------|-------------|
| A | Asset | Static asset processing errors |
| C | Cache | Build cache operations errors |
| C | Config | Configuration loading and validation errors |
| C | Content | Content file parsing and frontmatter errors |
| D | Discovery | Content and section discovery errors |
| G | Graph | Graph analysis errors |
| P | Parsing | YAML, JSON, TOML, and markdown parsing errors |
| R | Rendering | Template rendering and output generation errors |
| S | Server | Development server errors |
| T | Template_Function | Template function, shortcode, and directive errors |

## All Error Codes

### Asset Errors (Axxx)

| Code | Description |
|------|-------------|
| [X001](x001/) | Asset Not Found |
| [X002](x002/) | Asset Invalid Path |
| [X003](x003/) | Asset Processing Failed |
| [X004](x004/) | Asset Copy Error |
| [X005](x005/) | Asset Fingerprint Error |
| [X006](x006/) | Asset Minify Error |

### Cache Errors (Cxxx)

| Code | Description |
|------|-------------|
| [A001](a001/) | Cache Corruption |
| [A002](a002/) | Cache Version Mismatch |
| [A003](a003/) | Cache Read Error |
| [A004](a004/) | Cache Write Error |
| [A005](a005/) | Cache Invalidation Error |
| [A006](a006/) | Cache Lock Timeout |

### Config Errors (Cxxx)

| Code | Description |
|------|-------------|
| [C001](c001/) | Config Yaml Parse Error |
| [C002](c002/) | Config Key Missing |
| [C003](c003/) | Config Invalid Value |
| [C004](c004/) | Config Type Mismatch |
| [C005](c005/) | Config Defaults Missing |
| [C006](c006/) | Config Environment Unknown |
| [C007](c007/) | Config Circular Reference |
| [C008](c008/) | Config Deprecated Key |

### Content Errors (Cxxx)

| Code | Description |
|------|-------------|
| [N001](n001/) | Frontmatter Invalid |
| [N002](n002/) | Frontmatter Date Invalid |
| [N003](n003/) | Content File Encoding |
| [N004](n004/) | Content File Not Found |
| [N005](n005/) | Content Markdown Error |
| [N006](n006/) | Content Shortcode Error |
| [N007](n007/) | Content Toc Extraction Error |
| [N008](n008/) | Content Taxonomy Invalid |
| [N009](n009/) | Content Weight Invalid |
| [N010](n010/) | Content Slug Invalid |

### Discovery Errors (Dxxx)

| Code | Description |
|------|-------------|
| [D001](d001/) | Content Dir Not Found |
| [D002](d002/) | Invalid Content Path |
| [D003](d003/) | Section Index Missing |
| [D004](d004/) | Circular Section Reference |
| [D005](d005/) | Duplicate Page Path |
| [D006](d006/) | Invalid File Pattern |
| [D007](d007/) | Permission Denied |

### Graph Errors (Gxxx)

| Code | Description |
|------|-------------|
| [G001](g001/) | Graph Not Built |
| [G002](g002/) | Graph Invalid Parameter |
| [G003](g003/) | Graph Cycle Detected |
| [G004](g004/) | Graph Disconnected Component |
| [G005](g005/) | Graph Analysis Failed |

### Parsing Errors (Pxxx)

| Code | Description |
|------|-------------|
| [P001](p001/) | Yaml Parse Error |
| [P002](p002/) | Json Parse Error |
| [P003](p003/) | Toml Parse Error |
| [P004](p004/) | Markdown Parse Error |
| [P005](p005/) | Frontmatter Delimiter Missing |
| [P006](p006/) | Glossary Parse Error |

### Rendering Errors (Rxxx)

| Code | Description |
|------|-------------|
| [R001](r001/) | Template Not Found |
| [R002](r002/) | Template Syntax Error |
| [R003](r003/) | Template Undefined Variable |
| [R004](r004/) | Template Filter Error |
| [R005](r005/) | Template Include Error |
| [R006](r006/) | Template Macro Error |
| [R007](r007/) | Template Block Error |
| [R008](r008/) | Template Context Error |
| [R009](r009/) | Template Inheritance Error |
| [R010](r010/) | Render Output Error |

### Server Errors (Sxxx)

| Code | Description |
|------|-------------|
| [S001](s001/) | Server Port In Use |
| [S002](s002/) | Server Bind Error |
| [S003](s003/) | Server Reload Error |
| [S004](s004/) | Server Websocket Error |
| [S005](s005/) | Server Static File Error |

### Template_Function Errors (Txxx)

| Code | Description |
|------|-------------|
| [T001](t001/) | Shortcode Not Found |
| [T002](t002/) | Shortcode Argument Error |
| [T003](t003/) | Shortcode Render Error |
| [T004](t004/) | Directive Not Found |
| [T005](t005/) | Directive Argument Error |
| [T006](t006/) | Directive Since Empty |
| [T007](t007/) | Directive Deprecated Empty |
| [T008](t008/) | Directive Changed Empty |
| [T009](t009/) | Directive Include Not Found |


## Getting Help

If you encounter an error:

1. Check the error message and suggestion in the CLI output
2. Click the documentation link shown with the error
3. Review this reference for related errors
4. Check the [troubleshooting guide](/docs/guides/troubleshooting/)

For bugs or unclear errors, please [open an issue](https://github.com/bengal-ssg/bengal/issues).
