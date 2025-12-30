# Change Log

All notable changes to the "Bengal SSG Syntax Highlighter" extension will be documented in this file.

## [1.1.0] - 2025-12-30

### Added
- **Kida template syntax highlighting** in markdown code blocks
- Support for Kida-specific operators:
  - `??` (null coalescing operator)
  - `?.` (optional chaining)
  - `|>` (pipeline operator)
- Template tag highlighting: `{% %}`, `{{ }}`, `{# #}`
- Keyword highlighting: `let`, `if`, `for`, `in`, `match`, `case`, `end`, `extends`, `block`, `cache`, `spaceless`, etc.
- Constant highlighting: `true`, `false`, `none`, `null`
- Function call highlighting
- String and number highlighting
- Standalone Kida language support (`.kida` files)
- Language configuration with auto-closing pairs and folding

### Technical
- Added `kida.tmLanguage.json` for standalone Kida files
- Added `language-configuration.json` for bracket matching and folding
- Extended markdown injection to support `kida` code blocks
- All operators now use `keyword.operator.*` scopes for consistent theming

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
