# community_detection

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/analysis/community_detection.py

Community Detection for Bengal SSG.

Implements the Louvain method for discovering topical clusters in content.
The algorithm optimizes modularity to find natural groupings of pages.

The Louvain method works in two phases:
1. Local optimization: Move nodes to communities that maximize modularity gain
2. Aggregation: Treat each community as a single node and repeat

References:
    - Blondel, V. D., et al. (2008). Fast unfolding of communities in large networks.
      Journal of Statistical Mechanics: Theory and Experiment.

*Note: Template has undefined variables. This is fallback content.*
