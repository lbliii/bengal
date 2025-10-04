# Bengal CLI Ergonomics Audit ᓚᘏᗢ

**Date**: October 3, 2025  
**Goal**: Make the CLI purrfect - identify sharp edges and improve UX

---

## 🎯 Executive Summary

The Bengal CLI has a solid foundation with good personality (emojis, colors, cat ASCII art), but there are several ergonomic issues and missing features that could make it more user-friendly and competitive with Hugo/11ty.

**Overall Rating**: 7/10 (Good foundation, needs refinement)

---

## 🔴 Critical Issues

### 1. **Negative Flags Are Confusing**
```bash
bengal serve --no-watch      # Double negative to think about
bengal serve --no-auto-port  # Hard to remember
```

**Problem**: Users have to think "I want to NOT do X" which is cognitively harder.

**Fix**: Use positive flags with sensible defaults
```bash
bengal serve --watch / --no-watch     # Boolean flag (current default: true)
bengal serve --auto-port / --no-auto-port  # Boolean flag (current default: true)
```

Better approach:
```bash
bengal serve                          # Watch enabled by default
bengal serve --watch=false            # Explicit disable
# OR use click's flag_value feature
bengal serve --static                 # No watch, static mode
```

---

### 2. **Timestamp Bug in `new page`**
```python
date: {Path(__file__).stat().st_mtime}  # Line 252 in cli.py
```

**Problem**: This uses the modification time of the CLI file itself, not the current time!

**Fix**:
```python
from datetime import datetime
date: {datetime.now().isoformat()}
```

---

### 3. **Duplicate KeyboardInterrupt Handling**
The `serve` command catches `KeyboardInterrupt` in TWO places:
- Line 104-105 in cli.py
- Line 334-343 in dev_server.py

**Problem**: The first handler prints "Server stopped", then the dev_server handler prints its own message. Users see both.

**Fix**: Remove the handler in cli.py, let dev_server handle it entirely.

---

### 4. **Conflicting Flags Not Validated**
```bash
bengal build --quiet --verbose  # Both accepted, quiet wins
```

**Problem**: No validation that these are mutually exclusive.

**Fix**: Add Click's `@click.mutually_exclusive` or manual validation:
```python
if quiet and verbose:
    raise click.UsageError("--quiet and --verbose are mutually exclusive")
```

---

## 🟡 Major Ergonomic Issues

### 5. **Missing `--open` Flag for Serve**
Every modern dev server has this:
```bash
hugo server --open
vite --open
webpack serve --open
```

Users expect the browser to open automatically.

**Fix**: Add `--open/-o` flag
```python
@click.option('--open', '-o', is_flag=True, help='Open browser automatically')
def serve(..., open_browser: bool):
    # After server starts
    if open_browser:
        import webbrowser
        webbrowser.open(f'http://{host}:{actual_port}/')
```

---

### 6. **No `--force` Flag for Destructive Operations**
```bash
bengal clean  # No confirmation!
```

**Problem**: Deletes entire output directory without asking.

**Fix**: Add confirmation prompt or `--force` flag
```python
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def clean(force: bool, ...):
    if not force:
        if not click.confirm(f"Delete {site.output_dir}?"):
            click.echo("Cancelled")
            return
    site.clean()
```

---

### 7. **Missing `init` Command**
```bash
bengal new site my-blog  # Creates subdirectory
```

**Problem**: No way to initialize in current directory (like `git init`)

**Fix**: Add `bengal init` command
```bash
bengal init           # Initialize in current directory
bengal init --name "My Blog"  # Optional name
```

---

### 8. **No `--watch` Mode for Build**
Hugo has this useful feature:
```bash
hugo --watch  # Rebuild on changes but don't serve
```

**Use case**: CI/CD preview builds, docker containers

**Fix**: Add `--watch` to build command
```python
@main.command()
@click.option('--watch', is_flag=True, help='Watch for changes and rebuild')
def build(..., watch: bool):
    if watch:
        # Use file watcher like serve does
        pass
```

---

### 9. **Source Argument Is Awkward**
```bash
bengal build /path/to/site  # Must specify path
```

**Problem**: 
- Always defaults to `.` (current dir) anyway
- But requires `exists=True`, so if you typo, confusing error
- Not discoverable that you CAN specify a path

**Fix**: Make it an option instead
```python
@click.option('--source', '-s', type=click.Path(exists=True), default='.', 
              help='Site source directory')
def build(source: str, ...):
```

---

### 10. **Config Path Repeated Everywhere**
Every command has:
```python
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
```

**Problem**: Repetitive, inconsistent help text potential

**Fix**: Create a shared decorator
```python
def config_option(f):
    return click.option('--config', '-c', type=click.Path(exists=True),
                       help='Path to config file (default: bengal.toml)')(f)

@main.command()
@config_option
def build(...):
```

---

## 🟢 Minor Polish Issues

### 11. **Missing Command Aliases**
Most CLI tools have short aliases:
```bash
hugo s      # serve
hugo b      # build
npm i       # install
```

**Fix**: Add aliases using Click's `name` parameter
```python
@main.command(name='serve', aliases=['s'])
def serve_cmd(...):
```

Note: Click doesn't support aliases directly, need Click 8.1+ or custom group.

---

### 12. **No Shell Completion**
Users can't tab-complete commands/options.

**Fix**: Add shell completion
```python
# In setup.py or pyproject.toml
[project.scripts]
bengal = "bengal.cli:main"
# Then document:
# eval "$(_BENGAL_COMPLETE=bash_source bengal)"  # Bash
# eval "$(_BENGAL_COMPLETE=zsh_source bengal)"   # Zsh
```

---

### 13. **Inconsistent Exit Codes**
All errors use `raise click.Abort()` which exits with code 1.

**Problem**: Can't distinguish between different error types in CI/CD

**Fix**: Use different exit codes
```python
sys.exit(1)   # General error
sys.exit(2)   # Config error
sys.exit(3)   # Build error
sys.exit(130) # Keyboard interrupt (standard)
```

---

### 14. **No `--dry-run` Option**
For commands that make changes (build, clean, new), users might want to preview:
```bash
bengal build --dry-run   # Show what would be built
bengal clean --dry-run   # Show what would be deleted
```

---

### 15. **Missing `--output` Override**
```bash
bengal build --output ./dist  # Override config output_dir
```

**Use case**: CI/CD systems that want specific output locations

---

### 16. **No `--version` Shortcut**
```bash
bengal --version  # Works
bengal -v         # Conflicts with --verbose
```

**Fix**: Document that `-v` is for verbose, `--version` for version

---

### 17. **Help Text Could Be More Descriptive**
Current:
```
--parallel/--no-parallel  Use parallel processing
```

Better:
```
--parallel/--no-parallel  Enable parallel processing for faster builds
                          (default: true, disable for debugging)
```

---

### 18. **New Page: Section Path Not Validated**
```bash
bengal new page my-page --section "foo/bar/baz"
```

Creates nested structure but doesn't check if it makes sense with site structure.

---

### 19. **No Progress Indicator for Long Operations**
When building large sites, no feedback during:
- Asset copying
- Taxonomy generation
- Template rendering

**Fix**: Add progress bars or spinners
```python
with click.progressbar(pages, label='Rendering pages') as bar:
    for page in bar:
        render(page)
```

---

### 20. **Server URL Not Clickable in Some Terminals**
Some terminals auto-link URLs, some don't. Could use OSC 8 escape codes:
```python
# Terminal hyperlink
f"\033]8;;http://{host}:{port}\033\\http://{host}:{port}\033]8;;\033\\"
```

---

## 📊 Competitive Analysis

| Feature | Bengal | Hugo | 11ty | MkDocs |
|---------|--------|------|------|--------|
| `--open` flag | ❌ | ✅ | ✅ | ✅ |
| `--watch` on build | ❌ | ✅ | ✅ | ❌ |
| Shell completion | ❌ | ✅ | ✅ | ✅ |
| `init` command | ❌ | ✅ | ✅ | ✅ |
| Confirmation prompts | ❌ | ✅ | ❌ | ✅ |
| Command aliases | ❌ | ✅ | ❌ | ❌ |
| Progress bars | ❌ | ✅ | ❌ | ✅ |
| Exit code docs | ❌ | ✅ | ❌ | ❌ |

---

## 🎨 UX Wins (Keep These!)

1. ✅ **Beautiful output** - Colors, emojis, cat ASCII art
2. ✅ **Personality** - Playful but professional
3. ✅ **Auto-port selection** - Smart default behavior
4. ✅ **Clear error messages** - Good error formatting
5. ✅ **Smart defaults** - Parallel on, strict in dev
6. ✅ **Phase timing** - Detailed build performance stats
7. ✅ **Warning categorization** - Groups warnings by type

---

## 🎯 Recommended Priority Order

### Phase 1: Critical Fixes (1-2 hours)
1. Fix timestamp bug in `new page`
2. Remove duplicate KeyboardInterrupt handler
3. Add `--quiet/--verbose` mutual exclusion
4. Add `--force` confirmation for clean

### Phase 2: Major Features (3-4 hours)
5. Add `--open` flag to serve
6. Add `bengal init` command  
7. Add `--watch` to build command
8. Improve help text across all commands

### Phase 3: Polish (2-3 hours)
9. Add shell completion
10. Add shared config decorator
11. Add `--output` override for build
12. Add progress indicators

### Phase 4: Advanced (if time)
13. Command aliases (needs Click 8.1+)
14. Better exit codes
15. `--dry-run` support
16. Clickable URLs

---

## 📝 Example Improved Commands

### Serve Command (After Fixes)
```python
@main.command()
@click.option('--host', default='localhost', help='Server host address')
@click.option('--port', '-p', default=5173, type=int, help='Server port number')
@click.option('--watch/--no-watch', default=True, 
              help='Watch for file changes and rebuild (default: enabled)')
@click.option('--auto-port/--no-auto-port', default=True,
              help='Automatically find available port if specified port is taken')
@click.option('--open', '-o', is_flag=True, 
              help='Open browser automatically after server starts')
@config_option
@source_option
def serve(host: str, port: int, watch: bool, auto_port: bool, 
          open_browser: bool, config: str, source: str) -> None:
    """
    🚀 Start development server with hot reload.
    
    The server watches for changes in content, assets, and templates,
    automatically rebuilding the site when files are modified.
    
    Examples:
      bengal serve                    # Start with defaults
      bengal serve --port 3000 --open # Custom port, open browser
      bengal serve --no-watch         # Static server, no rebuilding
    """
    try:
        show_welcome()
        
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        site = Site.from_config(root_path, config_path)
        site.config["strict_mode"] = True
        
        # Start server
        actual_port = site.serve(host=host, port=port, watch=watch, auto_port=auto_port)
        
        # Open browser if requested
        if open_browser:
            import webbrowser
            import time
            time.sleep(0.5)  # Give server time to start
            webbrowser.open(f'http://{host}:{actual_port}/')
        
    except Exception as e:
        show_error(f"Server failed: {e}", show_art=True)
        raise click.Abort()
```

### Build Command (After Fixes)
```python
@main.command()
@click.option('--parallel/--no-parallel', default=True,
              help='Enable parallel processing for faster builds (default: enabled)')
@click.option('--incremental', '-i', is_flag=True,
              help='Only rebuild changed files (experimental)')
@click.option('--verbose', '-v', is_flag=True,
              help='Show detailed build information and file-by-file progress')
@click.option('--quiet', '-q', is_flag=True,
              help='Minimal output - only show errors and final summary')
@click.option('--strict', is_flag=True,
              help='Fail on template errors and warnings (recommended for CI/CD)')
@click.option('--debug', is_flag=True,
              help='Show debug output and full tracebacks for errors')
@click.option('--watch', '-w', is_flag=True,
              help='Watch for changes and rebuild (without dev server)')
@click.option('--output', '-o', type=click.Path(),
              help='Override output directory from config')
@config_option
@source_option
def build(parallel: bool, incremental: bool, verbose: bool, quiet: bool,
          strict: bool, debug: bool, watch: bool, output: str,
          config: str, source: str) -> None:
    """
    🔨 Build the static site.
    
    Generates HTML files from your content, applies templates,
    processes assets, and outputs a production-ready site.
    
    Examples:
      bengal build                    # Standard build
      bengal build --no-parallel      # Sequential build (easier to debug)
      bengal build --watch            # Rebuild on changes
      bengal build --strict --quiet   # CI/CD mode
    """
    # Validate conflicting flags
    if quiet and verbose:
        raise click.UsageError("Cannot use --quiet and --verbose together")
    
    try:
        if not watch:
            show_building_indicator("Building site")
        
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        site = Site.from_config(root_path, config_path)
        
        # Override config with CLI flags
        if strict:
            site.config["strict_mode"] = True
        if debug:
            site.config["debug"] = True
        if output:
            site.output_dir = Path(output)
        
        if watch:
            # Watch mode
            _build_watch_mode(site, parallel, incremental, verbose)
        else:
            # One-time build
            stats = site.build(parallel=parallel, incremental=incremental, verbose=verbose)
            
            if not quiet:
                display_build_stats(stats, show_art=True, output_dir=str(site.output_dir))
            else:
                click.echo(click.style("✅ Build complete!", fg='green', bold=True))
                click.echo(click.style(f"   ↪ {site.output_dir}", fg='cyan'))
        
    except Exception as e:
        show_error(f"Build failed: {e}", show_art=True)
        if debug:
            raise
        raise click.Abort()
```

### New Init Command
```python
@main.command()
@click.option('--name', prompt='Site name', help='Name of your site')
@click.option('--theme', default='default', help='Theme to use')
@click.option('--force', '-f', is_flag=True, help='Initialize even if directory is not empty')
def init(name: str, theme: str, force: bool) -> None:
    """
    ✨ Initialize a new Bengal site in the current directory.
    
    Creates the directory structure and config file needed for a Bengal site.
    Use 'bengal new site <name>' to create a new site in a subdirectory instead.
    
    Examples:
      bengal init                     # Interactive prompt for name
      bengal init --name "My Blog"    # Non-interactive
      bengal init --force             # Initialize in non-empty directory
    """
    try:
        site_path = Path.cwd()
        
        # Check if directory is empty
        if not force and any(site_path.iterdir()):
            if not click.confirm("Directory is not empty. Continue?"):
                click.echo("Cancelled")
                return
        
        # Check if already a Bengal site
        if (site_path / 'bengal.toml').exists() and not force:
            show_error("Already a Bengal site! Use --force to reinitialize.", show_art=False)
            raise click.Abort()
        
        click.echo(click.style(f"\n✨ Initializing Bengal site: {name}", fg='cyan', bold=True))
        
        # Create directory structure
        (site_path / 'content').mkdir(exist_ok=True)
        (site_path / 'assets' / 'css').mkdir(parents=True, exist_ok=True)
        (site_path / 'assets' / 'js').mkdir(exist_ok=True)
        (site_path / 'assets' / 'images').mkdir(exist_ok=True)
        (site_path / 'templates').mkdir(exist_ok=True)
        
        click.echo(click.style("   ├─ ", fg='cyan') + "Created directory structure")
        
        # Create config file
        config_content = f"""[site]
title = "{name}"
baseurl = ""
theme = "{theme}"

[build]
output_dir = "public"
parallel = true

[assets]
minify = true
fingerprint = true
"""
        (site_path / 'bengal.toml').write_text(config_content)
        click.echo(click.style("   ├─ ", fg='cyan') + "Created bengal.toml")
        
        # Create sample index page
        from datetime import datetime
        index_content = f"""---
title: Welcome to {name}
date: {datetime.now().isoformat()}
---

# Welcome to {name}

This is your new Bengal static site. Start editing this file to begin!

## Features

- Fast builds with parallel processing
- Modular architecture  
- Asset optimization
- SEO friendly

## Next Steps

1. Edit `content/index.md` (this file)
2. Create new pages with `bengal new page <name>`
3. Build your site with `bengal build`
4. Preview with `bengal serve`
"""
        (site_path / 'content' / 'index.md').write_text(index_content)
        click.echo(click.style("   └─ ", fg='cyan') + "Created sample index page")
        
        click.echo(click.style(f"\n✅ Site initialized successfully!", fg='green', bold=True))
        click.echo(click.style("\n📚 Next steps:", fg='cyan', bold=True))
        click.echo(click.style("   └─ ", fg='cyan') + "bengal serve")
        click.echo()
        
    except Exception as e:
        show_error(f"Failed to initialize site: {e}", show_art=False)
        raise click.Abort()
```

---

## 🧪 Testing Recommendations

Add CLI integration tests:

```python
# tests/test_cli.py
from click.testing import CliRunner
from bengal.cli import main

def test_build_quiet_verbose_conflict():
    """Test that --quiet and --verbose are mutually exclusive."""
    runner = CliRunner()
    result = runner.invoke(main, ['build', '--quiet', '--verbose'])
    assert result.exit_code != 0
    assert 'mutually exclusive' in result.output

def test_serve_open_flag():
    """Test that --open flag is accepted."""
    runner = CliRunner()
    # Mock the server startup
    result = runner.invoke(main, ['serve', '--open', '--help'])
    assert '--open' in result.output

def test_init_command():
    """Test bengal init creates proper structure."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ['init', '--name', 'test-site'])
        assert result.exit_code == 0
        assert Path('bengal.toml').exists()
        assert Path('content/index.md').exists()
```

---

## 📚 Documentation Needs

Update docs to mention:
1. All command-line flags with examples
2. Exit codes and their meanings  
3. Shell completion setup
4. Common workflows (dev, production, CI/CD)
5. Troubleshooting guide

---

## 🎭 Summary

The Bengal CLI is already charming and functional, but these improvements will make it:
- **Safer** - Confirmations, validations, better error codes
- **Faster to use** - Aliases, completion, --open flag
- **More flexible** - Watch mode, output override, init command  
- **More intuitive** - Positive flags, better help text, no conflicts
- **More competitive** - Feature parity with Hugo/11ty

**Estimated total effort**: 8-12 hours for all improvements

**Biggest wins**: Fix bugs (#2, #3), add --open (#5), add init (#7), add --watch build (#8)

