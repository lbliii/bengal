# Phase 2 Analysis - Additional Templates & Features

**Date**: October 2, 2025  
**Current Status**: Phase 1 Foundation Complete ✅  
**Next Phase**: Additional Templates & Content Organization

---

## 📊 Where We Are Now

### ✅ What's Working (Phase 1)

**Core Architecture**
- Site, Page, Section, Asset object model
- Content discovery (Markdown files → Pages)
- Section hierarchy (directories → Sections)
- Rendering pipeline (Parse → Template → Output)
- Asset management (CSS/JS copying)

**Templates Available**
- `base.html` - Layout with header/footer
- `page.html` - Individual pages
- `post.html` - Individual blog posts  
- `index.html` - Homepage

**Current Build Output**
```
public/
├── index.html              ← Homepage
├── about/index.html        ← Individual page
├── posts/
│   └── first-post/
│       └── index.html      ← Individual post
├── sitemap.xml            ← SEO
└── rss.xml                ← RSS feed
```

### ❌ What's Missing

**1. No Listing/Archive Pages**
- Can't browse all blog posts
- Can't see posts by category/tag
- No section index pages
- No pagination for long lists

**2. No Taxonomy System**
- Posts have tags, but no tag pages
- Can't browse by tag
- No tag index/cloud

**3. No Special Pages**
- No 404 error page
- No search page
- No archive by date

**4. No Reusable Components**
- No partials (header, footer, sidebar as separate files)
- No macros for common patterns
- Duplication between templates

---

## 🎯 What Phase 2 Needs to Accomplish

### Core Goal
**Enable content organization and discovery beyond individual pages**

### Specific Features

#### 1. Archive/Listing Pages ⭐ **HIGH PRIORITY**
**Purpose**: Browse all posts in a section

**Example URLs**:
- `/blog/` - All blog posts
- `/posts/` - All posts in posts section
- `/docs/` - All documentation pages

**What's Needed**:
- Section index template
- List all pages in a section
- Sort by date (newest first)
- Pagination for long lists
- Preview/excerpt display

#### 2. Tag/Taxonomy Pages ⭐ **HIGH PRIORITY**
**Purpose**: Browse posts by tag

**Example URLs**:
- `/tags/` - All tags
- `/tags/tutorial/` - Posts tagged "tutorial"
- `/tags/getting-started/` - Posts tagged "getting-started"

**What's Needed**:
- Taxonomy collection system
- Tag index page (all tags)
- Individual tag pages
- Post count per tag
- Tag cloud/list display

#### 3. Pagination Component ⭐ **HIGH PRIORITY**
**Purpose**: Navigate long lists

**What's Needed**:
- Split lists into pages
- Previous/Next navigation
- Page numbers
- Configurable items per page
- Template partial for pagination UI

#### 4. Reusable Components ⭐ **MEDIUM PRIORITY**
**Purpose**: Reduce duplication, improve maintainability

**Components Needed**:
- Article card partial (for listings)
- Pagination partial
- Breadcrumbs partial
- Sidebar partial
- Tag list partial

#### 5. Special Pages ⭐ **MEDIUM PRIORITY**
**Pages Needed**:
- 404 error page
- Search page (client-side)
- Archive by date page

---

## 🔍 Technical Gaps to Fill

### Gap 1: No Programmatic Page Generation

**Current State**:
- Pages only created from Markdown files
- One Markdown file = One HTML page
- No way to generate pages programmatically

**Need**:
- Generate pages without source Markdown
- Create listing pages dynamically
- Build tag pages on-the-fly

**Solution Required**:
- Add `generate_pages()` method to Site
- Create virtual pages for listings
- Pass page lists to templates

### Gap 2: No Taxonomy System

**Current State**:
- Pages have `tags` metadata
- Tags extracted but not collected
- No way to group pages by tag

**Need**:
- Collect all tags across site
- Group pages by tag
- Count pages per tag
- Sort tags by count/name

**Solution Required**:
- Add `collect_taxonomies()` method
- Create Taxonomy class/dict structure
- Store in Site object

### Gap 3: No Pagination Logic

**Current State**:
- Lists render all items
- No limit on items per page
- No page splitting

**Need**:
- Split lists into chunks
- Generate multiple pages (page/1/, page/2/, etc.)
- Maintain navigation state

**Solution Required**:
- Add `paginate()` utility function
- Generate paginated page objects
- Template context with pagination info

### Gap 4: Template Inheritance Limitations

**Current State**:
- Templates use `extends` and `blocks`
- No partials/includes
- Duplication of article cards, etc.

**Need**:
- Reusable template components
- Include partials in templates
- Jinja2 macros for common patterns

**Solution Required**:
- Create `templates/partials/` directory
- Define reusable components
- Use `{% include %}` and macros

---

## 🏗️ Implementation Plan

### Step 1: Foundation for Dynamic Pages

**Goal**: Enable programmatic page generation

**Tasks**:
1. Create `VirtualPage` class (or extend Page)
2. Add `generate_pages()` to Site
3. Test generating a simple listing page

**Affected Files**:
- `bengal/core/page.py` (extend or create VirtualPage)
- `bengal/core/site.py` (add generation logic)

### Step 2: Taxonomy Collection

**Goal**: Collect and organize tags

**Tasks**:
1. Create `collect_taxonomies()` method
2. Build tag → pages mapping
3. Store in Site object
4. Count and sort tags

**Affected Files**:
- `bengal/core/site.py` (add taxonomy collection)
- `bengal/core/page.py` (ensure tags accessible)

### Step 3: Archive Template

**Goal**: List all posts in a section

**Tasks**:
1. Create `archive.html` template
2. Display list of posts
3. Show post cards with excerpts
4. Sort by date

**New Files**:
- `templates/archive.html`
- `templates/partials/article-card.html`

### Step 4: Tag Pages

**Goal**: Browse posts by tag

**Tasks**:
1. Create `tags.html` (tag index)
2. Create `tag.html` (single tag page)
3. Generate tag pages dynamically
4. Display posts for each tag

**New Files**:
- `templates/tags.html`
- `templates/tag.html`

### Step 5: Pagination

**Goal**: Split long lists into pages

**Tasks**:
1. Create pagination utility
2. Generate paginated pages
3. Create pagination partial
4. Add to archive and tag templates

**New Files**:
- `bengal/utils/pagination.py`
- `templates/partials/pagination.html`

### Step 6: Component Library

**Goal**: Reusable template components

**Tasks**:
1. Extract common patterns to partials
2. Create article card component
3. Create breadcrumbs component
4. Create tag list component

**New Files**:
- `templates/partials/article-card.html`
- `templates/partials/breadcrumbs.html`
- `templates/partials/tag-list.html`
- `templates/macros/components.html`

### Step 7: Special Pages

**Goal**: 404 and search pages

**Tasks**:
1. Create 404.html template
2. Create search.html template
3. Generate 404 page
4. Add search functionality (client-side)

**New Files**:
- `templates/404.html`
- `templates/search.html`
- `bengal/postprocess/search_index.py`

---

## 📝 Detailed Requirements

### Archive Page Requirements

**Template**: `archive.html`

**Context Variables**:
```python
{
    'section': Section object,
    'pages': List[Page],  # All pages in section
    'total': int,         # Total page count
    'page': int,          # Current page number (for pagination)
    'pages_per_page': int,
    'has_next': bool,
    'has_prev': bool,
}
```

**Features**:
- Title (section name)
- List of posts (card format)
- Pagination (if > 10 posts)
- Sort by date (newest first)

### Tag Index Page Requirements

**Template**: `tags.html`  
**URL**: `/tags/`

**Context Variables**:
```python
{
    'tags': [
        {'name': 'tutorial', 'count': 5, 'pages': [...]},
        {'name': 'guide', 'count': 3, 'pages': [...]},
    ]
}
```

**Features**:
- List all tags
- Show post count per tag
- Link to individual tag pages
- Optional: Tag cloud with sizes

### Tag Page Requirements

**Template**: `tag.html`  
**URL**: `/tags/{tag}/`

**Context Variables**:
```python
{
    'tag': 'tutorial',
    'pages': List[Page],  # Posts with this tag
    'total': int,
}
```

**Features**:
- Tag name as title
- List of posts with this tag
- Pagination (if > 10 posts)
- Link back to tag index

### Pagination Requirements

**Partial**: `partials/pagination.html`

**Context Variables**:
```python
{
    'current_page': 1,
    'total_pages': 5,
    'has_next': True,
    'has_prev': False,
    'next_url': '/blog/page/2/',
    'prev_url': None,
}
```

**Features**:
- Previous button (disabled if first page)
- Page numbers (with current highlighted)
- Next button (disabled if last page)
- Show "Page X of Y"

---

## 🎨 Design Considerations

### URL Structure

**Archive Pages**:
```
/blog/                    # All posts, page 1
/blog/page/2/            # Page 2
/blog/page/3/            # Page 3
```

**Tag Pages**:
```
/tags/                   # All tags
/tags/tutorial/          # Posts tagged "tutorial", page 1
/tags/tutorial/page/2/   # Page 2
```

**Special Pages**:
```
/404.html               # Error page
/search/                # Search page
```

### Configuration Options

**In `bengal.toml`**:
```toml
[pagination]
items_per_page = 10
show_page_numbers = true
max_page_links = 5

[taxonomies]
enabled = ["tags", "categories"]
tag_layout = "cloud"  # or "list"

[archives]
generate_section_archives = true
sort_by = "date"
sort_order = "desc"
```

---

## 🔄 Build Process Changes

### Current Build Flow
```
1. Discover content → Pages
2. Render each page → HTML
3. Copy assets
4. Generate sitemap/RSS
```

### Enhanced Build Flow (Phase 2)
```
1. Discover content → Pages
2. Collect taxonomies → Tags, Categories
3. Generate virtual pages → Archives, Tag pages
4. Render all pages → HTML
5. Copy assets
6. Generate sitemap/RSS
7. Generate search index (optional)
```

---

## 📊 Complexity Assessment

### Low Complexity ⭐
- Reusable components (partials)
- 404 page
- Article card component

### Medium Complexity ⭐⭐
- Archive template
- Tag collection
- Basic pagination

### High Complexity ⭐⭐⭐
- Dynamic page generation
- Advanced pagination (with URLs)
- Search functionality
- Taxonomy system

---

## 🎯 Recommended Implementation Order

### Phase 2A: Foundation (Week 1)
1. ✅ Create reusable components/partials
2. ✅ Add taxonomy collection
3. ✅ Create basic archive template
4. ✅ Test with existing content

### Phase 2B: Listing Pages (Week 2)
1. ✅ Implement dynamic page generation
2. ✅ Generate section archive pages
3. ✅ Add pagination logic
4. ✅ Test with multiple posts

### Phase 2C: Taxonomy Pages (Week 3)
1. ✅ Generate tag index page
2. ✅ Generate individual tag pages
3. ✅ Add tag filtering
4. ✅ Style tag components

### Phase 2D: Polish (Week 4)
1. ✅ Create 404 page
2. ✅ Add breadcrumbs
3. ✅ Improve navigation
4. ✅ Documentation

---

## 🚀 Success Criteria

### Phase 2 is complete when:

- [ ] Can browse all posts in a section
- [ ] Can click tags to see related posts
- [ ] Long lists have pagination
- [ ] 404 page exists and looks good
- [ ] Components are reusable (no duplication)
- [ ] URLs are clean and semantic
- [ ] Everything works with existing theme
- [ ] Documentation is updated

---

## 💡 Key Decisions Needed

### 1. Page Generation Approach
**Option A**: Create VirtualPage class  
**Option B**: Extend existing Page class  
**Option C**: Use Page with null source_path  

**Recommendation**: Option C - Simplest, reuses existing code

### 2. Taxonomy Storage
**Option A**: Dict in Site object  
**Option B**: Separate Taxonomy class  
**Option C**: Database/JSON file  

**Recommendation**: Option A - Simple, in-memory, fast

### 3. Pagination Strategy
**Option A**: Generate multiple HTML files  
**Option B**: Single page with JS  
**Option C**: Hybrid  

**Recommendation**: Option A - True static site, SEO friendly

### 4. URL Scheme
**Option A**: `/blog/2/` (page number in path)  
**Option B**: `/blog/page/2/` (explicit "page")  
**Option C**: `/blog/?page=2` (query parameter)  

**Recommendation**: Option B - Clear, Hugo-like, SEO friendly

---

## 📋 Summary

**Phase 2 Scope**: Add listing/archive pages, tag pages, pagination, and reusable components

**Why Important**: Users need to browse/discover content, not just view individual pages

**Prerequisites**: ✅ All met (Phase 1 complete)

**Estimated Effort**: 2-3 weeks (across 4 sub-phases)

**Risk Level**: Medium (new concepts but clear patterns to follow)

**Next Step**: Start with Phase 2A - Foundation (reusable components + taxonomy collection)

---

## 🎬 Ready to Start?

Once you confirm this analysis aligns with your vision, we'll begin with:

1. **Create template partials** (article cards, pagination UI)
2. **Add taxonomy collection** (gather all tags)
3. **Build archive template** (list posts in a section)
4. **Test with quickstart example**

This gives us immediate visible results while laying groundwork for more complex features.

Sound good? 🚀

