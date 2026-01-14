# RFC: CLI Upgrade Notifications & Self-Update Command

## Status: Draft
## Created: 2026-01-14
## Origin: Feature request for professional CLI UX parity with npm, pip, cargo, gh

---

## Summary

**Problem**: Users have no visibility into Bengal updates without manually checking PyPI or GitHub releases. This leads to:
- Running outdated versions with known bugs
- Missing new features and performance improvements
- No convenient upgrade path (must manually run `pip install --upgrade bengal`)

**Solution**: Implement two complementary features:
1. **Passive notifications**: Check PyPI for updates and display a non-intrusive banner when a newer version is available
2. **Active upgrade command**: `bengal upgrade` command that detects the installation method and runs the appropriate upgrade

**Priority**: Low (UX polish, non-blocking)
**Scope**: ~200 LOC implementation + ~50 LOC tests

---

## User Experience

### Passive Notification (Automatic)

After any command, if an upgrade is available:

```
$ bengal build
Building your site... (Bengal v0.1.8)
✓ Built 42 pages in 1.2s

╭─ Upgrade Available ─────────────────────────────────────╮
│ Bengal v0.2.0 is available (you have v0.1.8)           │
│ Run: bengal upgrade                                     │
╰─────────────────────────────────────────────────────────╯
```

### Active Upgrade Command

```
$ bengal upgrade
Checking for updates...

╭─ Bengal Upgrade ────────────────────────────────────────╮
│ Current version: 0.1.8                                  │
│ Latest version:  0.2.0                                  │
│                                                         │
│ Detected: uv (pyproject.toml)                          │
│ Command:  uv pip install --upgrade bengal              │
╰─────────────────────────────────────────────────────────╯

Proceed with upgrade? [Y/n]: y

⠋ Upgrading bengal...
✓ Successfully upgraded to v0.2.0

Release notes: https://github.com/lbliii/bengal/releases/tag/v0.2.0
```

### Dry-Run Mode

```
$ bengal upgrade --dry-run
Would run: uv pip install --upgrade bengal
Current: 0.1.8 → Latest: 0.2.0
```

---

## Design

### Architecture

```
bengal/cli/commands/upgrade/
├── __init__.py          # Package exports
├── check.py         # PyPI version checking + caching
├── command.py       # `bengal upgrade` command implementation
└── installers.py    # Installer detection (uv, pip, pipx, etc.)
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `check.py` | Query PyPI, cache results, version comparison |
| `command.py` | CLI command, user prompts, execute upgrade |
| `installers.py` | Detect how Bengal was installed, generate upgrade command |

### Cache Location

User-level cache (not project-level) since upgrade state is global:

```
~/.config/bengal/upgrade_check.json   # Linux/macOS (XDG)
~/.bengal/upgrade_check.json          # Fallback
%APPDATA%\bengal\upgrade_check.json   # Windows
```

Cache format:
```json
{
  "latest_version": "0.2.0",
  "checked_at": "2026-01-14T10:30:00Z",
  "current_version": "0.1.8"
}
```

### Version Check Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    check_for_upgrade()                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Skip check if:        │
              │  - CI environment      │
              │  - NO_UPDATE_CHECK=1   │
              │  - Non-interactive TTY │
              │  - --quiet flag        │
              └────────────────────────┘
                           │ No skip
                           ▼
              ┌────────────────────────┐
              │  Load cache            │
              │  ~/.config/bengal/     │
              │  upgrade_check.json    │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Cache fresh?          │──── Yes ───▶ Use cached result
              │  (< 24 hours old)      │
              └────────────────────────┘
                           │ No (stale or missing)
                           ▼
              ┌────────────────────────┐
              │  Query PyPI            │
              │  GET /pypi/bengal/json │
              │  Timeout: 2s           │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Update cache          │
              │  Compare versions      │
              │  Return notification   │
              └────────────────────────┘
```

### Installer Detection

The `bengal upgrade` command should "just work" regardless of how Bengal was installed:

| Installation Method | Detection | Upgrade Command |
|---------------------|-----------|-----------------|
| **uv** (recommended) | `uv.lock` in cwd or `UV_*` env vars | `uv pip install --upgrade bengal` |
| **pip** (venv) | `sys.prefix != sys.base_prefix` | `pip install --upgrade bengal` |
| **pipx** | `pipx list` includes bengal | `pipx upgrade bengal` |
| **pip** (global) | Fallback | `pip install --upgrade bengal` |
| **conda** | `CONDA_PREFIX` env var | `conda update bengal` |
| **system package** | `/usr/bin/bengal` | Show manual instructions |

Detection priority (check in order):
1. `uv.lock` exists → uv
2. `pipx list` shows bengal → pipx
3. Virtual environment active → pip in venv
4. `CONDA_PREFIX` set → conda
5. Fallback → pip (user install)

---

## Implementation

### Phase 1: Core Infrastructure (~80 LOC)

**File: `bengal/cli/commands/upgrade/check.py`**

```python
"""
PyPI version checking with TTL-based caching.

Checks are:
- Cached for 24 hours to avoid network spam
- Skipped in CI environments
- Non-blocking (2s timeout, silent failures)
- User-level cache (~/.config/bengal/)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple

import httpx
from packaging.version import Version

from bengal import __version__

# Cache TTL: 24 hours
CACHE_TTL = timedelta(hours=24)

# PyPI endpoint
PYPI_URL = "https://pypi.org/pypi/bengal/json"

# Request timeout (don't slow down CLI)
TIMEOUT = 2.0


class UpgradeInfo(NamedTuple):
    """Information about available upgrade."""
    current: str
    latest: str
    
    @property
    def is_outdated(self) -> bool:
        """True if current version is older than latest."""
        return Version(self.current) < Version(self.latest)


def get_cache_path() -> Path:
    """Get platform-appropriate cache path."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "bengal" / "upgrade_check.json"


def should_check() -> bool:
    """Determine if we should check for updates."""
    # Skip in CI environments
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS"]
    if any(os.environ.get(var) for var in ci_vars):
        return False
    
    # Skip if explicitly disabled
    if os.environ.get("BENGAL_NO_UPDATE_CHECK", "").lower() in ("1", "true", "yes"):
        return False
    
    # Skip if not interactive terminal
    if not sys.stderr.isatty():
        return False
    
    return True


def load_cache() -> dict | None:
    """Load cached upgrade check result."""
    cache_path = get_cache_path()
    if not cache_path.exists():
        return None
    
    try:
        data = json.loads(cache_path.read_text())
        checked_at = datetime.fromisoformat(data["checked_at"])
        if datetime.now(timezone.utc) - checked_at < CACHE_TTL:
            return data
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    
    return None


def save_cache(latest_version: str) -> None:
    """Save upgrade check result to cache."""
    cache_path = get_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "latest_version": latest_version,
        "current_version": __version__,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    cache_path.write_text(json.dumps(data, indent=2))


def fetch_latest_version() -> str | None:
    """Fetch latest version from PyPI."""
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(PYPI_URL)
            response.raise_for_status()
            data = response.json()
            return data["info"]["version"]
    except Exception:
        return None


def check_for_upgrade() -> UpgradeInfo | None:
    """
    Check if a newer version of Bengal is available.
    
    Returns:
        UpgradeInfo if upgrade available, None otherwise
    """
    if not should_check():
        return None
    
    # Try cache first
    cached = load_cache()
    if cached:
        latest = cached["latest_version"]
    else:
        # Fetch from PyPI
        latest = fetch_latest_version()
        if latest:
            save_cache(latest)
    
    if not latest:
        return None
    
    info = UpgradeInfo(current=__version__, latest=latest)
    return info if info.is_outdated else None
```

### Phase 2: Installer Detection (~60 LOC)

**File: `bengal/cli/commands/upgrade/installers.py`**

```python
"""
Installer detection for bengal upgrade command.

Detects how Bengal was installed and generates appropriate upgrade command.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InstallerInfo:
    """Information about detected installer."""
    name: str
    command: list[str]
    display_command: str
    
    @property
    def is_available(self) -> bool:
        """Check if the installer is available."""
        return shutil.which(self.command[0]) is not None


def detect_installer() -> InstallerInfo:
    """
    Detect how Bengal was installed.
    
    Returns:
        InstallerInfo with appropriate upgrade command
    """
    # Check for uv (preferred for Bengal)
    if _is_uv_project():
        return InstallerInfo(
            name="uv",
            command=["uv", "pip", "install", "--upgrade", "bengal"],
            display_command="uv pip install --upgrade bengal",
        )
    
    # Check for pipx
    if _is_pipx_install():
        return InstallerInfo(
            name="pipx",
            command=["pipx", "upgrade", "bengal"],
            display_command="pipx upgrade bengal",
        )
    
    # Check for conda
    if os.environ.get("CONDA_PREFIX"):
        return InstallerInfo(
            name="conda",
            command=["conda", "update", "-y", "bengal"],
            display_command="conda update bengal",
        )
    
    # Check for virtual environment
    if sys.prefix != sys.base_prefix:
        return InstallerInfo(
            name="pip (venv)",
            command=[sys.executable, "-m", "pip", "install", "--upgrade", "bengal"],
            display_command="pip install --upgrade bengal",
        )
    
    # Fallback to pip with --user
    return InstallerInfo(
        name="pip",
        command=[sys.executable, "-m", "pip", "install", "--upgrade", "--user", "bengal"],
        display_command="pip install --upgrade --user bengal",
    )


def _is_uv_project() -> bool:
    """Check if current directory is a uv-managed project."""
    # Check for uv.lock in current directory or parents
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "uv.lock").exists():
            return True
        if parent == parent.parent:  # Root reached
            break
    
    # Check for UV environment variables
    return bool(os.environ.get("UV_CACHE_DIR") or os.environ.get("UV_PYTHON"))


def _is_pipx_install() -> bool:
    """Check if Bengal was installed via pipx."""
    if not shutil.which("pipx"):
        return False
    
    try:
        result = subprocess.run(
            ["pipx", "list", "--short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "bengal" in result.stdout
    except Exception:
        return False
```

### Phase 3: Upgrade Command (~80 LOC)

**File: `bengal/cli/commands/upgrade/command.py`**

```python
"""
bengal upgrade command implementation.
"""

from __future__ import annotations

import subprocess
import sys

import click
import questionary

from bengal import __version__
from bengal.cli.base import BengalCommand
from bengal.output import CLIOutput
from bengal.cli.commands.upgrade.check import PYPI_URL, fetch_latest_version
from bengal.cli.commands.upgrade.installers import detect_installer


@click.command(cls=BengalCommand, name="upgrade")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without executing",
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force upgrade even if already on latest version",
)
def upgrade(dry_run: bool, yes: bool, force: bool) -> None:
    """
    Upgrade Bengal to the latest version.
    
    Automatically detects how Bengal was installed (uv, pip, pipx, conda)
    and runs the appropriate upgrade command.
    
    Examples:
        bengal upgrade           # Interactive upgrade
        bengal upgrade -y        # Skip confirmation
        bengal upgrade --dry-run # Show command without running
    """
    cli = CLIOutput()
    
    # Check for latest version
    cli.info("Checking for updates...")
    latest = fetch_latest_version()
    
    if not latest:
        cli.error("Failed to check PyPI for latest version")
        cli.tip("Check your internet connection or try again later")
        raise SystemExit(1)
    
    # Detect installer
    installer = detect_installer()
    
    # Display upgrade info
    is_outdated = latest != __version__
    
    click.echo()
    click.secho("╭─ Bengal Upgrade " + "─" * 42 + "╮", fg="cyan")
    click.secho(f"│ Current version: {__version__:<40} │", fg="cyan")
    click.secho(f"│ Latest version:  {latest:<40} │", fg="cyan")
    click.secho(f"│{' ' * 58}│", fg="cyan")
    click.secho(f"│ Detected: {installer.name:<47} │", fg="cyan")
    click.secho(f"│ Command:  {installer.display_command:<47} │", fg="cyan")
    click.secho("╰" + "─" * 58 + "╯", fg="cyan")
    click.echo()
    
    if not is_outdated and not force:
        cli.success(f"Already on latest version (v{__version__})")
        return
    
    if dry_run:
        cli.info(f"Would run: {installer.display_command}")
        return
    
    # Confirm with user
    if not yes:
        if not questionary.confirm("Proceed with upgrade?", default=True).ask():
            cli.info("Upgrade cancelled")
            return
    
    # Execute upgrade
    cli.info("Upgrading bengal...")
    
    try:
        result = subprocess.run(
            installer.command,
            check=True,
            capture_output=True,
            text=True,
        )
        cli.success(f"Successfully upgraded to v{latest}")
        click.echo()
        click.secho(
            f"Release notes: https://github.com/lbliii/bengal/releases/tag/v{latest}",
            dim=True,
        )
    except subprocess.CalledProcessError as e:
        cli.error("Upgrade failed")
        if e.stderr:
            click.echo(e.stderr, err=True)
        cli.tip(f"Try running manually: {installer.display_command}")
        raise SystemExit(1)
```

### Phase 4: CLI Integration (~20 LOC)

**Modify: `bengal/cli/__init__.py`**

```python
# Add import at top
from bengal.cli.commands.upgrade.command import upgrade as upgrade_cmd

# Add command registration (after other main.add_command calls)
main.add_command(upgrade_cmd, name="upgrade")

# Add notification hook in main() function, after command execution
# This is called via atexit or Click's result_callback
def _show_upgrade_notification() -> None:
    """Show upgrade notification if available (non-blocking)."""
    try:
        from bengal.cli.commands.upgrade.check import check_for_upgrade
        
        info = check_for_upgrade()
        if info and info.is_outdated:
            click.echo()
            click.secho("╭─ Upgrade Available " + "─" * 38 + "╮", fg="yellow", err=True)
            click.secho(
                f"│ Bengal v{info.latest} is available (you have v{info.current})" + " " * (47 - len(info.latest) - len(info.current)) + "│",
                fg="yellow",
                err=True,
            )
            click.secho(f"│ Run: bengal upgrade{' ' * 38}│", fg="yellow", err=True)
            click.secho("╰" + "─" * 58 + "╯", fg="yellow", err=True)
    except Exception:
        pass  # Never fail CLI due to upgrade check
```

---

## Environment Controls

| Variable | Effect |
|----------|--------|
| `BENGAL_NO_UPDATE_CHECK=1` | Disable all upgrade checks |
| `CI=1` (or `GITHUB_ACTIONS`, etc.) | Auto-disable in CI |
| `--quiet` flag | Suppress upgrade notifications |

---

## Testing Strategy

### Unit Tests

```python
# tests/test_upgrade_check.py

def test_should_check_returns_false_in_ci(monkeypatch):
    """Upgrade checks disabled in CI environments."""
    monkeypatch.setenv("CI", "1")
    assert not should_check()

def test_cache_ttl_respected(tmp_path, monkeypatch):
    """Cached results used within TTL."""
    # Create fresh cache
    cache = tmp_path / "upgrade_check.json"
    cache.write_text(json.dumps({
        "latest_version": "0.2.0",
        "current_version": "0.1.8",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }))
    
    monkeypatch.setattr("bengal.cli.commands.upgrade.check.get_cache_path", lambda: cache)
    
    # Should use cache, not fetch
    with patch("bengal.cli.commands.upgrade.check.fetch_latest_version") as mock:
        check_for_upgrade()
        mock.assert_not_called()

def test_installer_detection_uv(tmp_path, monkeypatch):
    """Detect uv when uv.lock exists."""
    (tmp_path / "uv.lock").touch()
    monkeypatch.chdir(tmp_path)
    
    installer = detect_installer()
    assert installer.name == "uv"
    assert "uv pip install" in installer.display_command
```

### Integration Tests

```python
# tests/integration/test_upgrade_command.py

def test_upgrade_dry_run(cli_runner):
    """--dry-run shows command without executing."""
    result = cli_runner.invoke(main, ["upgrade", "--dry-run"])
    assert result.exit_code == 0
    assert "Would run:" in result.output

def test_upgrade_already_latest(cli_runner, monkeypatch):
    """Shows success when already on latest."""
    monkeypatch.setattr(
        "bengal.cli.commands.upgrade.check.fetch_latest_version",
        lambda: __version__
    )
    result = cli_runner.invoke(main, ["upgrade"])
    assert "Already on latest" in result.output
```

---

## Rollout Plan

### Phase 1: Core (Week 1)
- [ ] Implement `check.py` with caching
- [ ] Add `installers.py` for installer detection
- [ ] Unit tests for cache and detection

### Phase 2: Command (Week 1)
- [ ] Implement `upgrade` command
- [ ] Integration tests
- [ ] Documentation

### Phase 3: Notification (Week 2)
- [ ] Add notification hook to CLI main
- [ ] Add `--quiet` flag support
- [ ] E2E testing

### Phase 4: Polish (Week 2)
- [ ] Add to CLI help/documentation
- [ ] Add release notes link
- [ ] User feedback integration

---

## Security Considerations

### Supply Chain
- Only queries official PyPI API over HTTPS
- No automatic code execution without user confirmation
- Installer commands use full paths (`sys.executable`)

### Privacy
- No telemetry or user tracking
- Cache stored locally only
- Network requests are minimal (once per 24h)

### Failure Modes
- Network failures are silent (don't break CLI)
- Invalid cache is ignored and refreshed
- Upgrade failures show manual command

---

## Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| `httpx` | PyPI API requests | ✅ Already installed |
| `packaging` | Version comparison | ⚠️ Needs addition to pyproject.toml |
| `click` | CLI framework | ✅ Already installed |
| `questionary` | Interactive prompts | ✅ Already installed |

No new external dependencies required (beyond declarative addition of `packaging`).

---

## Alternatives Considered

### 1. Background Thread Check
**Rejected**: Adds complexity for minimal latency benefit. Synchronous check with 2s timeout is fast enough.

### 2. Check on Every Command
**Rejected**: Would slow down every invocation. TTL-based caching (24h) is sufficient.

### 3. System Package Manager Detection
**Deferred**: Complex to detect apt/brew/dnf installations reliably. Can add later if needed.

### 4. Auto-Update (No Confirmation)
**Rejected**: Users should control when updates happen. Silent updates can break workflows.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Check latency | < 100ms (cached), < 2s (network) |
| Cache hit rate | > 95% (24h TTL) |
| Installer detection accuracy | > 99% |
| User upgrade rate | Increase by 50% (vs manual checking) |

---

## References

- [pip's upgrade check](https://pip.pypa.io/en/stable/user_guide/#configuration) - Inspiration for caching approach
- [npm update-notifier](https://github.com/yeoman/update-notifier) - Popular Node.js implementation
- [GitHub CLI upgrade](https://cli.github.com/manual/gh_upgrade) - UX inspiration
- [PyPI JSON API](https://warehouse.pypa.io/api-reference/json.html) - API documentation
