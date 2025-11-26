# Security & Edge Case Audit Report

**Date**: 2025-11-26  
**Auditor**: Adversarial Code Review  
**Scope**: Bengal core features pre-public release  
**Status**: 🔴 **Critical issues found requiring immediate attention**

---

## Executive Summary

Found **2 critical**, **3 medium**, and **4 low/informational** issues that should be addressed before public release. The most severe is a command injection vulnerability in the template watcher dev tool.

---

## 🔴 Critical Issues

### 1. Command Injection via `shell=True`

**Location**: `bengal/autodoc/cli_dev_tools.py:385`

**Severity**: 🔴 **CRITICAL**

**Description**: User-provided command is passed directly to `subprocess.run()` with `shell=True`, allowing arbitrary command execution.

```python
# VULNERABLE CODE
def run_command(changed_files):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
```

**Attack Vector**: 
```bash
bengal template-dev watch --command "echo hello; rm -rf /"
```

**Impact**: Full system compromise. Attacker can execute arbitrary shell commands with the privileges of the Bengal process.

**Fix**: 
```python
# Option 1: Reject shell metacharacters
import shlex
if any(c in command for c in ['|', ';', '&', '$', '`', '(', ')', '<', '>']):
    raise click.ClickException("Command contains shell metacharacters. Use a script file instead.")

# Option 2: Use shell=False with shlex.split()
result = subprocess.run(shlex.split(command), capture_output=True, text=True)
```

**Priority**: P0 - Fix before any public release

---

### 2. Recursive Include Directive Stack Overflow

**Location**: `bengal/rendering/plugins/directives/include.py`

**Severity**: 🔴 **CRITICAL**

**Description**: The include directive recursively parses included content as markdown, which can contain more include directives. No depth limit or cycle detection exists.

**Attack Vector**: Create two files that include each other:

```markdown
<!-- a.md -->
```{include} b.md
```

<!-- b.md -->
```{include} a.md
```
```

**Impact**: Stack overflow, process crash, denial of service during site build.

**Fix**:
```python
class IncludeDirective(DirectivePlugin):
    MAX_INCLUDE_DEPTH = 10
    
    def parse(self, block: BlockParser, m: Match, state: BlockState) -> dict[str, Any]:
        # Track include depth
        current_depth = getattr(state, '_include_depth', 0)
        if current_depth >= self.MAX_INCLUDE_DEPTH:
            logger.warning("include_max_depth_exceeded", depth=current_depth)
            return {
                "type": "include",
                "attrs": {"error": f"Maximum include depth ({self.MAX_INCLUDE_DEPTH}) exceeded"},
                "children": [],
            }
        
        # Track included files to detect cycles
        included_files = getattr(state, '_included_files', set())
        resolved_path = self._resolve_path(path, state)
        if resolved_path:
            canonical = str(resolved_path.resolve())
            if canonical in included_files:
                logger.warning("include_cycle_detected", path=path)
                return {
                    "type": "include",
                    "attrs": {"error": f"Include cycle detected: {path}"},
                    "children": [],
                }
            included_files.add(canonical)
            state._included_files = included_files
        
        state._include_depth = current_depth + 1
        # ... rest of parse
```

**Priority**: P0 - Fix before any public release

---

## 🟠 Medium Issues

### 3. Link Validator is a No-Op

**Location**: `bengal/rendering/link_validator.py:119-129`

**Severity**: 🟠 **MEDIUM**

**Description**: The `_is_valid_link()` method always returns `True` for internal links. The documentation claims broken link detection, but it's not actually implemented.

```python
# CURRENT CODE - Always returns True!
def _is_valid_link(self, link: str, page: Page) -> bool:
    # ... skips external links ...
    
    # For now, assume internal links are valid
    # A full implementation would need to:
    # 1. Resolve the link relative to the page
    # 2. Check if the target file exists in the output
    # 3. Handle anchors (#sections)
    return True  # <-- BUG: No validation happens
```

**Impact**: Broken internal links won't be detected during build, leading to 404s in production.

**Fix**: Implement actual link resolution and validation:
```python
def _is_valid_link(self, link: str, page: Page) -> bool:
    # ... external link handling ...
    
    # Resolve the link relative to the page
    from urllib.parse import urlparse, urljoin
    parsed = urlparse(link)
    
    # Strip fragment
    path = parsed.path
    if not path:
        return True  # Fragment-only link
    
    # Resolve relative to page URL
    resolved = urljoin(page.url, path)
    
    # Check if target exists in site pages
    target_exists = any(
        p.url == resolved or p.url == resolved.rstrip('/') + '/'
        for p in self._site.pages
    )
    
    return target_exists
```

**Priority**: P1 - Important for documentation quality

---

### 4. No File Size Limit on Include/Literalinclude

**Location**: `bengal/rendering/plugins/directives/include.py:205`, `literalinclude.py:277`

**Severity**: 🟠 **MEDIUM**

**Description**: Include directives read entire files into memory without size limits.

**Attack Vector**: Include a very large file (e.g., a 1GB log file in the site directory):
```markdown
```{include} huge-file.log
```
```

**Impact**: Memory exhaustion, OOM kill, denial of service during build.

**Fix**:
```python
MAX_INCLUDE_SIZE = 10 * 1024 * 1024  # 10 MB

def _load_file(self, file_path: Path, ...) -> str | None:
    try:
        file_size = file_path.stat().st_size
        if file_size > MAX_INCLUDE_SIZE:
            logger.warning(
                "include_file_too_large",
                path=str(file_path),
                size=file_size,
                limit=MAX_INCLUDE_SIZE
            )
            return None
        # ... rest of loading
```

**Priority**: P1 - Should fix before users have large sites

---

### 5. Symlink Path Traversal Edge Case

**Location**: `bengal/rendering/plugins/directives/include.py:181-188`

**Severity**: 🟠 **MEDIUM**

**Description**: Path traversal check uses `.resolve()` which follows symlinks. A symlink inside the site root pointing outside could bypass the containment check.

**Attack Vector**:
```bash
# Create symlink inside content pointing outside
ln -s /etc/passwd content/etc-passwd-link

# Then include it
```{include} etc-passwd-link
```
```

**Current Code**:
```python
# Check happens AFTER resolve() follows symlinks
file_path.resolve().relative_to(root_path.resolve())
```

The `.resolve()` follows the symlink, and if the symlink target happens to be under a path that's a prefix of `root_path.resolve()`, it could pass.

**Fix**:
```python
def _resolve_path(self, path: str, state: BlockState) -> Path | None:
    # ... existing path construction ...
    
    # Check the path BEFORE following symlinks
    if file_path.is_symlink():
        logger.warning("include_symlink_rejected", path=str(file_path))
        return None
    
    # Then check the resolved path is within site root
    try:
        file_path.resolve().relative_to(root_path.resolve())
    except ValueError:
        logger.warning("include_outside_site_root", path=str(file_path))
        return None
    
    return file_path
```

**Priority**: P1 - Security hardening

---

## 🟡 Low/Informational Issues

### 6. Theme Install Package Name From User Input

**Location**: `bengal/cli/commands/theme.py:583`

**Severity**: 🟡 **LOW**

**Description**: Package name in `pip install` comes from user input, though it's prefixed with `bengal-theme-`.

```python
pkg = f"bengal-theme-{name}"
cmd = [sys.executable, "-m", "pip", "install", pkg]
subprocess.run(cmd, ...)
```

**Mitigating Factors**:
- Uses `shell=False` (safe)
- pip/uv have their own validation
- Package name is prefixed

**Recommendation**: Add package name validation:
```python
import re
if not re.match(r'^[a-z0-9][a-z0-9\-]*$', name):
    raise click.ClickException("Invalid theme name. Use lowercase letters, numbers, and hyphens.")
```

**Priority**: P2 - Defense in depth

---

### 7. Variable Substitution Has Limited Sandboxing

**Location**: `bengal/rendering/plugins/variable_substitution.py:210-238`

**Severity**: 🟡 **LOW**

**Description**: The `_eval_expression()` method uses `getattr()` to traverse object paths. While it doesn't use `eval()`, it could potentially access unintended attributes.

**Current Safeguards**:
- Only allows dot notation
- Filters Jinja2 syntax (|, {%, etc.)
- Returns placeholder on error (fails safe)

**Potential Concern**: Access to internal methods via `{{ page.__class__.__name__ }}` or similar.

**Recommendation**: Add attribute name filtering:
```python
FORBIDDEN_ATTRS = {'__class__', '__dict__', '__module__', '__builtins__'}

def _eval_expression(self, expr: str) -> Any:
    parts = expr.split(".")
    for part in parts:
        if part.startswith('_') or part in self.FORBIDDEN_ATTRS:
            raise ValueError(f"Access to private/forbidden attribute: {part}")
    # ... rest of evaluation
```

**Priority**: P3 - Security hardening

---

### 8. Asset Pipeline External Commands

**Location**: `bengal/assets/pipeline.py:251`

**Severity**: 🟡 **LOW**

**Description**: The asset pipeline runs external commands (sass, postcss, esbuild) but constructs command arrays safely.

**Current Code** (SAFE):
```python
def _run(self, cmd: list[str], cwd: Path) -> None:
    # Uses list[str] not string with shell=True
    proc = subprocess.run(cmd, check=False, cwd=str(cwd), capture_output=True, text=True)
```

**Status**: ✅ **No immediate fix needed** - already uses safe subprocess pattern.

**Priority**: N/A - Informational

---

### 9. No Timeout on File Operations

**Location**: Various file I/O operations

**Severity**: 🟡 **LOW**

**Description**: File read operations don't have timeouts. On network filesystems or slow storage, this could cause hangs.

**Recommendation**: Consider adding timeouts for build operations, especially in the dev server.

**Priority**: P3 - Nice to have

---

## ✅ What's Already Secure

1. **YAML Parsing**: Uses `yaml.safe_load()` - ✅ No arbitrary code execution
2. **Template Rendering**: Jinja2 autoescape enabled - ✅ XSS protection
3. **JSON Parsing**: Standard `json.loads()` - ✅ Safe
4. **Frontmatter**: Uses python-frontmatter with safe_load - ✅ Safe
5. **Path Traversal in Include**: Basic protection exists - ⚠️ Needs symlink hardening
6. **Configuration Validation**: Type checking and range validation - ✅ Good

---

## Action Items by Priority

### P0 - Must Fix Before Release
- [ ] Fix command injection in `cli_dev_tools.py:385`
- [ ] Add recursion guard to include directive

### P1 - Should Fix Before Release
- [ ] Implement actual link validation
- [ ] Add file size limits to include directives
- [ ] Harden symlink handling in include directives

### P2 - Fix Soon After Release
- [ ] Validate theme names in install command
- [ ] Add attribute filtering to variable substitution

### P3 - Nice to Have
- [ ] Add timeouts to file operations
- [ ] Consider ReDoS analysis of regex patterns

---

## Testing Recommendations

Create test cases for:

1. **Recursive include detection**:
   ```python
   def test_include_cycle_detection(tmp_path):
       # Create a.md that includes b.md
       # Create b.md that includes a.md
       # Assert build fails gracefully with cycle error
   ```

2. **Include depth limit**:
   ```python
   def test_include_max_depth(tmp_path):
       # Create 20 files that include each other in a chain
       # Assert build stops at MAX_INCLUDE_DEPTH
   ```

3. **Symlink rejection**:
   ```python
   def test_include_rejects_symlinks(tmp_path):
       # Create symlink pointing outside site root
       # Assert include returns error
   ```

4. **Large file rejection**:
   ```python
   def test_include_rejects_large_files(tmp_path):
       # Create file > MAX_INCLUDE_SIZE
       # Assert include returns error
   ```

---

## Conclusion

Bengal has a solid security foundation with safe YAML parsing, proper template escaping, and mostly safe subprocess usage. However, the **command injection vulnerability** and **recursive include issue** are critical and must be fixed before public release.

The codebase shows good security awareness in most areas, but the issues found are the kind that slip through without adversarial testing. After fixing these issues, Bengal will be much more robust for general use.

