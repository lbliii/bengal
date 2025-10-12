# Tabulator.js Setup Instructions

The data table component requires Tabulator.js library files. These are not included in the repository due to size and licensing clarity.

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

For development/testing, you can temporarily use the CDN by editing `base.html`:

```html
<!-- Replace asset_url calls with CDN URLs -->
<link rel="stylesheet" href="https://unpkg.com/tabulator-tables@6.2.5/dist/css/tabulator.min.css">
<script src="https://unpkg.com/tabulator-tables@6.2.5/dist/js/tabulator.min.js"></script>
```

**Note**: This is not recommended for production as it adds external dependencies.

## Verification

After downloading, verify the files:

```bash
# Check files exist and have reasonable size
ls -lh bengal/themes/default/assets/js/tabulator.min.js
ls -lh bengal/themes/default/assets/css/tabulator.min.css

# JavaScript should be ~85KB
# CSS should be ~35KB
```

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
