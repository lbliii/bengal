# RFC: Supply Chain Security Improvements

**Status**: Draft  
**Created**: 2026-01-14  
**Priority**: Low  
**Effort**: Low (~30 minutes)  
**Tracking**: `plan/rfc-supply-chain-security.md`

---

## Executive Summary

Socket.dev currently scores Bengal 75/100 for supply chain security. Two quick wins can improve this score with minimal effort:

1. **Add `SECURITY.md`** — GitHub security policy for responsible disclosure
2. **Enable Dependabot** — Automated dependency vulnerability alerts and updates

**Impact**: These changes signal security maturity to package scanners and provide actual security value through automated monitoring.

---

## Problem Statement

### Current State

| Item | Status | Impact on Score |
|------|--------|-----------------|
| Security policy | ❌ Missing | Medium deduction |
| Dependabot alerts | ❌ Disabled | Low deduction |
| Dependency pinning | ⚠️ Uses `>=` only | Medium deduction |
| Package maturity | ⚠️ Alpha status | Low deduction |

### Socket.dev Scoring Factors

Socket.dev evaluates supply chain security across:

- **Maintenance signals**: Security policy, issue response time, update frequency
- **Dependency hygiene**: Pinned versions, vulnerability monitoring, transitive deps
- **Project maturity**: Download counts, age, stable releases

Adding `SECURITY.md` and Dependabot addresses the first two categories.

---

## Proposed Changes

### 1. Add `SECURITY.md`

GitHub recognizes `SECURITY.md` in the repository root and displays it on the Security tab.

**Location**: `/SECURITY.md`

**Content**:

```markdown
# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅ Yes    |
| < 0.1   | ❌ No     |

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

To report a security issue, please email:

📧 **lbeezr@icloud.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

### Response Timeline

| Stage | Timeline |
|-------|----------|
| Initial acknowledgment | Within 48 hours |
| Status update | Within 7 days |
| Fix timeline provided | Within 14 days |
| Public disclosure | After fix released, coordinated with reporter |

### Scope

This security policy covers:
- The `bengal` Python package (PyPI)
- The Bengal CLI tool
- Build-time code execution (templates, directives, autodoc)
- Generated output security (XSS, injection)

Out of scope:
- User-deployed sites (see [Security Hardening docs](https://github.com/lbliii/bengal/blob/main/site/content/docs/reference/security.md))
- Third-party dependencies (report to respective projects)
- Hosting platform configuration

### Recognition

We appreciate responsible disclosure. Contributors who report valid security issues will be:
- Credited in the security advisory (unless anonymity requested)
- Listed in release notes
- Considered for future beta access to security features

## Security Best Practices

For deploying Bengal sites securely, see our [Security Hardening Guide](https://bengal.dev/docs/reference/security/).
```

**Why This Matters**:
- GitHub displays security policy in the Security tab
- Package scanners detect `SECURITY.md` as a positive signal
- Provides clear channel for responsible disclosure
- Reduces likelihood of public zero-day disclosures

---

### 2. Enable Dependabot

Dependabot provides:
- **Security alerts**: Notifications when dependencies have known CVEs
- **Version updates**: Automated PRs when new versions are available
- **Grouped updates**: Batch related updates to reduce PR noise

**Location**: `/.github/dependabot.yml`

**Content**:

```yaml
# Dependabot configuration
# https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file

version: 2

updates:
  # Python dependencies (PyPI)
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "America/Los_Angeles"
    # Group minor/patch updates to reduce PR noise
    groups:
      python-minor-patch:
        patterns:
          - "*"
        update-types:
          - "minor"
          - "patch"
    # Limit open PRs to avoid overwhelming
    open-pull-requests-limit: 5
    # Add labels for filtering
    labels:
      - "dependencies"
      - "python"
    # Commit message format
    commit-message:
      prefix: "deps"
      include: "scope"
    # Reviewers for security updates
    reviewers:
      - "lbliii"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    groups:
      github-actions:
        patterns:
          - "*"
    labels:
      - "dependencies"
      - "ci"
    commit-message:
      prefix: "ci"
```

**Why This Matters**:
- Automated CVE detection for all dependencies
- Proactive updates before vulnerabilities become critical
- GitHub Security tab integration
- Package scanners detect Dependabot as a positive maintenance signal

---

## Implementation Plan

### Phase 1: Create Files (15 min)

| Task | Output |
|------|--------|
| Create `SECURITY.md` in repo root | Responsible disclosure policy |
| Create `.github/dependabot.yml` | Automated dependency updates |
| Verify files appear in GitHub Security tab | Visual confirmation |

### Phase 2: Enable GitHub Features (5 min)

1. Go to **Settings → Security → Code security and analysis**
2. Enable:
   - ✅ Dependency graph
   - ✅ Dependabot alerts
   - ✅ Dependabot security updates
   - ✅ Dependabot version updates (optional, can use config only)

### Phase 3: Verify (10 min)

```bash
# Verify SECURITY.md renders
open https://github.com/lbliii/bengal/security/policy

# Verify Dependabot config is valid
# (GitHub will show errors if invalid)
open https://github.com/lbliii/bengal/security/dependabot

# Check for any immediate alerts
open https://github.com/lbliii/bengal/security/dependabot
```

---

## Expected Outcomes

### Socket.dev Score Improvement

| Factor | Before | After | Delta |
|--------|--------|-------|-------|
| Security policy | Missing | Present | +5-10 pts |
| Dependency monitoring | None | Dependabot | +3-5 pts |
| **Estimated Total** | 75/100 | ~83-90/100 | +8-15 pts |

*Note: Exact scoring is proprietary. Estimates based on documented factors.*

### Actual Security Benefits

| Benefit | Description |
|---------|-------------|
| CVE alerts | Immediate notification of vulnerable dependencies |
| Coordinated disclosure | Clear channel for security researchers |
| Update visibility | Automated PRs for available updates |
| Audit trail | GitHub Security tab shows security posture |

---

## Files Created

### `/SECURITY.md`

```
SECURITY.md
├── Supported Versions table
├── Reporting instructions (email)
├── Response timeline
├── Scope definition
├── Recognition policy
└── Link to deployment security docs
```

### `/.github/dependabot.yml`

```
.github/dependabot.yml
├── pip ecosystem (weekly Monday)
│   ├── Grouped minor/patch updates
│   ├── 5 PR limit
│   └── deps: commit prefix
└── github-actions ecosystem (weekly Monday)
    ├── Grouped updates
    └── ci: commit prefix
```

---

## Testing

### Validation Checklist

- [ ] `SECURITY.md` renders correctly on GitHub
- [ ] Security tab shows security policy link
- [ ] Dependabot config passes GitHub validation
- [ ] Dependabot alerts enabled in repo settings
- [ ] First Dependabot PR appears within 24 hours (if updates available)

### Manual Verification

```bash
# Verify SECURITY.md is valid markdown
python -c "import markdown; markdown.markdown(open('SECURITY.md').read())"

# Verify dependabot.yml is valid YAML
python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dependabot PR noise | Medium | Low | Grouped updates, 5 PR limit |
| Breaking updates | Low | Medium | CI runs on Dependabot PRs |
| Email spam | Low | Low | Email is already public in pyproject.toml |

---

## Out of Scope

These items would further improve the score but require more effort:

| Item | Effort | Tracked In |
|------|--------|------------|
| Pin dependency upper bounds | Medium | Future RFC |
| Publish 1.0 stable release | High | Roadmap |
| Increase package downloads | Time | Organic growth |
| Add CodeQL scanning | Low | Can add to this RFC if desired |

---

## Future Considerations

### Optional: Add CodeQL Scanning

If desired, add `.github/workflows/codeql.yml`:

```yaml
name: "CodeQL"

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "30 1 * * 1"

jobs:
  analyze:
    name: Analyze
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: python
      - uses: github/codeql-action/analyze@v3
```

This adds static analysis for security vulnerabilities in the codebase itself.

---

## Appendix: Related Documentation

- [GitHub Security Policy docs](https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository)
- [Dependabot configuration options](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
- [Socket.dev scoring methodology](https://docs.socket.dev/docs/package-scores)
- [Existing security docs](site/content/docs/reference/security.md) — User-facing deployment security

---

## Execution Checklist

- [ ] Create `SECURITY.md` in repo root
- [ ] Create `.github/dependabot.yml`
- [ ] Push to main branch
- [ ] Enable Dependabot alerts in GitHub Settings
- [ ] Verify Security tab shows policy
- [ ] Wait 24h for first Dependabot scan
- [ ] Re-check Socket.dev score after 1 week
