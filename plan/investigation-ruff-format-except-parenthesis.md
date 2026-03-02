# Investigation: Ruff Format "Corrupting" except (A, B) Syntax

## Summary

**Root cause:** Ruff 0.15+ with `target-version = "py314"` applies **PEP 758** formatting: it converts `except (KeyboardInterrupt, SystemExit):` to `except KeyboardInterrupt, SystemExit:`. This is **valid Python 3.14**, not a bug.

The "Files were modified by following hooks" loop occurs because:
1. You commit with parenthesized syntax
2. Ruff format runs and converts to PEP 758 style
3. Pre-commit aborts (files changed)
4. Prek restores its stash (if any unstaged changes existed)
5. The restore can overwrite or conflict with ruff's output

---

## PEP 758 (Python 3.14)

[PEP 758](https://peps.python.org/pep-0758/) allows unparenthesized `except` when catching multiple exceptions **without** the `as` clause:

```python
# Both valid in Python 3.14:
except (KeyboardInterrupt, SystemExit):   # Old style (still valid)
except KeyboardInterrupt, SystemExit:    # New style (PEP 758)
```

Ruff 0.15.0+ with `target-version = "py314"` formats to the new style per the 2026 style guide. Your `pyproject.toml` has:

```toml
[tool.ruff]
target-version = "py314"
```

So ruff is behaving correctly.

---

## Why the Commit Loop Happens

1. **Prek stash:** Before hooks run, prek stashes unstaged changes to `/Users/llane/.cache/prek/patches/*.patch`
2. **Hooks run:** Ruff format modifies staged files in place
3. **Abort:** Pre-commit sees "Files were modified" and aborts the commit
4. **Restore:** Prek restores the stash

**Conflict scenario:** If the stash contained changes to the same file ruff modified, the restore applies the stash on top of ruff's output. Depending on overlap, you can get:
- Merge conflicts
- Stash content overwriting ruff's formatting
- Inconsistent state (e.g. some lines from stash, some from ruff)

---

## Options

### A. Accept PEP 758 (Recommended)

The new syntax is valid and will become standard. No config change needed.

**Workflow fix:** Run format before committing so hooks don't need to modify:

```bash
poe format   # or: ruff format .
git add -A
git commit -m "..."
```

### B. Keep Parenthesized Style

If you prefer `except (A, B):` for readability or compatibility with older tooling:

**Option B1 – Ruff skip magic comment (per-file):**
```python
# fmt: off
except (KeyboardInterrupt, SystemExit):
# fmt: on
```
Not ideal; clutters code.

**Option B2 – Downgrade ruff** to pre-0.15 (loses other fixes; not recommended).

**Option B3 – Ruff config:** Check if ruff has a format option to preserve exception parentheses. As of 0.15.1, the formatter follows PEP 758 for py314; there may not be a toggle.

### C. Fix the Prek Restore Loop

The real pain is the commit → abort → restore cycle. Mitigations:

1. **Always format before commit:** Add to your workflow or a pre-commit script that runs `ruff format` before the actual commit hook.
2. **When hooks modify:** Run `git add -A && git commit -m "..."` again. The second commit should pass (ruff won't change already-formatted code).
3. **Prek issue:** If prek's stash/restore is overwriting hook output, consider filing an issue with prek or using standard pre-commit for the ruff hooks.

---

## Recommended Actions

1. **Update python.mdc** (or a docs note): Document that `except A, B` (no parens) is valid Python 3.14 per PEP 758 and that ruff formats to this style.
2. **Workflow:** Run `poe format` before committing, or re-add and commit when "Files were modified" appears.
3. **Stop using `--no-verify`:** The "corruption" was valid code; the loop is a workflow issue, not a ruff bug.

---

## References

- [PEP 758 – Allow except and except* expressions without parentheses](https://peps.python.org/pep-0758/)
- [Ruff v0.15.0](https://astral.sh/blog/ruff-v0.15.0) – PEP 758 support
- [Ruff 0.15.1](https://newreleases.io/project/pypi/ruff/release/0.15.1) – Exception handler parenthesis fix
- [Ruff #23090](https://github.com/astral-sh/ruff/issues/23090) – Same symptom; closed as not-a-bug (PEP 758 is valid in 3.14)
- `pyproject.toml` line 197: `"ruff>=0.15.1", # 0.15.1+ fixes except-parenthesis bug (PEP 758 + as clause)`
