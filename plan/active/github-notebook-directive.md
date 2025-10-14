# GitHub Notebook Directive

## Concept

Fetch and render notebooks directly from GitHub repos:

```markdown
\```{github-notebook} user/repo/path/to/notebook.ipynb
:ref: main
:hide-prompts: true
\```
```

## Implementation

### Simple Version (2 hours)

```python
# bengal/rendering/plugins/directives/github_notebook.py
from mistune.directives import DirectivePlugin
import requests
from pathlib import Path
import hashlib

class GitHubNotebookDirective(DirectivePlugin):
    """
    Fetch and render notebooks from GitHub.

    Syntax:
        ```{github-notebook} owner/repo/path/to/file.ipynb
        :ref: main
        :hide-prompts: true
        :cache: true
        ```

    Features:
    - Fetches from GitHub raw content API
    - Caches locally to avoid rate limits
    - Same rendering options as local notebooks
    """

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(".bengal-cache/github-notebooks")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, block, m, state):
        # Parse: "owner/repo/path/to/file.ipynb"
        github_path = self.parse_title(m)
        options = self.parse_options(m)

        ref = options.get('ref', 'main')
        use_cache = options.get('cache', 'true') == 'true'

        # Fetch notebook
        notebook_html = self._fetch_and_render(
            github_path,
            ref,
            use_cache=use_cache,
            hide_prompts=options.get('hide-prompts') == 'true'
        )

        return {
            "type": "github_notebook",
            "attrs": {
                "html": notebook_html,
                "source": f"https://github.com/{github_path}",
            }
        }

    def _fetch_and_render(self, github_path: str, ref: str, use_cache: bool, hide_prompts: bool) -> str:
        """Fetch notebook from GitHub and render to HTML."""
        # Parse: "owner/repo/path/to/file.ipynb"
        parts = github_path.split('/', 2)
        if len(parts) < 3:
            return f'<div class="error">Invalid GitHub path: {github_path}</div>'

        owner, repo, path = parts

        # Build raw content URL
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"

        # Check cache
        cache_key = hashlib.sha256(f"{url}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.html"

        if use_cache and cache_file.exists():
            # TODO: Add TTL check
            return cache_file.read_text()

        # Fetch from GitHub
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            notebook_json = response.text

            # Convert to HTML
            import nbformat
            from nbconvert import HTMLExporter

            notebook = nbformat.reads(notebook_json, as_version=4)

            html_exporter = HTMLExporter()
            html_exporter.exclude_input_prompt = hide_prompts
            html_exporter.exclude_output_prompt = hide_prompts

            (body, resources) = html_exporter.from_notebook_node(notebook)

            html = f'<div class="github-notebook" data-source="{url}">\n{body}\n</div>'

            # Cache it
            if use_cache:
                cache_file.write_text(html)

            return html

        except Exception as e:
            return f'<div class="notebook-error">Failed to fetch {url}<br>Error: {e}</div>'

    def __call__(self, directive, md):
        directive.register("github-notebook", self.parse)
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("github_notebook", render_github_notebook)


def render_github_notebook(renderer, html: str, source: str) -> str:
    """Render with source attribution."""
    return f'{html}\n<p class="notebook-source"><small>Source: <a href="{source}">{source}</a></small></p>'
```

## Usage

### Basic
```markdown
# Example from scikit-learn

\```{github-notebook} scikit-learn/scikit-learn/examples/linear_model/plot_ols.ipynb
:ref: main
\```
```

### With Options
```markdown
\```{github-notebook} fastai/fastbook/01_intro.ipynb
:ref: master
:hide-prompts: true
:cache: true
\```
```

## Benefits

✅ **Reference canonical examples** - No need to copy notebooks
✅ **Always up-to-date** - Fetch latest from upstream
✅ **Reduced maintenance** - Don't maintain copies
✅ **Attribution** - Link back to source
✅ **Works with any public repo** - Not just yours

## Challenges

⚠️ **Rate limits** - GitHub has API rate limits
  - Solution: Cache aggressively
  - Solution: Fetch during build (not runtime)

⚠️ **Build requires network** - Can't build offline
  - Solution: Cache with long TTL
  - Solution: Optional fallback to cached version

⚠️ **External dependency** - Upstream notebook might break
  - Solution: Pin to specific commit SHA
  - Solution: Cache validated version

## Enhanced Version (4 hours)

Add:
1. **Token support** - Higher rate limits with GitHub token
2. **TTL caching** - Smart cache invalidation
3. **Pin to commit** - `ref: abc123def456` for stability
4. **Private repos** - With token authentication
5. **Offline mode** - Use cache when network unavailable

```python
\```{github-notebook} myorg/private-repo/analysis.ipynb
:ref: v1.2.3
:token: ${GITHUB_TOKEN}
:cache-ttl: 86400
:fallback-to-cache: true
\```
```

## Use Cases

### 1. Reference Canonical Examples
```markdown
# Following the scikit-learn tutorial:

\```{github-notebook} scikit-learn/scikit-learn-tutorials/notebooks/01_intro.ipynb
\```
```

### 2. Multi-Repo Documentation
Your docs repo references notebooks from your main repo:

```
docs-repo/
└── content/
    └── tutorials/
        └── quickstart.md  ← References notebooks from main-repo

main-repo/
└── examples/
    └── quickstart.ipynb  ← Lives here
```

```markdown
\```{github-notebook} myorg/main-repo/examples/quickstart.ipynb
:ref: v2.0.0
\```
```

### 3. Community Examples
```markdown
# Community Examples

Check out this great analysis by @user:

\```{github-notebook} user/awesome-analysis/notebooks/demo.ipynb
\```
```

## Comparison to Alternatives

### nbviewer / GitHub Rendering
- ❌ Separate page (loses context)
- ❌ Different styling
- ✅ No build-time dependency

### Copy notebook locally
- ❌ Maintenance burden (duplicated content)
- ❌ Can get out of sync
- ✅ Guaranteed availability

### GitHub Notebook Directive
- ✅ Embedded in your docs (context preserved)
- ✅ Always up-to-date (or pinned to version)
- ✅ Your styling
- ⚠️ Network dependency at build time (mitigated by caching)

## Recommendation

**Yes, build this!** But as a separate enhancement after local notebook support.

**Priority:**
1. Local notebook directive (core feature)
2. GitHub notebook directive (nice enhancement)

**Why?**
- Same implementation (~90% code reuse)
- Just changes the loading mechanism
- Local notebooks must work first anyway
