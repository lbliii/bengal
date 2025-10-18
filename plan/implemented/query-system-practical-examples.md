# Query System: Practical Use Examples

**Companion to:** extensible-query-system-design.md  
**Status:** Examples  
**Created:** 2025-10-18

---

## Scenario 1: Personal Blog with Author Pages

### Site Structure
```
content/
  blog/
    2024-01-15-python-tips.md       # author: Jane Smith
    2024-02-20-web-dev.md           # author: Jane Smith
    2024-03-10-databases.md         # author: Bob Jones
    guest-posts/
      2024-04-05-security.md        # author: Alice Chen
```

### Current Approach (Without Indexes)

```jinja2
{# templates/author.html - Author page showing all posts by author #}
<h1>Posts by {{ author_name }}</h1>

{% set author_posts = [] %}
{% for post in site.pages %}  {# O(n) - loops through ALL pages #}
  {% if post.metadata.author == author_name and post.section == 'blog' %}
    {% set _ = author_posts.append(post) %}
  {% endif %}
{% endfor %}

{# On a 10K page site, this runs 10K comparisons PER author page #}
{# With 50 authors = 500K comparisons total #}

{% for post in author_posts | sort(attribute='date', reverse=true) %}
  <article>
    <h2><a href="{{ url_for(post) }}">{{ post.title }}</a></h2>
    <time>{{ post.date | strftime('%B %d, %Y') }}</time>
  </article>
{% endfor %}
```

**Performance:** O(n) per author page × number of authors = **500K operations** for 50 authors on 10K pages

### With Indexes (Proposed)

```jinja2
{# templates/author.html - Same output, O(1) lookup #}
<h1>Posts by {{ author_name }}</h1>

{# O(1) hash table lookup - instant #}
{% set author_post_paths = site.indexes.author.get(author_name) %}
{% set author_posts = author_post_paths | resolve_pages %}

{# Already sorted by date (index maintains sort order) #}
{% for post in author_posts %}
  <article>
    <h2><a href="{{ url_for(post) }}">{{ post.title }}</a></h2>
    <time>{{ post.date | strftime('%B %d, %Y') }}</time>
  </article>
{% endfor %}

{# Show post count #}
<p>{{ author_posts | length }} posts</p>
```

**Performance:** O(1) lookup × 50 authors = **50 operations** (10,000x faster!)

### Author Index Definition

```python
# Built-in - no code needed, just works!
# bengal/cache/indexes/author_index.py (already provided)

class AuthorIndex(QueryIndex):
    def extract_keys(self, page):
        author = page.metadata.get('author')
        if author:
            # Support both string and dict formats
            if isinstance(author, dict):
                name = author.get('name')
                email = author.get('email', '')
                return [(name, {'email': email})]
            return [(author, {})]
        return []
```

### Frontmatter Examples

```yaml
---
title: Python Tips
author: Jane Smith
date: 2024-01-15
---

# Or with more detail:
---
title: Python Tips
author:
  name: Jane Smith
  email: jane@example.com
  bio: Python enthusiast
date: 2024-01-15
---
```

---

## Scenario 2: Documentation Site with Categories

### Site Structure
```
content/
  docs/
    getting-started/
      installation.md           # category: setup
      configuration.md          # category: setup
    guides/
      authentication.md         # category: security
      authorization.md          # category: security
      database.md              # category: data
    api/
      rest-api.md              # category: api
      graphql.md               # category: api
```

### Current Approach (Complex Logic)

```jinja2
{# templates/docs-sidebar.html - Category-based navigation #}
<aside class="sidebar">
  {% set categories = {} %}

  {# Step 1: Build category map - O(n) #}
  {% for page in site.pages %}
    {% if page.section == 'docs' %}
      {% set cat = page.metadata.category | default('uncategorized') %}
      {% if cat not in categories %}
        {% set _ = categories.update({cat: []}) %}
      {% endif %}
      {% set _ = categories[cat].append(page) %}
    {% endif %}
  {% endfor %}

  {# Step 2: Render categories #}
  {% for category, pages in categories.items() | sort %}
    <div class="category">
      <h3>{{ category | title }}</h3>
      <ul>
        {% for page in pages | sort(attribute='title') %}
          <li><a href="{{ url_for(page) }}">{{ page.title }}</a></li>
        {% endfor %}
      </ul>
    </div>
  {% endfor %}
</aside>
```

**Problems:**
- Runs on EVERY page render
- O(n) iteration per page
- Sorting happens at render time
- No caching between pages

**Performance:** 5K docs pages × 5K pages to scan = **25M operations** over full site build

### With Indexes

```jinja2
{# templates/docs-sidebar.html - Same output, pre-computed #}
<aside class="sidebar">
  {% set categories = ['setup', 'security', 'data', 'api'] %}

  {% for category in categories %}
    <div class="category">
      <h3>{{ category | title }}</h3>
      <ul>
        {# O(1) lookup per category #}
        {% set cat_pages = site.indexes.category.get(category) | resolve_pages %}
        {% for page in cat_pages | sort(attribute='title') %}
          <li>
            <a href="{{ url_for(page) }}"
               {% if page.url == current_page.url %}class="active"{% endif %}>
              {{ page.title }}
            </a>
          </li>
        {% endfor %}
      </ul>
    </div>
  {% endfor %}
</aside>
```

**Performance:** 4 categories × O(1) lookup = **4 operations** (6,250,000x faster!)

### Dynamic Category Discovery

```jinja2
{# Don't hardcode categories - discover them #}
{% set all_categories = site.indexes.category.keys() | sort %}

{% for category in all_categories %}
  {# ... same as above ... #}
{% endfor %}
```

---

## Scenario 3: Multi-Language Documentation

### Site Structure
```
content/
  en/
    docs/getting-started.md     # lang: en
    blog/python-tips.md         # lang: en
  es/
    docs/getting-started.md     # lang: es, translation_key: docs/getting-started
    blog/python-tips.md         # lang: es, translation_key: blog/python-tips
  fr/
    docs/getting-started.md     # lang: fr, translation_key: docs/getting-started
```

### Current Approach (Expensive)

```jinja2
{# templates/language-switcher.html #}
<div class="language-switcher">
  {% set current_key = page.translation_key %}

  {# Find all translations of current page - O(n) scan #}
  {% set translations = [] %}
  {% for p in site.pages %}
    {% if p.translation_key == current_key and p.lang != page.lang %}
      {% set _ = translations.append(p) %}
    {% endif %}
  {% endfor %}

  {% for translation in translations %}
    <a href="{{ url_for(translation) }}" hreflang="{{ translation.lang }}">
      {{ translation.lang | upper }}
    </a>
  {% endfor %}
</div>
```

**Performance:** O(n) per page = **10M operations** on 10K multilingual site

### With Custom TranslationIndex

```python
# mysite/indexes/translation_index.py

class TranslationIndex(QueryIndex):
    """Index pages by translation key."""

    def __init__(self, cache_path):
        super().__init__('translation', cache_path)

    def extract_keys(self, page):
        key = page.metadata.get('translation_key') or page.translation_key
        if key:
            return [(key, {'lang': page.lang or 'en'})]
        return []
```

```python
# Register in bengal.toml or code
site.indexes.register('translation', TranslationIndex(...))
```

```jinja2
{# templates/language-switcher.html - O(1) lookup #}
<div class="language-switcher">
  {# O(1) hash lookup by translation key #}
  {% set translation_paths = site.indexes.translation.get(page.translation_key) %}
  {% set translations = translation_paths | resolve_pages %}

  {% for translation in translations %}
    {% if translation.lang != page.lang %}
      <a href="{{ url_for(translation) }}" hreflang="{{ translation.lang }}">
        {{ translation.lang | upper }}
      </a>
    {% endif %}
  {% endfor %}
</div>
```

**Performance:** O(1) per page = **10K operations** (1000x faster!)

---

## Scenario 4: Recipe Site with Multiple Taxonomies

### Site Structure
```yaml
# content/recipes/chocolate-cake.md
---
title: Chocolate Cake
category: dessert
cuisine: american
difficulty: medium
cook_time: 60
dietary: [vegetarian, gluten-free-option]
season: [fall, winter]
---
```

### Use Case: Complex Recipe Browser

#### Current Approach (Multiple O(n) Scans)

```jinja2
{# templates/recipe-browser.html #}
<div class="filters">
  {# Category filter #}
  <select name="category">
    {% for recipe in site.pages %}  {# O(n) scan 1 #}
      {# ... extract unique categories ... #}
    {% endfor %}
  </select>

  {# Cuisine filter #}
  <select name="cuisine">
    {% for recipe in site.pages %}  {# O(n) scan 2 #}
      {# ... extract unique cuisines ... #}
    {% endfor %}
  </select>

  {# Difficulty filter #}
  <select name="difficulty">
    {% for recipe in site.pages %}  {# O(n) scan 3 #}
      {# ... extract unique difficulties ... #}
    {% endfor %}
  </select>
</div>

{# Show filtered results #}
{% set filtered = [] %}
{% for recipe in site.pages %}  {# O(n) scan 4 #}
  {% if (not filter_category or recipe.category == filter_category) and
        (not filter_cuisine or recipe.cuisine == filter_cuisine) %}
    {% set _ = filtered.append(recipe) %}
  {% endif %}
{% endfor %}
```

**Performance:** 4 × O(n) scans = **40K operations** on 10K recipes

#### With Multiple Indexes

```python
# mysite/indexes/recipe_indexes.py

class CategoryIndex(QueryIndex):
    def extract_keys(self, page):
        if page.section == 'recipes':
            category = page.metadata.get('category')
            return [(category, {})] if category else []
        return []

class CuisineIndex(QueryIndex):
    def extract_keys(self, page):
        if page.section == 'recipes':
            cuisine = page.metadata.get('cuisine')
            return [(cuisine, {})] if cuisine else []
        return []

class DifficultyIndex(QueryIndex):
    def extract_keys(self, page):
        if page.section == 'recipes':
            difficulty = page.metadata.get('difficulty', 'medium')
            return [(difficulty, {})]
        return []

class CookTimeIndex(QueryIndex):
    def extract_keys(self, page):
        if page.section == 'recipes':
            time = page.metadata.get('cook_time', 0)
            # Bucket by time ranges
            if time < 30:
                return [('quick', {'max': 30})]
            elif time < 60:
                return [('medium', {'max': 60})]
            else:
                return [('long', {'max': 999})]
        return []
```

```jinja2
{# templates/recipe-browser.html - All O(1) lookups #}
<div class="filters">
  {# Category filter - O(1) to get all categories #}
  <select name="category">
    {% for cat in site.indexes.category.keys() | sort %}
      <option value="{{ cat }}">{{ cat | title }}</option>
    {% endfor %}
  </select>

  {# Cuisine filter - O(1) to get all cuisines #}
  <select name="cuisine">
    {% for cuisine in site.indexes.cuisine.keys() | sort %}
      <option value="{{ cuisine }}">{{ cuisine | title }}</option>
    {% endfor %}
  </select>

  {# Difficulty filter #}
  <select name="difficulty">
    {% for diff in ['easy', 'medium', 'hard'] %}
      <option value="{{ diff }}">{{ diff | title }}</option>
    {% endfor %}
  </select>

  {# Cook time filter #}
  <select name="cook_time">
    {% for time in ['quick', 'medium', 'long'] %}
      <option value="{{ time }}">{{ time | title }}</option>
    {% endfor %}
  </select>
</div>

{# Show filtered results - O(1) lookups #}
{% if filter_category %}
  {% set filtered = site.indexes.category.get(filter_category) | resolve_pages %}
{% elif filter_cuisine %}
  {% set filtered = site.indexes.cuisine.get(filter_cuisine) | resolve_pages %}
{% elif filter_cook_time %}
  {% set filtered = site.indexes.cook_time.get(filter_cook_time) | resolve_pages %}
{% else %}
  {% set filtered = site.pages | where('section', 'recipes') %}
{% endif %}

{# Further client-side filtering with JavaScript for multi-select #}
<div class="recipes" data-recipes="{{ filtered | jsonify }}">
  {% for recipe in filtered | sort(attribute='title') %}
    <div class="recipe-card"
         data-category="{{ recipe.category }}"
         data-cuisine="{{ recipe.cuisine }}"
         data-difficulty="{{ recipe.difficulty }}">
      <h3>{{ recipe.title }}</h3>
      <p>{{ recipe.description }}</p>
    </div>
  {% endfor %}
</div>
```

**Performance:** 4 × O(1) lookups = **4 operations** (10,000x faster!)

---

## Scenario 5: Technical Blog with Series

### Site Structure
```yaml
# content/blog/django-tutorial-part-1.md
---
title: Django Tutorial - Part 1
series: django-tutorial
series_order: 1
---

# content/blog/django-tutorial-part-2.md
---
title: Django Tutorial - Part 2
series: django-tutorial
series_order: 2
---
```

### Current Approach (Complex Navigation)

```jinja2
{# templates/post.html - Show series navigation #}
{% if page.metadata.series %}
  <div class="series-navigation">
    <h3>Part of: {{ page.metadata.series | title }}</h3>

    {# Find all posts in series - O(n) #}
    {% set series_posts = [] %}
    {% for post in site.pages %}
      {% if post.metadata.series == page.metadata.series %}
        {% set _ = series_posts.append(post) %}
      {% endif %}
    {% endfor %}

    {# Sort by order #}
    {% set series_posts = series_posts | sort(attribute='metadata.series_order') %}

    <ol>
      {% for post in series_posts %}
        <li>
          {% if post.url == page.url %}
            <strong>{{ post.title }}</strong> (current)
          {% else %}
            <a href="{{ url_for(post) }}">{{ post.title }}</a>
          {% endif %}
        </li>
      {% endfor %}
    </ol>

    {# Previous/Next links #}
    {% set current_idx = series_posts.index(page) %}
    {% if current_idx > 0 %}
      <a href="{{ url_for(series_posts[current_idx - 1]) }}">← Previous</a>
    {% endif %}
    {% if current_idx < series_posts | length - 1 %}
      <a href="{{ url_for(series_posts[current_idx + 1]) }}">Next →</a>
    {% endif %}
  </div>
{% endif %}
```

**Performance:** O(n) per post with series = expensive on large sites

### With SeriesIndex

```python
# mysite/indexes/series_index.py

class SeriesIndex(QueryIndex):
    def extract_keys(self, page):
        series = page.metadata.get('series')
        if series:
            order = page.metadata.get('series_order', 0)
            return [(series, {'order': order, 'title': page.title})]
        return []
```

```jinja2
{# templates/post.html - O(1) series lookup #}
{% if page.metadata.series %}
  {% set series_name = page.metadata.series %}
  {% set series_posts = site.indexes.series.get(series_name) | resolve_pages %}
  {% set series_posts = series_posts | sort(attribute='metadata.series_order') %}

  <div class="series-navigation">
    <h3>Part of: {{ series_name | title }}</h3>

    <ol>
      {% for post in series_posts %}
        <li>
          {% if post.url == page.url %}
            <strong>{{ post.title }}</strong> (current)
          {% else %}
            <a href="{{ url_for(post) }}">{{ post.title }}</a>
          {% endif %}
        </li>
      {% endfor %}
    </ol>

    {# Previous/Next with O(1) lookup #}
    {% set current_order = page.metadata.series_order %}
    {% set prev = series_posts | selectattr('metadata.series_order', 'eq', current_order - 1) | first %}
    {% set next = series_posts | selectattr('metadata.series_order', 'eq', current_order + 1) | first %}

    <nav class="series-nav">
      {% if prev %}
        <a href="{{ url_for(prev) }}" class="prev">← {{ prev.title }}</a>
      {% endif %}
      {% if next %}
        <a href="{{ url_for(next) }}" class="next">{{ next.title }} →</a>
      {% endif %}
    </nav>
  </div>
{% endif %}
```

**Performance:** O(1) lookup + O(k) sort where k = posts in series (typically 5-10)

---

## Scenario 6: Job Board / Listings Site

### Site Structure
```yaml
# content/jobs/senior-python-dev.md
---
title: Senior Python Developer
company: TechCorp
location: San Francisco, CA
remote: true
job_type: full-time
experience_level: senior
salary_range: 150k-200k
posted_date: 2024-10-01
tags: [python, django, postgresql]
---
```

### Multiple Indexes for Job Search

```python
# mysite/indexes/job_indexes.py

class LocationIndex(QueryIndex):
    """Index by location."""
    def extract_keys(self, page):
        if page.section == 'jobs':
            location = page.metadata.get('location')
            return [(location, {})] if location else []
        return []

class RemoteIndex(QueryIndex):
    """Index by remote/hybrid/onsite."""
    def extract_keys(self, page):
        if page.section == 'jobs':
            if page.metadata.get('remote'):
                return [('remote', {})]
            elif page.metadata.get('hybrid'):
                return [('hybrid', {})]
            else:
                return [('onsite', {})]
        return []

class ExperienceIndex(QueryIndex):
    """Index by experience level."""
    def extract_keys(self, page):
        if page.section == 'jobs':
            level = page.metadata.get('experience_level', 'mid')
            return [(level, {})]
        return []

class SalaryRangeIndex(QueryIndex):
    """Index by salary range buckets."""
    def extract_keys(self, page):
        if page.section == 'jobs':
            salary = page.metadata.get('salary_range', '')
            # Parse "150k-200k" format
            if 'k' in salary.lower():
                min_salary = int(salary.split('-')[0].replace('k', '').strip())
                if min_salary < 75:
                    return [('entry', {'max': 75})]
                elif min_salary < 125:
                    return [('mid', {'max': 125})]
                else:
                    return [('senior', {'max': 999})]
        return []
```

### Job Search Template

```jinja2
{# templates/jobs-search.html #}
<form class="job-filters">
  <div class="filter-group">
    <label>Location</label>
    <select name="location">
      <option value="">All Locations</option>
      {% for loc in site.indexes.location.keys() | sort %}
        <option value="{{ loc }}">{{ loc }}</option>
      {% endfor %}
    </select>
  </div>

  <div class="filter-group">
    <label>Work Type</label>
    <select name="remote">
      <option value="">All</option>
      {% for type in ['remote', 'hybrid', 'onsite'] %}
        <option value="{{ type }}">{{ type | title }}</option>
      {% endfor %}
    </select>
  </div>

  <div class="filter-group">
    <label>Experience Level</label>
    <select name="experience">
      <option value="">All</option>
      {% for level in ['junior', 'mid', 'senior', 'lead'] %}
        <option value="{{ level }}">{{ level | title }}</option>
      {% endfor %}
    </select>
  </div>

  <div class="filter-group">
    <label>Salary Range</label>
    <select name="salary">
      <option value="">All</option>
      {% for range in ['entry', 'mid', 'senior'] %}
        <option value="{{ range }}">{{ range | title }}</option>
      {% endfor %}
    </select>
  </div>
</form>

{# Display jobs based on filters - All O(1) lookups #}
<div class="job-listings">
  {% if filter_location %}
    {% set jobs = site.indexes.location.get(filter_location) | resolve_pages %}
  {% elif filter_remote %}
    {% set jobs = site.indexes.remote.get(filter_remote) | resolve_pages %}
  {% elif filter_experience %}
    {% set jobs = site.indexes.experience.get(filter_experience) | resolve_pages %}
  {% elif filter_salary %}
    {% set jobs = site.indexes.salary_range.get(filter_salary) | resolve_pages %}
  {% else %}
    {% set jobs = site.pages | where('section', 'jobs') %}
  {% endif %}

  {# Sort by posted date #}
  {% for job in jobs | sort(attribute='posted_date', reverse=true) %}
    <div class="job-card">
      <h3>{{ job.title }}</h3>
      <p class="company">{{ job.company }}</p>
      <p class="details">
        <span class="location">📍 {{ job.location }}</span>
        {% if job.remote %}<span class="remote">🏠 Remote</span>{% endif %}
        <span class="level">{{ job.experience_level | title }}</span>
      </p>
      <p class="salary">💰 {{ job.salary_range }}</p>
      <a href="{{ url_for(job) }}" class="apply-btn">View Job</a>
    </div>
  {% endfor %}
</div>
```

---

## Scenario 7: Academic Papers / Research Site

### Site Structure
```yaml
# content/papers/quantum-computing-2024.md
---
title: Advances in Quantum Computing
authors: [Alice Smith, Bob Jones]
publication_year: 2024
venue: ICQC 2024
research_area: quantum-computing
institution: MIT
citations: 42
peer_reviewed: true
open_access: true
---
```

### Custom Academic Indexes

```python
# mysite/indexes/academic_indexes.py

class ResearchAreaIndex(QueryIndex):
    """Index by research area."""
    def extract_keys(self, page):
        if page.section == 'papers':
            area = page.metadata.get('research_area')
            return [(area, {})] if area else []
        return []

class YearIndex(QueryIndex):
    """Index by publication year."""
    def extract_keys(self, page):
        if page.section == 'papers':
            year = page.metadata.get('publication_year')
            return [(str(year), {})] if year else []
        return []

class AuthorIndex(QueryIndex):
    """Index by authors (multi-valued)."""
    def extract_keys(self, page):
        if page.section == 'papers':
            authors = page.metadata.get('authors', [])
            # Create an entry for each author
            return [(author, {}) for author in authors]
        return []

class InstitutionIndex(QueryIndex):
    """Index by institution."""
    def extract_keys(self, page):
        if page.section == 'papers':
            inst = page.metadata.get('institution')
            return [(inst, {})] if inst else []
        return []

class CitationRangeIndex(QueryIndex):
    """Index by citation count buckets."""
    def extract_keys(self, page):
        if page.section == 'papers':
            citations = page.metadata.get('citations', 0)
            if citations < 10:
                return [('low', {'max': 10})]
            elif citations < 50:
                return [('medium', {'max': 50})]
            else:
                return [('high', {'max': 999999})]
        return []
```

### Research Portal Template

```jinja2
{# templates/research-portal.html #}
<div class="research-portal">
  <aside class="filters">
    <h3>Browse Research</h3>

    {# Research areas #}
    <div class="filter-section">
      <h4>Research Areas</h4>
      <ul>
        {% for area in site.indexes.research_area.keys() | sort %}
          {% set count = site.indexes.research_area.get(area) | length %}
          <li>
            <a href="?area={{ area }}">
              {{ area | replace('-', ' ') | title }} ({{ count }})
            </a>
          </li>
        {% endfor %}
      </ul>
    </div>

    {# Years #}
    <div class="filter-section">
      <h4>Publication Year</h4>
      <ul>
        {% for year in site.indexes.year.keys() | sort(reverse=true) %}
          {% set count = site.indexes.year.get(year) | length %}
          <li>
            <a href="?year={{ year }}">{{ year }} ({{ count }})</a>
          </li>
        {% endfor %}
      </ul>
    </div>

    {# Institutions #}
    <div class="filter-section">
      <h4>Institutions</h4>
      <ul>
        {% for inst in site.indexes.institution.keys() | sort %}
          {% set count = site.indexes.institution.get(inst) | length %}
          <li>
            <a href="?institution={{ inst }}">{{ inst }} ({{ count }})</a>
          </li>
        {% endfor %}
      </ul>
    </div>
  </aside>

  <main class="papers-list">
    {# Filter papers based on query params - All O(1) lookups #}
    {% if filter_area %}
      {% set papers = site.indexes.research_area.get(filter_area) | resolve_pages %}
      <h2>{{ filter_area | replace('-', ' ') | title }}</h2>
    {% elif filter_year %}
      {% set papers = site.indexes.year.get(filter_year) | resolve_pages %}
      <h2>Publications in {{ filter_year }}</h2>
    {% elif filter_institution %}
      {% set papers = site.indexes.institution.get(filter_institution) | resolve_pages %}
      <h2>{{ filter_institution }} Publications</h2>
    {% else %}
      {% set papers = site.pages | where('section', 'papers') %}
      <h2>All Publications</h2>
    {% endif %}

    {# Sort by citations or year #}
    {% for paper in papers | sort(attribute='citations', reverse=true) %}
      <article class="paper-card">
        <h3><a href="{{ url_for(paper) }}">{{ paper.title }}</a></h3>
        <p class="authors">
          {{ paper.authors | join(', ') }}
        </p>
        <p class="meta">
          <span class="venue">{{ paper.venue }}</span> •
          <span class="year">{{ paper.publication_year }}</span> •
          <span class="citations">📊 {{ paper.citations }} citations</span>
          {% if paper.open_access %}
            <span class="open-access">🔓 Open Access</span>
          {% endif %}
        </p>
      </article>
    {% endfor %}
  </main>
</div>
```

### Author Profile Page

```jinja2
{# templates/author-profile.html #}
<div class="author-profile">
  <h1>{{ author_name }}</h1>

  {# O(1) lookup for all papers by this author #}
  {% set author_papers = site.indexes.author.get(author_name) | resolve_pages %}
  {% set author_papers = author_papers | sort(attribute='publication_year', reverse=true) %}

  <div class="stats">
    <div class="stat">
      <span class="number">{{ author_papers | length }}</span>
      <span class="label">Publications</span>
    </div>
    <div class="stat">
      <span class="number">{{ author_papers | sum(attribute='citations') }}</span>
      <span class="label">Total Citations</span>
    </div>
    <div class="stat">
      {% set years = author_papers | map(attribute='publication_year') | unique | sort %}
      <span class="number">{{ years | first }}–{{ years | last }}</span>
      <span class="label">Active Years</span>
    </div>
  </div>

  <h2>Publications</h2>
  {% for paper in author_papers %}
    <article class="publication">
      <h3><a href="{{ url_for(paper) }}">{{ paper.title }}</a></h3>
      <p class="coauthors">
        with {{ paper.authors | reject('equalto', author_name) | join(', ') }}
      </p>
      <p class="meta">{{ paper.venue }}, {{ paper.publication_year }}</p>
    </article>
  {% endfor %}
</div>
```

---

## Performance Comparison Summary

| Scenario | Without Indexes | With Indexes | Speedup |
|----------|----------------|--------------|---------|
| Author pages (50 authors, 10K pages) | 500K ops | 50 ops | **10,000x** |
| Docs sidebar (5K docs) | 25M ops | 4 ops | **6,250,000x** |
| Language switcher (10K pages) | 10M ops | 10K ops | **1,000x** |
| Recipe browser (10K recipes) | 40K ops | 4 ops | **10,000x** |
| Series navigation | O(n) per page | O(1) + O(k) | **~100x** |
| Job search (multiple filters) | O(n) per query | O(1) per query | **1,000-10,000x** |
| Research portal | O(n) per filter | O(1) per filter | **1,000-10,000x** |

---

## Key Takeaways

1. **Indexes eliminate O(n) scans** - Most dramatic for pages with repeated queries
2. **Extensibility is powerful** - Custom indexes for domain-specific needs
3. **Template code is simpler** - No complex filtering logic
4. **Build-time computation** - Cost paid once, benefit on every render
5. **Incremental updates work** - Only rebuild affected index entries

---

## Migration Strategy

### Step 1: Identify O(n) Patterns
```bash
# Search for expensive patterns in templates
grep -r "for .* in site.pages" templates/
grep -r "{% for .*%}.*{% for" templates/  # Nested loops
```

### Step 2: Replace with Indexes
```jinja2
{# Before #}
{% for post in site.pages %}
  {% if post.author == author_name %}
    ...
  {% endif %}
{% endfor %}

{# After #}
{% set posts = site.indexes.author.get(author_name) | resolve_pages %}
{% for post in posts %}
  ...
{% endfor %}
```

### Step 3: Add Custom Indexes as Needed
```python
# Register custom indexes in bengal.toml or programmatically
```

### Step 4: Benchmark
```bash
# Before and after build times
time bengal site build
```

---

## Conclusion

The index system provides:
- ✅ **Massive performance gains** (100-10,000x faster)
- ✅ **Simpler templates** (less filtering logic)
- ✅ **Extensibility** (custom indexes for any use case)
- ✅ **Safety** (impossible to create O(n²) bugs)
- ✅ **Incremental updates** (fast builds)

Perfect fit for Bengal's performance profile and architecture!
