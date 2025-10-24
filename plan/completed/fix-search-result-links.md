# Fix: Search Result Links Broken on Deployed Sites

**Status**: ✅ Implemented  
**Date**: 2025-10-24  
**Commit**: `17df12b`

## Problem

Search result links were broken on deployed sites with a `baseurl` configuration (e.g., GitHub Pages at `https://lbliii.github.io/bengal/`). Clicking a search result would navigate to an incorrect URL missing the baseurl prefix.

### Root Cause

The search JavaScript (`search.js`) was prioritizing `page.uri` (relative path) over `page.url` (full path with baseurl):

```javascript
// BEFORE (broken)
href: page.uri || page.url,
```

For a site with `baseurl = "/bengal"`:
- `page.uri` = `/cli/new/site/` ❌ (missing baseurl)
- `page.url` = `/bengal/cli/new/site/` ✅ (includes baseurl)

The code was using the wrong field first, causing links to fail on deployed sites.

## Solution

Swapped the priority to prefer `page.url` over `page.uri`:

```javascript
// AFTER (fixed)
href: page.url || page.uri,
```

### Why This Works

The `index.json` generator (`bengal/postprocess/output_formats.py`) already includes both fields:
- `url`: Full path with baseurl (for deployed sites)
- `uri`: Relative path (Hugo convention, fallback)

By prioritizing `url`, links work correctly on:
- ✅ GitHub Pages with subpath (`/bengal`)
- ✅ Custom domains with baseurl
- ✅ Local development (baseurl is empty, both fields are the same)

## Files Changed

- `bengal/themes/default/assets/js/search.js` (line 177)

## Verification

1. Built site with `baseurl = "/bengal"`
2. Confirmed minified `search.js` contains `href:page.url||page.uri`
3. Search results now link correctly to `/bengal/cli/new/site/` instead of `/cli/new/site/`

## Impact

- ✅ Fixes broken search on all deployed sites with baseurl
- ✅ No breaking changes (maintains fallback to `uri`)
- ✅ Works for both local and deployed environments
