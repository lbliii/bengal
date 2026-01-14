# Golden File Tests

Golden file tests verify that Bengal produces consistent, expected output across builds and releases.

## Structure

```
tests/golden/
├── README.md
├── simple_site/
│   ├── input/           # Source files (bengal.toml, content/)
│   │   ├── bengal.toml
│   │   └── content/
│   │       ├── _index.md
│   │       └── about.md
│   └── expected/        # Expected output (normalized HTML)
│       ├── index.html
│       └── about/index.html
├── blog_site/
│   └── ...
└── taxonomy_site/
    └── ...
```

## Running Golden Tests

```bash
# Run all golden tests
pytest tests/integration/test_golden_output.py -v

# Update golden files after intentional changes
pytest tests/integration/test_golden_output.py --update-golden
```

## How It Works

1. **Input**: Each scenario has an `input/` directory with a complete Bengal site
2. **Build**: Tests copy the input to a temp directory and run `site.build()`
3. **Normalize**: Output HTML is normalized to remove volatile content:
   - Build timestamps
   - Content hashes in asset URLs
   - Non-essential whitespace
4. **Compare**: Normalized output is compared against `expected/` files

## Adding New Scenarios

1. Create a new directory under `tests/golden/` (e.g., `blog_site/`)
2. Add `input/bengal.toml` and `input/content/` files
3. Run with `--update-golden` to generate expected output
4. Review the generated files before committing

## Normalization Rules

The following patterns are normalized during comparison:

- `data-build-time="..."` → `data-build-time=""`
- `data-build-timestamp="..."` → `data-build-timestamp=""`
- `.a1b2c3d4.css` (content hashes) → `.HASH.css`
- Multiple whitespace → single space

## When to Use Golden Tests

- **Use for**: Output correctness, rendering behavior, template changes
- **Not for**: Performance, error handling, edge cases (use unit/integration tests)

## Maintaining Golden Files

When making intentional changes to Bengal's output:

1. Make the code change
2. Run `pytest tests/integration/test_golden_output.py --update-golden`
3. Review the diff in `expected/` files
4. Commit both the code change and updated golden files
