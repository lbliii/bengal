# RFC: Docker Distribution

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2024-12-03  
**Priority**: P2 (Medium)  
**Subsystems**: `cli`, `distribution`, `dev-server`

---

## Summary

Provide official Docker images for Bengal to dramatically lower the barrier to entry for users who are:
- New to Python
- Intimidated by Python 3.14t (free-threaded variant)
- Unfamiliar with virtual environments
- Want to try Bengal without committing to a local install

**Key Innovation**: Leverage Bengal's existing content layer (`github_loader`) to enable "zero-volume" builds - users can build documentation directly from a GitHub repo without any local files.

---

## Motivation

### Problem

Bengal's optimal performance requires Python 3.14t (free-threaded), which creates significant friction:

1. **Python 3.14t is bleeding edge** - Not available via standard package managers
2. **Virtual environments are confusing** - New users struggle with venv, activation, PATH
3. **Environment variables** - `PYTHON_GIL=0` requirement adds another step
4. **Platform differences** - Install process varies across macOS, Linux, Windows

### User Friction Audit

| Step | Friction Level | Drop-off Risk |
|------|---------------|---------------|
| Install Python 3.14t | 🔴 High | Many users stop here |
| Create virtual environment | 🟡 Medium | Confusing for non-Python devs |
| Activate venv | 🟡 Medium | Easy to forget |
| Set `PYTHON_GIL=0` | 🟡 Medium | Non-obvious requirement |
| `pip install bengal` | 🟢 Low | Standard |
| Run `bengal serve` | 🟢 Low | Standard |

**Total steps**: 6  
**High-friction steps**: 4

### With Docker

| Step | Friction Level |
|------|---------------|
| `docker run ...` | 🟢 Low |

**Total steps**: 1

### Industry Precedent

| SSG | Official Docker | Downloads |
|-----|-----------------|-----------|
| Hugo | ✅ `klakegg/hugo` | 100M+ |
| Jekyll | ✅ `jekyll/jekyll` | 50M+ |
| Sphinx | ✅ `sphinxdoc/sphinx` | 10M+ |
| MkDocs | ❌ Community only | - |

Docker images significantly expand user reach, especially for:
- CI/CD pipelines
- Quick evaluation ("try before you buy")
- Teams with mixed tech stacks
- Education/workshops

---

## Proposal

### Image Variants

```
ghcr.io/bengal/bengal:latest        # Python 3.14t (recommended)
ghcr.io/bengal/bengal:3.14t         # Explicit free-threaded tag
ghcr.io/bengal/bengal:3.12          # Standard Python (fallback)
ghcr.io/bengal/bengal:<version>     # Specific Bengal version
```

### Quick Start Usage

#### Build a Site

```bash
# Build site in current directory
docker run --rm -v $(pwd):/site ghcr.io/bengal/bengal build

# Specify output directory
docker run --rm -v $(pwd):/site ghcr.io/bengal/bengal build --output /site/dist
```

#### Dev Server with Live Reload

```bash
# Start dev server (auto-detects polling mode)
docker run --rm -p 8000:8000 -v $(pwd):/site ghcr.io/bengal/bengal serve

# Explicit polling interval (ms)
docker run --rm -p 8000:8000 -v $(pwd):/site \
  -e BENGAL_WATCH_POLL=500 \
  ghcr.io/bengal/bengal serve
```

#### Docker Compose (Recommended for Dev)

```yaml
# docker-compose.yml
services:
  bengal:
    image: ghcr.io/bengal/bengal:latest
    ports:
      - "8000:8000"
    volumes:
      - .:/site:cached  # :cached improves macOS performance
    command: serve --host 0.0.0.0
```

```bash
# Start with:
docker compose up

# Build with:
docker compose run --rm bengal build
```

### Live Reload Strategy

**Challenge**: File system events (inotify) don't propagate reliably from host to container on macOS/Windows.

**Solution**: Auto-detect container environment and switch to polling mode.

```python
# bengal/server/watcher.py

def get_watch_mode() -> str:
    """Determine optimal file watching strategy."""
    # Explicit override
    if poll_interval := os.environ.get("BENGAL_WATCH_POLL"):
        return "poll"

    # Container detection
    if _is_in_container():
        return "poll"

    # Native mode (Linux with native mounts, or local dev)
    return "native"

def _is_in_container() -> bool:
    """Detect if running inside Docker/Podman."""
    return (
        Path("/.dockerenv").exists() or
        Path("/run/.containerenv").exists() or
        os.environ.get("BENGAL_DOCKER") == "1"
    )
```

**Polling Performance**:

| Interval | CPU Impact | Latency | Use Case |
|----------|-----------|---------|----------|
| 100ms | Higher | ~100ms | Demos, presentations |
| 500ms | Low | ~500ms | **Default** - normal dev |
| 1000ms | Minimal | ~1s | Large sites, CI |

### Dockerfile

```dockerfile
# Dockerfile
ARG PYTHON_VERSION=3.14-rc

FROM python:${PYTHON_VERSION}-slim AS base

# Labels for GitHub Container Registry
LABEL org.opencontainers.image.source="https://github.com/you/bengal"
LABEL org.opencontainers.image.description="Bengal Static Site Generator"
LABEL org.opencontainers.image.licenses="MIT"

# Install Bengal
RUN pip install --no-cache-dir bengal

# Container-aware defaults
ENV BENGAL_DOCKER=1
ENV BENGAL_WATCH_POLL=500
ENV BENGAL_HOST=0.0.0.0
ENV PYTHON_GIL=0

# Working directory is the site root
WORKDIR /site

# Expose dev server port
EXPOSE 8000

# Default command
ENTRYPOINT ["bengal"]
CMD ["--help"]

# -------------------------------------------------------------------
# Free-threaded variant (for maximum performance)
# -------------------------------------------------------------------
FROM python:3.14-rc-slim AS free-threaded

# Same as above but with explicit free-threading
ENV PYTHON_GIL=0

# ... (same as base)
```

### Multi-Architecture Support

Build for both `amd64` and `arm64` (Apple Silicon):

```yaml
# .github/workflows/docker-publish.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ghcr.io/bengal/bengal:latest
            ghcr.io/bengal/bengal:${{ github.ref_name }}
```

---

## Implementation

### Phase 1: Basic Docker Image

**Files**:
- `Dockerfile` - Multi-stage build
- `.dockerignore` - Exclude unnecessary files
- `docker-compose.yml` - Example compose file

**Tasks**:
- [ ] Create Dockerfile with Python 3.14t base
- [ ] Add container detection to dev server
- [ ] Implement polling-mode file watcher
- [ ] Test on macOS (Docker Desktop)
- [ ] Test on Linux (native Docker)
- [ ] Test on Windows (WSL2 + Docker Desktop)

### Phase 2: CI/CD Publishing

**Files**:
- `.github/workflows/docker-publish.yml`

**Tasks**:
- [ ] GitHub Actions workflow for building images
- [ ] Multi-arch builds (amd64, arm64)
- [ ] Push to GitHub Container Registry
- [ ] Tag with version numbers
- [ ] Automated builds on release

### Phase 3: Documentation & UX

**Files**:
- `site/content/docs/getting-started/docker.md`
- `site/content/docs/guides/docker-development.md`
- `README.md` (update Quick Start section)

**Tasks**:
- [ ] Docker quick start guide
- [ ] Docker Compose examples
- [ ] CI/CD integration examples (GitHub Actions, GitLab CI)
- [ ] Troubleshooting guide (common issues)

### Phase 4: Optimization

**Tasks**:
- [ ] Slim image variant (smaller download)
- [ ] Pre-built theme assets in image
- [ ] Build cache volume for faster rebuilds
- [ ] Health check endpoint for orchestration

---

## Remote Content Mode (Content Layer Integration)

Bengal's content layer already supports `github_loader`, enabling a powerful "zero-volume" Docker pattern:

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │   Bengal    │───▶│ Content Layer │───▶│  GitHub   │  │
│  │   CLI       │    │ github_loader │    │   API     │  │
│  └─────────────┘    └──────────────┘    └───────────┘  │
│         │                                               │
│         ▼                                               │
│  ┌─────────────┐                                        │
│  │   Output    │ ──▶ (volume mount or artifact upload)  │
│  │   public/   │                                        │
│  └─────────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

### Zero-Volume Build from GitHub

```bash
# Build directly from a GitHub repo - no local files needed!
docker run --rm \
  -e BENGAL_CONTENT_REPO=myorg/my-docs \
  -e BENGAL_CONTENT_BRANCH=main \
  -e BENGAL_CONTENT_PATH=docs \
  -v $(pwd)/output:/site/public \
  ghcr.io/bengal/bengal build

# With private repo
docker run --rm \
  -e BENGAL_CONTENT_REPO=myorg/private-docs \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -v $(pwd)/output:/site/public \
  ghcr.io/bengal/bengal build
```

### Config-as-Environment Pattern

```bash
# Complete site definition via env vars
docker run --rm \
  -e BENGAL_SITE_TITLE="My Documentation" \
  -e BENGAL_SITE_BASEURL="/docs" \
  -e BENGAL_CONTENT_REPO=myorg/api-docs \
  -e BENGAL_CONTENT_PATH=content \
  -e BENGAL_THEME=default \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -v $(pwd)/output:/site/public \
  ghcr.io/bengal/bengal build
```

### Implementation

```python
# bengal/config/env_loader.py (new)
"""Load site configuration from environment variables."""

import os
from bengal.content_layer import github_loader

def create_env_config() -> dict:
    """
    Create site config from BENGAL_* environment variables.

    Environment Variables:
        BENGAL_SITE_TITLE: Site title
        BENGAL_SITE_BASEURL: Base URL
        BENGAL_CONTENT_REPO: GitHub repo (owner/repo)
        BENGAL_CONTENT_BRANCH: Branch (default: main)
        BENGAL_CONTENT_PATH: Path within repo (default: "")
        BENGAL_THEME: Theme name (default: "default")
        GITHUB_TOKEN: GitHub token for private repos
    """
    config = {}

    # Site config
    if title := os.environ.get("BENGAL_SITE_TITLE"):
        config.setdefault("site", {})["title"] = title
    if baseurl := os.environ.get("BENGAL_SITE_BASEURL"):
        config.setdefault("site", {})["baseurl"] = baseurl

    # Content source
    if repo := os.environ.get("BENGAL_CONTENT_REPO"):
        branch = os.environ.get("BENGAL_CONTENT_BRANCH", "main")
        path = os.environ.get("BENGAL_CONTENT_PATH", "")

        config["content_source"] = {
            "type": "github",
            "repo": repo,
            "branch": branch,
            "path": path,
        }

    # Theme
    if theme := os.environ.get("BENGAL_THEME"):
        config["theme"] = theme

    return config
```

### Dockerfile Update for Remote Content

```dockerfile
# Support both local and remote content modes

# Default: local mode (expects volume mount)
# Remote: set BENGAL_CONTENT_REPO env var

COPY docker-entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["--help"]
```

```bash
#!/bin/bash
# docker-entrypoint.sh

# If BENGAL_CONTENT_REPO is set, create a minimal site config
if [ -n "$BENGAL_CONTENT_REPO" ]; then
    # Generate bengal.toml from env vars
    python -c "
from bengal.config.env_loader import create_env_config
import toml
config = create_env_config()
with open('/site/bengal.toml', 'w') as f:
    toml.dump(config, f)
"
fi

exec bengal "$@"
```

### Use Case: Serverless Documentation Builds

```yaml
# Netlify/Vercel function that builds docs on-demand
# No source code in the function - just pulls from GitHub

FROM ghcr.io/bengal/bengal:latest

ENV BENGAL_CONTENT_REPO=myorg/docs
ENV BENGAL_CONTENT_BRANCH=main
ENV GITHUB_TOKEN=${GITHUB_TOKEN}

CMD ["build", "--output", "/output"]
```

### Use Case: Multi-Repo Documentation Aggregation

```python
# collections.py - Aggregate docs from multiple repos
from bengal.content_layer import github_loader, local_loader

collections = {
    # Local content
    "guides": define_collection(
        schema=Guide,
        loader=local_loader("content/guides"),
    ),

    # API docs from another repo
    "api": define_collection(
        schema=APIDoc,
        loader=github_loader(
            repo="myorg/api",
            path="docs/api",
        ),
    ),

    # SDK docs from SDK repo
    "sdk": define_collection(
        schema=SDKDoc,
        loader=github_loader(
            repo="myorg/sdk-python",
            path="docs",
        ),
    ),
}
```

### Caching for Remote Content

```bash
# Cache remote content between builds
docker run --rm \
  -e BENGAL_CONTENT_REPO=myorg/docs \
  -v bengal-cache:/root/.cache/bengal \
  -v $(pwd)/output:/site/public \
  ghcr.io/bengal/bengal build

# Bengal uses ETag/Last-Modified headers to skip unchanged content
```

---

## Use Cases

### 1. Quick Evaluation ("Try Before Install")

```bash
# Option A: Clone example site and run
git clone https://github.com/bengal/example-site
cd example-site
docker run --rm -p 8000:8000 -v $(pwd):/site ghcr.io/bengal/bengal serve

# Option B: Zero-clone! Build directly from GitHub
docker run --rm \
  -e BENGAL_CONTENT_REPO=bengal/example-site \
  -v $(pwd)/output:/site/public \
  ghcr.io/bengal/bengal build
# Output appears in ./output/ - no git clone needed!
```

### 2. CI/CD Pipeline

```yaml
# .github/workflows/docs.yml
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/bengal/bengal:latest
    steps:
      - uses: actions/checkout@v4
      - run: bengal build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: public/
```

### 3. Workshop/Tutorial Environment

```bash
# Instructor provides single command:
docker run --rm -p 8000:8000 -v $(pwd):/site ghcr.io/bengal/bengal serve

# All attendees have identical environment regardless of:
# - macOS vs Linux vs Windows
# - Python version installed (or not)
# - Virtual environment confusion
```

### 4. Team with Mixed Tech Stack

```yaml
# docker-compose.yml (part of project)
services:
  docs:
    image: ghcr.io/bengal/bengal:latest
    volumes:
      - ./docs:/site
    command: build

  frontend:
    image: node:20
    # ...

  backend:
    image: python:3.12
    # ...
```

### 5. Air-Gapped/Offline Environments

```bash
# Pre-pull image
docker pull ghcr.io/bengal/bengal:latest
docker save ghcr.io/bengal/bengal:latest > bengal-image.tar

# Transfer to offline machine, then:
docker load < bengal-image.tar
docker run --rm -v $(pwd):/site ghcr.io/bengal/bengal build
```

---

## Alternatives Considered

### 1. pipx / uv tool

```bash
pipx install bengal
# or
uv tool install bengal
```

**Pros**: Native performance, no container overhead  
**Cons**: Still requires Python, doesn't solve 3.14t availability

**Verdict**: Complementary - document both options for different audiences.

### 2. Pre-built Binaries (PyInstaller/Nuitka)

Create standalone executables that bundle Python.

**Pros**: True zero-dependency  
**Cons**:
- Python 3.14t support in these tools is uncertain
- Large binary size (~50-100MB)
- Platform-specific builds needed
- Harder to update

**Verdict**: Consider for v2, but Docker provides faster path to users.

### 3. Homebrew Formula

```bash
brew install bengal
```

**Pros**: Great UX for macOS/Linux users  
**Cons**:
- macOS/Linux only
- Maintaining formula is ongoing work
- Still need to solve Python 3.14t dependency

**Verdict**: Worth doing later, but Docker first for broader reach.

### 4. GitHub Codespaces Template

Zero-install browser-based development.

**Pros**: Literally zero install  
**Cons**: Requires GitHub account, cloud-only, costs money for heavy use

**Verdict**: Excellent addition - create a template repo with devcontainer.json.

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_container_detection.py

def test_container_detection_docker():
    """Detect Docker container via /.dockerenv."""
    with patch("pathlib.Path.exists", return_value=True):
        assert _is_in_container() is True

def test_container_detection_env_var():
    """Detect container via BENGAL_DOCKER env var."""
    with patch.dict(os.environ, {"BENGAL_DOCKER": "1"}):
        assert _is_in_container() is True

def test_watch_mode_auto_poll_in_container():
    """Auto-switch to polling in container."""
    with patch("bengal.server.watcher._is_in_container", return_value=True):
        assert get_watch_mode() == "poll"
```

### Integration Tests

```python
# tests/integration/test_docker_build.py (run in CI)

def test_docker_build_produces_output():
    """Docker image can build a site."""
    result = subprocess.run([
        "docker", "run", "--rm",
        "-v", f"{TEST_SITE}:/site",
        "ghcr.io/bengal/bengal:latest",
        "build"
    ], capture_output=True)
    assert result.returncode == 0
    assert (TEST_SITE / "public/index.html").exists()
```

### Manual Testing Matrix

| Platform | Docker Runtime | Status |
|----------|---------------|--------|
| macOS (Intel) | Docker Desktop | ⬜ |
| macOS (Apple Silicon) | Docker Desktop | ⬜ |
| Linux (amd64) | Native Docker | ⬜ |
| Linux (arm64) | Native Docker | ⬜ |
| Windows | WSL2 + Docker Desktop | ⬜ |
| Windows | Docker Desktop (Hyper-V) | ⬜ |

---

## Rollout Plan

### Phase 1: Internal Testing (Week 1)
- [ ] Build Dockerfile locally
- [ ] Test on all platforms
- [ ] Benchmark build times vs native

### Phase 2: Beta Release (Week 2)
- [ ] Publish to GHCR with `beta` tag
- [ ] Document known limitations
- [ ] Gather feedback from early adopters

### Phase 3: Documentation (Week 3)
- [ ] Docker quick start in README
- [ ] Dedicated Docker guide in docs
- [ ] CI/CD examples

### Phase 4: Stable Release (Week 4)
- [ ] Publish `latest` tag
- [ ] Announce in release notes
- [ ] Add to main installation docs

---

## Success Criteria

- [ ] Single `docker run` command builds a site
- [ ] Dev server works with live reload on macOS/Windows (via polling)
- [ ] Multi-arch images (amd64 + arm64) published to GHCR
- [ ] Image size under 200MB
- [ ] Build performance within 20% of native Python 3.14t
- [ ] Documentation covers common use cases
- [ ] CI/CD examples for GitHub Actions, GitLab CI
- [ ] **Remote content mode**: Build from GitHub repo via `BENGAL_CONTENT_REPO` env var
- [ ] **Zero-volume builds**: Complete site generation without local volume mounts

---

## Open Questions

### 1. Image Registry

**Options**:
- GitHub Container Registry (ghcr.io) - ✅ Recommended
- Docker Hub - Requires separate account, rate limits
- Both - More maintenance

**Recommendation**: Start with GHCR only, add Docker Hub later if demand exists.

### 2. Python Version Strategy

**Options**:
- Only 3.14t (simplest, fastest)
- 3.14t + 3.12 fallback (broader compatibility)
- Multiple versions (most flexible, most maintenance)

**Recommendation**: Ship 3.14t as default with 3.12 fallback tag.

### 3. Image Size vs Features

**Options**:
- Slim image (~150MB) - Bengal only
- Full image (~300MB) - Bengal + common tools (git, curl, jq)

**Recommendation**: Start slim, add `bengal:full` variant if requested.

### 4. Default Command

**Options**:
- `bengal --help` (current) - Shows help, user adds command
- `bengal build` - Assumes build intent
- `bengal serve` - Assumes dev intent

**Recommendation**: `--help` is safest default, prevents accidental operations.

### 5. Volume Permissions

Docker volumes can have permission issues on Linux.

**Options**:
- Document workaround (`--user $(id -u):$(id -g)`)
- Add entrypoint script that fixes permissions
- Use rootless containers

**Recommendation**: Document the `--user` flag, investigate entrypoint script.

### 6. Remote Content Mode - Theme Handling

When building from a remote repo, where do themes come from?

**Options**:
- Default theme bundled in image (simplest)
- Theme specified by repo's `bengal.toml` (fetched with content)
- Theme from separate GitHub repo via `BENGAL_THEME_REPO`
- Theme URL pointing to a tarball

**Recommendation**:
1. Bundle default theme in image
2. Support `BENGAL_THEME_REPO` for custom themes
3. Future: Theme registry/CDN

### 7. Remote Content Mode - Dev Server

Can we support live reload for remote content?

**Options**:
- Polling GitHub API for changes (rate limits, latency)
- GitHub webhooks (requires callback URL)
- No dev server for remote mode (build-only)

**Recommendation**: Start with build-only for remote mode. Dev server requires local volume mount. Document this clearly.

---

## Performance Considerations

### Expected Overhead

| Operation | Native | Docker | Overhead |
|-----------|--------|--------|----------|
| Cold start | 0ms | ~500ms | Container init |
| File read | ~1ms | ~2ms | Volume I/O |
| Build (100 pages) | ~2s | ~2.5s | ~25% |
| Watch (polling) | ~10ms | ~500ms | Polling interval |

**Note**: Overhead is acceptable for the UX benefit. Power users can install natively.

### Optimization Opportunities

1. **BuildKit caching** - Cache pip packages between builds
2. **Volume caching** - `:cached` flag on macOS
3. **Pre-built assets** - Include compiled theme in image
4. **Multi-stage build** - Smaller final image

---

## Security Considerations

1. **Non-root user** - Run Bengal as non-root inside container
2. **Read-only filesystem** - Consider `--read-only` for build-only operations
3. **No network by default** - `--network=none` for builds (optional)
4. **Minimal base image** - Use slim variant, fewer CVEs

---

## References

- [Docker Official Images Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Hugo Docker Workflow](https://gohugo.io/getting-started/installing/#docker)
- [Jekyll Docker](https://github.com/envygeeks/jekyll-docker)
- [GitHub Container Registry Docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Multi-platform Docker Builds](https://docs.docker.com/build/building/multi-platform/)
