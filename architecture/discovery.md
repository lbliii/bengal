# Discovery System

The discovery system is responsible for finding and cataloging all content, sections, and assets in a Bengal site.

## Content Discovery (`bengal/discovery/content_discovery.py`)

### Purpose
Walks the content directory recursively to create Page and Section objects

### Responsibilities
- Walks content directory recursively
- Creates Page and Section objects
- Parses frontmatter
- Organizes content into hierarchy
- **Includes autodoc-generated markdown files**
- **Uses Utilities**: Delegates to `bengal.utils.file_io.read_text_file()` for robust file reading with encoding fallback

### Process Flow
1. Start at content root directory
2. Recursively traverse directories
3. For each directory:
   - Create Section object
   - Look for `_index.md` (section index page)
   - Find all markdown files
4. For each markdown file:
   - Read file content
   - Parse frontmatter (YAML/TOML)
   - Extract metadata
   - Create Page object
   - Associate with parent Section
5. Build section hierarchy
6. Return organized Pages and Sections

### Features
- Encoding fallback (UTF-8 → latin-1)
- UTF-8 BOM stripping during read to avoid confusing frontmatter parsing
- Error handling for malformed files (frontmatter syntax errors fall back to content-only)
- Automatic section creation
- Hierarchical organization
- Cross-reference index building

## Asset Discovery (`bengal/discovery/asset_discovery.py`)

### Purpose
Finds all static assets and creates Asset objects

### Responsibilities
- Finds all static assets
- Preserves directory structure
- Creates Asset objects with metadata
- Tracks asset types (CSS, JS, images, fonts, etc.)

### Process Flow
1. Walk assets directory
2. For each file:
   - Determine asset type (by extension)
   - Create Asset object
   - Preserve relative path
   - Track for processing
3. Also discover theme assets
4. Return organized Asset list

### Asset Types
- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`
- **Stylesheets**: `.css`, `.scss`, `.sass`, `.less`
- **Scripts**: `.js`, `.mjs`, `.ts`
- **Fonts**: `.woff`, `.woff2`, `.ttf`, `.otf`, `.eot`
- **Data**: `.json`, `.yaml`, `.yml`, `.toml`, `.xml`
- **Documents**: `.pdf`, `.doc`, `.docx`
- **Other**: Any other files

### Features
- Type detection by extension
- Path preservation
- Metadata extraction
- Theme asset integration
- Optimization hints
