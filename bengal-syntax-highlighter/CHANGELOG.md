# Change Log

All notable changes to the "Bengal SSG Syntax Highlighter" extension will be documented in this file.

## [1.0.0] - 2025-10-04

### Added
- Initial release
- Syntax highlighting for Bengal SSG markdown directives
- Support for tabs directive with `### Tab:` markers
- Support for 9 admonition types (note, tip, warning, danger, error, info, example, success, caution)
- Support for dropdown/details directives
- Support for code-tabs directive
- Highlighting for directive options (`:key: value` pattern)
- Markdown injection grammar for seamless integration
- Works with all VS Code themes
- Compatible with Cursor editor

### Features
- **Tabs directive**: Prominent highlighting of `### Tab:` markers
- **All directives**: Yellow/gold directive names
- **Tab markers**: Bold pink "Tab:" keyword, bold orange tab names
- **Options**: Cyan keys, green values
- **Nested directives**: Full markdown support inside directives
- **Error detection**: Malformed syntax doesn't highlight

### Technical
- Uses TextMate injection grammar
- Scopes follow standard naming conventions
- No performance impact
- Works with existing `.md` files

