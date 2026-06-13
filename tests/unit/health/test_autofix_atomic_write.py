"""
Atomic-write guard for AutoFixer (issue #440).

AutoFixer is the one health subsystem that modifies *user* source files.
A SIGINT/crash/OOM mid-write must never leave a user's content partially
written. These tests pin the write through the crash-safe
``atomic_write_text`` (temp-file-then-atomic-rename) helper.

If either ``apply_fix`` closure regresses to a direct
``file_path.write_text(...)``, the "uses atomic helper" test stops seeing
the patched symbol and fails, and the "crash mid-write" test sees a
truncated original file and fails. The assertions are therefore
discriminating: they break if the bug is reintroduced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import bengal.health.remediation.autofix as autofix_mod
from bengal.health.remediation.autofix import AutoFixer
from bengal.health.report import HealthReport

# A nested colon-fence directive tree where every fence is depth-3, so the
# fixer must increase fence depths (a real rewrite of user content).
NESTED_MD = """# Title

:::{tab-set}

:::{tab-item} One

:::{note}
hello
:::

:::

:::
"""

TAB_SET_LINE = 3  # 1-based line of the outermost ``:::{tab-set}`` fence


def _make_page(tmp_path: Path) -> Path:
    page = tmp_path / "content" / "page.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(NESTED_MD, encoding="utf-8")
    return page


def _fixer(tmp_path: Path) -> AutoFixer:
    return AutoFixer(HealthReport(), site_root=tmp_path)


def test_fence_fix_writes_through_atomic_helper(tmp_path, monkeypatch):
    """The fence-fix write must go through ``atomic_write_text``.

    Discriminating: a regression to ``file_path.write_text`` would never
    invoke the patched module symbol, leaving ``calls`` empty.
    """
    page = _make_page(tmp_path)
    fixer = _fixer(tmp_path)

    calls: list[tuple[Path, str]] = []
    real = autofix_mod.atomic_write_text

    def spy(path, content, *args, **kwargs):
        calls.append((Path(path), content))
        return real(path, content, *args, **kwargs)

    monkeypatch.setattr(autofix_mod, "atomic_write_text", spy)

    apply_fix = fixer._create_fence_fix(page, line_number=TAB_SET_LINE)
    assert apply_fix() is True

    assert len(calls) == 1, "fence fix must write exactly once, via atomic_write_text"
    written_path, written_content = calls[0]
    assert written_path == page
    # The fix deepened a nested fence; the new content is what was written.
    assert written_content == page.read_text(encoding="utf-8")
    assert written_content != NESTED_MD


def test_file_fix_writes_through_atomic_helper(tmp_path, monkeypatch):
    """The whole-file fix path (``_create_file_fix``) is also atomic."""
    page = _make_page(tmp_path)
    fixer = _fixer(tmp_path)

    calls: list[Path] = []
    real = autofix_mod.atomic_write_text

    def spy(path, content, *args, **kwargs):
        calls.append(Path(path))
        return real(path, content, *args, **kwargs)

    monkeypatch.setattr(autofix_mod, "atomic_write_text", spy)

    apply_fix = fixer._create_file_fix(page, line_numbers=[TAB_SET_LINE])
    assert apply_fix() is True
    assert calls == [page], "whole-file fix must write exactly once, via atomic_write_text"


def test_write_failure_leaves_original_file_intact_and_cleans_tmp(tmp_path, monkeypatch):
    """A failure during the atomic rename must not corrupt the user's file.

    We make the final ``Path.replace`` (the rename step) raise ``OSError``,
    simulating a disk-full/cross-device failure at the worst moment. The
    original source file must remain byte-for-byte intact -- never truncated
    or partially written -- and the helper must clean up its temp file rather
    than leave it masquerading near the destination.

    Discriminating: with the old direct ``file_path.write_text`` there is no
    rename to intercept; the truncate-then-write would corrupt the file, so
    the "original intact" assertion would fail.
    """
    page = _make_page(tmp_path)
    fixer = _fixer(tmp_path)

    original = page.read_text(encoding="utf-8")
    assert original == NESTED_MD

    real_replace = Path.replace

    def boom(self, target):
        # Only blow up the destination rename, not unrelated replaces.
        if Path(target) == page:
            raise OSError("simulated rename failure (e.g. ENOSPC / EXDEV)")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", boom)

    apply_fix = fixer._create_fence_fix(page, line_number=TAB_SET_LINE)

    # apply_fix swallows the OSError (broad ``except Exception``) and reports
    # failure rather than crashing the build.
    assert apply_fix() is False

    # Original file is byte-for-byte intact: no partial write.
    assert page.read_text(encoding="utf-8") == original

    # No orphan temp file left behind in the content directory.
    leftovers = [p for p in page.parent.iterdir() if p.name != page.name and p.suffix == ".tmp"]
    assert leftovers == [], f"temp file not cleaned up after failure: {leftovers}"


def test_sigint_mid_rename_never_truncates_user_source(tmp_path, monkeypatch):
    """A SIGINT (KeyboardInterrupt) mid-rename must never truncate user source.

    This is the literal data-safety scenario from issue #440: Ctrl-C while the
    fixer is writing a user's content file. The atomic temp-then-rename pattern
    guarantees the destination is only ever swapped via an atomic rename, so an
    interruption before/during that rename leaves the original file completely
    intact.

    Discriminating: a regression to ``file_path.write_text`` truncates and
    rewrites the destination in place, so an interruption would leave the
    user's source partially written -- this assertion would fail.
    """
    page = _make_page(tmp_path)
    fixer = _fixer(tmp_path)

    original = page.read_text(encoding="utf-8")
    assert original == NESTED_MD

    real_replace = Path.replace

    def boom(self, target):
        if Path(target) == page:
            raise KeyboardInterrupt("simulated SIGINT mid-rename")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", boom)

    apply_fix = fixer._create_fence_fix(page, line_number=TAB_SET_LINE)

    # KeyboardInterrupt is a BaseException; it propagates past apply_fix's
    # ``except Exception``, mirroring a real interrupt.
    with pytest.raises(KeyboardInterrupt):
        apply_fix()

    # The load-bearing invariant: the user's source is never truncated.
    assert page.read_text(encoding="utf-8") == original
