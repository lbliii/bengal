"""Tests for environment detection."""

from bengal.config.environment import detect_environment, get_environment_file_candidates


class TestDetectEnvironment:
    """Test detect_environment function."""

    def test_explicit_bengal_env(self, monkeypatch):
        """Test explicit BENGAL_ENV takes priority."""
        monkeypatch.setenv("BENGAL_ENV", "production")

        assert detect_environment() == "production"

    def test_netlify_production(self, monkeypatch):
        """Test Netlify production detection."""
        monkeypatch.setenv("NETLIFY", "true")
        monkeypatch.setenv("CONTEXT", "production")

        assert detect_environment() == "production"

    def test_netlify_preview(self, monkeypatch):
        """Test Netlify preview detection."""
        monkeypatch.setenv("NETLIFY", "true")
        monkeypatch.setenv("CONTEXT", "deploy-preview")

        assert detect_environment() == "preview"

    def test_netlify_branch_deploy(self, monkeypatch):
        """Test Netlify branch deploy as preview."""
        monkeypatch.setenv("NETLIFY", "true")
        monkeypatch.setenv("CONTEXT", "branch-deploy")

        assert detect_environment() == "preview"

    def test_vercel_production(self, monkeypatch):
        """Test Vercel production detection."""
        monkeypatch.setenv("VERCEL", "1")
        monkeypatch.setenv("VERCEL_ENV", "production")

        assert detect_environment() == "production"

    def test_vercel_preview(self, monkeypatch):
        """Test Vercel preview detection."""
        monkeypatch.setenv("VERCEL", "1")
        monkeypatch.setenv("VERCEL_ENV", "preview")

        assert detect_environment() == "preview"

    def test_github_actions(self, monkeypatch):
        """Test GitHub Actions detection (assumes production)."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")

        assert detect_environment() == "production"

    def test_default_local(self, monkeypatch):
        """Test default environment is local."""
        # Clear all env vars
        for key in ["BENGAL_ENV", "NETLIFY", "VERCEL", "GITHUB_ACTIONS"]:
            monkeypatch.delenv(key, raising=False)

        assert detect_environment() == "local"

    def test_bengal_env_overrides_platform(self, monkeypatch):
        """Test BENGAL_ENV overrides platform detection."""
        monkeypatch.setenv("BENGAL_ENV", "local")
        monkeypatch.setenv("NETLIFY", "true")
        monkeypatch.setenv("CONTEXT", "production")

        # BENGAL_ENV takes priority
        assert detect_environment() == "local"

    def test_case_insensitive(self, monkeypatch):
        """Test environment names are normalized to lowercase."""
        monkeypatch.setenv("BENGAL_ENV", "PRODUCTION")

        assert detect_environment() == "production"

    def test_strips_whitespace(self, monkeypatch):
        """Test environment names are stripped."""
        monkeypatch.setenv("BENGAL_ENV", "  production  ")

        assert detect_environment() == "production"


class TestGetEnvironmentFileCandidates:
    """Test get_environment_file_candidates function."""

    def test_production_candidates(self):
        """Test production file candidates."""
        candidates = get_environment_file_candidates("production")

        assert "production.yaml" in candidates
        assert "production.yml" in candidates
        assert "prod.yaml" in candidates
        assert "prod.yml" in candidates

    def test_preview_candidates(self):
        """Test preview file candidates."""
        candidates = get_environment_file_candidates("preview")

        assert "preview.yaml" in candidates
        assert "staging.yaml" in candidates
        assert "stage.yaml" in candidates

    def test_local_candidates(self):
        """Test local file candidates."""
        candidates = get_environment_file_candidates("local")

        assert "local.yaml" in candidates
        assert "dev.yaml" in candidates
        assert "development.yaml" in candidates

    def test_unknown_environment(self):
        """Test unknown environment returns sensible defaults."""
        candidates = get_environment_file_candidates("custom")

        assert "custom.yaml" in candidates
        assert "custom.yml" in candidates

    def test_candidates_order(self):
        """Test candidates are in priority order."""
        candidates = get_environment_file_candidates("production")

        # Primary name should come before aliases
        assert candidates.index("production.yaml") < candidates.index("prod.yaml")
