# Bengal i18n Strategy for 2025 and Beyond

**Date:** October 19, 2025  
**Status:** Strategy Document

## The AI-Era Translation Landscape

### Traditional Approach (Sphinx, Hugo, etc.)

**gettext/.po/.mo Workflow:**
1. Extract translatable strings from templates/code
2. Send .po files to professional translators
3. Translators use poedit/Crowdin/Transifex
4. Compile .mo files
5. Ship pre-translated UI in 70+ languages

**Problems:**
- Massive overhead (~7,000+ LOC in Sphinx)
- Requires translation team coordination
- Expensive for small projects
- Updates require re-translation
- Still doesn't translate user content

### 2025 Reality: AI + Browser Translation

**Browser Translation (Built-in):**
- Chrome, Edge, Safari auto-translate entire pages
- One-click for users
- Zero effort for site owners
- Works in 100+ languages
- Good enough for 90% of readers

**AI Translation (ChatGPT, Claude, etc.):**
```bash
# Translate entire markdown file
claude "Translate this file to French, maintain all front matter and code blocks" < about.md > content/fr/about.md

# Batch translate
for file in content/en/**/*.md; do
  target="content/fr/${file#content/en/}"
  claude "Translate to French" < "$file" > "$target"
done
```

**Benefits:**
- Near-professional quality
- Handles technical content, code blocks, formatting
- Can translate in seconds vs days/weeks
- Context-aware
- Getting better every month

## Bengal's i18n Philosophy

### What Bengal Provides

✅ **Content Organization**
- Directory-based: `content/en/`, `content/fr/`, `content/es/`
- Per-page language metadata
- Translation linking via `translation_key`

✅ **URL Structure**
- Clean language prefixes: `/fr/docs/getting-started/`
- SEO-friendly hreflang alternates
- Configurable default language behavior

✅ **Language-Aware Features**
- Per-locale menus
- Per-locale taxonomies (tags, categories)
- Per-locale RSS feeds
- Per-locale search indexes
- Sitemap with proper alternates

✅ **Template Translation**
- Simple YAML/JSON/TOML files: `i18n/fr.yaml`
- Template helpers: `t('nav.search')`
- Parameter interpolation: `"Hello {name}"`
- Automatic fallback to default language

### What Bengal Doesn't Provide (by Design)

❌ **Professional Translation Workflows**
- No .po/.mo files
- No msgfmt/msgmerge/xgettext
- No poedit/Crowdin integration
- No translation memory
- No fuzzy matching
- No translation progress tracking

**Why Not?**
1. AI can translate better and faster than most human translators
2. Browser translation handles casual readers automatically
3. Professional sites that need verified translations can manage translations externally
4. Simpler YAML files are easier for developers and AI

## Use Cases and Recommendations

### Scenario 1: Personal Blog / Small Site
**Need:** Occasional international readers

**Strategy:** Do nothing
- Write in your native language
- Let browsers auto-translate for readers
- **Bengal requirement:** None

### Scenario 2: SEO-Focused Content Site
**Need:** Rank in multiple language markets

**Strategy:** AI-translated content
1. Write content in English (or primary language)
2. Use AI to translate key pages to target languages
3. Organize in `content/en/`, `content/fr/`, etc.
4. Configure Bengal's `[i18n]` for URL prefixes
5. **Result:** Search engines index separate language versions, proper hreflang

**Bengal requirement:**
```toml
[i18n]
strategy = "prefix"
default_language = "en"
languages = [{code = "en"}, {code = "fr"}, {code = "es"}]
```

### Scenario 3: Professional/Corporate Site
**Need:** Curated, verified translations with brand voice

**Strategy:** Professional translations + Bengal structure
1. Hire translators or use translation service
2. Store translations as markdown in language directories
3. Manage UI strings in `i18n/<lang>.yaml` files
4. Update as needed (Git workflow)
5. **Result:** Full control, verified translations, professional quality

**Bengal requirement:**
```toml
[i18n]
strategy = "prefix"
default_language = "en"
default_in_subdir = false
share_taxonomies = false  # Separate tags per locale

[[i18n.languages]]
code = "en"
name = "English"
hreflang = "en"

[[i18n.languages]]
code = "fr"
name = "Français"
hreflang = "fr-FR"
```

Plus `i18n/en.yaml`, `i18n/fr.yaml` for UI strings.

### Scenario 4: Legal/Regulated Content
**Need:** Certified translations for compliance

**Strategy:** External translation service + Bengal
1. Use certified translation service
2. Import certified translations as markdown
3. Version control alongside source
4. **Result:** Compliance + proper multi-language site structure

**Bengal requirement:** Same as Scenario 3

## What About Sphinx's 70+ UI Translations?

**Sphinx ships with:**
- Arabic (ar)
- Bengali (bn)
- Chinese (zh_CN, zh_TW)
- French (fr)
- German (de)
- Spanish (es)
- Japanese (ja)
- Korean (ko)
- Russian (ru)
- ... 60+ more

**These translate:**
- "Search"
- "Previous"
- "Next"
- "Table of Contents"
- Error messages
- Build output

**Do we need this in Bengal?**

**NO, because:**

1. **Browser translation** - Browsers translate these strings automatically
2. **Small string count** - Bengal's default theme has ~20 UI strings (vs 100+ in Sphinx)
3. **Easy to translate** - Single YAML file per language
4. **AI can do it** - "Translate this i18n/en.yaml to French" takes 5 seconds
5. **Most users want English** - Technical documentation readers expect English
6. **Themes can include** - Theme developers can ship pre-translated i18n files

**If we wanted to:**
```bash
# Generate i18n files for 10 languages in 30 seconds
for lang in fr es de it pt ja ko zh ru ar; do
  claude "Translate i18n/en.yaml to $lang language, output only YAML" < i18n/en.yaml > i18n/$lang.yaml
done
```

## Competitive Analysis

### Sphinx (2007 approach)
- ✅ 70+ pre-translated languages
- ✅ Professional .po/.mo workflow
- ✅ Translation extraction tools
- ❌ Complex setup
- ❌ Requires translation infrastructure
- ❌ Still doesn't translate user content
- ❌ Built for pre-AI era

### Hugo (2013 approach)
- ✅ Content-based i18n (like Bengal)
- ✅ Directory structure or filename-based
- ✅ Per-language config files
- ⚠️ More complex than Bengal
- ❌ No built-in UI translations

### Jekyll (2008 approach)
- ❌ No built-in i18n
- ⚠️ Requires plugins
- ⚠️ Manual URL management

### Bengal (2025 approach)
- ✅ Content-based i18n
- ✅ Clean directory structure
- ✅ Proper URL prefixing
- ✅ Template translation helpers
- ✅ SEO features (hreflang, per-locale sitemaps)
- ✅ Simple YAML-based UI translation
- ✅ **AI-friendly** - Easy to generate translations
- ✅ **Browser-translation friendly** - Works with auto-translate
- ❌ No .po/.mo workflow (feature, not bug)
- ❌ No pre-translated UI (themes can add)

## Future Considerations

### Should We Add Pre-Translated UI?

**Option 1: Ship with 10-20 languages**
- Pros: Works out of box for common languages
- Cons: Maintenance burden, bloat, still incomplete coverage
- **Decision:** Not worth it, themes can do this

**Option 2: AI translation on-demand**
```bash
bengal utils i18n generate --languages fr,es,de,ja
# Generates i18n/<lang>.yaml using AI
```
- Pros: Zero maintenance, infinite languages, always fresh
- Cons: Requires API key, network access
- **Decision:** Interesting for future

**Option 3: Status quo**
- Pros: Simple, flexible, AI-friendly
- Cons: Users must provide translations
- **Decision:** Best for now, users can use AI directly

### Should We Support .po/.mo?

**Arguments FOR:**
- Professional translation teams expect it
- Tool ecosystem (poedit, Crowdin, etc.)
- Translation memory
- Industry standard

**Arguments AGAINST:**
- Huge complexity (~7,000+ LOC)
- Maintenance burden
- Less relevant in AI era
- Most Bengal users won't use it
- Can use external tools then import

**Decision:** No, unless strong user demand

### RTL Language Support?

**Current status:** Unknown, probably works with CSS
**Action needed:** Test with Arabic, Hebrew
**Priority:** Medium (affects legitimate use cases)

## Recommendations

### For Bengal Core

1. ✅ **Keep current approach** - Content-based i18n with YAML translations is perfect for 2025
2. ✅ **Document AI workflows** - Show users how to use ChatGPT/Claude for translation
3. ⚠️ **Test RTL support** - Ensure Arabic, Hebrew work properly
4. 💡 **Consider AI helper** - `bengal utils i18n generate` for on-demand translation
5. ❌ **Don't add .po/.mo** - Complexity not worth it in AI era

### For Documentation

1. Show AI translation workflow
   ```bash
   # Example: Translate site to French
   for file in content/en/**/*.md; do
     target="content/fr/${file#content/en/}"
     mkdir -p "$(dirname "$target")"
     claude "Translate to French, preserve front matter and code" < "$file" > "$target"
   done
   ```

2. Show browser translation reality
   - Most users will see auto-translated version
   - It's okay, it works

3. Show SEO benefits
   - When you need multiple language versions for search engines
   - hreflang alternates
   - Per-locale sitemaps

4. Provide templates
   - Example `i18n/en.yaml` with common UI strings
   - Show how to translate with AI
   - Theme-specific i18n files

### For Themes

1. **Include common languages** - Themes can ship with pre-translated i18n files
2. **Document translation** - Show theme users how to add languages
3. **Use semantic keys** - `nav.search` not `search_button` for better AI translation

## Conclusion

**Bengal's i18n approach is actually ahead of its time:**

1. **Content-focused** - Supports multi-language content structure (SEO, professional sites)
2. **Simple** - YAML files, no complex tooling
3. **AI-friendly** - Easy to generate translations with ChatGPT/Claude
4. **Browser-friendly** - Works with auto-translation
5. **Flexible** - Professional sites can use external translation services
6. **Modern** - Built for 2025, not 2007

**The "gap" vs Sphinx isn't a gap - it's intentional simplicity for the AI era.**

Users who need:
- Casual translation → Browser handles it
- SEO translation → AI generates it, Bengal structures it
- Professional translation → External service, Bengal organizes it
- Complex workflows → Probably not Bengal's target user

**Bottom line:** Don't chase Sphinx's 18-year-old translation infrastructure. Bengal's approach is better suited for 2025 and beyond.
