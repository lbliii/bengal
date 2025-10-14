---
title: "Marimo Executable Cells Demo"
description: "Interactive Python code blocks using Marimo"
weight: 100
toc: true
draft: true
---

# Marimo Executable Cells

Bengal supports executable Python code blocks using [Marimo](https://marimo.io/), a reactive notebook system.

```{note}
**Marimo is an optional dependency.** Install with `pip install marimo` to enable executable Python cells.

The `{marimo}` directive is only available when Marimo is installed. Without it, this page will show placeholder content.
```

## Basic Example

```{marimo}
import pandas as pd

# Create sample data
data = pd.DataFrame({
    'product': ['Widget A', 'Widget B', 'Widget C'],
    'sales': [150, 230, 180],
    'profit': [45, 69, 54]
})

data
```

## With Visualization

```{marimo}
import matplotlib.pyplot as plt
import numpy as np

# Generate data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(10, 4))
plt.plot(x, y, 'b-', linewidth=2)
plt.title('Sine Wave')
plt.xlabel('X')
plt.ylabel('sin(X)')
plt.grid(True, alpha=0.3)
plt.tight_layout()
```

## Hide Source Code

You can hide the code and only show outputs:

```{marimo}
:show-code: false

import pandas as pd

# Sales summary
summary = {
    'Total Sales': '$42,500',
    'Avg Order': '$127',
    'Top Product': 'Widget B'
}

pd.DataFrame([summary])
```

## With Labels

Label cells for caching and cross-references:

```{marimo}
:label: revenue-calculation
:show-code: true

revenue = 150 + 230 + 180
profit_margin = (45 + 69 + 54) / revenue

print(f"Total Revenue: ${revenue}")
print(f"Profit Margin: {profit_margin:.1%}")
```

## Multiple Cells in Sequence

Cells maintain execution context within a page:

```{marimo}
# Load data
import pandas as pd
sales_data = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar'],
    'revenue': [10000, 12000, 11500]
})
print("Data loaded")
```

```{marimo}
# Analyze data (uses sales_data from previous cell)
total = sales_data['revenue'].sum()
average = sales_data['revenue'].mean()

print(f"Total: ${total:,}")
print(f"Average: ${average:,.2f}")
```

## Complex Analysis

```{marimo}
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Generate sample time series data
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=90, freq='D')
values = 100 + np.cumsum(np.random.randn(90) * 5)

df = pd.DataFrame({
    'date': dates,
    'value': values
})

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# Time series
ax1.plot(df['date'], df['value'], 'b-', linewidth=2)
ax1.set_title('Time Series Data')
ax1.set_xlabel('Date')
ax1.set_ylabel('Value')
ax1.grid(True, alpha=0.3)

# Distribution
ax2.hist(df['value'], bins=20, color='skyblue', edgecolor='black', alpha=0.7)
ax2.set_title('Value Distribution')
ax2.set_xlabel('Value')
ax2.set_ylabel('Frequency')
ax2.grid(True, alpha=0.3)

plt.tight_layout()

# Summary statistics
print(f"Mean: {df['value'].mean():.2f}")
print(f"Std Dev: {df['value'].std():.2f}")
print(f"Min: {df['value'].min():.2f}")
print(f"Max: {df['value'].max():.2f}")
```

## Use Cases

### Data Analysis

Perfect for embedding live data analysis in documentation:

- Load and explore datasets
- Show transformation steps
- Visualize results
- All in one page!

### API Examples

Show actual API responses:

```{marimo}
:show-code: true

# Simulate API response
api_response = {
    "status": "success",
    "data": {
        "users": 1247,
        "active": 892,
        "new_today": 23
    },
    "timestamp": "2024-10-14T10:30:00Z"
}

import json
print(json.dumps(api_response, indent=2))
```

### Tutorial Content

Interactive tutorials with live code:

1. Show concept
2. Execute code
3. See results
4. Experiment!

## Tips

- **Use `show-code: false`** for cleaner output-focused displays
- **Add labels** to cells you want to cache or reference
- **Break complex analysis** into multiple cells for clarity
- **Show both code and output** for educational content

## More Information

- [Marimo Documentation](https://docs.marimo.io/)
- [Marimo Islands Guide](https://docs.marimo.io/guides/exporting/)
- [Bengal Marimo Support](/docs/features/marimo)
