# Bengal Error Reference

## Template Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Missing context variables: X" | Template references undefined var | Use params/config/theme, or add to context |
| "UndefinedError" | Variable not in template context | Use safe patterns (params.x, config.x) |
| href vs path wrong | Using _path for links | Use href ?? _path (href first) |

## Directive Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Unknown directive" | Directive not registered | Add to registry or fix directive name |
| "Invalid directive syntax" | Malformed ::: block | Check opening, options, closing |
| "Missing required argument" | Directive needs title/arg | Add required positional arg |

## Config Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Invalid TOML" | Syntax error in bengal.toml | Check brackets, quotes, commas |
| "content_dir not found" | Path doesn't exist | Create content/ or fix path |
| "Theme not found" | Theme name invalid | Use "default" or create themes/ |

## Build Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| Stale output | Incremental cache | Run `bengal build --full` |
| Partial build | Interrupted build | Run `bengal build` again |
| Permission denied | Output dir | Check write permissions |
