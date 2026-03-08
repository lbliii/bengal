# Bengal Agent Skills

Agent Skills for [Bengal](https://github.com/b-stack/bengal) static site generator. These skills help AI agents assist users with Bengal workflows.

Format: [Agent Skills](https://agentskills.io) (open standard).

## Skills

| Skill | Description |
|-------|-------------|
| [bengal-template-fix](bengal-template-fix/) | Fix common template errors, safe patterns, href vs path |
| [bengal-add-directive](bengal-add-directive/) | Add new MyST directives |
| [bengal-site-scaffold](bengal-site-scaffold/) | Scaffold a new Bengal site |
| [bengal-debug-build](bengal-debug-build/) | Debug build failures and validation errors |
| [bengal-content-migration](bengal-content-migration/) | Migrate content from Jekyll, Hugo, or other SSGs |
| [bengal-taxonomy](bengal-taxonomy/) | Use tags, categories, and query indexes |
| [bengal-theme-customize](bengal-theme-customize/) | Customize or extend themes |
| [bengal-add-filter](bengal-add-filter/) | Add custom Jinja/Kida filters |

## Usage

Add the `skills/` path to your agent's skill discovery. Configuration is product-specific:

- **Cursor**: Add skills to project or user skills directory
- **Claude Code**: Configure skills path in settings
- **Other agents**: See [agentskills.io/client-implementation](https://agentskills.io/client-implementation/adding-skills-support)

## Validation

Validate skills against the Agent Skills spec (if [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) is installed):

```bash
skills-ref validate ./skills/bengal-template-fix
```

## Links

- [Agent Skills](https://agentskills.io)
- [Bengal documentation](https://bengal.b-stack.dev)
- [Bengal GitHub](https://github.com/b-stack/bengal)
