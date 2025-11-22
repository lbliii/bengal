# profile

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/profile.py

Build profile system for persona-based observability.

Provides three profiles optimized for different user workflows:
- Writer: Fast, clean builds for content authors
- Theme Developer: Template-focused debugging for theme builders
- Developer: Full observability for framework contributors

Example:
    from bengal.utils.profile import BuildProfile

    profile = BuildProfile.from_cli_args(dev=True)
    config = profile.get_config()

    if config['track_memory']:
        # Enable memory tracking
        pass

*Note: Template has undefined variables. This is fallback content.*
