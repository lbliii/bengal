# Tabulator.js Setup Instructions

The data table component requires Tabulator.js library files. These are not included in the repository due to size and licensing clarity.

**Note**: The CSS file is automatically bundled into `style.css` via `@import` - no separate `<link>` tag needed in templates. The JavaScript file is loaded in `base.html`.

## Quick Setup

### Option 1: Download via Command Line

```bash
# From the bengal root directory
cd bengal/themes/default/assets

# Download JavaScript
curl -o js/tabulator.min.js https://unpkg.com/tabulator-tables@6.2.5/dist/js/tabulator.min.js

# Download CSS
curl -o css/tabulator.min.css https://unpkg.com/tabulator-tables@6.2.5/dist/css/tabulator.min.css
```

### Option 2: Download Manually

1. **JavaScript Library**
   - URL: https://unpkg.com/tabulator-tables@6.2.5/dist/js/tabulator.min.js
   - Save to: `bengal/themes/default/assets/js/tabulator.min.js`
   - Size: ~85KB

2. **CSS Stylesheet**
   - URL: https://unpkg.com/tabulator-tables@6.2.5/dist/css/tabulator.min.css
   - Save to: `bengal/themes/default/assets/css/tabulator.min.css`
   - Size: ~35KB

### Option 3: Use CDN (Development Only)

For development/testing, you can temporarily use the CDN:
- **CSS**: Edit `assets/css/style.css` and replace the `@import url('tabulator.min.css');` line with a CDN URL
- **JS**: Edit `base.html` and replace `asset_url('js/tabulator.min.js')` with CDN URL

**Note**: This is not recommended for production as it adds external dependencies.

## Verification

After downloading, verify the files:

```bash
# Check files exist and have reasonable size
ls -lh bengal/themes/default/assets/js/tabulator.min.js
ls -lh bengal/themes/default/assets/css/tabulator.min.css

# JavaScript should be ~85KB (loaded separately in base.html)
# CSS should be ~35KB (bundled into style.css via @import)
```

## Asset Loading

- **CSS**: Imported in `assets/css/style.css` via `@import url('tabulator.min.css');` and bundled into the main stylesheet
- **JavaScript**: Loaded in `templates/base.html` via `{{ asset_url('js/tabulator.min.js') }}`
- **Initialization**: `data-table.js` auto-initializes tables on DOM ready

## License

Tabulator.js is MIT licensed. See: https://github.com/olifolkerd/tabulator

## Version

Current version: **6.2.5**

To upgrade in the future, simply change the version number in the URLs above.

## Documentation

- Official docs: https://tabulator.info/
- GitHub: https://github.com/olifolkerd/tabulator
- Examples: https://tabulator.info/examples/

## Troubleshooting

### Files Not Loading

If tables don't appear:

1. Check browser console for 404 errors
2. Verify files are in correct locations
3. Check file permissions (should be readable)
4. Clear browser cache

### Size Warnings

If files are much larger/smaller than expected:

- JavaScript should be 80-90KB minified
- CSS should be 30-40KB minified
- If wildly different, re-download from official source

## Alternative: npm Install

If you're using the optional asset pipeline with npm:

```bash
npm install tabulator-tables@6.2.5
```

Then copy from `node_modules/tabulator-tables/dist/` to the theme assets directory.
