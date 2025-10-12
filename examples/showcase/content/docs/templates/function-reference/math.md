---
title: "Math Functions"
description: "6 mathematical functions for calculations and number formatting"
date: 2025-10-04
weight: 3
tags: ["templates", "functions", "math", "calculations"]
toc: true
---

# Math Functions

Bengal provides **6 essential math functions** for calculations and number formatting in templates. Perfect for statistics, progress bars, pricing, and any numeric displays.

---

## 📚 Function Overview

| Function | Purpose | Example |
|----------|---------|---------|
| `percentage` | Calculate percentage | `{{ part | percentage(total, 1) }}%` |
| `times` | Multiply numbers | `{{ price | times(1.1) }}` |
| `divided_by` | Divide numbers | `{{ total | divided_by(count) }}` |
| `ceil` | Round up | `{{ 4.2 | ceil }}` |
| `floor` | Round down | `{{ 4.9 | floor }}` |
| `round` | Round to decimals | `{{ 3.14159 | round(2) }}` |

---

## 📊 percentage

Calculate percentage with formatting.

### Signature

```jinja2
{{ part | percentage(total, decimals=0) }}
```

### Parameters

- **part** (number): Part value (numerator)
- **total** (number): Total value (denominator)
- **decimals** (int, optional): Decimal places to show. Default: `0`

### Returns

Formatted percentage string with `%` sign (e.g., `"75%"`, `"87.50%"`).

### Examples

#### Basic Percentage

```jinja2
{# Show completion percentage #}
<div class="progress">
  {{ completed | percentage(total_tasks) }} complete
</div>
```

**Example:**
- `completed = 15`, `total_tasks = 20`
- Output: `"75% complete"`

#### With Decimal Places

```jinja2
{# Show score with precision #}
<div class="score">
  Score: {{ points | percentage(max_points, 2) }}
</div>
```

**Example:**
- `points = 87.5`, `max_points = 100`
- Output: `"Score: 87.50%"`

#### Progress Bar

```jinja2
{# Visual progress bar #}
{% set progress = pages_built | percentage(total_pages, 0) %}

<div class="progress-bar">
  <div class="progress-fill" style="width: {{ progress }}">
    <span>{{ progress }}</span>
  </div>
</div>
```

**Result:**
```html
<div class="progress-bar">
  <div class="progress-fill" style="width: 75%">
    <span>75%</span>
  </div>
</div>
```

#### Statistics Dashboard

```jinja2
<div class="stats">
  <div class="stat">
    <span class="label">Pass Rate</span>
    <span class="value">{{ passed | percentage(total, 1) }}</span>
  </div>

  <div class="stat">
    <span class="label">Test Coverage</span>
    <span class="value">{{ covered_lines | percentage(total_lines, 2) }}</span>
  </div>

  <div class="stat">
    <span class="label">Success Rate</span>
    <span class="value">{{ successful | percentage(attempts, 0) }}</span>
  </div>
</div>
```

### Edge Cases

```{warning} Division by Zero
If `total` is 0, returns `"0%"` to avoid division errors:

```jinja2
{{ 10 | percentage(0) }}  {# Returns "0%" (not error) #}
```

Always safe to use, even with zero denominators!
```

### Real-World Examples

```{example} Build Progress

```jinja2
{# Show build statistics #}
<div class="build-stats">
  <h3>Build Progress</h3>

  <p>
    Built {{ pages_complete }} of {{ total_pages }} pages
    ({{ pages_complete | percentage(total_pages) }})
  </p>

  <p>
    Cache hit rate: {{ cache_hits | percentage(total_requests, 1) }}
  </p>

  <p>
    Test coverage: {{ covered | percentage(total, 2) }}
  </p>
</div>
```

**Output:**
```
Built 147 of 200 pages (74%)
Cache hit rate: 94.2%
Test coverage: 87.50%
```
```

---

## ✖️ times

Multiply a value by a multiplier.

### Signature

```jinja2
{{ value | times(multiplier) }}
```

### Parameters

- **value** (number): Value to multiply
- **multiplier** (number): Multiplier

### Returns

Product of `value * multiplier`.

### Examples

#### Add Tax

```jinja2
{# Add 10% tax to price #}
<div class="price">
  <span class="subtotal">${{ price }}</span>
  <span class="total">${{ price | times(1.1) | round(2) }}</span>
</div>
```

**Example:**
- `price = 99.99`
- `price | times(1.1)` = `109.989`
- With `round(2)` = `$109.99`

#### Scale Values

```jinja2
{# Convert units #}
<p>Distance: {{ miles | times(1.60934) | round(2) }} km</p>
<p>Temperature: {{ fahrenheit | times(0.5556) | round(1) }}°C</p>
```

#### Bulk Calculations

```jinja2
{# Calculate total for quantity #}
{% for item in cart %}
  <tr>
    <td>{{ item.name }}</td>
    <td>{{ item.quantity }}</td>
    <td>${{ item.price }}</td>
    <td>${{ item.price | times(item.quantity) | round(2) }}</td>
  </tr>
{% endfor %}
```

#### Grid Layout

```jinja2
{# Calculate column width #}
{% set column_width = 100 | divided_by(columns) %}

<div class="grid">
  {% for item in items %}
    <div style="width: {{ column_width }}%">
      {{ item.title }}
    </div>
  {% endfor %}
</div>
```

### Practical Uses

````{tabs}
:id: times-uses

### Tab: Pricing

```jinja2
{# Price calculations #}
Base: ${{ base_price }}
With discount: ${{ base_price | times(0.8) }}  {# 20% off #}
With markup: ${{ cost | times(1.5) }}  {# 50% markup #}
```

### Tab: Conversions

```jinja2
{# Unit conversions #}
{{ inches | times(2.54) }} cm
{{ pounds | times(0.453592) }} kg
{{ gallons | times(3.78541) }} liters
```

### Tab: Scaling

```jinja2
{# Scale dimensions #}
{% set scale = 1.5 %}
width: {{ original_width | times(scale) }}px
height: {{ original_height | times(scale) }}px
```
````

---

## ➗ divided_by

Divide a value by a divisor.

### Signature

```jinja2
{{ value | divided_by(divisor) }}
```

### Parameters

- **value** (number): Value to divide (dividend)
- **divisor** (number): Divisor

### Returns

Quotient of `value / divisor` (returns `0` if divisor is `0`).

### Examples

#### Calculate Average

```jinja2
{# Average post length #}
{% set total_words = posts | map(attribute='word_count') | sum %}
{% set avg_words = total_words | divided_by(posts | length) | round(0) %}

<p>Average post length: {{ avg_words }} words</p>
```

#### Time Conversions

```jinja2
{# Convert seconds to minutes #}
<p>Duration: {{ seconds | divided_by(60) | round(1) }} minutes</p>

{# Convert seconds to hours #}
<p>Time: {{ seconds | divided_by(3600) | round(2) }} hours</p>
```

#### Pagination Math

```jinja2
{# Calculate total pages #}
{% set page_size = 10 %}
{% set total_pages = (items | length) | divided_by(page_size) | ceil %}

<p>Showing page 1 of {{ total_pages }}</p>
```

#### Grid Columns

```jinja2
{# Equal width columns #}
{% set columns = 3 %}
{% set column_width = 100 | divided_by(columns) %}

<div class="column" style="width: {{ column_width }}%">
  ...
</div>
```

### Division by Zero

```{note} Safe Division
Returns `0` if divisor is `0` (no error thrown):

```jinja2
{{ 100 | divided_by(0) }}  {# Returns 0 (safe) #}
```

If you need different behavior, check first:
```jinja2
{% if divisor > 0 %}
  {{ value | divided_by(divisor) }}
{% else %}
  N/A
{% endif %}
```
```

### Combine with Rounding

```{example} Practical Division

```jinja2
{# Calculate metrics with proper formatting #}
<div class="metrics">
  {# Words per post (no decimals) #}
  <div>
    {{ total_words | divided_by(post_count) | round(0) }} words/post
  </div>

  {# Average reading time (1 decimal) #}
  <div>
    {{ total_minutes | divided_by(post_count) | round(1) }} min/post
  </div>

  {# Bytes to MB (2 decimals) #}
  <div>
    {{ bytes | divided_by(1048576) | round(2) }} MB
  </div>
</div>
```
```

---

## ⬆️ ceil

Round up to nearest integer.

### Signature

```jinja2
{{ value | ceil }}
```

### Parameters

- **value** (number): Value to round up

### Returns

Ceiling value (smallest integer ≥ value).

### Examples

#### Round Up Pages

```jinja2
{# Calculate number of pages needed #}
{% set items_per_page = 10 %}
{% set total_pages = (items | length) | divided_by(items_per_page) | ceil %}

<p>{{ total_pages }} pages needed</p>
```

**Example:**
- 23 items ÷ 10 = 2.3
- `ceil` = 3 pages (need 3 pages to show all items)

#### Bulk Pricing

```jinja2
{# Items sold in packs of 6 #}
{% set packs_needed = quantity | divided_by(6) | ceil %}

<p>
  {{ quantity }} items requires {{ packs_needed }} packs
  ({{ packs_needed | times(6) }} total items)
</p>
```

#### Time Estimates

```jinja2
{# Round up to next minute #}
{% set minutes = seconds | divided_by(60) | ceil %}
<p>Estimated time: {{ minutes }} minutes</p>
```

### Ceil vs Round vs Floor

````{tabs}
:id: rounding-comparison

### Tab: ceil (Round Up)

```jinja2
{{ 4.1 | ceil }}  {# 5 #}
{{ 4.5 | ceil }}  {# 5 #}
{{ 4.9 | ceil }}  {# 5 #}
{{ 5.0 | ceil }}  {# 5 #}
```

**Use when:** Need whole units, prefer over-estimate

### Tab: floor (Round Down)

```jinja2
{{ 4.1 | floor }}  {# 4 #}
{{ 4.5 | floor }}  {# 4 #}
{{ 4.9 | floor }}  {# 4 #}
{{ 5.0 | floor }}  {# 5 #}
```

**Use when:** Need whole units, prefer under-estimate

### Tab: round (Nearest)

```jinja2
{{ 4.1 | round }}  {# 4 #}
{{ 4.5 | round }}  {# 5 (rounds up at .5) #}
{{ 4.9 | round }}  {# 5 #}
{{ 5.0 | round }}  {# 5 #}
```

**Use when:** Want most accurate whole number
````

---

## ⬇️ floor

Round down to nearest integer.

### Signature

```jinja2
{{ value | floor }}
```

### Parameters

- **value** (number): Value to round down

### Returns

Floor value (largest integer ≤ value).

### Examples

#### Completed Items

```jinja2
{# Show only fully completed items #}
{% set completed = progress | times(total) | divided_by(100) | floor %}

<p>{{ completed }} of {{ total }} items complete</p>
```

#### Discount Calculation

```jinja2
{# Floor to avoid giving extra discount #}
{% set discount_amount = price | times(0.157) | floor %}
<p>Save ${{ discount_amount }}</p>
```

#### Pagination Current Page

```jinja2
{# Current page index (0-based) #}
{% set page_index = offset | divided_by(page_size) | floor %}
```

### When to Use Floor

```{tip} Floor Use Cases

**Good for:**
- ✅ Counting completed items
- ✅ Currency (avoid rounding up payments)
- ✅ Capacity planning (available slots)
- ✅ Quotas (used vs available)

**Example:**
```jinja2
{# Don't overcount available seats #}
{% set seats_available = capacity | times(0.8) | floor %}
{# If capacity is 100, gives 80, not 81 #}
```
```

---

## 🎯 round

Round to specified decimal places.

### Signature

```jinja2
{{ value | round(decimals=0) }}
```

### Parameters

- **value** (number): Value to round
- **decimals** (int, optional): Number of decimal places. Default: `0`

### Returns

Rounded value to specified precision.

### Examples

#### No Decimals (Integer)

```jinja2
{# Round to whole number #}
<p>Average: {{ average | round }} items</p>
```

**Example:**
- `average = 4.567`
- Output: `"Average: 5 items"`

#### Currency (2 Decimals)

```jinja2
{# Format money #}
<div class="price">${{ price | round(2) }}</div>
```

**Example:**
- `price = 19.995`
- Output: `"$20.00"`

#### Percentages (1-2 Decimals)

```jinja2
{# Show precise percentage #}
<p>Completion: {{ progress | percentage(total, 1) }}</p>
```

#### Statistics (Variable Precision)

```jinja2
<dl class="stats">
  <dt>Average Rating</dt>
  <dd>{{ avg_rating | round(1) }} / 5.0</dd>

  <dt>Response Time</dt>
  <dd>{{ response_ms | round(0) }} ms</dd>

  <dt>Success Rate</dt>
  <dd>{{ success_rate | round(2) }}%</dd>
</dl>
```

### Rounding Behavior

```{example} Standard Rounding

**Python uses "round half to even" (banker's rounding):**

```jinja2
{{ 2.5 | round }}  {# 2 (rounds to nearest even) #}
{{ 3.5 | round }}  {# 4 (rounds to nearest even) #}
{{ 4.5 | round }}  {# 4 (rounds to nearest even) #}
{{ 5.5 | round }}  {# 6 (rounds to nearest even) #}
```

**For values not exactly .5:**
```jinja2
{{ 4.4 | round }}  {# 4 (rounds down) #}
{{ 4.6 | round }}  {# 5 (rounds up) #}
```

**Most cases just round normally as expected!**
```

### Decimal Places

````{tabs}
:id: decimal-places

### Tab: 0 Decimals

```jinja2
{{ 3.14159 | round }}     {# 3 #}
{{ 2.71828 | round(0) }}  {# 3 #}
```

Whole numbers

### Tab: 1 Decimal

```jinja2
{{ 3.14159 | round(1) }}  {# 3.1 #}
{{ 2.71828 | round(1) }}  {# 2.7 #}
```

One decimal place

### Tab: 2 Decimals

```jinja2
{{ 3.14159 | round(2) }}  {# 3.14 #}
{{ 2.71828 | round(2) }}  {# 2.72 #}
```

Common for money

### Tab: 3+ Decimals

```jinja2
{{ 3.14159 | round(3) }}  {# 3.142 #}
{{ 3.14159 | round(5) }}  {# 3.14159 #}
```

Scientific precision
````

---

## 🎯 Common Patterns

### Price Display with Tax

```jinja2
<div class="pricing">
  <div class="subtotal">
    Subtotal: ${{ subtotal | round(2) }}
  </div>

  {% set tax = subtotal | times(0.0825) %}
  <div class="tax">
    Tax (8.25%): ${{ tax | round(2) }}
  </div>

  {% set total = subtotal | times(1.0825) %}
  <div class="total">
    Total: ${{ total | round(2) }}
  </div>
</div>
```

### Progress Dashboard

```jinja2
<div class="progress-dashboard">
  {# Build progress #}
  <div class="metric">
    <div class="label">Build Progress</div>
    <div class="value">
      {{ pages_built | percentage(total_pages) }}
    </div>
    <div class="bar">
      <div style="width: {{ pages_built | percentage(total_pages) }}"></div>
    </div>
  </div>

  {# Cache efficiency #}
  <div class="metric">
    <div class="label">Cache Hit Rate</div>
    <div class="value">
      {{ cache_hits | percentage(total_requests, 1) }}
    </div>
  </div>

  {# Average build time #}
  <div class="metric">
    <div class="label">Avg Build Time</div>
    <div class="value">
      {{ total_time | divided_by(num_builds) | round(2) }}s
    </div>
  </div>
</div>
```

### Pagination Calculation

```jinja2
{% set items_per_page = 20 %}
{% set total_items = posts | length %}
{% set total_pages = total_items | divided_by(items_per_page) | ceil %}

<nav class="pagination">
  <div class="info">
    Page {{ current_page }} of {{ total_pages }}
    ({{ total_items }} total items)
  </div>

  <div class="controls">
    {% if current_page > 1 %}
      <a href="?page={{ current_page - 1 }}">Previous</a>
    {% endif %}

    {% if current_page < total_pages %}
      <a href="?page={{ current_page + 1 }}">Next</a>
    {% endif %}
  </div>
</nav>
```

### Unit Conversions

```jinja2
{# File size display #}
{% set bytes = file.size %}
{% if bytes < 1024 %}
  {{ bytes }} B
{% elif bytes < 1048576 %}
  {{ bytes | divided_by(1024) | round(2) }} KB
{% elif bytes < 1073741824 %}
  {{ bytes | divided_by(1048576) | round(2) }} MB
{% else %}
  {{ bytes | divided_by(1073741824) | round(2) }} GB
{% endif %}
```

---

## 📊 Performance Stats Example

Here's a complete example combining all math functions:

```jinja2
<div class="build-stats">
  <h2>Build Statistics</h2>

  {# Basic counts #}
  <div class="stat-grid">
    <div class="stat">
      <span class="label">Total Pages</span>
      <span class="value">{{ total_pages }}</span>
    </div>

    <div class="stat">
      <span class="label">Build Time</span>
      <span class="value">{{ build_time | round(2) }}s</span>
    </div>

    <div class="stat">
      <span class="label">Pages/Second</span>
      <span class="value">
        {{ total_pages | divided_by(build_time) | round(1) }}
      </span>
    </div>
  </div>

  {# Progress bars #}
  <div class="progress-section">
    <div class="progress-item">
      <label>Cache Hit Rate</label>
      <div class="bar">
        {% set cache_rate = cache_hits | percentage(total_requests, 1) %}
        <div class="fill" style="width: {{ cache_rate }}">
          {{ cache_rate }}
        </div>
      </div>
    </div>

    <div class="progress-item">
      <label>Test Coverage</label>
      <div class="bar">
        {% set coverage = covered_lines | percentage(total_lines, 1) %}
        <div class="fill" style="width: {{ coverage }}">
          {{ coverage }}
        </div>
      </div>
    </div>
  </div>

  {# Averages #}
  <div class="averages">
    <h3>Averages</h3>

    <ul>
      <li>
        Words per page:
        {{ total_words | divided_by(total_pages) | round(0) }}
      </li>

      <li>
        Reading time:
        {{ total_words | divided_by(200) | divided_by(total_pages) | round(1) }} min
      </li>

      <li>
        Build speed improvement:
        {{ old_time | divided_by(new_time) | round(1) }}x faster
      </li>
    </ul>
  </div>
</div>
```

---

## 📚 Related Functions

- **[String Functions](strings.md)** - truncate_chars, reading_time
- **[Collection Functions](collections.md)** - length, sum
- **[Date Functions](dates.md)** - time calculations

---

## 💡 Best Practices

```{success} Always Round Currency

```jinja2
{# Good #}
${{ price | round(2) }}

{# Bad - might show $19.999999 #}
${{ price }}
```

Money should always have exactly 2 decimal places!
```

```{tip} Chain Math Operations

```jinja2
{# Calculate percentage of average #}
{% set result = value
    | divided_by(count)  # Get average
    | times(100)         # Convert to percentage
    | round(1)           # One decimal
%}

{{ result }}%
```

Operations execute left-to-right.
```

```{warning} Integer Division
Remember Python division always returns float:

```jinja2
{{ 10 | divided_by(3) }}  {# 3.333... (not 3) #}
```

Use `floor` or `ceil` if you need integer:
```jinja2
{{ 10 | divided_by(3) | floor }}  {# 3 #}
{{ 10 | divided_by(3) | ceil }}   {# 4 #}
```
```

```{note} Precision Matters
For financial calculations, round at the END:

```jinja2
{# Good #}
{% set total = subtotal | times(1.0825) | round(2) %}

{# Bad - rounds too early #}
{% set tax = subtotal | times(0.0825) | round(2) %}
{% set total = subtotal + tax %}  # Less accurate
```
```

---

**Module:** `bengal.rendering.template_functions.math_functions`  
**Functions:** 6  
**Last Updated:** October 4, 2025
